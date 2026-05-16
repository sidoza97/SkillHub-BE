import json
import re
from collections import Counter
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from sqlalchemy import or_

from ..models.db_models import Employee, EmployeeProfile, Skill, User
from ..models.schemas import NLSearchRequest
from ..services.llm_service import chat_completion
from ..services.search_service import semantic_search
from ..utils.auth import require_hr

router = APIRouter(prefix="/search", tags=["search"])


def _serialize_employee(emp):
    return {
        "id": emp.id,
        "name": emp.name,
        "title": emp.title,
        "email": emp.email,
        "department": emp.department,
        "location": emp.location,
        "current_project": emp.current_project,
        "is_available": emp.is_available,
        "created_at": emp.created_at.isoformat(),
        "skills": [
            {
                "id": s.id,
                "name": s.name,
                "category": s.category,
                "proficiency": s.proficiency,
                "years_experience": s.years_experience,
                "is_inferred": s.is_inferred,
                "employee_id": s.employee_id,
                "confidence": s.confidence,
            }
            for s in emp.skills
        ],
    }


@router.post("/nl")
def natural_language_search(
    request: NLSearchRequest,
    x_llm_provider: Optional[str] = Header(default="gemma"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr),
):
    provider = x_llm_provider or "gemma"
    results = semantic_search(request.query, db, provider=provider, top_k=request.top_k or 10)
    return [
        {"employee": _serialize_employee(r["employee"]), "match_score": r["match_score"], "explanation": r["explanation"]}
        for r in results
    ]


# ── Team Builder ─────────────────────────────────────────────────────────────

class TeamRequest(BaseModel):
    description: str
    team_size: Optional[int] = None  # If None, AI infers from description


TEAM_PROMPT = """You are an expert HR assistant. A manager needs to assemble a team.

Project Description: "{description}"

{team_size_instruction}

Available Employees:
{profiles}

Return ONLY a valid JSON object:
{{
  "team": [
    {{
      "employee_id": 1,
      "role": "Frontend Lead",
      "rationale": "2-3 sentences why this person fits this role",
      "match_score": 92
    }}
  ],
  "team_rationale": "Overall 2-3 sentence explanation of why this team composition works, including the team size decision",
  "alternatives": [
    {{
      "employee_id": 5,
      "for_role": "Frontend Lead",
      "note": "Good alternative if primary is unavailable"
    }}
  ]
}}"""


@router.post("/team")
def team_builder(
    request: TeamRequest,
    x_llm_provider: Optional[str] = Header(default="gemma"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr),
):
    provider = x_llm_provider or "gemma"
    employees = db.query(Employee).all()
    if not employees:
        raise HTTPException(status_code=400, detail="No employees in database")

    profiles = ""
    for emp in employees:
        skills = ", ".join(f"{s.name}({s.proficiency})" for s in emp.skills if not s.is_inferred)
        available_str = "Available" if emp.is_available else f"On project: {emp.current_project}"
        profiles += f"\nID:{emp.id} | {emp.name} | {emp.title or 'Developer'} | {emp.location or 'N/A'} | {available_str}\nSkills: {skills or 'None'}\n"

    if request.team_size:
        team_size_instruction = f"Assemble a team of exactly {request.team_size} people."
    else:
        team_size_instruction = (
            "Infer the ideal team size from the project description. "
            "Select as many people as the project genuinely needs — typically 2–8. "
            "Do not add people who are not required."
        )

    prompt = TEAM_PROMPT.format(
        description=request.description,
        team_size_instruction=team_size_instruction,
        profiles=profiles,
    )
    try:
        response = chat_completion(
            messages=[{"role": "user", "content": prompt}],
            provider=provider,
            temperature=0.3,
        )
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"```(?:json)?\n?", "", cleaned).strip().rstrip("`").strip()
        result = json.loads(cleaned)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")

    emp_map = {emp.id: emp for emp in employees}
    enriched_team = []
    for member in result.get("team", []):
        emp_id = member.get("employee_id")
        if emp_id in emp_map:
            enriched_team.append({**member, "employee": _serialize_employee(emp_map[emp_id])})

    enriched_alts = []
    for alt in result.get("alternatives", []):
        emp_id = alt.get("employee_id")
        if emp_id in emp_map:
            enriched_alts.append({**alt, "employee": _serialize_employee(emp_map[emp_id])})

    return {
        "team": enriched_team,
        "team_rationale": result.get("team_rationale", ""),
        "alternatives": enriched_alts,
    }


# ── Skill Gap Analysis ────────────────────────────────────────────────────────

@router.get("/skill-gaps")
def skill_gap_analysis(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr),
):
    approved_ids = db.query(EmployeeProfile.employee_id).filter(EmployeeProfile.status == "approved")
    has_any_profile = db.query(EmployeeProfile.employee_id)
    employees = (
        db.query(Employee)
        .filter(or_(~Employee.id.in_(has_any_profile), Employee.id.in_(approved_ids)))
        .all()
    )
    total = len(employees)
    if total == 0:
        return {"total_employees": 0, "skill_distribution": [], "categories": {}, "gaps": []}

    all_skills = db.query(Skill).filter(Skill.is_inferred == False).all()

    skill_counter: Counter = Counter()
    category_skills: dict[str, Counter] = {}
    proficiency_map: dict[str, Counter] = {}

    for s in all_skills:
        skill_counter[s.name] += 1
        cat = s.category or "other"
        if cat not in category_skills:
            category_skills[cat] = Counter()
        category_skills[cat][s.name] += 1
        if s.name not in proficiency_map:
            proficiency_map[s.name] = Counter()
        if s.proficiency:
            proficiency_map[s.name][s.proficiency] += 1

    # Top skills
    top_skills = [
        {
            "name": name,
            "count": count,
            "coverage_pct": round(count / total * 100),
            "proficiency_breakdown": dict(proficiency_map.get(name, {})),
        }
        for name, count in skill_counter.most_common(30)
    ]

    # Categories summary
    categories = {}
    for cat, counter in category_skills.items():
        categories[cat] = {
            "skill_count": len(counter),
            "top_skills": [{"name": n, "count": c} for n, c in counter.most_common(5)],
        }

    # Gaps = skills with only 1 employee (single point of failure)
    gaps = [
        {"name": name, "count": count, "risk": "high" if count == 1 else "medium"}
        for name, count in skill_counter.items()
        if count <= 2
    ]
    gaps.sort(key=lambda x: x["count"])

    available_count = sum(1 for e in employees if e.is_available)

    return {
        "total_employees": total,
        "available_employees": available_count,
        "total_skill_records": len(all_skills),
        "unique_skills": len(skill_counter),
        "skill_distribution": top_skills,
        "categories": categories,
        "gaps": gaps[:20],
    }


# ── Conversational Chat Search (LangGraph) ────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str
    message: str


@router.post("/chat")
def chat_search(
    request: ChatRequest,
    x_llm_provider: Optional[str] = Header(default="gemma"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr),
):
    from ..services.chat_graph import get_graph

    provider = x_llm_provider or "gemma"
    graph = get_graph()

    config = {"configurable": {"thread_id": request.session_id, "provider": provider}}
    state_input = {"messages": [{"role": "user", "content": request.message}]}

    try:
        final = graph.invoke(state_input, config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph error: {str(e)}")

    return {
        "response_intro": final.get("response_intro", "Here are the results:"),
        "results": final.get("current_results") or [],
    }
