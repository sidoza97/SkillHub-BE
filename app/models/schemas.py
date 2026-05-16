from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str
    password: str
    role: str
    name: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict


class SkillBase(BaseModel):
    name: str
    category: Optional[str] = None
    proficiency: Optional[str] = None
    years_experience: Optional[float] = None
    is_inferred: Optional[bool] = False
    confidence: Optional[float] = None


class SkillCreate(SkillBase):
    pass


class SkillOut(SkillBase):
    id: int
    employee_id: int

    class Config:
        from_attributes = True


class EmployeeBase(BaseModel):
    name: str
    email: str
    title: Optional[str] = None
    location: Optional[str] = None
    current_project: Optional[str] = None
    is_available: Optional[bool] = True


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeOut(EmployeeBase):
    id: int
    created_at: datetime
    skills: List[SkillOut] = []

    class Config:
        from_attributes = True


class ProfileOut(BaseModel):
    id: int
    employee_id: int
    status: str
    raw_text: Optional[str] = None
    extracted_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    employee: Optional[EmployeeOut] = None

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    extracted_json: Optional[str] = None


class NLSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 10


class TextIngestionRequest(BaseModel):
    text: str
    employee_id: Optional[int] = None
