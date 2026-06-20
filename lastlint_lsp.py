"""Language Server Protocol wrapper around lastlint.

A thin server exposing two capabilities:

* **Diagnostics** — runs `lint_text` on open/change/save and publishes one
  `Diagnostic` per `Finding`.
* **Formatting** — runs `fix_text` for `textDocument/formatting`, returning a
  single whole-document edit. This is what powers editor format-on-save.

The conversion logic (`to_diagnostics`, `format_edits`) is kept pure and free
of server state so it can be unit-tested without spinning up a server.

Run with: ``lastlint-lsp`` (speaks LSP over stdio).

The optional ``ignore`` list of rule codes may be passed as an
``initializationOptions`` field, e.g. ``{"ignore": ["E001", "E013"]}``.

The server dependencies (``pygls``, ``lsprotocol``) live in the optional
``lsp`` extra. This module imports cleanly without them so that ``main`` can
print an install hint instead of a raw traceback; the server itself is only
constructed in ``_build_server``, behind that guard.
"""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version
from typing import NoReturn

import lastlint

try:
    from lsprotocol import types as t
except ModuleNotFoundError:  # the optional 'lsp' extra isn't installed
    t = None  # type: ignore[assignment]

SOURCE = "lastlint"

try:
    VERSION = version("lastlint")
except PackageNotFoundError:  # running from a source tree without an install
    VERSION = "0.0.0"


def to_diagnostics(
    text: str, ignore: frozenset[str] = frozenset()
) -> list[t.Diagnostic]:
    """Convert lastlint findings into LSP diagnostics.

    Findings carry 1-based line/col and only a point (no end column); LSP wants
    0-based positions and a range. We anchor a one-character range at the point.
    For E001 (line too long) we extend the range to end-of-line so the whole
    overflow is underlined.
    """
    lines = text.split("\n")
    out: list[t.Diagnostic] = []
    for f in lastlint.lint_text(text, ignore=ignore):
        row = max(f.line - 1, 0)
        start_col = max(f.col - 1, 0)
        if f.rule == "E001" and row < len(lines):
            end_col = len(lines[row])
        else:
            end_col = start_col + 1
        out.append(
            t.Diagnostic(
                range=t.Range(
                    t.Position(row, start_col),
                    t.Position(row, end_col),
                ),
                message=f.msg,
                code=f.rule,
                severity=t.DiagnosticSeverity.Warning,
                source=SOURCE,
            )
        )
    return out


def format_edits(text: str, ignore: frozenset[str] = frozenset()) -> list[t.TextEdit]:
    """Return a whole-document replacement, or nothing if already clean."""
    fixed = lastlint.fix_text(text, ignore=ignore)
    if fixed == text:
        return []
    lines = text.split("\n")
    end = t.Position(len(lines) - 1, len(lines[-1]))
    return [t.TextEdit(range=t.Range(t.Position(0, 0), end), new_text=fixed)]


def _missing_lsp_extra() -> NoReturn:
    sys.stderr.write(
        "lastlint-lsp requires the optional 'lsp' extra, which is not "
        "installed.\nInstall it with one of:\n"
        "    uv tool install 'lastlint[lsp]'\n"
        "    pip install 'lastlint[lsp]'\n"
    )
    raise SystemExit(1)


def _build_server():
    """Construct the language server. Importing pygls here (not at module top)
    keeps the module importable without the ``lsp`` extra."""
    from pygls.server import LanguageServer

    class LastlintServer(LanguageServer):
        def __init__(self) -> None:
            super().__init__("lastlint-lsp", VERSION)
            self.ignore: frozenset[str] = frozenset()

    server = LastlintServer()

    @server.feature(t.INITIALIZE)
    def on_initialize(ls: LastlintServer, params: t.InitializeParams) -> None:
        opts = params.initialization_options or {}
        raw = opts.get("ignore") if isinstance(opts, dict) else None
        if raw:
            codes = {str(c).strip().upper() for c in raw if str(c).strip()}
            ls.ignore = frozenset(codes & lastlint.ALL_RULES)

    def _publish(ls: LastlintServer, uri: str) -> None:
        doc = ls.workspace.get_text_document(uri)
        ls.publish_diagnostics(uri, to_diagnostics(doc.source, ls.ignore))

    @server.feature(t.TEXT_DOCUMENT_DID_OPEN)
    def on_open(ls: LastlintServer, params: t.DidOpenTextDocumentParams) -> None:
        _publish(ls, params.text_document.uri)

    @server.feature(t.TEXT_DOCUMENT_DID_CHANGE)
    def on_change(ls: LastlintServer, params: t.DidChangeTextDocumentParams) -> None:
        _publish(ls, params.text_document.uri)

    @server.feature(t.TEXT_DOCUMENT_DID_SAVE)
    def on_save(ls: LastlintServer, params: t.DidSaveTextDocumentParams) -> None:
        _publish(ls, params.text_document.uri)

    @server.feature(t.TEXT_DOCUMENT_FORMATTING)
    def on_format(
        ls: LastlintServer, params: t.DocumentFormattingParams
    ) -> list[t.TextEdit]:
        doc = ls.workspace.get_text_document(params.text_document.uri)
        return format_edits(doc.source, ls.ignore)

    return server


def main() -> None:
    try:
        server = _build_server()
    except ModuleNotFoundError:
        _missing_lsp_extra()
    server.start_io()


if __name__ == "__main__":
    main()
