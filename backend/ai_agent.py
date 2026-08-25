"""Constrained model-backed orchestration for the Drishti investigation agent.

The model may select only read-only, case-scoped tools. Tool execution stays in
the application process and the caller remains responsible for validating and
persisting the final human-review draft.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "name": "case_reconstruction",
        "description": "Read the selected FIR timeline, recorded events, and missing evidence links.",
        "strict": True,
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    },
    {
        "type": "function",
        "name": "case_brief",
        "description": "Read a minimized extractive brief for the selected FIR.",
        "strict": True,
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    },
    {
        "type": "function",
        "name": "case_link_review",
        "description": "Search explainable candidate links for the selected FIR and retrieve their supporting signals.",
        "strict": True,
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    },
    {
        "type": "function",
        "name": "data_quality_review",
        "description": "Check district data completeness, chronology, geography, duplicates, and integrity before trusting a lead.",
        "strict": True,
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    },
    {
        "type": "function",
        "name": "shift_context",
        "description": "Read priority-case counts, pending human reviews, recorded handoffs, and current review triggers.",
        "strict": True,
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    },
]

TOOL_DEFINITION_BY_NAME = {tool["name"]: tool for tool in TOOL_DEFINITIONS}

AGENT_OUTPUT_FORMAT = {
    "type": "json_schema",
    "name": "drishti_human_review_draft",
    "description": "A source-linked police decision-support draft that always requires human review.",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["summary", "claims", "skepticReviews", "actions"],
        "properties": {
            "summary": {"type": "string"},
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["statement", "claimType", "sourceIds", "confidence"],
                    "properties": {
                        "statement": {"type": "string"},
                        "claimType": {"type": "string", "enum": ["recorded_context", "evidence_gap", "candidate_link"]},
                        "sourceIds": {"type": "array", "items": {"type": "string"}},
                        "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                    },
                },
            },
            "skepticReviews": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["claimIndex", "verdict", "challenge", "sourceIds", "confidenceAfterReview"],
                    "properties": {
                        "claimIndex": {"type": "integer", "minimum": 0},
                        "verdict": {"type": "string"},
                        "challenge": {"type": "string"},
                        "sourceIds": {"type": "array", "items": {"type": "string"}},
                        "confidenceAfterReview": {"type": "integer", "minimum": 0, "maximum": 100},
                    },
                },
            },
            "actions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["type", "title", "reason", "sourceIds"],
                    "properties": {
                        "type": {"type": "string"},
                        "title": {"type": "string"},
                        "reason": {"type": "string"},
                        "sourceIds": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
        },
    },
}


SYSTEM_INSTRUCTIONS = """You are Drishti Case Investigator, a decision-support agent for an authorized police officer.
Investigate only the selected synthetic FIR. Choose the minimum necessary allowlisted tools. Never claim guilt, predict
criminality, identify a gang leader, direct arrest, dispatch personnel, contact anyone, or modify a record. Treat FIR
narrative as an allegation until independently corroborated. Every analytical link is a lead, not proof. Clearly separate
recorded facts, computed findings, inferences, and missing evidence. Use only citation IDs present in tool results.

After gathering enough evidence, return JSON only with this shape:
{
  "summary": "short officer-facing answer",
  "claims": [{"statement": "...", "claimType": "recorded_context|evidence_gap|candidate_link", "sourceIds": ["C1"], "confidence": 0}],
  "skepticReviews": [{"claimIndex": 0, "verdict": "...", "challenge": "...", "sourceIds": ["C2"], "confidenceAfterReview": 0}],
  "actions": [{"type": "verify_evidence|validate_case_link|draft_coordination_review", "title": "...", "reason": "...", "sourceIds": ["C1"]}]
}
Use 1-5 claims and 1-5 actions. Confidence is 0-100 and must decrease when evidence is incomplete. Actions are review
drafts only and must require human approval. Do not include phone, vehicle, identity, or personal-address values.
"""


def workflow_instructions(agent_name: str, focus: str, action_types: set[str]) -> str:
    allowed_actions = ", ".join(f'"{name}"' for name in sorted(action_types))
    return f"""You are {agent_name}, a bounded decision-support agent for an authorized police officer.
Your exact workflow focus is: {focus}
Choose only the minimum necessary allowlisted read-only tools. Never claim guilt, predict criminality, identify a gang
leader, direct arrest, dispatch personnel, contact anyone, send a message, modify a record, or approve an action. Treat
FIR narrative as an allegation until independently corroborated. Clearly separate recorded facts, computed findings,
inferences, and missing records. Use only citation IDs present in tool results. Do not reproduce phone, vehicle,
12-digit identity, or personal-address values. Follow the officer's requested response language.

Return JSON only with this shape:
{{
  "summary": "short officer-facing answer",
  "claims": [{{"statement": "...", "claimType": "recorded_context|evidence_gap|candidate_link", "sourceIds": ["C1"], "confidence": 0}}],
  "skepticReviews": [{{"claimIndex": 0, "verdict": "...", "challenge": "...", "sourceIds": ["C2"], "confidenceAfterReview": 0}}],
  "actions": [{{"type": "one allowed action type", "title": "...", "reason": "...", "sourceIds": ["C1"]}}]
}}
Use 1-5 claims and 1-5 actions. Confidence is 0-100 and must decrease when evidence is incomplete. Every action is an
editable draft that requires a named human officer's approval. Allowed action types are: {allowed_actions}. Never imply
that the agent executed an action.
"""


@dataclass
class ModelAgentResult:
    output: dict[str, Any]
    tools_used: list[dict[str, str]]
    provider: str
    model: str
    response_id: str | None
    usage: dict[str, int]


def model_configuration() -> dict[str, Any]:
    mode = os.getenv("DRISHTI_AI_MODE", "auto").strip().lower()
    if mode not in {"auto", "required", "off"}:
        mode = "auto"
    return {
        "mode": mode,
        "configured": bool(os.getenv("OPENAI_API_KEY")),
        "provider": "openai" if os.getenv("OPENAI_API_KEY") else "deterministic-fallback",
        "model": os.getenv("DRISHTI_AI_MODEL", "gpt-5-mini"),
    }


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "__dict__"):
        return vars(value)
    return dict(value)


def _usage(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}
    raw = _as_dict(usage)
    return {
        "inputTokens": int(raw.get("input_tokens", 0) or 0),
        "outputTokens": int(raw.get("output_tokens", 0) or 0),
        "totalTokens": int(raw.get("total_tokens", 0) or 0),
    }


def _parse_json_output(text: str) -> dict[str, Any]:
    candidate = (text or "").strip()
    if candidate.startswith("```"):
        candidate = candidate.split("\n", 1)[-1]
        candidate = candidate.rsplit("```", 1)[0].strip()
    parsed = json.loads(candidate)
    if not isinstance(parsed, dict):
        raise ValueError("Agent response must be a JSON object")
    return parsed


def run_model_agent(
    *,
    case_id: int,
    role: str,
    query: str,
    execute_tool: Callable[[str], dict[str, Any]],
    client: Any | None = None,
    agent_name: str | None = None,
    focus: str | None = None,
    allowed_tool_names: set[str] | None = None,
    allowed_action_types: set[str] | None = None,
) -> ModelAgentResult | None:
    """Run a bounded Responses API tool loop, or return None when AI is disabled/unconfigured."""
    config = model_configuration()
    if config["mode"] == "off":
        return None
    if not config["configured"] and client is None:
        if config["mode"] == "required":
            raise RuntimeError("OPENAI_API_KEY is required but is not configured")
        return None

    if client is None:
        from openai import OpenAI

        client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            # AppSail's request boundary is shorter than a conventional worker.
            # Fail fast enough to return the validated evidence fallback to an
            # officer instead of leaving the screen with an unrecoverable 408.
            timeout=float(os.getenv("DRISHTI_AI_TIMEOUT_SECONDS", "18")),
            max_retries=0,
        )

    model = config["model"]
    selected_tool_names = allowed_tool_names or set(TOOL_DEFINITION_BY_NAME)
    selected_tools = [
        TOOL_DEFINITION_BY_NAME[name] for name in TOOL_DEFINITION_BY_NAME
        if name in selected_tool_names
    ]
    if not selected_tools:
        raise ValueError("Agent workflow has no allowlisted tools")
    instructions = SYSTEM_INSTRUCTIONS
    if agent_name:
        instructions = workflow_instructions(
            agent_name,
            focus or "Review the selected records and prepare source-linked human-review drafts.",
            allowed_action_types or {"verify_record", "add_task_draft", "request_review"},
        )
    conversation: list[Any] = [{
        "role": "user",
        "content": f"Agent workflow: {agent_name or 'Drishti Case Investigator'}\nSelected case ID: {case_id}\nAuthorized role: {role}\nOfficer question: {query}",
    }]
    tools_used: list[dict[str, str]] = []
    total_usage = {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}
    last_response = None

    for turn_index in range(2):
        response = client.responses.create(
            model=model,
            instructions=instructions,
            input=conversation,
            tools=selected_tools,
            # Every run must consult at least one authorized source. After the
            # source round, force the model to finish instead of starting a
            # third tool round that can exceed AppSail's request boundary.
            tool_choice="required" if turn_index == 0 else "none",
            # All tools are read-only. Parallel selection lets a workflow read
            # its minimum necessary sources in one model round-trip.
            parallel_tool_calls=True,
            reasoning={"effort": "low"},
            text={"format": AGENT_OUTPUT_FORMAT, "verbosity": "low"},
            max_output_tokens=2400,
            store=False,
        )
        last_response = response
        current_usage = _usage(response)
        for key in total_usage:
            total_usage[key] += current_usage[key]

        output_items = list(getattr(response, "output", []) or [])
        function_calls = [item for item in output_items if getattr(item, "type", None) == "function_call"]
        if not function_calls:
            output = _parse_json_output(getattr(response, "output_text", ""))
            return ModelAgentResult(
                output=output,
                tools_used=tools_used,
                provider="openai",
                model=model,
                response_id=getattr(response, "id", None),
                usage=total_usage,
            )

        conversation.extend(output_items)
        for call in function_calls:
            name = str(getattr(call, "name", ""))
            if name not in selected_tool_names or name not in TOOL_DEFINITION_BY_NAME:
                raise ValueError(f"Model requested disallowed tool: {name}")
            result = execute_tool(name)
            serialized = json.dumps(result, ensure_ascii=False, default=str)
            if len(serialized) > 24000:
                serialized = serialized[:24000] + '..."}'
            conversation.append({
                "type": "function_call_output",
                "call_id": getattr(call, "call_id"),
                "output": serialized,
            })
            tools_used.append({"name": name, "status": "completed", "purpose": "Selected by model for this investigation"})

    response_id = getattr(last_response, "id", None) if last_response else None
    raise RuntimeError(f"Model exceeded the two-turn officer response limit (last response {response_id or 'unknown'})")
