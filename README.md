# otis-latex-linter

A linter for [Evan Chen's LaTeX style guide](https://web.evanchen.cc/latex-style-guide.html),
packaged as a [pre-commit](https://pre-commit.com/) hook.

## Usage

Add to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/cjquines/otis-latex-linter
    rev: v0.1.0
    hooks:
      - id: otis-latex-lint
```

## Standalone

```sh
pip install .
otis-latex-lint path/to/file.tex
```

Output format is `file:line:col: EXXX: message`, parseable by editors.

Pass `--fix` to auto-fix supported rules in place: `E002`, `E003`, `E004`,
`E005`, `E006`, `E009`, `E010`, `E013`, `E014`, `E017`. For example, E013
pads under-indented lines inside indent envs to `2 * depth` spaces
(already-correctly-indented or deeper lines are left alone), and E014 strips
trailing whitespace.

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

E013 applies to a conservative allowlist of envs (`align`, `itemize`,
`enumerate`, `proof`, `theorem`, matrices, etc.); other envs are not
checked. See `INDENT_ENVS` in `otis_latex_lint.py` to adjust.

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
