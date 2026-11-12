from __future__ import annotations

from io import StringIO

from conllu2vert.conllu import Document, Sentence, Token
from conllu2vert.vertical import VerticalWriter


def make_token(
    word: str = "a",
    lemma: str = "a",
    tag: str = "NOUN",
    feats: str = "_",
    deprel: str = "root",
    sense: str = "x",
) -> Token:
    return Token(word, lemma, tag, feats, deprel, sense)


def test_writer_outputs_documents_and_sentences() -> None:
    document = Document(
        "D1",
        [
            Sentence("s1", (make_token(),)),
            Sentence("s2", (make_token(word="b", lemma="b", sense="_"),)),
        ],
    )
    stream = StringIO()

    VerticalWriter(stream).write_document(document, 1)

    assert stream.getvalue() == (
        '<doc file="D1" n="1">\n'
        '<s id="s1">\n'
        "a\ta\tNOUN\t_\troot\tx\n"
        "</s>\n"
        '<s id="s2">\n'
        "b\tb\tNOUN\t_\troot\t_\n"
        "</s>\n"
        "</doc>\n"
    )


def test_writer_escapes_structure_ids() -> None:
    document = Document('a&"b', [Sentence("s<1>", (make_token(),))])
    stream = StringIO()

    VerticalWriter(stream).write_document(document, 2)

    assert stream.getvalue().startswith(
        '<doc file="a&amp;&quot;b" n="2">\n<s id="s&lt;1&gt;">\n'
    )


def test_writer_skips_empty_documents() -> None:
    stream = StringIO()

    VerticalWriter(stream).write_document(Document("empty"), 1)

    assert stream.getvalue() == ""
