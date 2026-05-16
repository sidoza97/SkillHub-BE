from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "hr" or "employee"
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=True)
    department = Column(String, nullable=True)
    location = Column(String, nullable=True)
    current_project = Column(String, nullable=True)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    skills = relationship("Skill", back_populates="employee", cascade="all, delete-orphan")
    profiles = relationship("EmployeeProfile", back_populates="employee", cascade="all, delete-orphan")


class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    status = Column(String, default="pending")  # pending / approved / rejected
    raw_text = Column(Text, nullable=True)
    extracted_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = relationship("Employee", back_populates="profiles")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)  # language/framework/platform/tool/domain
    proficiency = Column(String, nullable=True)  # novice/intermediate/expert
    years_experience = Column(Float, nullable=True)
    is_inferred = Column(Boolean, default=False)
    confidence = Column(Float, nullable=True)

    employee = relationship("Employee", back_populates="skills")
