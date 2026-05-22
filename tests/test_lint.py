from pathlib import Path

import pytest

from otis_latex_lint import find_inline_math, fix_text, lint_text, mask_verbatim

FIXTURES = Path(__file__).parent / "fixtures"


def rules(text: str) -> set[str]:
    return {f.rule for f in lint_text(text)}


def test_violations_fixture_covers_all_rules():
    text = (FIXTURES / "violations.tex").read_text()
    expected = {
        "E001",
        "E002",
        "E003",
        "E004",
        "E005",
        "E006",
        "E007",
        "E009",
        "E010",
        "E011",
        "E012",
        "E013",
        "E014",
        "E015",
        "E017",
    }
    got = rules(text)
    missing = expected - got
    assert not missing, f"missing rules: {sorted(missing)}"


def test_clean_fixture_has_no_findings():
    text = (FIXTURES / "clean.tex").read_text()
    findings = lint_text(text)
    assert not findings, "\n".join(f.format("clean.tex") for f in findings)


def test_inline_math_spans():
    assert find_inline_math("hello $a+b$ world") == [(6, 11)]
    assert find_inline_math("none here") == []
    assert find_inline_math(r"$a$ and $b$") == [(0, 3), (8, 11)]
    # escaped $ is not math
    assert find_inline_math(r"$5 \$ x$") == [(0, 8)]
    # $$ is not inline math
    assert find_inline_math(r"$$x = 1$$") == []


def test_verbatim_envs_are_masked():
    text = 'before\n\\begin{asy}\nlabel("$X$");\n\\end{asy}\nafter'
    masked = mask_verbatim(text)
    assert "label" not in masked
    assert "before" in masked and "after" in masked
    # newlines preserved (so line numbers stay correct)
    assert masked.count("\n") == text.count("\n")


def test_suppression_pragma():
    text = 'A line with "literal" quotes.  % latex-lint: disable=E002\n'
    assert "E002" not in rules(text)


def test_dollar_in_asy_is_not_flagged():
    text = '\\begin{asy}\nlabel("$X$");\n\\end{asy}\n'
    assert not lint_text(text)


@pytest.mark.parametrize(
    "snippet,rule",
    [
        ("a" * 101, "E001"),
        ('Say "hi"', "E002"),
        ("$sin(x)$", "E003"),
        (r"$x \ldots y$", "E004"),
        ("foo...bar", "E004"),
        (r"$x=3,$", "E005"),
        ("foo ,bar", "E006"),
        ("$x =3$", "E007"),
        ("$a||b$", "E009"),
        ("$a | b$", "E009"),
        ("$a * b$", "E009"),
        ("$2x4$", "E009"),
        ("$n mod 7$", "E009"),
        ("$$x$$", "E010"),
        (r"\] \[", "E011"),
        (r"\begin{align*} a", "E012"),
        (r"foo\\\\", "E015"),
        (r"$f : \mathbb{R}$", "E017"),
        ("\\begin{itemize}\n\\ii bad\n\\end{itemize}\n", "E013"),
        ("trailing spaces here   ", "E014"),
    ],
)
def test_individual_rule(snippet: str, rule: str):
    assert rule in rules(snippet)


def test_fix_E013_pads_under_indented_lines():
    text = "\\begin{itemize}\n\\ii bad indent here\n\\end{itemize}\n"
    fixed = fix_text(text)
    assert fixed == "\\begin{itemize}\n  \\ii bad indent here\n\\end{itemize}\n"
    assert "E013" not in rules(fixed)


def test_fix_E013_preserves_deeper_indent():
    text = "\\begin{itemize}\n      \\ii deep\n\\end{itemize}\n"
    assert fix_text(text) == text


def test_fix_E013_handles_nesting():
    text = (
        "\\begin{itemize}\n"
        "\\ii outer\n"
        "\\begin{enumerate}\n"
        "\\ii inner\n"
        "\\end{enumerate}\n"
        "\\end{itemize}\n"
    )
    fixed = fix_text(text)
    assert fixed == (
        "\\begin{itemize}\n"
        "  \\ii outer\n"
        "  \\begin{enumerate}\n"
        "    \\ii inner\n"
        "  \\end{enumerate}\n"
        "\\end{itemize}\n"
    )
    assert "E013" not in rules(fixed)


def test_fix_E013_skips_overflow():
    # A line that would exceed the 100-char limit once padded is left alone.
    body = "\\ii " + "x" * 97  # 101 chars; +2 indent would make 103
    text = f"\\begin{{itemize}}\n{body}\n\\end{{itemize}}\n"
    fixed = fix_text(text)
    assert f"\n{body}\n" in fixed  # untouched, no leading spaces added


def test_fix_E013_skips_verbatim():
    text = "\\begin{itemize}\n\\begin{verbatim}\nfoo\n\\end{verbatim}\n\\end{itemize}\n"
    fixed = fix_text(text)
    # verbatim body line must be untouched (no leading spaces added)
    assert "\nfoo\n" in fixed


def test_fix_is_idempotent_on_clean_fixture():
    text = (FIXTURES / "clean.tex").read_text()
    assert fix_text(text) == text


@pytest.mark.parametrize(
    "before,after,rule",
    [
        ('Say "hi" loud', "Say ``hi'' loud", "E002"),
        ("$sin(x) + cos(y)$", r"$\sin(x) + \cos(y)$", "E003"),
        (r"$x \ldots y \cdots z$", r"$x \dots y \dots z$", "E004"),
        (r"We have $x = 3.$ done", r"We have $x = 3$. done", "E005"),
        ("foo , bar ; baz", "foo, bar; baz", "E006"),
        ("$a||b$", r"$a\parallel b$", "E009"),
        (r"$a | b$", r"$a \mid b$", "E009"),
        (r"$x...y$", r"$x\dots y$", "E004"),
        ("$$x = 1$$", r"\[x = 1\]", "E010"),
        (r"$f : \mathbb{R}$", r"$f \colon \mathbb{R}$", "E017"),
        ("clean line  ", "clean line", "E014"),
    ],
)
def test_fix_resolves_rule(before: str, after: str, rule: str):
    fixed = fix_text(before)
    assert fixed == after
    assert rule not in rules(fixed)
    assert fix_text(fixed) == fixed


def test_fix_E002_skips_verbatim():
    text = '\\begin{verbatim}\nprint("hi")\n\\end{verbatim}\n'
    assert fix_text(text) == text


def test_E002_ignores_umlaut_accent():
    # `\"` is the umlaut accent (e.g. Erd\"os), not a literal quote.
    text = 'Paul Erd\\"os and Kurt G\\"{o}del.\n'
    assert "E002" not in rules(text)
    assert fix_text(text) == text


def test_ignore_skips_reporting():
    text = 'Say "hi"\n'
    assert "E002" in {f.rule for f in lint_text(text)}
    assert "E002" not in {f.rule for f in lint_text(text, frozenset({"E002"}))}


def test_ignore_skips_fixing():
    text = 'Say "hi"\n'
    assert fix_text(text, frozenset({"E002"})) == text


def test_fix_E010_alternates_pairs():
    text = "$$a$$ and $$b$$"
    assert fix_text(text) == r"\[a\] and \[b\]"
