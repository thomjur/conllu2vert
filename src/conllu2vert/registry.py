"""Generating a Sketch Engine registry template."""

from __future__ import annotations

from dataclasses import dataclass

from .conllu import ATTRIBUTES

__all__ = ["RegistryConfig", "render_registry"]


@dataclass(frozen=True)
class RegistryConfig:
    """Values used in the generated Sketch Engine registry."""

    maintainer: str = "thomas.jurczyk@googlemail.com"
    info: str = "C05corpus"
    name: str = "C05 Corpus"
    path_id: str = "czerofive"
    encoding: str = "UTF-8"
    language: str = "Pahlavi"
    indexed_path: str = "/corpora/czerofive/indexed/"
    vertical_path: str = "/corpora/czerofive/vertical/source"
    infohref: str = "XXX"
    tagsetdoc: str = "XXX"
    fullref: str = "doc.file,doc.n"


def render_registry(config: RegistryConfig | None = None) -> str:
    """Return the registry text matching the generated vertical file.

    The ATTRIBUTE order is derived from the same tuple the writer uses, so the
    registry cannot silently drift away from the column order.
    """

    config = config or RegistryConfig()

    lines = [
        f'MAINTAINER "{config.maintainer}"',
        f'INFO "{config.info}"',
        f'NAME "{config.name}"',
        f"PATH {config.path_id}",
        f'ENCODING "{config.encoding}"',
        f'LANGUAGE "{config.language}"',
        "",
        f"PATH   '{config.indexed_path}'",
        f"VERTICAL  '{config.vertical_path}'",
        "",
        f'INFOHREF "{config.infohref}"',
        f'TAGSETDOC "{config.tagsetdoc}"',
        "",
        f'FULLREF "{config.fullref}"',
        "",
    ]
    lines.extend(f"ATTRIBUTE {attribute}" for attribute in ATTRIBUTES)
    lines.extend(
        [
            "",
            "STRUCTURE doc {",
            "    ATTRIBUTE file",
            "    ATTRIBUTE n",
            "}",
            "",
            "STRUCTURE s {",
            "    ATTRIBUTE id",
            "}",
            "",
        ]
    )
    return "\n".join(lines)
