"""Role-aware catalog for Drishti's bounded police decision-support agents."""

from __future__ import annotations

from dataclasses import asdict, dataclass


SAFE_ACTION_TYPES = {
    "verify_record",
    "add_task_draft",
    "request_review",
    "prepare_document_draft",
    "validate_case_link",
    "draft_coordination_review",
}


@dataclass(frozen=True)
class AgentSpec:
    id: str
    name: str
    name_kn: str
    category: str
    surface: str
    description: str
    description_kn: str
    roles: tuple[str, ...]
    tools: tuple[str, ...]
    requires_case: bool
    default_prompt: str
    focus: str
    action_types: tuple[str, ...]

    def public_dict(self) -> dict:
        result = asdict(self)
        result["requiresCase"] = result.pop("requires_case")
        result["defaultPrompt"] = result.pop("default_prompt")
        result["nameKn"] = result.pop("name_kn")
        result["descriptionKn"] = result.pop("description_kn")
        result["roles"] = list(self.roles)
        result["tools"] = list(self.tools)
        result["actionTypes"] = list(result.pop("action_types"))
        return result


ALL_ROLES = ("command", "district", "station", "analyst")
PATROL_ROLES = ("patrol",)
SUPERVISORS = ("command", "district")
CASE_ROLES = ("command", "district", "station", "analyst")


AGENTS = (
    AgentSpec(
        "shift-briefing", "Shift Briefing Agent", "ಪಾಳಿ ಮಾಹಿತಿ ಏಜೆಂಟ್", "My shift", "today",
        "Builds a source-linked briefing of priority cases, pending reviews, and recorded handoffs.",
        "ಆದ್ಯತೆಯ ಪ್ರಕರಣಗಳು, ಬಾಕಿ ಪರಿಶೀಲನೆಗಳು ಮತ್ತು ದಾಖಲಿತ ಹಸ್ತಾಂತರಗಳ ಮೂಲ-ಸಂಬಂಧಿತ ಮಾಹಿತಿ ಸಿದ್ಧಪಡಿಸುತ್ತದೆ.",
        ALL_ROLES, ("shift_context", "case_brief", "data_quality_review"), False,
        "Prepare my shift briefing. Show only items needing a recorded decision or verification.",
        "Prioritize urgent recorded work, explain why it matters, and separate alerts from verified facts.",
        ("add_task_draft", "request_review"),
    ),
    AgentSpec(
        "patrol-shift-briefing", "Patrol Shift Briefing", "ಗಸ್ತು ಪಾಳಿ ಮಾಹಿತಿ", "My shift", "today",
        "Prepares a minimum-necessary briefing of recorded location priorities and pending command confirmation.",
        "ದಾಖಲಿತ ಸ್ಥಳ ಆದ್ಯತೆಗಳು ಮತ್ತು ಬಾಕಿ ಕಮಾಂಡ್ ದೃಢೀಕರಣದ ಕನಿಷ್ಠ-ಅಗತ್ಯ ಮಾಹಿತಿ ಸಿದ್ಧಪಡಿಸುತ್ತದೆ.",
        PATROL_ROLES, ("shift_context",), False,
        "Prepare the current patrol shift briefing. Show recorded location priorities and clearly state that deployment requires supervisor confirmation.",
        "Use minimum-necessary shift context. Do not expose FIR narrative, identities, or infer a deployment instruction.",
        ("add_task_draft", "request_review"),
    ),
    AgentSpec(
        "case-triage", "Case Triage Agent", "ಪ್ರಕರಣ ಆದ್ಯತಾ ಏಜೆಂಟ್", "Investigation", "case-overview",
        "Identifies immediate case priorities, evidence readiness, and the safest first investigative step.",
        "ತಕ್ಷಣದ ಪ್ರಕರಣ ಆದ್ಯತೆ, ಸಾಕ್ಷ್ಯ ಸಿದ್ಧತೆ ಮತ್ತು ಸುರಕ್ಷಿತ ಮೊದಲ ತನಿಖಾ ಹಂತವನ್ನು ಗುರುತಿಸುತ್ತದೆ.",
        CASE_ROLES, ("case_reconstruction", "case_brief", "data_quality_review"), True,
        "Triage this FIR and identify the first source-linked investigation steps.",
        "Return a restrained triage, not a guilt or enforcement assessment.",
        ("verify_record", "add_task_draft", "request_review"),
    ),
    AgentSpec(
        "evidence-gap", "Evidence Gap Agent", "ಸಾಕ್ಷ್ಯ ಕೊರತೆ ಏಜೆಂಟ್", "Investigation", "evidence",
        "Checks which expected records are present, missing, partial, or contradictory.",
        "ನಿರೀಕ್ಷಿತ ದಾಖಲೆಗಳು ಇರುವುದೇ, ಕಾಣೆಯಾಗಿದೆಯೇ, ಭಾಗಶಃ ಇದೆಯೇ ಅಥವಾ ವಿರೋಧಾಭಾಸವಿದೆಯೇ ಎಂದು ಪರಿಶೀಲಿಸುತ್ತದೆ.",
        CASE_ROLES, ("case_reconstruction", "case_brief", "data_quality_review"), True,
        "Check this FIR for missing, partial, and conflicting evidence before review.",
        "Treat absence in Drishti as a record gap, never proof that evidence does not exist.",
        ("verify_record", "add_task_draft", "request_review"),
    ),
    AgentSpec(
        "timeline-reconstruction", "Timeline Reconstruction Agent", "ಕಾಲಕ್ರಮ ಪುನರ್‌ನಿರ್ಮಾಣ ಏಜೆಂಟ್", "Investigation", "timeline",
        "Builds a recorded chronology and flags unexplained time gaps or conflicting timestamps.",
        "ದಾಖಲಿತ ಕಾಲಕ್ರಮ ನಿರ್ಮಿಸಿ ವಿವರಿಸಲಾಗದ ಸಮಯ ಅಂತರಗಳು ಅಥವಾ ವಿರೋಧಿ ಸಮಯಮುದ್ರಗಳನ್ನು ಗುರುತಿಸುತ್ತದೆ.",
        CASE_ROLES, ("case_reconstruction", "case_brief"), True,
        "Review the recorded chronology and identify time gaps that require verification.",
        "Distinguish recorded timestamps from inferred ordering and never invent an event.",
        ("verify_record", "add_task_draft"),
    ),
    AgentSpec(
        "linked-case-verification", "Linked Case Verification Agent", "ಸಂಬಂಧಿತ ಪ್ರಕರಣ ಪರಿಶೀಲನಾ ಏಜೆಂಟ್", "Investigation", "linked-cases",
        "Challenges candidate FIR links and lists the independent signals needed for verification.",
        "ಅಭ್ಯರ್ಥಿ ಎಫ್‌ಐಆರ್ ಸಂಪರ್ಕಗಳನ್ನು ಪ್ರಶ್ನಿಸಿ ಪರಿಶೀಲನೆಗೆ ಬೇಕಾದ ಸ್ವತಂತ್ರ ಸಂಕೇತಗಳನ್ನು ಪಟ್ಟಿ ಮಾಡುತ್ತದೆ.",
        CASE_ROLES, ("case_link_review", "case_brief", "data_quality_review"), True,
        "Verify the candidate linked FIRs and explain which signals are leads rather than proof.",
        "Reject links supported only by common offence labels, geography, or duplicated narrative.",
        ("validate_case_link", "verify_record", "request_review"),
    ),
    AgentSpec(
        "statement-consistency", "Statement Consistency Agent", "ಹೇಳಿಕೆ ಹೊಂದಾಣಿಕೆ ಏಜೆಂಟ್", "Investigation", "evidence",
        "Compares recorded narrative signals and identifies statements or dates requiring reconciliation.",
        "ದಾಖಲಿತ ವಿವರಣಾ ಸಂಕೇತಗಳನ್ನು ಹೋಲಿಸಿ ಹೊಂದಾಣಿಕೆ ಬೇಕಾದ ಹೇಳಿಕೆಗಳು ಅಥವಾ ದಿನಾಂಕಗಳನ್ನು ಗುರುತಿಸುತ್ತದೆ.",
        CASE_ROLES, ("case_brief", "case_reconstruction", "data_quality_review"), True,
        "Check the recorded case narrative and chronology for inconsistencies requiring officer verification.",
        "Do not decide credibility or truthfulness; identify only record-level inconsistencies.",
        ("verify_record", "add_task_draft", "request_review"),
    ),
    AgentSpec(
        "investigation-planning", "Investigation Planning Agent", "ತನಿಖಾ ಯೋಜನಾ ಏಜೆಂಟ್", "Investigation", "case-overview",
        "Drafts an ordered, editable investigation checklist grounded in current evidence gaps.",
        "ಪ್ರಸ್ತುತ ಸಾಕ್ಷ್ಯ ಕೊರತೆ ಆಧಾರಿತ ಕ್ರಮಬದ್ಧ, ಸಂಪಾದಿಸಬಹುದಾದ ತನಿಖಾ ಪರಿಶೀಲನಾ ಪಟ್ಟಿ ಸಿದ್ಧಪಡಿಸುತ್ತದೆ.",
        CASE_ROLES, ("case_reconstruction", "case_brief", "case_link_review"), True,
        "Draft an ordered investigation checklist using only the cited case records.",
        "Every item is a draft task and must remain editable and unapproved.",
        ("add_task_draft", "verify_record", "request_review"),
    ),
    AgentSpec(
        "supervisor-review", "Supervisor Review Agent", "ಮೇಲ್ವಿಚಾರಕ ಪರಿಶೀಲನಾ ಏಜೆಂಟ್", "Supervision", "review-queue",
        "Prepares the decision required, unresolved risks, and cited records for supervisor review.",
        "ಮೇಲ್ವಿಚಾರಕ ಪರಿಶೀಲನೆಗೆ ಬೇಕಾದ ನಿರ್ಧಾರ, ಬಗೆಹರಿಯದ ಅಪಾಯಗಳು ಮತ್ತು ಉಲ್ಲೇಖಿತ ದಾಖಲೆಗಳನ್ನು ಸಿದ್ಧಪಡಿಸುತ್ತದೆ.",
        SUPERVISORS, ("case_reconstruction", "case_brief", "case_link_review", "data_quality_review"), True,
        "Prepare a supervisor review brief and state the exact human decision required.",
        "Do not approve, reject, coordinate, or authorize an operational action.",
        ("request_review", "verify_record", "draft_coordination_review"),
    ),
    AgentSpec(
        "fir-drafting", "FIR Drafting Agent", "ಎಫ್‌ಐಆರ್ ಕರಡು ಏಜೆಂಟ್", "Station work", "fir-intake",
        "Structures officer-provided facts into an editable FIR draft without adding allegations.",
        "ಅಧಿಕಾರಿ ನೀಡಿದ ವಾಸ್ತವಾಂಶಗಳನ್ನು ಹೊಸ ಆರೋಪ ಸೇರಿಸದೆ ಸಂಪಾದಿಸಬಹುದಾದ ಎಫ್‌ಐಆರ್ ಕರಡಾಗಿ ರಚಿಸುತ್ತದೆ.",
        ("station", "district"), ("case_brief", "data_quality_review"), True,
        "Review this FIR narrative for completeness and prepare a structure-only correction draft.",
        "Preserve the original narrative and never invent a person, offence, identifier, or event.",
        ("prepare_document_draft", "verify_record", "request_review"),
    ),
    AgentSpec(
        "legal-procedure", "Legal Procedure Agent", "ಕಾನೂನು ಪ್ರಕ್ರಿಯಾ ಏಜೆಂಟ್", "Station work", "case-overview",
        "Checks whether recorded procedural stages and required approvals appear complete.",
        "ದಾಖಲಿತ ಪ್ರಕ್ರಿಯಾ ಹಂತಗಳು ಮತ್ತು ಅಗತ್ಯ ಅನುಮೋದನೆಗಳು ಪೂರ್ಣವಾಗಿದೆಯೇ ಎಂದು ಪರಿಶೀಲಿಸುತ್ತದೆ.",
        ("station", "district", "command"), ("case_reconstruction", "case_brief"), True,
        "Check the recorded procedural stages and list items requiring authorized legal review.",
        "Provide a checklist, not legal advice or an interpretation of guilt.",
        ("verify_record", "add_task_draft", "request_review"),
    ),
    AgentSpec(
        "evidence-intake", "Evidence Intake Agent", "ಸಾಕ್ಷ್ಯ ಸ್ವೀಕೃತಿ ಏಜೆಂಟ್", "Station work", "evidence",
        "Checks evidence-record metadata and drafts missing chain-of-custody fields for completion.",
        "ಸಾಕ್ಷ್ಯ ದಾಖಲೆ ಮೆಟಾಡೇಟಾ ಪರಿಶೀಲಿಸಿ ಕಾಣೆಯಾದ ವಶ ಸರಪಳಿ ಕ್ಷೇತ್ರಗಳ ಪೂರ್ಣತೆಗೆ ಕರಡು ಸಿದ್ಧಪಡಿಸುತ್ತದೆ.",
        ("station", "district", "analyst"), ("case_reconstruction", "data_quality_review"), True,
        "Review the evidence register for metadata and chain-of-custody fields requiring completion.",
        "Do not infer image or video content and do not alter an evidence record.",
        ("verify_record", "prepare_document_draft", "request_review"),
    ),
    AgentSpec(
        "data-quality", "Data Quality Agent", "ಡೇಟಾ ಗುಣಮಟ್ಟ ಏಜೆಂಟ್", "Governance", "data-quality",
        "Finds missing fields, duplicate narratives, chronology issues, and invalid geography.",
        "ಕಾಣೆಯಾದ ಕ್ಷೇತ್ರಗಳು, ನಕಲಿ ವಿವರಣೆಗಳು, ಕಾಲಕ್ರಮ ಸಮಸ್ಯೆಗಳು ಮತ್ತು ಅಮಾನ್ಯ ಭೌಗೋಳಿಕತೆಯನ್ನು ಗುರುತಿಸುತ್ತದೆ.",
        ("command", "district", "analyst"), ("data_quality_review", "shift_context"), False,
        "Review current data-quality risks and prioritize corrections affecting investigation reliability.",
        "Explain analytical impact and never rewrite a source record automatically.",
        ("verify_record", "add_task_draft", "request_review"),
    ),
    AgentSpec(
        "district-coordination", "District Coordination Agent", "ಜಿಲ್ಲಾ ಸಮನ್ವಯ ಏಜೆಂಟ್", "Supervision", "linked-cases",
        "Drafts a bounded cross-district verification memo from cited candidate links.",
        "ಉಲ್ಲೇಖಿತ ಅಭ್ಯರ್ಥಿ ಸಂಪರ್ಕಗಳಿಂದ ಮಿತ ಅಂತರ-ಜಿಲ್ಲಾ ಪರಿಶೀಲನಾ ಜ್ಞಾಪನ ಕರಡು ಸಿದ್ಧಪಡಿಸುತ್ತದೆ.",
        SUPERVISORS, ("case_link_review", "case_reconstruction", "data_quality_review"), True,
        "Draft a cross-district verification memo without sending it or merging investigations.",
        "Coordination remains a draft until a designated supervisor signs off.",
        ("draft_coordination_review", "validate_case_link", "request_review"),
    ),
    AgentSpec(
        "victim-follow-up", "Victim Follow-up Agent", "ಸಂತ್ರಸ್ತರ ಅನುಸರಣೆ ಏಜೆಂಟ್", "Station work", "case-overview",
        "Prepares a privacy-minimized follow-up checklist from recorded case gaps.",
        "ದಾಖಲಿತ ಪ್ರಕರಣ ಕೊರತೆಗಳಿಂದ ಗೌಪ್ಯತೆ-ಕನಿಷ್ಠ ಅನುಸರಣೆ ಪರಿಶೀಲನಾ ಪಟ್ಟಿ ಸಿದ್ಧಪಡಿಸುತ್ತದೆ.",
        ("station", "district"), ("case_brief", "case_reconstruction"), True,
        "Prepare a sensitive victim follow-up checklist using minimum necessary case information.",
        "Do not contact anyone, expose identifiers, or draft coercive language.",
        ("add_task_draft", "prepare_document_draft", "request_review"),
    ),
    AgentSpec(
        "court-readiness", "Court Readiness Agent", "ನ್ಯಾಯಾಲಯ ಸಿದ್ಧತಾ ಏಜೆಂಟ್", "Case completion", "reviews",
        "Checks chargesheet-stage records, evidence references, and unresolved documentation gaps.",
        "ಆರೋಪಪಟ್ಟಿ ಹಂತದ ದಾಖಲೆಗಳು, ಸಾಕ್ಷ್ಯ ಉಲ್ಲೇಖಗಳು ಮತ್ತು ಬಗೆಹರಿಯದ ದಾಖಲೆ ಕೊರತೆಗಳನ್ನು ಪರಿಶೀಲಿಸುತ್ತದೆ.",
        ("station", "district", "command"), ("case_reconstruction", "case_brief", "data_quality_review"), True,
        "Review this case for chargesheet and court-document readiness using only recorded fields.",
        "Flag missing documentation for authorized review; do not provide a legal conclusion.",
        ("verify_record", "add_task_draft", "request_review", "prepare_document_draft"),
    ),
)


AGENT_BY_ID = {agent.id: agent for agent in AGENTS}


def get_agent(agent_id: str) -> AgentSpec | None:
    return AGENT_BY_ID.get((agent_id or "").strip().lower())


def agents_for_role(role: str) -> list[AgentSpec]:
    normalized = (role or "").strip().lower()
    return [agent for agent in AGENTS if normalized in agent.roles]
