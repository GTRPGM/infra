from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "docs/dev/detail/ref_contract_matrix.md"


def test_contract_matrix_exists_and_has_core_sections() -> None:
    assert MATRIX_PATH.exists(), "contract inventory document is missing"
    text = MATRIX_PATH.read_text(encoding="utf-8")

    required_headers = [
        "## 1) Immutable Contract Sources",
        "### Scenario Service -> State Manager (`/state/scenario/inject`)",
        "### GM -> Rule Engine (`/play/scenario`)",
        "### GM -> Scenario Service (`/api/v1/check/validate`)",
        "### GM -> State Manager",
        "### BE-router -> GM proxy (`/gm/turn`)",
        "## 3) Defect List (Severity / Owner)",
    ]
    for header in required_headers:
        assert header in text, f"missing section: {header}"


def test_contract_matrix_referenced_paths_exist() -> None:
    text = MATRIX_PATH.read_text(encoding="utf-8")
    paths = re.findall(r"`((?:services|docs)/[^`]+)`", text)
    assert paths, "no repository paths found in contract matrix"

    missing = [p for p in paths if not (ROOT / p).exists()]
    assert not missing, f"referenced paths do not exist: {missing}"


def test_contract_matrix_has_severity_levels() -> None:
    text = MATRIX_PATH.read_text(encoding="utf-8")
    for level in ["Blocker", "Major", "Minor"]:
        assert level in text, f"missing severity level: {level}"
