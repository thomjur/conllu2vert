"""Writing documents in Sketch Engine vertical format."""

from __future__ import annotations

from typing import TextIO

from .conllu import ATTRIBUTES, Document, Token

__all__ = ["VerticalWriter", "ATTRIBUTES"]


def _quote_attribute(value: str) -> str:
    """Quote a structure attribute value for a vertical file."""

    value = (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    return f'"{value}"'


def _token_line(token: Token) -> str:
    columns = token.columns()
    for value in columns:
        if "\t" in value or "\n" in value or "\r" in value:
            raise ValueError(f"attribute value contains a tab or newline: {value!r}")
    return "\t".join(columns)


class VerticalWriter:
    """Write documents to a stream in Sketch Engine vertical format."""

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream

    def write_document(self, document: Document, number: int) -> None:
        if not document.sentences:
            return

        self._stream.write(
            f"<doc file={_quote_attribute(document.file)} n=\"{number}\">\n"
        )
        for sentence in document.sentences:
            self._stream.write(f"<s id={_quote_attribute(sentence.id)}>\n")
            for token in sentence.tokens:
                self._stream.write(_token_line(token) + "\n")
            self._stream.write("</s>\n")
        self._stream.write("</doc>\n")
