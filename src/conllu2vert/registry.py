"""Generating a Sketch Engine registry template."""

from __future__ import annotations

from .conllu import ATTRIBUTES

__all__ = ["render_registry"]


def render_registry(
    *,
    corpora_path: str = "/corpora/pahlavi",
    vertical_path: str = "/corpora/src/pahlavi.vert",
) -> str:
    """Return the registry text matching the generated vertical file.

    The ATTRIBUTE order is derived from the same tuple the writer uses, so the
    registry cannot silently drift away from the column order.
    """

    lines = [
        f"PATH {corpora_path}",
        f'VERTICAL "{vertical_path}"',
        'ENCODING "utf-8"',
        "",
    ]
    lines.extend(f"ATTRIBUTE {attribute}" for attribute in ATTRIBUTES)
    lines.extend(
        [
            "",
            "STRUCTURE doc {",
            "    ATTRIBUTE id",
            "}",
            "STRUCTURE s {",
            "    ATTRIBUTE id",
            "}",
            "",
        ]
    )
    return "\n".join(lines)
