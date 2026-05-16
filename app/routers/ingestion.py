import json
import os
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.db_models import Employee, EmployeeProfile, User
from ..models.schemas import TextIngestionRequest
from ..services.extraction_service import extract_skills_from_text
from ..services.pdf_service import extract_text_from_pdf
from ..utils.auth import get_current_user, require_hr

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


def _resolve_employee_id(employee_id: Optional[int], current_user: User, db: Session) -> int:
    emp_id = employee_id or current_user.employee_id
    if not emp_id:
        raise HTTPException(status_code=400, detail="No employee ID associated with this account")
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    if current_user.role == "employee" and current_user.employee_id != emp_id:
        raise HTTPException(status_code=403, detail="Not authorized to upload for this employee")
    return emp_id


def _create_profile(employee_id: int, raw_text: str, provider: str, db: Session):
    extracted = extract_skills_from_text(raw_text, provider=provider)
    profile = EmployeeProfile(
        employee_id=employee_id,
        raw_text=raw_text,
        extracted_json=json.dumps(extracted),
        status="pending",
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _apply_extraction_to_employee(employee_id: int, extracted: dict, db: Session):
    """Write extracted skills + personal info directly to the Employee row so the
    employee can see their data immediately, before HR approves the profile."""
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        return

    personal = extracted.get("personal_info") or {}
    if personal.get("title"):
        emp.title = personal["title"]
    if personal.get("location"):
        emp.location = personal["location"]
    if personal.get("name") and personal["name"].strip():
        emp.name = personal["name"].strip()

    # Replace all existing skills with freshly extracted ones
    from ..models.db_models import Skill as SkillModel
    db.query(SkillModel).filter(SkillModel.employee_id == employee_id).delete()
    for s in extracted.get("skills", []) + extracted.get("inferred_skills", []):
        db.add(SkillModel(
            employee_id=employee_id,
            name=s.get("name", ""),
            category=s.get("category"),
            proficiency=s.get("proficiency"),
            years_experience=s.get("years_experience"),
            is_inferred=s.get("is_inferred", False),
            confidence=s.get("confidence", 1.0),
        ))
    db.commit()


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    employee_id: Optional[int] = Form(default=None),
    x_llm_provider: Optional[str] = Header(default="gemma"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_bytes = await file.read()
    raw_text = extract_text_from_pdf(file_bytes)
    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    emp_id = _resolve_employee_id(employee_id, current_user, db)
    provider = x_llm_provider or "gemma"
    profile = _create_profile(emp_id, raw_text, provider, db)
    extracted = json.loads(profile.extracted_json)
    _apply_extraction_to_employee(emp_id, extracted, db)
    return {
        "profile_id": profile.id,
        "status": profile.status,
        "extracted": extracted,
    }


@router.post("/text")
async def ingest_text(
    request: TextIngestionRequest,
    x_llm_provider: Optional[str] = Header(default="gemma"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp_id = _resolve_employee_id(request.employee_id, current_user, db)
    provider = x_llm_provider or "gemma"
    profile = _create_profile(emp_id, request.text, provider, db)
    extracted = json.loads(profile.extracted_json)
    _apply_extraction_to_employee(emp_id, extracted, db)
    return {
        "profile_id": profile.id,
        "status": profile.status,
        "extracted": extracted,
    }


# ── GitHub Ingestion ──────────────────────────────────────────────────────────

class GitHubIngestRequest(BaseModel):
    username: str
    employee_id: Optional[int] = None

@router.post("/github")
async def ingest_github(
    request: GitHubIngestRequest,
    x_llm_provider: Optional[str] = Header(default="gemma"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp_id = _resolve_employee_id(request.employee_id, current_user, db)
    provider = x_llm_provider or "gemma"

    github_token = os.getenv("GITHUB_TOKEN", "")
    headers = {}
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    headers["Accept"] = "application/vnd.github.v3+json"

    async with httpx.AsyncClient(timeout=15) as client:
        repos_resp = await client.get(
            f"https://api.github.com/users/{request.username}/repos",
            params={"per_page": 20, "sort": "pushed", "type": "owner"},
            headers=headers,
        )

    if repos_resp.status_code == 404:
        raise HTTPException(status_code=404, detail=f"GitHub user '{request.username}' not found")
    if repos_resp.status_code == 403:
        raise HTTPException(status_code=429, detail="GitHub API rate limit exceeded. Add a GITHUB_TOKEN to .env to increase limits.")

    repos = repos_resp.json()
    if not isinstance(repos, list):
        raise HTTPException(status_code=400, detail="Could not fetch GitHub repositories")

    # Build skill inference text
    lang_counts: dict = {}
    repo_lines = []
    for repo in repos[:12]:
        lang = repo.get("language")
        if lang:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
        topics = ", ".join(repo.get("topics", [])[:3])
        stars  = repo.get("stargazers_count", 0)
        desc   = repo.get("description") or ""
        line   = f"- {repo['name']} | {lang or 'N/A'} | ⭐{stars}"
        if topics:
            line += f" | topics: {topics}"
        if desc:
            line += f" | {desc[:80]}"
        repo_lines.append(line)

    lang_summary = ", ".join(f"{l}({c})" for l, c in sorted(lang_counts.items(), key=lambda x: -x[1]))
    raw_text = (
        f"GitHub Developer Profile: {request.username}\n"
        f"Languages used: {lang_summary}\n\n"
        f"Public Repositories:\n" + "\n".join(repo_lines)
    )

    profile = _create_profile(emp_id, raw_text, provider, db)
    return {
        "profile_id": profile.id,
        "status": profile.status,
        "extracted": json.loads(profile.extracted_json),
        "repos_analyzed": len(repo_lines),
        "languages_found": lang_counts,
    }


# ── Bulk Text Ingestion ───────────────────────────────────────────────────────

class BulkTextItem(BaseModel):
    employee_id: int
    text: str

class BulkTextRequest(BaseModel):
    items: List[BulkTextItem]

@router.post("/bulk-text")
async def bulk_ingest_text(
    request: BulkTextRequest,
    x_llm_provider: Optional[str] = Header(default="gemma"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr),
):
    from ..models.db_models import Employee as EmpModel
    provider = x_llm_provider or "gemma"
    results = []
    for item in request.items[:20]:  # max 20 per batch
        emp = db.query(EmpModel).filter(EmpModel.id == item.employee_id).first()
        if not emp:
            results.append({"employee_id": item.employee_id, "status": "error", "detail": "Employee not found"})
            continue
        try:
            profile = _create_profile(item.employee_id, item.text, provider, db)
            results.append({"employee_id": item.employee_id, "profile_id": profile.id, "status": "ok"})
        except Exception as e:
            results.append({"employee_id": item.employee_id, "status": "error", "detail": str(e)})
    return {"results": results, "processed": len(results)}


# ── Auto Resume Upload (bulk new-employee flow) ───────────────────────────────

@router.post("/auto-resume")
async def auto_resume_upload(
    file: UploadFile = File(...),
    x_llm_provider: Optional[str] = Header(default="gemma"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr),
):
    """
    Upload a resume PDF for an unknown/new employee.
    AI extracts personal info + skills, checks email uniqueness,
    creates Employee + pending EmployeeProfile if new.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_bytes = await file.read()
    raw_text = extract_text_from_pdf(file_bytes)
    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from PDF")

    provider = x_llm_provider or "gemma"
    extracted = extract_skills_from_text(raw_text, provider=provider)

    personal = extracted.get("personal_info") or {}
    name  = (personal.get("name") or "").strip()
    email = (personal.get("email") or "").strip().lower()
    title = (personal.get("title") or "").strip()
    location = (personal.get("location") or "").strip()

    if not email:
        raise HTTPException(
            status_code=422,
            detail="Could not extract email from resume — ensure the PDF contains contact info",
        )

    # Duplicate check
    existing = db.query(Employee).filter(Employee.email == email).first()
    if existing:
        return {
            "status": "skipped",
            "reason": "email_exists",
            "email": email,
            "name": existing.name,
            "existing_employee_id": existing.id,
        }

    # Create employee
    emp = Employee(
        name=name or email.split("@")[0].replace(".", " ").title(),
        email=email,
        title=title or None,
        location=location or None,
    )
    db.add(emp)
    db.flush()

    # Create pending profile
    profile = EmployeeProfile(
        employee_id=emp.id,
        raw_text=raw_text,
        extracted_json=json.dumps(extracted),
        status="pending",
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return {
        "status": "added",
        "employee_id": emp.id,
        "profile_id": profile.id,
        "name": emp.name,
        "email": emp.email,
        "title": emp.title,
        "location": emp.location,
        "skills_found": len(extracted.get("skills", [])),
        "extracted": extracted,
    }
