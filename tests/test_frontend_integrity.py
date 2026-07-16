import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "frontend" / "index.js").read_text(encoding="utf-8")


def test_html_ids_are_unique():
    ids = re.findall(r'\bid="([^"]+)"', HTML)

    assert len(ids) == len(set(ids))


def test_every_navigation_target_has_a_panel():
    targets = set(re.findall(r'data-target="([^"]+)"', HTML))
    panel_ids = set(re.findall(r'id="([^"]+)-panel"', HTML))

    assert targets <= panel_ids


def test_static_javascript_ids_exist_in_html():
    referenced = set(re.findall(r'getElementById\("([^"]+)"\)', JS))
    declared = set(re.findall(r'\bid="([^"]+)"', HTML))
    dynamically_rendered = {
        "alert-detail-cases",
        "alert-evidence-list",
        "alert-evidence-panel",
        "alert-dispatch-action",
        "alert-export-report",
        "alert-action-status",
    }

    assert referenced - declared - dynamically_rendered == set()


def test_no_demo_alert_popups_remain_in_operational_actions():
    assert "onclick=\"alert(" not in JS
