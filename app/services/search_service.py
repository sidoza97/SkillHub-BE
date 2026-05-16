import json
import logging
import re

from ..database import employee_collection

logger = logging.getLogger(__name__)

RANKING_PROMPT = """You are an expert HR assistant. Score and explain how well each employee matches the search query.

Search Query: "{query}"

Employee Profiles:
{profiles}

For each employee return a match_score (0-100) and a concise plain-English explanation (2-3 sentences).
Higher score = better match. Consider skills, experience, location, availability, and projects.

Return ONLY a valid JSON array — no markdown, no code fences:
[
  {{
    "employee_id": 1,
    "match_score": 94,
    "explanation": "Expert in React (5 yrs), led 2 real-time apps using Socket.IO, currently unallocated."
  }}
]

Order by match_score descending. Include every employee listed above."""


def build_employee_text(employee) -> str:
    skills_text = ", ".join(
        f"{s.name} ({s.proficiency}, {s.years_experience}yrs)"
        for s in employee.skills
    )
    return (
        f"Name: {employee.name}\n"
        f"Title: {employee.title or 'Developer'}\n"
        f"Location: {employee.location or 'Unknown'}\n"
        f"Department: {employee.department or 'Engineering'}\n"
        f"Available: {'Yes' if employee.is_available else 'No, on project: ' + (employee.current_project or '')}\n"
        f"Skills: {skills_text or 'None listed'}"
    )


def index_employee(employee) -> None:
    text = build_employee_text(employee)
    existing = employee_collection.get(ids=[str(employee.id)])
    if existing["ids"]:
        employee_collection.update(
            ids=[str(employee.id)],
            documents=[text],
            metadatas=[{"name": employee.name, "employee_id": employee.id}],
        )
    else:
        employee_collection.add(
            ids=[str(employee.id)],
            documents=[text],
            metadatas=[{"name": employee.name, "employee_id": employee.id}],
        )


def semantic_search(query: str, db, provider: str = "deepseek", top_k: int = 10) -> list:
    from ..models.db_models import Employee
    from .llm_service import chat_completion

    total = employee_collection.count()
    if total == 0:
        return []

    n_results = min(top_k, total)
    results = employee_collection.query(query_texts=[query], n_results=n_results)
    candidate_ids = [int(id_) for id_ in results["ids"][0]]

    employees = db.query(Employee).filter(Employee.id.in_(candidate_ids)).all()
    if not employees:
        return []

    profiles_text = ""
    for emp in employees:
        profiles_text += f"\n---\nEmployee ID: {emp.id}\n{build_employee_text(emp)}\n"

    try:
        prompt = RANKING_PROMPT.format(query=query, profiles=profiles_text)
        response = chat_completion(
            messages=[{"role": "user", "content": prompt}],
            provider=provider,
            temperature=0.2,
        )
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"```(?:json)?\n?", "", cleaned).strip().rstrip("`").strip()
        rankings = json.loads(cleaned)
    except Exception:
        logger.exception("LLM ranking failed for query %r (provider=%s)", query, provider)
        rankings = [
            {"employee_id": emp.id, "match_score": 50, "explanation": "Profile matched your search query."}
            for emp in employees
        ]

    emp_map = {emp.id: emp for emp in employees}
    search_results = []
    for rank in sorted(rankings, key=lambda x: x.get("match_score", 0), reverse=True):
        emp_id = rank.get("employee_id")
        if emp_id in emp_map:
            search_results.append(
                {
                    "employee": emp_map[emp_id],
                    "match_score": rank.get("match_score", 0),
                    "explanation": rank.get("explanation", ""),
                }
            )

    return search_results
