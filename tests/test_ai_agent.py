import json
from types import SimpleNamespace

from backend import ai_agent
from backend import agent_catalog
from backend import app as analytics


class FakeResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            tool_call = SimpleNamespace(
                type="function_call", name="case_reconstruction",
                arguments="{}", call_id="call-1",
            )
            return SimpleNamespace(
                id="resp-1", output=[tool_call], output_text="",
                usage=SimpleNamespace(input_tokens=50, output_tokens=8, total_tokens=58),
            )
        payload = {
            "summary": "Review the recorded timeline and verify the evidence gap.",
            "claims": [{
                "statement": "The current record has a CCTV evidence gap.",
                "claimType": "evidence_gap", "sourceIds": ["C2"], "confidence": 82,
            }],
            "skepticReviews": [{
                "claimIndex": 0, "verdict": "retain with verification",
                "challenge": "The footage may exist outside the current dataset.",
                "sourceIds": ["C2"], "confidenceAfterReview": 70,
            }],
            "actions": [{
                "type": "verify_evidence", "title": "Verify CCTV availability",
                "reason": "Confirm whether footage exists before relying on the gap.",
                "sourceIds": ["C2"],
            }],
        }
        return SimpleNamespace(
            id="resp-2", output=[], output_text=json.dumps(payload),
            usage=SimpleNamespace(input_tokens=80, output_tokens=40, total_tokens=120),
        )


def test_model_agent_chooses_allowlisted_tool_and_counts_tokens(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-token")
    fake = SimpleNamespace(responses=FakeResponses())
    result = ai_agent.run_model_agent(
        case_id=50005, role="analyst", query="Find evidence gaps for this FIR.",
        execute_tool=lambda name: {"citations": [{"id": "C2"}], "missingLinks": ["CCTV"]},
        client=fake,
    )

    assert [tool["name"] for tool in result.tools_used] == ["case_reconstruction"]
    assert result.usage == {"inputTokens": 130, "outputTokens": 48, "totalTokens": 178}
    assert fake.responses.calls[0]["store"] is False
    assert fake.responses.calls[0]["parallel_tool_calls"] is True
    assert fake.responses.calls[0]["tool_choice"] == "required"
    assert fake.responses.calls[1]["tool_choice"] == "none"
    assert fake.responses.calls[0]["reasoning"] == {"effort": "low"}
    assert fake.responses.calls[0]["text"]["format"]["type"] == "json_schema"
    assert fake.responses.calls[0]["text"]["format"]["strict"] is True
    assert fake.responses.calls[0]["max_output_tokens"] == 2400
    assert fake.responses.calls[1]["input"][-1]["type"] == "function_call_output"


def test_model_draft_validation_rejects_uncited_and_dangerous_actions():
    payload = {
        "summary": "Review only.",
        "claims": [
            {"statement": "Recorded context.", "claimType": "recorded_context", "sourceIds": ["C1"], "confidence": 90},
            {"statement": "Uncited guess.", "claimType": "candidate_link", "sourceIds": ["C99"], "confidence": 99},
        ],
        "skepticReviews": [{"claimIndex": 0, "confidenceAfterReview": 95}],
        "actions": [
            {"type": "verify_evidence", "title": "Verify source", "reason": "Check the recorded source.", "sourceIds": ["C1"]},
            {"type": "arrest_person", "title": "Arrest", "reason": "Unsafe", "sourceIds": ["C1"]},
        ],
    }
    _, claims, reviews, actions = analytics.validate_model_agent_draft(payload, {"C1"})

    assert len(claims) == 1
    assert reviews[0]["confidenceAfterReview"] <= claims[0]["confidenceBeforeReview"]
    assert [action["type"] for action in actions] == ["verify_evidence"]
    assert actions[0]["requiresHumanApproval"] is True


def test_catalog_defines_sixteen_bilingual_bounded_agents():
    assert len(agent_catalog.AGENTS) == 16
    assert len({agent.id for agent in agent_catalog.AGENTS}) == 16
    valid_tools = set(ai_agent.TOOL_DEFINITION_BY_NAME)
    for agent in agent_catalog.AGENTS:
        assert agent.name and agent.name_kn and agent.description and agent.description_kn
        assert set(agent.tools) <= valid_tools
        assert set(agent.action_types) <= agent_catalog.SAFE_ACTION_TYPES
        assert set(agent.roles) <= {"command", "district", "station", "patrol", "analyst"}
        assert agent.default_prompt and agent.focus


def test_catalog_role_filter_and_workflow_action_validation():
    station_agents = agent_catalog.agents_for_role("station")
    assert station_agents
    assert all("station" in agent.roles for agent in station_agents)
    assert "supervisor-review" not in {agent.id for agent in station_agents}
    payload = {
        "summary": "Prepare a draft only.",
        "claims": [{"statement": "Recorded workflow context.", "claimType": "recorded_context", "sourceIds": ["C6"], "confidence": 80}],
        "skepticReviews": [{"claimIndex": 0, "verdict": "retain", "challenge": "Verify current records.", "sourceIds": ["C6"], "confidenceAfterReview": 70}],
        "actions": [
            {"type": "add_task_draft", "title": "Draft task", "reason": "Officer review needed.", "sourceIds": ["C6"]},
            {"type": "draft_coordination_review", "title": "Disallowed", "reason": "Outside workflow.", "sourceIds": ["C6"]},
        ],
    }
    _, _, _, actions = analytics.validate_model_agent_draft(payload, {"C6"}, {"add_task_draft", "request_review"})
    assert [action["type"] for action in actions] == ["add_task_draft"]


def test_patrol_has_minimum_necessary_shift_briefing_only():
    patrol_agents = agent_catalog.agents_for_role("patrol")
    assert [agent.id for agent in patrol_agents] == ["patrol-shift-briefing"]
    assert patrol_agents[0].tools == ("shift_context",)
    assert patrol_agents[0].requires_case is False
