from pathlib import Path

import pytest

pytest.importorskip("pygls")

from lsprotocol import types as t

import lastlint
import lastlint_lsp as lsp

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def server():
    """An initialized server that records what it publishes.

    `lsp_initialize` is pygls' real initialize path, so this also sets up the
    workspace. Notifications go through `_handle_notification` (the same entry
    point pygls uses after deserializing a message) so that the builtin
    document-tracking handlers run alongside ours; that handler logs and
    swallows exceptions, so fail the test rather than let a crash masquerade
    as "published nothing".
    """
    s = lsp._build_server()
    s.lsp.lsp_initialize(
        t.InitializeParams(
            capabilities=t.ClientCapabilities(), root_uri=FIXTURES.as_uri()
        )
    )
    s.published = []
    s.publish_diagnostics = lambda uri, diags: s.published.append((uri, diags))
    s._report_server_error = lambda error, source: pytest.fail(f"{source}: {error!r}")
    return s


def did_open(server, uri, text):
    server.lsp._handle_notification(
        t.TEXT_DOCUMENT_DID_OPEN,
        t.DidOpenTextDocumentParams(
            text_document=t.TextDocumentItem(
                uri=uri, language_id="tex", version=1, text=text
            )
        ),
    )


def did_save(server, uri):
    server.lsp._handle_notification(
        t.TEXT_DOCUMENT_DID_SAVE,
        t.DidSaveTextDocumentParams(text_document=t.TextDocumentIdentifier(uri=uri)),
    )


def format_document(server, uri):
    handler = server.lsp.fm.features[t.TEXT_DOCUMENT_FORMATTING]
    return handler(
        t.DocumentFormattingParams(
            text_document=t.TextDocumentIdentifier(uri=uri),
            options=t.FormattingOptions(tab_size=2, insert_spaces=True),
        )
    )


def test_clean_fixture_yields_no_diagnostics():
    text = (FIXTURES / "clean.tex").read_text()
    assert lsp.to_diagnostics(text) == []
    assert lsp.format_edits(text) == []


def test_diagnostics_match_findings():
    text = (FIXTURES / "violations.tex").read_text()
    diags = lsp.to_diagnostics(text)
    findings = lastlint.lint_text(text)
    assert len(diags) == len(findings)
    # Positions are 0-based and well-formed.
    for d in diags:
        assert d.range.start.line >= 0
        assert d.range.start.character >= 0
        assert d.range.end.character >= d.range.start.character
        assert d.source == "lastlint"
    # 1-based finding maps to 0-based diagnostic.
    f, d = findings[0], diags[0]
    assert d.range.start.line == f.line - 1
    assert d.range.start.character == f.col - 1
    assert d.code == f.rule


def test_format_edit_applies_fix_text():
    text = (FIXTURES / "violations.tex").read_text()
    edits = lsp.format_edits(text)
    assert len(edits) == 1
    edit = edits[0]
    assert edit.new_text == lastlint.fix_text(text)
    # Edit replaces the whole document.
    assert edit.range.start.line == 0
    assert edit.range.start.character == 0


def test_ignore_filters_diagnostics():
    text = (FIXTURES / "violations.tex").read_text()
    all_diags = lsp.to_diagnostics(text)
    target = all_diags[0].code  # some rule that actually fires on the fixture
    filtered = lsp.to_diagnostics(text, frozenset({target}))
    assert not any(d.code == target for d in filtered)
    assert len(filtered) < len(all_diags)


def test_open_document_is_linted(server):
    path = FIXTURES / "violations.tex"
    text = path.read_text()
    did_open(server, path.as_uri(), text)
    assert len(server.published) == 1
    uri, diags = server.published[0]
    assert uri == path.as_uri()
    assert len(diags) == len(lastlint.lint_text(text))
    assert format_document(server, path.as_uri()) == lsp.format_edits(text)


def test_unopened_document_is_ignored(server):
    """Editors address us about buffers we were never attached to; see
    `_managed_source` for why. pygls would otherwise read the URI off disk and
    lint it as LaTeX."""
    path = FIXTURES / "violations.tex"  # real, unclean, but never opened
    assert lastlint.lint_text(path.read_text()), "fixture should have findings"

    did_save(server, path.as_uri())
    assert server.published == []
    assert format_document(server, path.as_uri()) == []
