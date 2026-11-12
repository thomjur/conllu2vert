"""Reading CoNLL-U files and turning them into documents, sentences and tokens."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

# Order matters: it is the column order of the vertical file and of the
# ATTRIBUTE lines in the Sketch Engine registry.
ATTRIBUTES = ("word", "lemma", "tag", "feats", "deprel", "sense")

_TOKEN_ID = re.compile(r"\d+")
_MULTIWORD_ID = re.compile(r"\d+-\d+")
_EMPTY_NODE_ID = re.compile(r"\d+\.\d+")
_TEXT_ID = re.compile(r"^#\s*text_id\s*=\s*(.*)$")
_SENT_ID = re.compile(r"^#\s*sent_id\s*=\s*(.*)$")


class ConlluError(ValueError):
    """Raised when a CoNLL-U file cannot be converted."""


@dataclass
class Stats:
    """Counters collected while reading one or more CoNLL-U files."""

    files: int = 0
    documents: int = 0
    sentences: int = 0
    tokens: int = 0
    quoted_comments: int = 0
    missing_text_ids: int = 0
    missing_sent_ids: int = 0
    suspicious_values: int = 0
    skipped: Counter[str] = field(default_factory=Counter)

    def merge(self, other: "Stats") -> None:
        self.files += other.files
        self.documents += other.documents
        self.sentences += other.sentences
        self.tokens += other.tokens
        self.quoted_comments += other.quoted_comments
        self.missing_text_ids += other.missing_text_ids
        self.missing_sent_ids += other.missing_sent_ids
        self.suspicious_values += other.suspicious_values
        self.skipped.update(other.skipped)


@dataclass(frozen=True, slots=True)
class Token:
    word: str
    lemma: str
    tag: str
    feats: str
    deprel: str
    sense: str

    def columns(self) -> tuple[str, ...]:
        """Return the values in vertical/registry attribute order."""
        return tuple(getattr(self, name) for name in ATTRIBUTES)


@dataclass(slots=True)
class Sentence:
    id: str
    tokens: tuple[Token, ...]


@dataclass(slots=True)
class Document:
    id: str
    sentences: list[Sentence] = field(default_factory=list)


def clean_comment_line(line: str) -> str:
    """Repair the broken CSV quoting found in some comment lines.

    Some source files contain comment lines exported as a quoted CSV field,
    for example with doubled quotation marks inside the comment.  The
    conversion only needs the comment value, so the CSV quoting is removed
    here.
    """

    line = line.rstrip("\r\n")
    if line.startswith('"#'):
        line = line[1:]
        if line.endswith('"'):
            line = line[:-1]
        line = line.replace('""', '"')
    return line


def _unquote(value: str) -> str:
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        return value[1:-1].replace('""', '"')
    return value


def _join_alternatives(value: str) -> str:
    """Turn ``a|b`` into ``a; b`` for lemma values."""

    parts = [part.strip() for part in _unquote(value).split("|")]
    parts = [part for part in parts if part and part != "_"]
    return "; ".join(parts) if parts else "_"


def _parse_sense(misc: str) -> str:
    """Collect every ``Sense=`` value from the MISC column."""

    senses: list[str] = []
    for part in _unquote(misc).split("|"):
        part = part.strip()
        if part.startswith("Sense="):
            value = part[len("Sense=") :].strip()
            if value and value != "_":
                senses.append(value)
    return "; ".join(senses) if senses else "_"


def _clean_field(value: str) -> str:
    value = _unquote(value)
    return value if value else "_"


def _parse_token(
    columns: list[str],
    *,
    path: Path,
    line_number: int,
    stats: Stats,
    strict: bool,
) -> Token:
    token = Token(
        word=_clean_field(columns[1]),
        lemma=_join_alternatives(columns[2]),
        tag=_clean_field(columns[3]),
        feats=_clean_field(columns[5]),
        deprel=_clean_field(columns[7]),
        sense=_parse_sense(columns[9]),
    )

    for name, value in zip(ATTRIBUTES, token.columns()):
        if "<" in value or ">" in value:
            stats.suspicious_values += 1
            if strict:
                raise ConlluError(
                    f"{path}:{line_number}: attribute {name!r} contains '<' or '>': {value!r}"
                )

    return token


def _skip_category(columns: list[str], token_id: str) -> str:
    if _MULTIWORD_ID.fullmatch(token_id):
        return "multiword_token"
    if _EMPTY_NODE_ID.fullmatch(token_id):
        return "empty_node"
    if token_id == "_":
        return "underscore_id"
    if len(columns) == 1:
        return "comment_continuation"
    if len(columns) != 10:
        return "wrong_column_count"
    return "non_numeric_id"


def read_documents(
    path: str | Path,
    *,
    stats: Stats | None = None,
    strict: bool = False,
) -> Iterator[Document]:
    """Yield the documents contained in one CoNLL-U file.

    A new document starts whenever ``# text_id = ...`` changes (or at the
    beginning of the file if there is no ``text_id``).  Multiword tokens,
    empty nodes and malformed rows without a numeric ID are skipped, because
    the vertical corpus should contain only surface tokens.
    """

    path = Path(path)
    stats = Stats() if stats is None else stats
    documents: list[Document] = []
    document: Document | None = None
    sentence_id: str | None = None
    sentence_tokens: list[Token] = []
    sentence_index = 0

    def close_sentence(*, reset_id: bool = False) -> None:
        nonlocal sentence_id, sentence_tokens, sentence_index
        if not sentence_tokens:
            if reset_id:
                sentence_id = None
            return
        if document is None:  # pragma: no cover - defensive
            raise ConlluError(f"{path}: token found before a document was opened")
        sentence_index += 1
        sid = sentence_id
        if not sid:
            sid = f"{document.id}_s{sentence_index}"
            stats.missing_sent_ids += 1
        document.sentences.append(Sentence(sid, tuple(sentence_tokens)))
        stats.sentences += 1
        stats.tokens += len(sentence_tokens)
        sentence_id = None
        sentence_tokens = []

    def start_document(new_id: str) -> None:
        nonlocal document, sentence_index
        close_sentence()
        if document is not None and document.sentences:
            documents.append(document)
            stats.documents += 1
        document = Document(new_id)
        sentence_index = 0

    def handle_comment(comment: str) -> None:
        nonlocal sentence_id
        text_id_match = _TEXT_ID.match(comment)
        if text_id_match:
            new_id = text_id_match.group(1).strip()
            if not new_id:
                new_id = path.stem
                stats.missing_text_ids += 1
            if document is None or document.id != new_id:
                start_document(new_id)
            return

        sent_id_match = _SENT_ID.match(comment)
        if sent_id_match:
            new_id = sent_id_match.group(1).strip()
            if new_id:
                sentence_id = new_id

    with path.open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, 1):
            line = raw_line.rstrip("\r\n")

            if not line:
                close_sentence(reset_id=True)
                continue

            if line.startswith("#"):
                handle_comment(line)
                continue

            if line.startswith('"#'):
                stats.quoted_comments += 1
                handle_comment(clean_comment_line(line))
                continue

            columns = line.split("\t")
            token_id = columns[0]

            if len(columns) == 10 and _TOKEN_ID.fullmatch(token_id):
                if document is None:
                    start_document(path.stem)
                    stats.missing_text_ids += 1
                sentence_tokens.append(
                    _parse_token(
                        columns,
                        path=path,
                        line_number=line_number,
                        stats=stats,
                        strict=strict,
                    )
                )
                continue

            category = _skip_category(columns, token_id)
            stats.skipped[category] += 1
            if strict and category in {"wrong_column_count", "non_numeric_id"}:
                raise ConlluError(
                    f"{path}:{line_number}: invalid token row ({category}): {line!r}"
                )

    close_sentence()
    if document is not None and document.sentences:
        documents.append(document)
        stats.documents += 1

    yield from documents


def read_many(
    paths: list[Path],
    *,
    stats: Stats | None = None,
    strict: bool = False,
) -> Iterator[Document]:
    """Yield documents from several files, in the order of ``paths``."""

    stats = Stats() if stats is None else stats
    for path in paths:
        stats.files += 1
        yield from read_documents(path, stats=stats, strict=strict)
