# lastlint: LaTeX strict linter

A linter for [Evan Chen's LaTeX style guide](https://web.evanchen.cc/latex-style-guide.html).

## Usage

### Pre-commit hook

Add to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/cjquines/lastlint
    rev: v0.5.0 # x-release-please-version
    hooks:
      - id: lastlint-fix
```

To only report errors rather than auto-fixing them,
use the `lastlint` hook id.

### Standalone

Install from PyPI. Using [uv](https://docs.astral.sh/uv/) (recommended):

```sh
uv tool install lastlint
lastlint path/to/file.tex another.tex
```

To run without installing: `uvx lastlint path/to/file.tex`.
With `pip`: `pip install lastlint`.

Multiple files are accepted, and glob patterns are expanded.

Pass `--fix` to auto-fix supported rules in place.

Pass `--ignore E001,E013` to skip both reporting and fixing.

On a terminal, output is grouped per file and colorized;
when piped or redirected it uses a plain
`file:line:col: EXXX: message`
format parseable by editors.
Force either mode with `--color always` or `--color never`
(also honors `NO_COLOR` and `FORCE_COLOR`).

### Editor

An optional language server exposes lastlint to compatible text editors.
Install it with the `lsp` extra:

```sh
uv tool install 'lastlint[lsp]'
# or: pip install 'lastlint[lsp]'
```

The server `lastlint-lsp`, over stdio,
publishes diagnostics and implements formatting,
so format-on-save will auto-fix LaTeX files.
Pass ignored rules through `initializationOptions`,
e.g. `{"ignore": ["E001", "E013"]}`.

The setups below assume `lastlint-lsp` is globally installed.
To skip a global install, replace the command with
`uvx --from 'lastlint[lsp]' lastlint-lsp`.

<details>
<summary>Neovim</summary>

0.11+, native `vim.lsp`:

```lua
vim.lsp.config('lastlint', {
  cmd = { 'lastlint-lsp' },
  filetypes = { 'tex', 'plaintex' },
  root_markers = { '.git' },
})
vim.lsp.enable('lastlint')
```

</details>

<details>
<summary>Sublime Text</summary>

The [LSP](https://lsp.sublimetext.io/) package, in `LSP.sublime-settings`:

```json
{
  "clients": {
    "lastlint": {
      "enabled": true,
      "command": ["lastlint-lsp"],
      "selector": "text.tex.latex"
    }
  }
}
```

</details>

<details>
<summary>Emacs</summary>

[Eglot](https://www.gnu.org/software/emacs/manual/html_mono/eglot.html) (built
in since 29) — then run `M-x eglot` in a TeX buffer:

```elisp
(with-eval-after-load 'eglot
  (add-to-list 'eglot-server-programs
               '((latex-mode LaTeX-mode) . ("lastlint-lsp"))))
```

</details>

## Suppression

Add an inline comment to skip rules on a single line:

```latex
This text has "intentional" quotes.  % lastlint: disable=E002
```

## Rules

Fixable rules are marked with 🔧.

| ID      | Rule from style guide                                |
| ------- | ---------------------------------------------------- |
| E001    | Line length must be ≤ 120                            |
| E002 🔧 | No literal `"`                                       |
| E003 🔧 | Operators (`\sin` etc.) must be commands             |
| E004 🔧 | No `\ldots`, `\cdots`, or `...`                      |
| E005 🔧 | No grammatical punctuation inside inline math        |
| E006 🔧 | No extraneous space before punctuation               |
| E007    | Spacing around `=` must be symmetric                 |
| E009 🔧 | No bad math operators (`\|` etc.)                    |
| E010 🔧 | No `$$ ... $$`                                       |
| E011    | No adjacent `\[ ... \]` blocks                       |
| E012    | `\begin{align*}` / `\end{align*}` must have own line |
| E013 🔧 | Env contents must be indented                        |
| E014 🔧 | No trailing whitespace                               |
| E015    | No `\\\\` paragraph break                            |
| E017 🔧 | No `:` for function signatures                       |

Rules not implemented:

- Rule 8 (balanced delimiters): hard to lint reliably.
- Rule 16 (variables in prose): requires natural-language understanding.

### E001

E001 skips two kinds of unfixable long lines:
those containing a URL (`http://` or `https://`),
and fully-commented lines (only whitespace before the `%`).
Lines with a long _trailing_ comment after real content are still flagged.

I recommend [SemBr](https://github.com/admk/sembr)
for automatically adding line breaks.

### E004

E004 picks the right `\dots` variant from context
(`\dotsc` after a comma, `\dotsb` after an operator)
and leaves a `\cdots` unresolved when neither side determines spacing.

### E013

E013 checks every env except a small denylist:
`document`, `center`, `quote`,
and the verbatim envs (`asy`, `verbatim`, `lstlisting`, …).
See `NO_INDENT_ENVS` in `lastlint.py` to adjust.

The `--fix` pads under-indented lines inside indent envs to `2 * depth` spaces
(already-correctly-indented or deeper lines are left alone).

## Development

```sh
pip install -e .[dev]
pytest
```
