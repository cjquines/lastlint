"""Linter for Evan Chen's LaTeX style guide.

https://web.evanchen.cc/latex-style-guide.html
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

MAX_LINE_LENGTH = 100

# Operators that should always be typeset as commands (\sin, not sin).
# Source: amsmath \DeclareMathOperator list; keep this conservative to avoid
# matching identifiers in prose that happen to be inside dollar signs.
OPERATORS = (
    "arccos arcsin arctan arg cos cosh cot coth csc deg det dim exp gcd hom "
    "inf injlim ker lcm lg lim liminf limsup ln log max min Pr projlim sec "
    "sin sinh sup tan tanh"
).split()

# Envs whose contents are not LaTeX prose and should be skipped.
VERBATIM_ENVS = ("asy", "asydef", "verbatim", "lstlisting", "minted")

SUPPRESS_RE = re.compile(r"%\s*latex-lint:\s*disable=([A-Z0-9, ]+)")


@dataclass(frozen=True)
class Finding:
    rule: str
    line: int
    col: int
    msg: str

    def format(self, path: str) -> str:
        return f"{path}:{self.line}:{self.col}: {self.rule}: {self.msg}"


# --------------------------------------------------------------------------- #
# Source model
# --------------------------------------------------------------------------- #


class Source:
    """The text of a file, plus a version with verbatim envs, comments, and
    anything after ``\\end{document}`` blanked out.

    Blanking preserves line numbers and character offsets, so positions
    reported against ``masked`` are still valid against the original text.
    Comment masking means rules never lint commented-out LaTeX; only E001
    (line length) and E014 (trailing whitespace), which scan raw ``lines``,
    still see comment text.
    """

    def __init__(self, text: str):
        self.text = text
        self.lines = text.split("\n")
        self.masked_lines, self.verbatim_lines = scan_verbatim(self.lines)
        self.masked_lines = [mask_comment(line) for line in self.masked_lines]
        self.masked_lines = mask_after_end_document(self.masked_lines)
        self.masked = "\n".join(self.masked_lines)
        self.suppressions = parse_suppressions(self.lines)

    def is_suppressed(self, line: int, rule: str) -> bool:
        return rule in self.suppressions.get(line, ())


_VERBATIM_BEGIN_RE = re.compile(rf"\\begin\{{({'|'.join(VERBATIM_ENVS)})\*?\}}")


def scan_verbatim(lines: list[str]) -> tuple[list[str], set[int]]:
    """Mask verbatim env contents and return the set of fully-verbatim line numbers.

    A line is "fully verbatim" iff it lies strictly between a verbatim env's
    \\begin and \\end. Lines containing either are partially verbatim (the
    LaTeX command part survives masking) and are not included.
    """
    masked = list(lines)
    verbatim_lines: set[int] = set()
    in_env: str | None = None

    for i, line in enumerate(lines, 1):
        if in_env is None:
            m = _VERBATIM_BEGIN_RE.search(line)
            if m:
                in_env = m.group(1)
                cut = m.end()
                masked[i - 1] = line[:cut] + " " * (len(line) - cut)
        else:
            end_re = re.compile(rf"\\end\{{{in_env}\*?\}}")
            m = end_re.search(line)
            if m:
                cut = m.start()
                masked[i - 1] = " " * cut + line[cut:]
                in_env = None
            else:
                masked[i - 1] = " " * len(line)
                verbatim_lines.add(i)
    return masked, verbatim_lines


def mask_verbatim(text: str) -> str:
    """Backwards-compatible wrapper used by tests."""
    masked_lines, _ = scan_verbatim(text.split("\n"))
    return "\n".join(masked_lines)


_COMMENT_RE = re.compile(r"(?<!\\)%")


def mask_comment(line: str) -> str:
    """Blank a trailing LaTeX comment (``%`` to end of line) with spaces.

    Run after verbatim masking, so any ``%`` here is a genuine comment, not
    verbatim content. ``\\%`` (an escaped literal percent) is left alone.
    """
    m = _COMMENT_RE.search(line)
    return line[: m.start()] + " " * (len(line) - m.start()) if m else line


_END_DOCUMENT_RE = re.compile(r"\\end\{document\}")


def mask_after_end_document(lines: list[str]) -> list[str]:
    """Blank everything strictly after the first ``\\end{document}``.

    LaTeX ignores it, so neither should the linter. Run after verbatim and
    comment masking, so an ``\\end{document}`` inside a verbatim block or a
    comment doesn't count.
    """
    out = list(lines)
    for i, line in enumerate(lines):
        m = _END_DOCUMENT_RE.search(line)
        if m:
            out[i] = line[: m.end()] + " " * (len(line) - m.end())
            for j in range(i + 1, len(lines)):
                out[j] = " " * len(lines[j])
            break
    return out


def parse_suppressions(lines: list[str]) -> dict[int, set[str]]:
    result: dict[int, set[str]] = {}
    for i, line in enumerate(lines, 1):
        m = SUPPRESS_RE.search(line)
        if m:
            result[i] = {tok.strip() for tok in m.group(1).split(",") if tok.strip()}
    return result


def find_inline_math(line: str) -> list[tuple[int, int]]:
    """Return [(start, end)] spans of $...$ on the line, end-exclusive.

    Skips escaped dollars (\\$) and double-dollars ($$); does not handle
    inline math that crosses a newline (rare in practice).
    """
    spans: list[tuple[int, int]] = []
    i = 0
    start = -1
    n = len(line)
    while i < n:
        c = line[i]
        if c == "\\" and i + 1 < n:
            i += 2
            continue
        if c == "$":
            if i + 1 < n and line[i + 1] == "$":
                i += 2
                continue
            if start == -1:
                start = i
            else:
                spans.append((start, i + 1))
                start = -1
            i += 1
            continue
        i += 1
    return spans


def offset_to_line_col(text: str, offset: int) -> tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    col = offset - (text.rfind("\n", 0, offset) + 1) + 1
    return line, col


# --------------------------------------------------------------------------- #
# Rules
# --------------------------------------------------------------------------- #


def rule_E001_line_length(src: Source) -> Iterator[Finding]:
    for i, line in enumerate(src.lines, 1):
        if i in src.verbatim_lines:
            continue
        if len(line) > MAX_LINE_LENGTH:
            yield Finding(
                "E001",
                i,
                MAX_LINE_LENGTH + 1,
                f"line is {len(line)} characters; max {MAX_LINE_LENGTH}",
            )


# A bare ASCII double quote, but not `\"` (the LaTeX umlaut accent, e.g. `\"o`).
_LITERAL_QUOTE_RE = re.compile(r'(?<!\\)"')


def rule_E002_literal_quote(src: Source) -> Iterator[Finding]:
    for i, line in enumerate(src.masked_lines, 1):
        for m in _LITERAL_QUOTE_RE.finditer(line):
            yield Finding(
                "E002", i, m.start() + 1, "literal \" is forbidden; use `` or ''"
            )


_OP_RE = re.compile(r"(?<![A-Za-z\\])(" + "|".join(OPERATORS) + r")(?![A-Za-z])")


def rule_E003_bare_operator(src: Source) -> Iterator[Finding]:
    for i, line in enumerate(src.masked_lines, 1):
        for s, e in find_inline_math(line):
            for m in _OP_RE.finditer(line, s, e):
                yield Finding(
                    "E003",
                    i,
                    m.start() + 1,
                    f"bare operator {m.group(1)!r}; use \\{m.group(1)}",
                )


def rule_E004_old_dots(src: Source) -> Iterator[Finding]:
    for i, line in enumerate(src.masked_lines, 1):
        for m in re.finditer(r"\\(ldots|cdots)\b", line):
            yield Finding(
                "E004", i, m.start() + 1, rf"\{m.group(1)} is forbidden; use \dots"
            )
        for m in re.finditer(r"\.{3,}", line):
            yield Finding(
                "E004", i, m.start() + 1, "literal '...' is forbidden; use \\dots"
            )


def rule_E005_math_punct(src: Source) -> Iterator[Finding]:
    # Grammatical punctuation immediately before the closing $ of inline math.
    # This is the common banned pattern: $x=3.$, $a,b,$.
    # Note: middle commas like $f(a,b)$ are mathematical, not grammatical,
    # and end with `)`, so they are not flagged.
    for i, line in enumerate(src.masked_lines, 1):
        for s, e in find_inline_math(line):
            if e - s >= 3 and line[e - 2] in ",.":
                yield Finding(
                    "E005",
                    i,
                    e - 1,
                    f"grammatical {line[e - 2]!r} inside math; move outside $",
                )


# ':' intentionally omitted: it has too many legitimate spaced uses
# (barycentric coordinates `(a : b : c)`, etc.).
_E006_RE = re.compile(r"(\S+)( +)([.,;!?])")


def _e006_matches(line: str) -> Iterator[re.Match[str]]:
    for m in _E006_RE.finditer(line):
        tok = m.group(1)
        # `\item ?`, `\item[label] ?`, etc.: the space terminating a control
        # word (or its optional arg) is required syntax, not a stray space.
        # But `\textbf{x} .` has a genuine stray space — the `}` already
        # closed the argument — so only exempt tokens not ending in `}`.
        is_command = tok.startswith("\\") and tok[1:2].isalpha()
        if not is_command or tok.endswith("}"):
            yield m


def rule_E006_space_before_punct(src: Source) -> Iterator[Finding]:
    for i, line in enumerate(src.masked_lines, 1):
        for m in _e006_matches(line):
            yield Finding(
                "E006", i, m.start(3) + 1, f"extra space before {m.group(3)!r}"
            )


def rule_E007_asymmetric_spacing(src: Source) -> Iterator[Finding]:
    # Detect `x =3` or `x= 3` patterns inside inline math.
    pat = re.compile(r"\S +=\S|\S= +\S")
    for i, line in enumerate(src.masked_lines, 1):
        for s, e in find_inline_math(line):
            for m in pat.finditer(line, s + 1, e - 1):
                yield Finding("E007", i, m.start() + 1, "asymmetric spacing around '='")


# Bad math operators, all reported under E009.
_PARALLEL_RE = re.compile(r"\|\|")
_MID_RE = re.compile(r" \| ")  # a spaced single bar is a relation, not |x|
_STAR_RE = re.compile(r"(?<![\^_{\\])\*")  # bare *, not a superscript star ^*
_TIMES_X_RE = re.compile(r"\d\s*x\s*\d")  # 2x4 / 2 x 4: x is multiplication
_MOD_RE = re.compile(r"(?<![A-Za-z\\])mod(?![A-Za-z])")  # not \bmod / \pmod


def rule_E009_bad_math_ops(src: Source) -> Iterator[Finding]:
    for i, line in enumerate(src.masked_lines, 1):
        for s, e in find_inline_math(line):
            for m in _PARALLEL_RE.finditer(line, s, e):
                yield Finding("E009", i, m.start() + 1, "|| in math; use \\parallel")
            for m in _MID_RE.finditer(line, s, e):
                yield Finding("E009", i, m.start() + 2, "| in math; use \\mid")
            for m in _STAR_RE.finditer(line, s, e):
                yield Finding(
                    "E009", i, m.start() + 1, "* in math; use \\cdot or \\times"
                )
            for m in _TIMES_X_RE.finditer(line, s, e):
                yield Finding(
                    "E009",
                    i,
                    m.start() + 1,
                    "literal 'x' between numbers; use \\times",
                )
            for m in _MOD_RE.finditer(line, s, e):
                yield Finding(
                    "E009", i, m.start() + 1, "literal 'mod'; use \\bmod or \\pmod"
                )


def rule_E010_double_dollar(src: Source) -> Iterator[Finding]:
    for m in re.finditer(r"\$\$", src.masked):
        line, col = offset_to_line_col(src.masked, m.start())
        yield Finding("E010", line, col, r"$$ is forbidden; use \[ ... \]")


def rule_E011_adjacent_display(src: Source) -> Iterator[Finding]:
    for m in re.finditer(r"\\\]\s*\\\[", src.masked):
        line, col = offset_to_line_col(src.masked, m.start())
        yield Finding(
            "E011", line, col, "adjacent \\[ ... \\] blocks should be one align*"
        )


def rule_E012_align_line(src: Source) -> Iterator[Finding]:
    pat = re.compile(r"\\(begin|end)\{align\*\}")
    for i, line in enumerate(src.masked_lines, 1):
        for m in pat.finditer(line):
            before = line[: m.start()]
            after = line[m.end() :]
            if before.strip() or after.strip():
                yield Finding(
                    "E012",
                    i,
                    m.start() + 1,
                    rf"\{m.group(1)}{{align*}} must be on its own line",
                )


def rule_E014_trailing_whitespace(src: Source) -> Iterator[Finding]:
    for i, line in enumerate(src.lines, 1):
        if i in src.verbatim_lines:
            continue
        m = re.search(r"[ \t]+$", line)
        if m:
            yield Finding("E014", i, m.start() + 1, "trailing whitespace")


def rule_E015_double_backslash_break(src: Source) -> Iterator[Finding]:
    # Match literal four backslashes followed by end-of-line or whitespace.
    # `\\` (two chars) inside a tabular/align is legal; `\\\\` as a paragraph
    # break is not.
    for i, line in enumerate(src.masked_lines, 1):
        for m in re.finditer(r"\\\\\\\\", line):
            yield Finding(
                "E015",
                i,
                m.start() + 1,
                r"\\\\ paragraph break is forbidden; use a blank line",
            )


# Envs whose body lines should be indented at least 2 spaces per nesting level.
# Denylist: every env counts toward indent depth except these. `document`,
# `center`, and `quote` wrap ordinary prose that idiomatically stays flush
# left; the verbatim envs have their contents masked and must not nest depth.
NO_INDENT_ENVS = frozenset({"document", "center", "quote"}) | set(VERBATIM_ENVS)

_BEGIN_END_RE = re.compile(r"\\(begin|end)\{([^}]+)\}")


def rule_E013_indentation(src: Source) -> Iterator[Finding]:
    depth = 0  # indent envs currently open
    for i, line in enumerate(src.masked_lines, 1):
        if i in src.verbatim_lines or not line.strip():
            # update depth only for non-verbatim, non-blank lines
            pass
        # Determine the starting depth for THIS line: if the line opens or
        # closes an env, the begin/end token itself sits at the outer depth.
        first_token = _BEGIN_END_RE.search(line)
        line_starts_with_end = bool(
            re.match(r"\s*\\end\{", line)
            and first_token
            and first_token.group(1) == "end"
        )

        # Effective depth for the indentation check on this line.
        effective_depth = depth - 1 if line_starts_with_end else depth

        if effective_depth > 0 and line.strip() and i not in src.verbatim_lines:
            indent = len(line) - len(line.lstrip(" "))
            expected = 2 * effective_depth
            if indent < expected:
                yield Finding(
                    "E013",
                    i,
                    1,
                    f"line should be indented at least {expected} spaces "
                    f"(env depth {effective_depth})",
                )

        # Update depth from all begin/end on this line.
        for m in _BEGIN_END_RE.finditer(line):
            kind, env = m.group(1), m.group(2)
            if env not in NO_INDENT_ENVS:
                depth += 1 if kind == "begin" else -1
        if depth < 0:
            depth = 0  # tolerate mismatched envs


_FONT_CMD = r"\\(math[a-z]+|[A-Z]+)\b"
_COLON_RE = re.compile(rf"[A-Za-z][ \t]*:[ \t]*{_FONT_CMD}")
# Only treat `:` as a function-signature colon when the math span also has a
# mapping arrow; a bare `:` is usually a ratio (`1 : 2`) and correct as-is.
_ARROW_RE = re.compile(
    r"\\(to|mapsto|rightarrow|longrightarrow|hookrightarrow)(?![a-zA-Z])"
)


def rule_E017_colon(src: Source) -> Iterator[Finding]:
    for i, line in enumerate(src.masked_lines, 1):
        for s, e in find_inline_math(line):
            if not _ARROW_RE.search(line, s + 1, e - 1):
                continue
            for m in _COLON_RE.finditer(line, s + 1, e - 1):
                yield Finding(
                    "E017",
                    i,
                    m.start() + 1,
                    "use \\colon for function signatures, not ':'",
                )


def _apply_line_edits(raw: str, edits: list[tuple[int, int, str]]) -> str:
    """Apply (start, end, replacement) edits to one line, right-to-left."""
    for s, e, repl in sorted(edits, key=lambda x: x[0], reverse=True):
        raw = raw[:s] + repl + raw[e:]
    return raw


def _per_line_fix(
    src: Source, edits_for: Callable[[int, str], list[tuple[int, int, str]]]
) -> str:
    out: list[str] = []
    for i, line in enumerate(src.masked_lines, 1):
        out.append(_apply_line_edits(src.lines[i - 1], edits_for(i, line)))
    return "\n".join(out)


def fix_E002_literal_quote(src: Source) -> str:
    """Convert " to `` (opener) or '' (closer) using a context heuristic."""

    def edits(_i: int, line: str) -> list[tuple[int, int, str]]:
        out = []
        for m in _LITERAL_QUOTE_RE.finditer(line):
            pos = m.start()
            prev = line[pos - 1] if pos > 0 else " "
            repl = "''" if prev.isalnum() or prev in ".,;:!?)]}" else "``"
            out.append((pos, pos + 1, repl))
        return out

    return _per_line_fix(src, edits)


def fix_E003_bare_operator(src: Source) -> str:
    def edits(_i: int, line: str) -> list[tuple[int, int, str]]:
        out = []
        for s, e in find_inline_math(line):
            for m in _OP_RE.finditer(line, s, e):
                out.append((m.start(), m.end(), "\\" + m.group(1)))
        return out

    return _per_line_fix(src, edits)


_DOTS_RE = re.compile(r"\\(?:ldots|cdots)\b|\.{3,}")
_DOTS_COMMA = {",", ";"}
_DOTS_BINOP_CHARS = set("+-=<>")
# Common binary-operator / relation control words. amsmath's \dotsb covers
# both, so no need to distinguish them.
_DOTS_BINOP_WORDS = {
    "cdot",
    "cdots",
    "times",
    "pm",
    "mp",
    "cup",
    "cap",
    "oplus",
    "otimes",
    "le",
    "ge",
    "leq",
    "geq",
    "ne",
    "neq",
    "approx",
    "sim",
    "simeq",
    "cong",
    "equiv",
    "subset",
    "subseteq",
    "supset",
    "supseteq",
    "to",
    "mapsto",
    "wedge",
    "vee",
    "div",
    "ast",
    "star",
    "circ",
    "bullet",
    "ll",
    "gg",
    "prec",
    "succ",
}


def _dots_token_class(token: str) -> str | None:
    """Classify a neighbouring token as 'comma', 'binop', or None."""
    if token in _DOTS_COMMA:
        return "comma"
    if token in _DOTS_BINOP_CHARS:
        return "binop"
    if token.startswith("\\") and token[1:] in _DOTS_BINOP_WORDS:
        return "binop"
    return None


def fix_E004_old_dots(src: Source) -> str:
    """Replace \\ldots/\\cdots/literal ... with the right \\dots variant.

    \\dots picks its spacing from the *following* token, so a bare \\dots is
    only safe when that token determines it. When it doesn't (end of math, a
    letter, a closing delimiter), we look at the *preceding* token and emit an
    explicit \\dotsc/\\dotsb instead; if neither side resolves it and the
    author wrote \\cdots, we leave it for them (the rule still flags it).
    """

    def edits(_i: int, line: str) -> list[tuple[int, int, str]]:
        spans = find_inline_math(line)
        out = []
        for m in _DOTS_RE.finditer(line):
            span = next(((s, e) for s, e in spans if s < m.start() < e), None)
            if span is None:
                # Prose ellipsis: \dots is correct and context-free.
                repl = r"\dots"
            else:
                # Search only within the enclosing $...$, excluding the $s.
                lo, hi = span[0] + 1, span[1] - 1
                before = line[lo : m.start()].rstrip()
                after = line[m.end() : hi].lstrip()
                cw = re.search(r"\\[a-zA-Z]+$", before)
                prev = cw.group() if cw else before[-1:]
                cwf = re.match(r"\\[a-zA-Z]+", after)
                nxt = cwf.group() if cwf else after[:1]

                if _dots_token_class(nxt) is not None:
                    repl = r"\dots"  # \dots detects this forward correctly
                elif _dots_token_class(prev) == "comma":
                    repl = r"\dotsc"
                elif _dots_token_class(prev) == "binop":
                    repl = r"\dotsb"
                elif m.group() == r"\cdots":
                    continue  # undeterminable; leave it for the author
                else:
                    repl = r"\dots"

            # `2...x` -> `2\dots x`: a control word needs a space before an
            # alphanumeric, or it would be read as part of the command name.
            if m.group().startswith(".") and m.end() < len(line):
                if line[m.end()].isalnum():
                    repl += " "
            out.append((m.start(), m.end(), repl))
        return out

    return _per_line_fix(src, edits)


def fix_E005_math_punct(src: Source) -> str:
    """Move a trailing `.` or `,` from inside inline math to just after it."""

    def edits(_i: int, line: str) -> list[tuple[int, int, str]]:
        out = []
        for s, e in find_inline_math(line):
            if e - s >= 3 and line[e - 2] in ",.":
                out.append((e - 2, e, "$" + line[e - 2]))
        return out

    return _per_line_fix(src, edits)


def fix_E006_space_before_punct(src: Source) -> str:
    def edits(_i: int, line: str) -> list[tuple[int, int, str]]:
        return [(m.start(2), m.end(2), "") for m in _e006_matches(line)]

    return _per_line_fix(src, edits)


def fix_E009_bad_math_ops(src: Source) -> str:
    """Fix the unambiguous E009 cases: || -> \\parallel and ` | ` -> ` \\mid `.

    ``*``, ``x``-as-times, and bare ``mod`` are left for the author: the
    correct replacement (\\cdot vs \\times, \\bmod vs \\pmod) is ambiguous.
    """

    def edits(_i: int, line: str) -> list[tuple[int, int, str]]:
        out = []
        for s, e in find_inline_math(line):
            for m in _PARALLEL_RE.finditer(line, s, e):
                pos = m.start()
                after = line[pos + 2] if pos + 2 < len(line) else ""
                repl = r"\parallel" + (" " if after.isalpha() else "")
                out.append((pos, pos + 2, repl))
            for m in _MID_RE.finditer(line, s, e):
                out.append((m.start(), m.end(), r" \mid "))
        return out

    return _per_line_fix(src, edits)


def fix_E010_double_dollar(src: Source) -> str:
    """Replace alternating `$$` with `\\[` and `\\]`."""
    parts: list[str] = []
    last = 0
    opening = True
    for m in re.finditer(r"\$\$", src.masked):
        parts.append(src.text[last : m.start()])
        parts.append(r"\[" if opening else r"\]")
        opening = not opening
        last = m.end()
    parts.append(src.text[last:])
    return "".join(parts)


def fix_E017_colon(src: Source) -> str:
    def edits(_i: int, line: str) -> list[tuple[int, int, str]]:
        out = []
        for s, e in find_inline_math(line):
            if not _ARROW_RE.search(line, s + 1, e - 1):
                continue
            for m in _COLON_RE.finditer(line, s + 1, e - 1):
                colon = line.index(":", m.start(), m.end())
                out.append((colon, colon + 1, r"\colon"))
        return out

    return _per_line_fix(src, edits)


def fix_E013_indentation(src: Source) -> str:
    """Pad under-indented lines inside indenting envs to ``2 * depth`` spaces.

    Lines already at or beyond the expected indent are left untouched, so
    deeper hand-alignment (e.g. continuation lines) is preserved.
    """
    out: list[str] = []
    depth = 0
    for i, line in enumerate(src.masked_lines, 1):
        raw = src.lines[i - 1]
        first_token = _BEGIN_END_RE.search(line)
        line_starts_with_end = bool(
            re.match(r"\s*\\end\{", line)
            and first_token
            and first_token.group(1) == "end"
        )
        effective_depth = depth - 1 if line_starts_with_end else depth

        # ``line`` is comment-masked, so a comment-only line is blank here and
        # is left untouched — consistent with the rule, which won't flag it.
        if effective_depth > 0 and line.strip() and i not in src.verbatim_lines:
            indent = len(raw) - len(raw.lstrip(" "))
            expected = 2 * effective_depth
            stripped = raw.lstrip(" ")
            # Don't pad a line past the E001 length limit: that would just
            # trade an E013 for an E001. Leave it for the author to rewrap;
            # E013 still reports it.
            if indent < expected and expected + len(stripped) <= MAX_LINE_LENGTH:
                raw = " " * expected + stripped

        out.append(raw)

        for m in _BEGIN_END_RE.finditer(line):
            kind, env = m.group(1), m.group(2)
            if env not in NO_INDENT_ENVS:
                depth += 1 if kind == "begin" else -1
        if depth < 0:
            depth = 0
    return "\n".join(out)


def fix_E014_trailing_whitespace(src: Source) -> str:
    out = []
    for i, line in enumerate(src.lines, 1):
        out.append(line if i in src.verbatim_lines else line.rstrip(" \t"))
    return "\n".join(out)


FIXERS: dict[str, Callable[[Source], str]] = {
    "E002": fix_E002_literal_quote,
    "E003": fix_E003_bare_operator,
    "E004": fix_E004_old_dots,
    "E005": fix_E005_math_punct,
    "E006": fix_E006_space_before_punct,
    "E009": fix_E009_bad_math_ops,
    "E010": fix_E010_double_dollar,
    "E013": fix_E013_indentation,
    "E014": fix_E014_trailing_whitespace,
    "E017": fix_E017_colon,
}


RULES: list[Callable[[Source], Iterator[Finding]]] = [
    rule_E001_line_length,
    rule_E002_literal_quote,
    rule_E003_bare_operator,
    rule_E004_old_dots,
    rule_E005_math_punct,
    rule_E006_space_before_punct,
    rule_E007_asymmetric_spacing,
    rule_E009_bad_math_ops,
    rule_E010_double_dollar,
    rule_E011_adjacent_display,
    rule_E012_align_line,
    rule_E013_indentation,
    rule_E014_trailing_whitespace,
    rule_E015_double_backslash_break,
    rule_E017_colon,
]


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #


def lint_text(text: str, ignore: frozenset[str] = frozenset()) -> list[Finding]:
    src = Source(text)
    findings: list[Finding] = []
    for rule in RULES:
        for f in rule(src):
            if f.rule not in ignore and not src.is_suppressed(f.line, f.rule):
                findings.append(f)
    findings.sort(key=lambda f: (f.line, f.col, f.rule))
    return findings


# Fixers can feed each other: e.g. E006 collapsing `. . .` into `...` exposes
# an E004. Run the whole pipeline until the file stops changing so a single
# `--fix` invocation always lands on a fixpoint.
MAX_FIX_PASSES = 8


def fix_text(text: str, ignore: frozenset[str] = frozenset()) -> str:
    """Apply every available fixer, repeating to a fixpoint.

    Idempotent on clean input. One fixer's output can be another's input, so
    a single pass is not enough to converge; iterate until stable.
    """
    for _ in range(MAX_FIX_PASSES):
        before = text
        for rule, fixer in FIXERS.items():
            if rule in ignore:
                continue
            src = Source(text)
            text = fixer(src)
        if text == before:
            break
    return text


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def lint_file(path: Path, ignore: frozenset[str] = frozenset()) -> list[Finding]:
    return lint_text(read_text(path), ignore)


ALL_RULES = frozenset(
    rule.__name__.split("_")[1] for rule in RULES
)  # {"E001", "E002", ...}


def parse_ignore(value: str) -> frozenset[str]:
    """Parse a comma-separated rule list, validating each code."""
    codes = {tok.strip().upper() for tok in value.split(",") if tok.strip()}
    unknown = codes - ALL_RULES
    if unknown:
        raise argparse.ArgumentTypeError(
            f"unknown rule(s): {', '.join(sorted(unknown))}"
        )
    return frozenset(codes)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="otis-latex-lint",
        description="Lint .tex files against Evan Chen's LaTeX style guide.",
    )
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument(
        "--fix",
        action="store_true",
        help=f"auto-fix rules where possible ({', '.join(sorted(FIXERS))}); "
        "writes files in place",
    )
    ap.add_argument(
        "--ignore",
        type=parse_ignore,
        default=frozenset(),
        metavar="E0XX,E0YY",
        help="comma-separated rule codes to skip (both reporting and fixing)",
    )
    args = ap.parse_args(argv)

    bad = 0
    for path in args.files:
        if args.fix:
            original = read_text(path)
            fixed = fix_text(original, args.ignore)
            if fixed != original:
                path.write_text(fixed, encoding="utf-8")
        for f in lint_file(path, args.ignore):
            print(f.format(str(path)))
            bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
