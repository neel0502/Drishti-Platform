import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "frontend" / "index.js").read_text(encoding="utf-8")
WORKSPACE_JS = (ROOT / "frontend" / "workspace-v2.js").read_text(encoding="utf-8")
WORKFLOW_JS = (ROOT / "frontend" / "workflow-v3.js").read_text(encoding="utf-8")
AGENT_JS = (ROOT / "frontend" / "agent-centre.js").read_text(encoding="utf-8")
COMMAND_JS = (ROOT / "frontend" / "command-assistant.js").read_text(encoding="utf-8")
COMMAND_CSS = (ROOT / "frontend" / "command-assistant.css").read_text(encoding="utf-8")
RESPONSIVE_CSS = (ROOT / "frontend" / "responsive-polish.css").read_text(encoding="utf-8")


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
        "agent-replay-button",
        "agent-audit-meta",
    }

    assert referenced - declared - dynamically_rendered == set()


def test_no_demo_alert_popups_remain_in_operational_actions():
    assert "onclick=\"alert(" not in JS


def test_officer_workspace_has_accessible_navigation_landmarks():
    assert 'class="skip-link" href="#main-workspace"' in HTML
    assert 'role="dialog" aria-modal="true"' in HTML
    assert 'role="tablist"' in HTML
    assert 'role="tabpanel"' in HTML
    assert HTML.count('aria-selected="true"') == 1


def test_demo_identity_boundary_is_visible_and_bilingual():
    assert 'class="identity-boundary-note"' in HTML
    assert 'data-i18n="identityBoundary"' in HTML
    assert 'identityBoundary:' in WORKSPACE_JS


def test_every_static_workspace_label_exists_in_both_languages():
    referenced = set(re.findall(r'data-i18n(?:-aria|-placeholder)?="([^"]+)"', HTML))
    en_block = re.search(r'en:\s*\{(.*?)\n\s*\},\n\s*kn:', WORKSPACE_JS, re.S).group(1)
    kn_block = re.search(r'kn:\s*\{(.*?)\n\s*\}\n\s*\};', WORKSPACE_JS, re.S).group(1)

    for key in referenced:
        pattern = rf'\b{re.escape(key)}\s*:'
        assert re.search(pattern, en_block), f"Missing English translation for {key}"
        assert re.search(pattern, kn_block), f"Missing Kannada translation for {key}"


def test_five_roles_have_distinct_home_priorities_and_actions():
    for role in ("command", "district", "station", "patrol", "analyst"):
        assert re.search(rf"\b{role}:\s*\{{[^}}]+greeting:", WORKSPACE_JS)
        assert re.search(rf"\b{role}:\s*\[", WORKFLOW_JS)


def test_police_tasks_are_primary_and_technical_agent_names_secondary():
    assert 'title: "Police tasks"' in AGENT_JS
    assert "agent-technical-name" in AGENT_JS
    assert '"patrol-shift-briefing": "Prepare this patrol shift"' in AGENT_JS


def test_agent_catalogue_ignores_stale_role_responses():
    assert "const requestedRole = role();" in AGENT_JS
    assert "if (requestedRole !== role()) return;" in AGENT_JS


def test_command_assistant_is_persistent_accessible_and_bilingual():
    assert 'id="command-orb"' in HTML
    assert 'id="command-assistant"' in HTML
    assert 'aria-modal="true"' in HTML
    assert "metaKey || event.ctrlKey" in COMMAND_JS
    assert 'event.key === "Tab"' in COMMAND_JS
    assert "trapFocus(event)" in COMMAND_JS
    assert "state.returnFocus" in COMMAND_JS
    assert "kn-IN" in COMMAND_JS


def test_command_assistant_is_role_scoped_and_human_controlled():
    assert 'currentRole === "patrol" ? "patrol-shift-briefing"' in COMMAND_JS
    assert 'roles: ["station", "district"]' in COMMAND_JS
    assert 'roles: ["command", "district"]' in COMMAND_JS
    assert 't("decisionDetail")' in COMMAND_JS
    assert "cannot dispatch, contact, alter records or approve action" in COMMAND_JS
    assert "window.DrishtiWorkspace?.openCase" in COMMAND_JS


def test_command_assistant_exposes_voice_sources_and_reduced_motion():
    assert "SpeechRecognition" in COMMAND_JS
    assert "speechSynthesis" in COMMAND_JS
    assert 'class="command-source"' in COMMAND_JS
    assert 'class="command-finding"' in COMMAND_JS
    assert "prefers-reduced-motion" in COMMAND_CSS


def test_today_voice_briefing_is_bilingual_private_and_controllable():
    assert 'id="today-voice-toggle"' in HTML
    assert 'id="today-voice-stop"' in HTML
    assert "SpeechSynthesisUtterance" in WORKSPACE_JS
    assert "speechSynthesis.pause()" in WORKSPACE_JS
    assert "speechSynthesis.resume()" in WORKSPACE_JS
    assert "speechSynthesis.cancel()" in WORKSPACE_JS
    assert 'utterance.lang = workspaceState.language === "kn" ? "kn-IN" : "en-IN"' in WORKSPACE_JS
    assert 'document.querySelectorAll("#today-priority-list .operational-item")' in WORKSPACE_JS
    assert 'briefingBoundary:' in WORKSPACE_JS


def test_today_detailed_ai_briefing_uses_bounded_shift_agent():
    assert 'id="today-ai-briefing-button"' in HTML
    assert 'id="today-ai-briefing"' in HTML
    assert 'fetch("/api/agents/run"' in WORKSPACE_JS
    assert 'currentRole() === "patrol" ? "patrol-shift-briefing" : "shift-briefing"' in WORKSPACE_JS
    assert 'body: JSON.stringify({ agentId, caseId: null, role: currentRole()' in WORKSPACE_JS
    assert 'data.run?.aiProvider === "deterministic-fallback"' in WORKSPACE_JS
    assert 'voiceBriefingState.aiText = String(data.answer || "")' in WORKSPACE_JS
    assert 'window.DrishtiAgents?.open(voiceBriefingState.aiAgentId, null)' in WORKSPACE_JS


def test_phone_and_tablet_shell_has_accessible_navigation():
    assert 'id="mobile-nav-scrim" hidden' in HTML
    assert "button.setAttribute('aria-expanded',String(open))" in JS
    assert "scrim.addEventListener('click'" in JS
    assert "event.key==='Escape'" in JS
    assert "window.innerWidth>900" in JS
    assert "@media (max-width: 900px)" in RESPONSIVE_CSS


def test_responsive_layer_prevents_known_workspace_overflow():
    assert ".agent-centre-layout > *" in RESPONSIVE_CSS
    assert "overflow-wrap: anywhere" in RESPONSIVE_CSS
    assert ".reconstruction-controls" in RESPONSIVE_CSS
    assert "grid-column: 1 / -1" in RESPONSIVE_CSS
    assert ".data-table-container" in RESPONSIVE_CSS
    assert "overflow-x: auto" in RESPONSIVE_CSS


def test_responsive_layer_enforces_touch_sized_controls():
    assert ".mobile-menu-btn" in RESPONSIVE_CSS
    assert ".search-submit" in RESPONSIVE_CSS
    assert ".command-close" in RESPONSIVE_CSS
    assert "min-width: 44px" in RESPONSIVE_CSS
    assert "min-height: 44px" in RESPONSIVE_CSS
