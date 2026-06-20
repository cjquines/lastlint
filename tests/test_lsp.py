from pathlib import Path

import pytest

pytest.importorskip("pygls")

import lastlint
import lastlint_lsp as lsp

FIXTURES = Path(__file__).parent / "fixtures"


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
