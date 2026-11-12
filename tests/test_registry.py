from __future__ import annotations

from conllu2vert.conllu import ATTRIBUTES
from conllu2vert.registry import RegistryConfig, render_registry


def test_registry_matches_attribute_order() -> None:
    registry = render_registry()

    attribute_lines = [
        line.split(maxsplit=1)[1]
        for line in registry.splitlines()
        if line.startswith("ATTRIBUTE ")
    ]

    assert attribute_lines == list(ATTRIBUTES)


def test_registry_contains_required_header_and_paths() -> None:
    registry = render_registry()

    assert registry.startswith(
        'MAINTAINER "thomas.jurczyk@googlemail.com"\n'
        'INFO "C05corpus"\n'
        'NAME "C05 Corpus"\n'
        "PATH czerofive\n"
        'ENCODING "UTF-8"\n'
        'LANGUAGE "Pahlavi"\n'
        "\n"
        "PATH   '/corpora/czerofive/indexed/'\n"
        "VERTICAL  '/corpora/czerofive/vertical/source'\n"
        "\n"
        'INFOHREF "XXX"\n'
        'TAGSETDOC "XXX"\n'
        "\n"
        'FULLREF "doc.file,doc.n"\n'
    )


def test_registry_declares_doc_file_and_n() -> None:
    registry = render_registry()

    assert "STRUCTURE doc {\n    ATTRIBUTE file\n    ATTRIBUTE n\n}\n" in registry
    assert "STRUCTURE s {\n    ATTRIBUTE id\n}\n" in registry
    assert registry.count("STRUCTURE s {") == 1


def test_registry_config_can_be_overridden() -> None:
    registry = render_registry(
        RegistryConfig(
            maintainer="test@example.org",
            info="TEST",
            name="Test Corpus",
            path_id="test",
            language="German",
            indexed_path="/data/test/indexed/",
            vertical_path="/data/test/vertical",
        )
    )

    assert 'MAINTAINER "test@example.org"' in registry
    assert 'INFO "TEST"' in registry
    assert 'NAME "Test Corpus"' in registry
    assert "PATH test\n" in registry
    assert 'LANGUAGE "German"' in registry
    assert "PATH   '/data/test/indexed/'" in registry
    assert "VERTICAL  '/data/test/vertical'" in registry
