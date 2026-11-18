"""Command line interface for conllu2vert."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .conllu import ConlluError, Document, Stats, read_documents
from .registry import RegistryConfig, render_registry
from .vertical import VerticalWriter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="conllu2vert",
        description=(
            "Convert CoNLL-U files into one Sketch Engine vertical corpus. "
            "Each input file becomes one or more <doc> elements."
        ),
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        metavar="FILE",
        help="CoNLL-U files (default: all *.conllu in --input-dir)",
    )
    parser.add_argument(
        "-i",
        "--input-dir",
        type=Path,
        default=Path("src/data/input"),
        help="directory searched when no FILE is given (default: src/data/input)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="vertical output file (default: <output-dir>/<corpus-name>.vert)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("src/data/output"),
        help="directory for default output and registry paths (default: src/data/output)",
    )
    parser.add_argument(
        "--corpus-name",
        default="czerofive",
        help="name used for output file and registry PATH (default: czerofive)",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=None,
        help="registry output file (default: <output-dir>/<corpus-name>.registry)",
    )
    parser.add_argument(
        "--no-registry",
        action="store_true",
        help="do not write a registry template",
    )
    parser.add_argument(
        "--maintainer",
        default="thomas.jurczyk@googlemail.com",
        help="MAINTAINER value in the registry",
    )
    parser.add_argument(
        "--info",
        default="C05corpus",
        help="INFO value in the registry",
    )
    parser.add_argument(
        "--name",
        default="C05 Corpus",
        help="NAME value in the registry",
    )
    parser.add_argument(
        "--language",
        default="Pahlavi",
        help="LANGUAGE value in the registry",
    )
    parser.add_argument(
        "--indexed-path",
        default=None,
        help="PATH value for indexed data (default: /corpora/<corpus-name>/indexed/)",
    )
    parser.add_argument(
        "--vertical-path",
        default=None,
        help="VERTICAL value in the registry (default: /corpora/<corpus-name>/vertical/source)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="abort on malformed token rows instead of skipping them",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="only print errors",
    )
    return parser


def _collect_inputs(args: argparse.Namespace) -> list[Path]:
    if args.inputs:
        paths = sorted(args.inputs)
    else:
        if not args.input_dir.is_dir():
            raise ConlluError(f"input directory does not exist: {args.input_dir}")
        paths = sorted(p for pattern in ('*.conllu', '*.tsv') for p in args.input_dir.glob(pattern))

    missing = [path for path in paths if not path.is_file()]
    if missing:
        names = ", ".join(str(path) for path in missing)
        raise ConlluError(f"input file does not exist: {names}")
    return paths


def _format_skipped(skipped: Stats) -> str:
    if not skipped.skipped:
        return ""
    parts = [f"{name}={count}" for name, count in sorted(skipped.skipped.items())]
    return ", ".join(parts)


def _find_duplicate_ids(documents: list[Document]) -> tuple[list[str], list[str]]:
    seen_docs: set[str] = set()
    seen_sentences: set[str] = set()
    duplicate_docs: list[str] = []
    duplicate_sentences: list[str] = []

    for document in documents:
        if document.file in seen_docs and document.file not in duplicate_docs:
            duplicate_docs.append(document.file)
        seen_docs.add(document.file)
        for sentence in document.sentences:
            if sentence.id in seen_sentences and sentence.id not in duplicate_sentences:
                duplicate_sentences.append(sentence.id)
            seen_sentences.add(sentence.id)

    return duplicate_docs, duplicate_sentences


def _write_vertical(path: Path, documents: list[Document]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            writer = VerticalWriter(handle)
            for number, document in enumerate(documents, 1):
                writer.write_document(document, number)
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _write_registry(path: Path, config: RegistryConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_registry(config), encoding="utf-8")


def _report_file(path: Path, documents: list[Document], stats: Stats) -> None:
    print(
        f"{path.name}: {len(documents)} doc(s), "
        f"{stats.sentences} sentence(s), {stats.tokens} token(s)"
    )
    details: list[str] = []
    skipped = _format_skipped(stats)
    if skipped:
        details.append(f"skipped: {skipped}")
    if stats.tokens_without_id:
        details.append(f"tokens without numeric id: {stats.tokens_without_id}")
    if stats.quoted_comments:
        details.append(f"repaired quoted comments: {stats.quoted_comments}")
    if stats.missing_sent_ids:
        details.append(f"missing sent_id: {stats.missing_sent_ids}")
    if stats.suspicious_values:
        details.append(f"values containing '<' or '>': {stats.suspicious_values}")
    for detail in details:
        print(f"  {detail}")


def _run(args: argparse.Namespace) -> int:
    paths = _collect_inputs(args)
    if not paths:
        raise ConlluError(
            f"no *.conllu/*.tsv files found in {args.input_dir} and no FILE given"
        )

    output = args.output or args.output_dir / f"{args.corpus_name}.vert"
    registry_path = None
    if not args.no_registry:
        registry_path = args.registry or args.output_dir / f"{args.corpus_name}.registry"

    indexed_path = (
        args.indexed_path or f"/corpora/{args.corpus_name}/indexed/"
    )
    vertical_path = (
        args.vertical_path or f"/corpora/{args.corpus_name}/vertical/source"
    )
    registry_config = RegistryConfig(
        maintainer=args.maintainer,
        info=args.info,
        name=args.name,
        path_id=args.corpus_name,
        language=args.language,
        indexed_path=indexed_path,
        vertical_path=vertical_path,
    )

    total = Stats()
    documents: list[Document] = []
    results: list[tuple[Path, list[Document], Stats]] = []

    for path in paths:
        file_stats = Stats(files=1)
        file_documents = list(
            read_documents(path, stats=file_stats, strict=args.strict)
        )
        total.merge(file_stats)
        documents.extend(file_documents)
        results.append((path, file_documents, file_stats))

    duplicate_docs, duplicate_sentences = _find_duplicate_ids(documents)

    _write_vertical(output, documents)

    if registry_path is not None:
        _write_registry(registry_path, registry_config)

    if not args.quiet:
        for path, file_documents, file_stats in results:
            _report_file(path, file_documents, file_stats)
        print(
            f"total: {total.files} file(s), {total.documents} doc(s), "
            f"{total.sentences} sentence(s), {total.tokens} token(s)"
        )
        print(f"vertical: {output}")
        if registry_path is not None:
            print(f"registry: {registry_path}")

    if duplicate_docs:
        print(
            "warning: duplicate doc id(s): " + ", ".join(duplicate_docs),
            file=sys.stderr,
        )
    if duplicate_sentences:
        preview = ", ".join(duplicate_sentences[:5])
        suffix = " ..." if len(duplicate_sentences) > 5 else ""
        print(
            f"warning: {len(duplicate_sentences)} duplicate sentence id(s): "
            f"{preview}{suffix}",
            file=sys.stderr,
        )

    if total.tokens == 0:
        print("warning: no tokens were written", file=sys.stderr)

    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _run(args)
    except (ConlluError, OSError) as error:
        print(f"conllu2vert: error: {error}", file=sys.stderr)
        return 1
