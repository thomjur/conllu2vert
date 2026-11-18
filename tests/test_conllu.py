from __future__ import annotations

from pathlib import Path

import pytest

from conllu2vert.conllu import (
    Document,
    Sentence,
    Stats,
    Token,
    clean_comment_line,
    document_id,
    read_documents,
)


def token_row(
    token_id: str,
    word: str,
    lemma: str,
    tag: str = "NOUN",
    feats: str = "_",
    deprel: str = "root",
    misc: str = "_",
) -> str:
    return "\t".join([token_id, word, lemma, tag, "_", feats, "0", deprel, "_", misc])


def write_file(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "sample.conllu"
    path.write_text(content, encoding="utf-8")
    return path


def test_read_documents_handles_edge_cases(tmp_path: Path) -> None:
    content = "\n".join(
        [
            "# text_id = DOC1",
            "# sent_id = s1",
            token_row("1-2", "foo", "_"),
            token_row("1", "a", "a", feats="Animacy=Inan", misc='"Sense=of ""muhr"" type"'),
            token_row("2", "b", "b", tag="VERB", deprel="dep", misc="Sense=x|Sense=y"),
            token_row("3", "c", "d|e", tag="ADJ", deprel="amod", misc="Sense=z"),
            token_row("4.1", "_", "_"),
            token_row("_", "bad", "bad", tag="X", misc="Sense=bad"),
            "",
            "# text_id = DOC1",
            "# sent_id = s2",
            token_row("1", "q", "q"),
            "",
            "# text_id = DOC2",
            token_row("1", "r", "r"),
            "",
        ]
    )
    path = write_file(tmp_path, content)
    stats = Stats()

    documents = list(read_documents(path, stats=stats))

    assert [document.file for document in documents] == ["sample"]
    assert len(documents[0].sentences) == 3
    assert documents[0].sentences[0].id == "s1"
    assert documents[0].sentences[0].tokens == (
        Token("a", "a", "NOUN", "Animacy=Inan", "root", 'of "muhr" type'),
        Token("b", "b", "VERB", "_", "dep", "x; y"),
        Token("c", "d; e", "ADJ", "_", "amod", "z"),
        Token("bad", "bad", "X", "_", "root", "bad"),
    )
    assert documents[0].sentences[1].tokens[0].word == "q"
    assert documents[0].sentences[2].id == "sample_s3"

    assert stats.documents == 1
    assert stats.sentences == 3
    assert stats.tokens == 6
    assert stats.tokens_without_id == 1
    assert stats.skipped == {
        "multiword_token": 1,
        "empty_node": 1,
    }
    assert stats.missing_sent_ids == 1


def test_read_documents_repairs_quoted_comments(tmp_path: Path) -> None:
    content = "\n".join(
        [
            '"# text_eng = He said ""hi"""',
            "# sent_id = s1",
            token_row("1", "x", "x"),
            "",
        ]
    )
    path = write_file(tmp_path, content)
    stats = Stats()

    documents = list(read_documents(path, stats=stats))

    assert stats.quoted_comments == 1
    assert stats.skipped == {}
    assert stats.tokens == 1
    assert documents[0].file == "sample"
    assert documents[0].sentences[0].id == "s1"


def test_read_documents_generates_missing_ids(tmp_path: Path) -> None:
    path = write_file(
        tmp_path,
        "\n".join([token_row("1", "x", "x"), ""]),
    )
    stats = Stats()

    documents = list(read_documents(path, stats=stats))

    assert documents[0].file == "sample"
    assert documents[0].sentences[0].id == "sample_s1"
    assert stats.missing_sent_ids == 1


def test_comment_continuation_is_ignored(tmp_path: Path) -> None:
    path = write_file(
        tmp_path,
        "\n".join(
            [
                "just a broken comment continuation",
                "# sent_id = s1",
                token_row("1", "x", "x"),
                "",
            ]
        ),
    )
    stats = Stats()

    documents = list(read_documents(path, stats=stats))

    assert stats.skipped["comment_continuation"] == 1
    assert stats.tokens == 1
    assert len(documents[0].sentences) == 1


def test_strict_mode_rejects_malformed_token_rows(tmp_path: Path) -> None:
    path = write_file(tmp_path, "1\tword\tlemma\n")

    with pytest.raises(ValueError, match="wrong_column_count"):
        list(read_documents(path, strict=True))


def test_clean_comment_line_removes_csv_quoting() -> None:
    assert clean_comment_line('"# text = He said ""hi"""\n') == '# text = He said "hi"'


def test_empty_sentences_are_skipped(tmp_path: Path) -> None:
    path = write_file(tmp_path, "\n\n# text_id = D\n\n")
    stats = Stats()

    assert list(read_documents(path, stats=stats)) == []
    assert stats.documents == 0
    assert stats.sentences == 0


def test_document_id_strips_extension_and_suffix() -> None:
    assert document_id("ADM-MK_conllu.tsv") == "ADM-MK"
    assert document_id("Dk5-B_conllu.conllu") == "Dk5-B"
    assert document_id("plain.conllu") == "plain"
    assert document_id("plain.tsv") == "plain"


def test_empty_text_id_does_not_split_documents(tmp_path: Path) -> None:
    content = "\n".join(
        [
            "# text_id = AWN",
            "# sent_id = s1",
            token_row("1", "a", "a"),
            "",
            "# text_id =",
            "# sent_id = s2",
            token_row("1", "b", "b"),
            "",
            "# text_id = AWN",
            "# sent_id = s3",
            token_row("1", "c", "c"),
            "",
        ]
    )
    path = write_file(tmp_path, content)
    stats = Stats()

    documents = list(read_documents(path, stats=stats))

    assert [document.file for document in documents] == ["sample"]
    assert len(documents[0].sentences) == 3
    assert stats.documents == 1
    assert stats.sentences == 3


def test_underscore_token_keeps_its_position(tmp_path: Path) -> None:
    content = "\n".join(
        [
            "# sent_id = s1",
            token_row("1", "a", "a"),
            token_row("_", "ud", "ud", tag="CCONJ"),
            token_row("2", "b", "b"),
            "",
        ]
    )
    path = write_file(tmp_path, content)
    stats = Stats()

    documents = list(read_documents(path, stats=stats))

    assert [token.word for token in documents[0].sentences[0].tokens] == [
        "a",
        "ud",
        "b",
    ]
    assert stats.tokens == 3
    assert stats.tokens_without_id == 1


def test_same_text_id_in_two_files_yields_distinct_documents(tmp_path: Path) -> None:
    content = "\n".join(
        [
            "# text_id = PY",
            "# sent_id = s1",
            token_row("1", "a", "a"),
            "",
        ]
    )
    first = tmp_path / "PY-Pt4_conllu.tsv"
    second = tmp_path / "PYextr-K7a_conllu.tsv"
    first.write_text(content, encoding="utf-8")
    second.write_text(content, encoding="utf-8")

    first_docs = list(read_documents(first))
    second_docs = list(read_documents(second))

    assert [document.file for document in first_docs] == ["PY-Pt4"]
    assert [document.file for document in second_docs] == ["PYextr-K7a"]


def test_sent_id_underscore_is_treated_as_missing(tmp_path: Path) -> None:
    content = "\n".join(
        [
            "# sent_id = _",
            token_row("1", "a", "a"),
            "",
        ]
    )
    path = write_file(tmp_path, content)
    stats = Stats()

    documents = list(read_documents(path, stats=stats))

    assert documents[0].sentences[0].id == "sample_s1"
    assert stats.missing_sent_ids == 1


def test_generated_sent_id_avoids_explicit_ids(tmp_path: Path) -> None:
    content = "\n".join(
        [
            "# sent_id = sample_s2",
            token_row("1", "a", "a"),
            "",
            "# sent_id = _",
            token_row("1", "b", "b"),
            "",
        ]
    )
    path = write_file(tmp_path, content)
    stats = Stats()

    documents = list(read_documents(path, stats=stats))

    assert [sentence.id for sentence in documents[0].sentences] == [
        "sample_s2",
        "sample_s3",
    ]
    assert stats.missing_sent_ids == 1
