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

Also recommended (cover rules this linter does not):

```yaml
- repo: https://github.com/pre-commit/pre-commit-hooks
  rev: v5.0.0
  hooks:
    - id: trailing-whitespace
      files: \.tex$
# latexindent.pl handles rule 13 (environment indentation)
```

## Standalone

```sh
pip install .
otis-latex-lint path/to/file.tex
```

Output format is `file:line:col: EXXX: message`, parseable by editors.

Pass `--fix` to auto-fix supported rules in place. Currently fixed: `E013`
(under-indented lines inside indent envs are padded to `2 * depth` spaces;
already-correctly-indented or deeper lines are left alone).

## Rules

| ID   | Rule from style guide                         |
| ---- | --------------------------------------------- |
| E001 | Line length ≤ 100                             |
| E002 | No literal `"`                                |
| E003 | Operators (`\sin` etc.) must be commands      |
| E004 | No `\ldots` or `\cdots`; use `\dots`          |
| E005 | No grammatical punctuation inside inline math |
| E006 | No extraneous space before punctuation        |
| E007 | Symmetric spacing around `=`                  |
| E009 | No `\|\|` for `\parallel`                     |
| E010 | No `$$ ... $$`                                |
| E011 | No adjacent `\[ ... \]` blocks                |
| E012 | `\begin{align*}` / `\end{align*}` on own line |
| E013 | Env contents indented at least 2 spaces       |
| E015 | No `\\\\` paragraph break                     |
| E017 | `\colon` for function signatures              |

E013 applies to a conservative allowlist of envs (`align`, `itemize`,
`enumerate`, `proof`, `theorem`, matrices, etc.); other envs are not
checked. See `INDENT_ENVS` in `otis_latex_lint.py` to adjust.

Rules **not** implemented:

- Rule 8 (balanced delimiters): hard to lint reliably.
- Rule 14 (trailing whitespace): use pre-commit's `trailing-whitespace`.
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
