from __future__ import annotations

from pathlib import Path

from conllu2vert.cli import main


def token_row(word: str, lemma: str) -> str:
    return "\t".join(["1", word, lemma, "NOUN", "_", "_", "0", "root", "_", "Sense=x"])


def test_cli_converts_all_files_into_one_corpus(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()

    (input_dir / "a.conllu").write_text(
        "\n".join(
            [
                "# text_id = A",
                "# sent_id = A_s1",
                token_row("a", "a"),
                "",
            ]
        ),
        encoding="utf-8",
    )
    (input_dir / "b.conllu").write_text(
        "\n".join(
            [
                "# text_id = B",
                "# sent_id = B_s1",
                token_row("b", "b"),
                "",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--quiet",
        ]
    )

    assert exit_code == 0
    vertical = output_dir / "czerofive.vert"
    registry = output_dir / "czerofive.registry"
    assert vertical.exists()
    assert registry.exists()

    content = vertical.read_text(encoding="utf-8")
    assert content.index('<doc file="A" n="1">') < content.index('<doc file="B" n="2">')
    assert content.count("<doc ") == 2
    assert "a\ta\tNOUN\t_\troot\tx\n" in content
    assert "b\tb\tNOUN\t_\troot\tx\n" in content

    registry_content = registry.read_text(encoding="utf-8")
    assert "ATTRIBUTE word\nATTRIBUTE lemma\nATTRIBUTE tag\n" in registry_content
    assert "ATTRIBUTE feats\nATTRIBUTE deprel\nATTRIBUTE sense\n" in registry_content


def test_cli_can_skip_registry_and_accept_explicit_files(tmp_path: Path) -> None:
    input_file = tmp_path / "one.conllu"
    input_file.write_text(
        "\n".join(
            [
                "# text_id = ONE",
                "# sent_id = one-1",
                token_row("x", "x"),
                "",
            ]
        ),
        encoding="utf-8",
    )
    output = tmp_path / "custom.vert"

    exit_code = main(
        [
            str(input_file),
            "--output",
            str(output),
            "--no-registry",
            "--quiet",
        ]
    )

    assert exit_code == 0
    assert output.exists()
    assert not (tmp_path / "custom.registry").exists()
    assert '<doc file="ONE" n="1">' in output.read_text(encoding="utf-8")


def test_cli_returns_error_for_missing_input_directory(tmp_path: Path, capsys) -> None:
    exit_code = main(["--input-dir", str(tmp_path / "missing"), "--quiet"])

    assert exit_code == 1
    assert "input directory does not exist" in capsys.readouterr().err
