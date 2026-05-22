# otis-latex-linter

A linter for [Evan Chen's LaTeX style guide](https://web.evanchen.cc/latex-style-guide.html),
packaged as a [pre-commit](https://pre-commit.com/) hook.

## Usage

Add to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/cjquines/otis-latex-linter
    rev: v0.3.0 # x-release-please-version
    hooks:
      - id: otis-latex-lint-fix
```

To only report errors rather than auto-fixing them,
use the `otis-latex-lint` hook id.

## Standalone

```sh
pip install .
otis-latex-lint path/to/file.tex another.tex
```

Multiple files are accepted, and glob patterns are expanded — handy when the
pattern is quoted (`otis-latex-lint 'src/**/*.tex'`) or on Windows, where the
shell does not glob. On a terminal, output is grouped per file and
colorized with a summary line; when piped or redirected it falls back to the
plain `file:line:col: EXXX: message` format parseable by editors. Force either
mode with `--color always` / `--color never` (also honors `NO_COLOR` and
`FORCE_COLOR`).

Pass `--ignore E001,E013` to skip rules entirely — both reporting and (with
`--fix`) fixing. Useful for projects that don't follow a particular rule.

Pass `--fix` to auto-fix supported rules in place: `E002`, `E003`, `E004`,
`E005`, `E006`, `E009`, `E010`, `E013`, `E014`, `E017`. For example, E013
pads under-indented lines inside indent envs to `2 * depth` spaces
(already-correctly-indented or deeper lines are left alone), and E014 strips
trailing whitespace. E004 picks the right `\dots` variant from context
(`\dotsc` after a comma, `\dotsb` after an operator) and leaves a `\cdots`
unresolved when neither side determines the spacing.

## Rules

| ID   | Rule from style guide                                     |
| ---- | --------------------------------------------------------- |
| E001 | Line length ≤ 100                                         |
| E002 | No literal `"`                                            |
| E003 | Operators (`\sin` etc.) must be commands                  |
| E004 | No `\ldots`, `\cdots`, or literal `...`; use `\dots`      |
| E005 | No grammatical punctuation inside inline math             |
| E006 | No extraneous space before punctuation                    |
| E007 | Symmetric spacing around `=`                              |
| E009 | Bad math operators (`\|\|`, spaced `\|`, `*`, `x`, `mod`) |
| E010 | No `$$ ... $$`                                            |
| E011 | No adjacent `\[ ... \]` blocks                            |
| E012 | `\begin{align*}` / `\end{align*}` on own line             |
| E013 | Env contents indented at least 2 spaces                   |
| E014 | No trailing whitespace                                    |
| E015 | No `\\\\` paragraph break                                 |
| E017 | `\colon` for function signatures                          |

E001 skips two kinds of unfixable long lines: those containing a URL
(`http://` or `https://`), which has no breakable whitespace, and
fully-commented lines (only whitespace before the `%`), which are dead code
the author can leave long. Lines with a long _trailing_ comment after real
content are still flagged.

E013 checks every env except a small denylist: `document`, `center`, `quote`,
and the verbatim envs (`asy`, `verbatim`, `lstlisting`, …). Those wrap prose
that idiomatically stays flush left; everything else — including theorem-like
envs — should have its body indented. See `NO_INDENT_ENVS` in
`otis_latex_lint.py` to adjust.

Rules **not** implemented:

- Rule 8 (balanced delimiters): hard to lint reliably.
- Rule 16 (variables in prose): requires natural-language understanding.

## Suppression

Add an inline comment to skip rules on a single line:

```latex
This text has "intentional" quotes.  % latex-lint: disable=E002
```

## Asymptote and verbatim

Contents of `\begin{asy}`, `\begin{asydef}`, `\begin{verbatim}`,
`\begin{lstlisting}`, and `\begin{minted}` are skipped.

## Development

```sh
pip install -e .[dev]
pytest
```
