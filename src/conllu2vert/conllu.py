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
    tokens_without_id: int = 0
    quoted_comments: int = 0
    missing_sent_ids: int = 0
    suspicious_values: int = 0
    skipped: Counter[str] = field(default_factory=Counter)

    def merge(self, other: "Stats") -> None:
        self.files += other.files
        self.documents += other.documents
        self.sentences += other.sentences
        self.tokens += other.tokens
        self.tokens_without_id += other.tokens_without_id
        self.quoted_comments += other.quoted_comments
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
    file: str
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
    if len(columns) == 1:
        return "comment_continuation"
    if len(columns) != 10:
        return "wrong_column_count"
    return "non_numeric_id"


def document_id(path: str | Path) -> str:
    """Return the document id of a file: its name without extension.

    A trailing ``_conllu`` suffix is removed, so ``ADM-MK_conllu.tsv``
    becomes ``ADM-MK``.
    """

    stem = Path(path).stem
    suffix = "_conllu"
    if stem.endswith(suffix):
        stem = stem[: -len(suffix)]
    return stem


def read_documents(
    path: str | Path,
    *,
    stats: Stats | None = None,
    strict: bool = False,
) -> Iterator[Document]:
    """Yield the single document contained in one CoNLL-U file.

    The document id is derived from the file name (see :func:`document_id`),
    so every input file becomes exactly one document.  ``# text_id`` is not
    used to split documents: it may be repeated or empty, which is harmless.
    Multiword tokens and empty nodes are skipped, because the individual
    surface tokens already exist.  Rows with ``_`` as their token id are kept:
    the vertical format does not write token ids and the rows are already in
    reading order.  Malformed rows are skipped.
    """

    path = Path(path)
    stats = Stats() if stats is None else stats
    document = Document(document_id(path))
    sentence_id: str | None = None
    sentence_tokens: list[Token] = []
    generated_sentences: list[tuple[Sentence, int]] = []

    def close_sentence(*, reset_id: bool = False) -> None:
        nonlocal sentence_id, sentence_tokens
        if not sentence_tokens:
            if reset_id:
                sentence_id = None
            return
        sid = sentence_id or ""
        sentence = Sentence(sid, tuple(sentence_tokens))
        document.sentences.append(sentence)
        if not sid:
            generated_sentences.append((sentence, len(document.sentences)))
            stats.missing_sent_ids += 1
        stats.sentences += 1
        stats.tokens += len(sentence_tokens)
        sentence_id = None
        sentence_tokens = []

    def assign_generated_ids() -> None:
        """Fill in ids for sentences without ``# sent_id``.

        The generated ``<file>_s<N>`` ids must not collide with explicit ids
        from the same file: a placeholder ``# sent_id = _`` can appear right
        next to real ids such as ``AWN-K20_s8``.
        """

        if not generated_sentences:
            return
        used = {sentence.id for sentence in document.sentences if sentence.id}
        for sentence, position in generated_sentences:
            index = position
            candidate = f"{document.file}_s{index}"
            while candidate in used:
                index += 1
                candidate = f"{document.file}_s{index}"
            sentence.id = candidate
            used.add(candidate)

    def handle_comment(comment: str) -> None:
        nonlocal sentence_id
        sent_id_match = _SENT_ID.match(comment)
        if sent_id_match:
            new_id = sent_id_match.group(1).strip()
            if new_id and new_id != "_":
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

            if len(columns) == 10 and (
                _TOKEN_ID.fullmatch(token_id) or token_id == "_"
            ):
                sentence_tokens.append(
                    _parse_token(
                        columns,
                        path=path,
                        line_number=line_number,
                        stats=stats,
                        strict=strict,
                    )
                )
                if token_id == "_":
                    stats.tokens_without_id += 1
                continue

            category = _skip_category(columns, token_id)
            stats.skipped[category] += 1
            if strict and category in {"wrong_column_count", "non_numeric_id"}:
                raise ConlluError(
                    f"{path}:{line_number}: invalid token row ({category}): {line!r}"
                )

    close_sentence()
    assign_generated_ids()
    if document.sentences:
        stats.documents += 1
        yield document


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
