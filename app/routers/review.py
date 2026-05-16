import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.db_models import Employee, EmployeeProfile, Skill, User
from ..models.schemas import ProfileOut, ProfileUpdate
from ..services.search_service import index_employee
from ..utils.auth import get_current_user, hash_password, require_hr

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/queue", response_model=List[ProfileOut])
def get_review_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr),
):
    return (
        db.query(EmployeeProfile)
        .filter(EmployeeProfile.status == "pending")
        .order_by(EmployeeProfile.created_at.desc())
        .all()
    )


@router.get("/all", response_model=List[ProfileOut])
def get_all_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr),
):
    return db.query(EmployeeProfile).order_by(EmployeeProfile.created_at.desc()).all()


@router.get("/{profile_id}", response_model=ProfileOut)
def get_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.query(EmployeeProfile).filter(EmployeeProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/{profile_id}")
def update_profile(
    profile_id: int,
    update: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.query(EmployeeProfile).filter(EmployeeProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if update.extracted_json is not None:
        profile.extracted_json = update.extracted_json
    db.commit()
    return {"message": "Profile updated"}


@router.put("/{profile_id}/approve")
def approve_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr),
):
    profile = db.query(EmployeeProfile).filter(EmployeeProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    try:
        extracted = json.loads(profile.extracted_json or "{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in profile")

    employee = db.query(Employee).filter(Employee.id == profile.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Update employee fields from extraction
    personal = extracted.get("personal_info", {})
    if personal.get("name"):
        employee.name = personal["name"]
    if personal.get("location"):
        employee.location = personal["location"]
    if personal.get("title"):
        employee.title = personal["title"]
    if extracted.get("department"):
        employee.department = extracted["department"]
    if extracted.get("current_project"):
        employee.current_project = extracted["current_project"]

    # Replace skills
    db.query(Skill).filter(Skill.employee_id == employee.id).delete()
    all_skills = extracted.get("skills", []) + extracted.get("inferred_skills", [])
    for s in all_skills:
        skill = Skill(
            employee_id=employee.id,
            name=s.get("name", ""),
            category=s.get("category"),
            proficiency=s.get("proficiency"),
            years_experience=s.get("years_experience"),
            is_inferred=s.get("is_inferred", False),
            confidence=s.get("confidence", 1.0),
        )
        db.add(skill)

    profile.status = "approved"
    db.commit()
    db.refresh(employee)

    # Index in ChromaDB for semantic search
    index_employee(employee)

    # Auto-create a User login account if this employee has none
    existing_user = db.query(User).filter(User.email == employee.email).first()
    if not existing_user:
        default_password = "SkillsHub@123"
        new_user = User(
            email=employee.email,
            hashed_password=hash_password(default_password),
            role="employee",
            employee_id=employee.id,
        )
        db.add(new_user)
        db.commit()
        return {
            "message": "Profile approved and employee indexed",
            "user_created": True,
            "employee_email": employee.email,
            "default_password": default_password,
        }

    # Ensure existing user is linked to this employee
    if existing_user.employee_id != employee.id:
        existing_user.employee_id = employee.id
        db.commit()

    return {"message": "Profile approved and employee indexed", "user_created": False}


@router.put("/{profile_id}/reject")
def reject_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr),
):
    profile = db.query(EmployeeProfile).filter(EmployeeProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile.status = "rejected"
    db.commit()
    return {"message": "Profile rejected"}
