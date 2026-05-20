from pathlib import Path

import pytest

from evan_latex_lint import find_inline_math, lint_text, mask_verbatim

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
        (r"$x=3,$", "E005"),
        ("foo ,bar", "E006"),
        ("$x =3$", "E007"),
        ("$a||b$", "E009"),
        ("$$x$$", "E010"),
        (r"\] \[", "E011"),
        (r"\begin{align*} a", "E012"),
        (r"foo\\\\", "E015"),
        (r"$f : \mathbb{R}$", "E017"),
        ("\\begin{itemize}\n\\ii bad\n\\end{itemize}\n", "E013"),
    ],
)
def test_individual_rule(snippet: str, rule: str):
    assert rule in rules(snippet)
