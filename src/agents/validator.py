"""Validator agent: strict quality gate. Fact-checks the edited report against the
research notes/sources and either accepts it or routes feedback back to the Writer."""
from datetime import datetime, timezone
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.llm import get_llm

SYSTEM_PROMPT = """You are the Validator Agent, a strict fact-checker and quality gate in a
report-writing pipeline. Compare the edited report against the research notes it was built
from. Check for:
- Factual claims in the report that are NOT supported by the research notes/sources (hallucinations).
- Important facts from the research notes that are missing from the report.
- Structural completeness (title, introduction, body, conclusion).
Be strict but fair. Only set is_valid to true if there are no material issues."""


class ValidationResult(BaseModel):
    is_valid: bool = Field(
        description="True only if the report is factually consistent with the research notes, "
        "reasonably complete, and well-structured."
    )
    issues: List[str] = Field(default_factory=list, description="Specific problems found; empty if none.")
    feedback: str = Field(description="Actionable feedback for the writer; empty string if is_valid is true.")


def validator_node(state):
    notes = state["research_notes"]
    report = state["edited_draft"]
    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions", 2)

    llm = get_llm(temperature=0)
    structured_llm = llm.with_structured_output(ValidationResult)
    result: ValidationResult = structured_llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Research notes:\n{notes}\n\nReport to validate:\n{report}"),
    ])

    new_revision_count = revision_count + (0 if result.is_valid else 1)
    forced_accept = (not result.is_valid) and new_revision_count >= max_revisions
    accepted = result.is_valid or forced_accept

    if result.is_valid:
        summary = "Validation passed — report is factually consistent and complete."
    elif forced_accept:
        summary = (
            f"Validation failed ({len(result.issues)} issue(s)) but max revisions "
            f"({max_revisions}) reached — accepting current report as final."
        )
    else:
        summary = f"Validation failed ({len(result.issues)} issue(s)) — routing feedback back to Writer."

    update = {
        "is_valid": accepted,
        "validation_feedback": result.feedback,
        "validation_issues": result.issues,
        "revision_count": new_revision_count,
        "trace": [{
            "agent": "validator",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
        }],
    }
    if accepted:
        update["final_report"] = report
    return update
