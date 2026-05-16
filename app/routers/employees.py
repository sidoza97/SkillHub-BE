from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.db_models import Employee, EmployeeProfile, Skill, User
from ..models.schemas import EmployeeCreate, EmployeeOut, SkillCreate, SkillOut
from ..utils.auth import get_current_user, require_hr

router = APIRouter(prefix="/employees", tags=["employees"])


def _check_employee_access(current_user: User, employee_id: int):
    if current_user.role == "employee" and current_user.employee_id != employee_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this profile")


def _active_employees_query(db: Session):
    """Employees with no profile (manually created) or an approved profile only."""
    approved_ids = db.query(EmployeeProfile.employee_id).filter(EmployeeProfile.status == "approved")
    has_any_profile = db.query(EmployeeProfile.employee_id)
    return db.query(Employee).filter(
        or_(~Employee.id.in_(has_any_profile), Employee.id.in_(approved_ids))
    )


@router.get("", response_model=List[EmployeeOut])
def list_employees(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _active_employees_query(db).order_by(Employee.name).all()


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


@router.post("", response_model=EmployeeOut)
def create_employee(
    emp_data: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr),
):
    if db.query(Employee).filter(Employee.email == emp_data.email).first():
        raise HTTPException(status_code=400, detail="Employee email already exists")
    if db.query(Employee).filter(Employee.name == emp_data.name).first():
        raise HTTPException(status_code=400, detail="An employee with this name already exists")
    emp = Employee(**emp_data.model_dump())
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


@router.delete("/{employee_id}")
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr),
):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    # Unlink user account if any
    linked_user = db.query(User).filter(User.employee_id == employee_id).first()
    if linked_user:
        linked_user.employee_id = None
        db.flush()
    db.delete(emp)
    db.commit()
    return {"ok": True}


@router.put("/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: int,
    emp_data: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_employee_access(current_user, employee_id)
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    for key, val in emp_data.model_dump(exclude_unset=True).items():
        setattr(emp, key, val)
    db.commit()
    db.refresh(emp)
    return emp


# ── Skill CRUD ───────────────────────────────────────────────────────────────

@router.post("/{employee_id}/skills", response_model=SkillOut)
def add_skill(
    employee_id: int,
    skill_data: SkillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_employee_access(current_user, employee_id)
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    skill = Skill(employee_id=employee_id, **skill_data.model_dump())
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.put("/{employee_id}/skills/{skill_id}", response_model=SkillOut)
def update_skill(
    employee_id: int,
    skill_id: int,
    skill_data: SkillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_employee_access(current_user, employee_id)
    skill = db.query(Skill).filter(Skill.id == skill_id, Skill.employee_id == employee_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    for key, val in skill_data.model_dump(exclude_unset=True).items():
        setattr(skill, key, val)
    db.commit()
    db.refresh(skill)
    return skill


@router.delete("/{employee_id}/skills/{skill_id}")
def delete_skill(
    employee_id: int,
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_employee_access(current_user, employee_id)
    skill = db.query(Skill).filter(Skill.id == skill_id, Skill.employee_id == employee_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    db.delete(skill)
    db.commit()
    return {"ok": True}
