from __future__ import annotations

from conllu2vert.conllu import ATTRIBUTES
from conllu2vert.registry import render_registry


def test_registry_matches_attribute_order() -> None:
    registry = render_registry(
        corpora_path="/corpora/test",
        vertical_path="/corpora/src/test.vert",
    )

    attribute_lines = [
        line.split(maxsplit=1)[1]
        for line in registry.splitlines()
        if line.startswith("ATTRIBUTE ")
    ]

    assert attribute_lines == list(ATTRIBUTES)


def test_registry_contains_paths_and_structures() -> None:
    registry = render_registry(
        corpora_path="/corpora/test",
        vertical_path="/corpora/src/test.vert",
    )

    assert registry.startswith(
        'PATH /corpora/test\n'
        'VERTICAL "/corpora/src/test.vert"\n'
        'ENCODING "utf-8"\n\n'
    )
    assert "STRUCTURE doc {\n    ATTRIBUTE id\n}\n" in registry
    assert "STRUCTURE s {\n    ATTRIBUTE id\n}\n" in registry
