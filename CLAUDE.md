# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A linter for [Evan Chen's LaTeX style guide](https://web.evanchen.cc/latex-style-guide.html),
shipped as a single-module package (`lastlint.py`) and as a pre-commit hook.

## Commands

```sh
pip install -e .[dev]   # editable install with prek + pytest
pytest                  # run the test suite
pytest tests/test_lint.py::test_clean_fixture_has_no_findings   # single test
lastlint path/to/file.tex          # lint
lastlint --fix path/to/file.tex    # auto-fix in place
prek run --all-files                      # run repo's own hooks (ruff, etc.)
```

Linting/formatting of this repo's Python is `ruff` via `prek` (see `prek.toml`).
Commit messages must be conventional-commit format (enforced by a commit-msg hook).

## Architecture

Everything lives in `lastlint.py`. Tests in `tests/test_lint.py` plus
two fixtures: `tests/fixtures/clean.tex` (must produce zero findings) and
`tests/fixtures/violations.tex` (must trigger every implemented rule).

Pipeline:

1. `Source` wraps the file text. It precomputes `masked_lines` — a copy with
   verbatim-env contents (`asy`, `verbatim`, `lstlisting`, …) blanked to
   spaces. Blanking preserves line/column offsets, so positions found against
   the mask are valid against the original. Most rules scan `masked_lines`;
   only line-length (E001) and trailing-whitespace (E014) scan raw `lines`.
2. Each rule is a `rule_EXXX_*` generator yielding `Finding`s, registered in
   the `RULES` list. The rule code is parsed from the function name.
3. Fixers are `fix_EXXX_*` functions returning the rewritten file text,
   registered in the `FIXERS` dict. Not every rule has a fixer.
4. `fix_text` runs all fixers repeatedly to a fixpoint (`MAX_FIX_PASSES`),
   because one fixer's output can be another's input.

## Conventions when adding a rule

- A new rule `EXXX` needs: a `rule_EXXX_*` generator added to `RULES`, a line
  in `tests/fixtures/violations.tex` that triggers it, and confirmation that
  `clean.tex` still produces no findings. `test_violations_fixture_covers_all_rules`
  enforces full coverage.
- Operate on `src.masked_lines` (not raw lines) unless the rule is genuinely
  about raw bytes — this is what skips Asymptote/verbatim content.
- For math-only rules, iterate `find_inline_math(line)` spans rather than
  matching the whole line.
- Suppression (`% lastlint: disable=EXXX`) and `--ignore` are handled
  centrally in `lint_text`/`fix_text`; rules don't deal with them.
- Rule codes are not contiguous — E008 and E016 are intentionally unused
  (rules 8 and 16 of the guide are not implementable). Don't renumber.

## Conventions when adding a fixer

- A fixer takes a `Source` and returns the full new file text. Most use the
  `_per_line_fix` / `_apply_line_edits` helpers (apply edits right-to-left so
  earlier offsets stay valid).
- Fixers must be idempotent and safe to chain; `fix_text` relies on reaching
  a fixpoint. Only fix the unambiguous cases — e.g. E009 fixes `||`→`\parallel`
  but leaves `*`/`x`/`mod` because the right replacement is author-dependent.
- Keep `README.md`'s list of fixable rules and the `--fix` help text in sync.

## Releases

Versioning is automated by release-please (`.github/workflows/release-please.yml`).
The version in `pyproject.toml` and the `rev:` in `README.md` (marked with
`# x-release-please-version`) are bumped by the release PR — don't edit them
by hand.
