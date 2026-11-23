"""AI assessment endpoint matching the Lab 2 OpenAPI contract."""

from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.concurrency import run_in_threadpool

from ml.models.baseline import assess

router = APIRouter()


class Requirement(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,39}$")
    text: str = Field(min_length=1, max_length=250)


class AssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    vacancy_revision: str = Field(min_length=1, max_length=80)
    requirements: list[Requirement] = Field(min_length=1, max_length=8)
    resume_text: str = Field(min_length=1, max_length=16000)

    @field_validator("requirements")
    @classmethod
    def unique_ids(cls, requirements):
        if len({item.id for item in requirements}) != len(requirements):
            raise ValueError("Requirement IDs must be unique")
        return requirements


@router.post("/v1/ai/assessments")
async def assess_resume(payload: AssessmentRequest):
    assessment_id = str(uuid4())
    requirements = [item.model_dump() for item in payload.requirements]
    citations, reason = await run_in_threadpool(assess, assessment_id, requirements, payload.resume_text)
    findings = []
    for item in requirements:
        if item["id"] in citations:
            finding = {"status": "evidenced", "evidence": citations[item["id"]]}
        else:
            finding = {
                "status": "needs_review",
                "question": f"Какой ваш практический опыт подтверждает требование «{item['text']}»?",
            }
        findings.append({"requirement_id": item["id"], **finding})
    result = {"assessment_id": assessment_id, "state": "manual_review" if reason else "evidence_ready", "findings": findings}
    if reason:
        result["reason"] = reason
    return result
