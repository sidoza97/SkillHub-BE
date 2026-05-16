import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import Base, SessionLocal, employee_collection, engine
from app.models.db_models import Employee, EmployeeProfile, Skill, User
from app.services.search_service import index_employee
from app.utils.auth import hash_password

EMPLOYEES_DATA = [
    {
        "name": "Rahul Sharma",
        "email": "rahul.sharma@gmail.com",
        "title": "Senior React Developer",
        "location": "Pune",
        "current_project": "E-commerce Platform",
        "is_available": False,
        "skills": [
            {"name": "React", "category": "framework", "proficiency": "expert", "years_experience": 5.0},
            {"name": "TypeScript", "category": "language", "proficiency": "expert", "years_experience": 4.0},
            {"name": "Node.js", "category": "platform", "proficiency": "intermediate", "years_experience": 3.0},
            {"name": "Next.js", "category": "framework", "proficiency": "expert", "years_experience": 4.0},
            {"name": "Redux", "category": "tool", "proficiency": "intermediate", "years_experience": 3.0},
        ],
        "inferred": [
            {"name": "JavaScript", "category": "language", "proficiency": "expert", "years_experience": 5.0, "is_inferred": True, "confidence": 0.95},
        ],
    },
    {
        "name": "Priya Patel",
        "email": "priya.patel@gmail.com",
        "title": "Full Stack Developer",
        "location": "Bangalore",
        "current_project": None,
        "is_available": True,
        "skills": [
            {"name": "Python", "category": "language", "proficiency": "expert", "years_experience": 6.0},
            {"name": "Django", "category": "framework", "proficiency": "expert", "years_experience": 5.0},
            {"name": "React", "category": "framework", "proficiency": "intermediate", "years_experience": 3.0},
            {"name": "PostgreSQL", "category": "tool", "proficiency": "expert", "years_experience": 5.0},
            {"name": "Docker", "category": "platform", "proficiency": "intermediate", "years_experience": 2.0},
        ],
        "inferred": [],
    },
    {
        "name": "Arjun Singh",
        "email": "arjun.singh@gmail.com",
        "title": "Senior Backend Developer",
        "location": "Mumbai",
        "current_project": "Payment Gateway",
        "is_available": False,
        "skills": [
            {"name": "Java", "category": "language", "proficiency": "expert", "years_experience": 7.0},
            {"name": "Spring Boot", "category": "framework", "proficiency": "expert", "years_experience": 5.0},
            {"name": "Kubernetes", "category": "platform", "proficiency": "intermediate", "years_experience": 2.0},
            {"name": "MySQL", "category": "tool", "proficiency": "expert", "years_experience": 6.0},
            {"name": "AWS", "category": "platform", "proficiency": "intermediate", "years_experience": 3.0},
        ],
        "inferred": [
            {"name": "Docker", "category": "platform", "proficiency": "intermediate", "years_experience": 2.0, "is_inferred": True, "confidence": 0.9},
        ],
    },
    {
        "name": "Neha Gupta",
        "email": "neha.gupta@gmail.com",
        "title": "Frontend Developer",
        "location": "Chennai",
        "current_project": None,
        "is_available": True,
        "skills": [
            {"name": "Vue.js", "category": "framework", "proficiency": "expert", "years_experience": 4.0},
            {"name": "JavaScript", "category": "language", "proficiency": "expert", "years_experience": 5.0},
            {"name": "CSS", "category": "tool", "proficiency": "intermediate", "years_experience": 4.0},
            {"name": "GraphQL", "category": "tool", "proficiency": "intermediate", "years_experience": 2.0},
        ],
        "inferred": [],
    },
    {
        "name": "Karan Mehta",
        "email": "karan.mehta@gmail.com",
        "title": "DevOps Engineer",
        "location": "Pune",
        "current_project": None,
        "is_available": True,
        "skills": [
            {"name": "Docker", "category": "platform", "proficiency": "expert", "years_experience": 5.0},
            {"name": "Kubernetes", "category": "platform", "proficiency": "expert", "years_experience": 4.0},
            {"name": "AWS", "category": "platform", "proficiency": "expert", "years_experience": 5.0},
            {"name": "Terraform", "category": "tool", "proficiency": "expert", "years_experience": 3.0},
            {"name": "Python", "category": "language", "proficiency": "intermediate", "years_experience": 3.0},
        ],
        "inferred": [],
    },
    {
        "name": "Divya Nair",
        "email": "divya.nair@gmail.com",
        "title": "Data Scientist",
        "location": "Bangalore",
        "current_project": "ML Pipeline",
        "is_available": False,
        "skills": [
            {"name": "Python", "category": "language", "proficiency": "expert", "years_experience": 5.0},
            {"name": "TensorFlow", "category": "framework", "proficiency": "expert", "years_experience": 3.0},
            {"name": "Pandas", "category": "tool", "proficiency": "expert", "years_experience": 4.0},
            {"name": "SQL", "category": "language", "proficiency": "intermediate", "years_experience": 3.0},
            {"name": "PyTorch", "category": "framework", "proficiency": "intermediate", "years_experience": 2.0},
        ],
        "inferred": [],
    },
    {
        "name": "Vikram Reddy",
        "email": "vikram.reddy@gmail.com",
        "title": "Senior Node.js Developer",
        "location": "Hyderabad",
        "current_project": None,
        "is_available": True,
        "skills": [
            {"name": "Node.js", "category": "platform", "proficiency": "expert", "years_experience": 6.0},
            {"name": "Express", "category": "framework", "proficiency": "expert", "years_experience": 5.0},
            {"name": "MongoDB", "category": "tool", "proficiency": "expert", "years_experience": 5.0},
            {"name": "WebSocket", "category": "tool", "proficiency": "expert", "years_experience": 4.0},
            {"name": "Redis", "category": "tool", "proficiency": "intermediate", "years_experience": 3.0},
        ],
        "inferred": [
            {"name": "JavaScript", "category": "language", "proficiency": "expert", "years_experience": 6.0, "is_inferred": True, "confidence": 0.95},
        ],
    },
    {
        "name": "Ananya Krishnan",
        "email": "ananya.krishnan@gmail.com",
        "title": "React Native Developer",
        "location": "Bangalore",
        "current_project": None,
        "is_available": True,
        "skills": [
            {"name": "React Native", "category": "framework", "proficiency": "expert", "years_experience": 4.0},
            {"name": "React", "category": "framework", "proficiency": "expert", "years_experience": 4.0},
            {"name": "JavaScript", "category": "language", "proficiency": "expert", "years_experience": 5.0},
            {"name": "TypeScript", "category": "language", "proficiency": "intermediate", "years_experience": 2.0},
        ],
        "inferred": [],
    },
    {
        "name": "Rohit Joshi",
        "email": "rohit.joshi@gmail.com",
        "title": "Angular Developer",
        "location": "Delhi",
        "current_project": "HR Portal",
        "is_available": False,
        "skills": [
            {"name": "Angular", "category": "framework", "proficiency": "expert", "years_experience": 5.0},
            {"name": "TypeScript", "category": "language", "proficiency": "expert", "years_experience": 5.0},
            {"name": "RxJS", "category": "tool", "proficiency": "expert", "years_experience": 4.0},
            {"name": "Node.js", "category": "platform", "proficiency": "intermediate", "years_experience": 2.0},
        ],
        "inferred": [
            {"name": "JavaScript", "category": "language", "proficiency": "expert", "years_experience": 5.0, "is_inferred": True, "confidence": 0.95},
        ],
    },
    {
        "name": "Sneha Agarwal",
        "email": "sneha.agarwal@gmail.com",
        "title": "Full Stack Developer",
        "location": "Pune",
        "current_project": None,
        "is_available": True,
        "skills": [
            {"name": "React", "category": "framework", "proficiency": "expert", "years_experience": 4.0},
            {"name": "Node.js", "category": "platform", "proficiency": "expert", "years_experience": 3.0},
            {"name": "MongoDB", "category": "tool", "proficiency": "expert", "years_experience": 3.0},
            {"name": "AWS", "category": "platform", "proficiency": "expert", "years_experience": 2.0},
            {"name": "Docker", "category": "platform", "proficiency": "intermediate", "years_experience": 2.0},
        ],
        "inferred": [
            {"name": "JavaScript", "category": "language", "proficiency": "expert", "years_experience": 4.0, "is_inferred": True, "confidence": 0.9},
        ],
    },
    {
        "name": "Aditya Kumar",
        "email": "aditya.kumar@gmail.com",
        "title": "Senior Python Developer",
        "location": "Chennai",
        "current_project": None,
        "is_available": True,
        "skills": [
            {"name": "Python", "category": "language", "proficiency": "expert", "years_experience": 7.0},
            {"name": "FastAPI", "category": "framework", "proficiency": "expert", "years_experience": 3.0},
            {"name": "SQLAlchemy", "category": "tool", "proficiency": "expert", "years_experience": 4.0},
            {"name": "PostgreSQL", "category": "tool", "proficiency": "expert", "years_experience": 5.0},
            {"name": "Docker", "category": "platform", "proficiency": "intermediate", "years_experience": 3.0},
        ],
        "inferred": [],
    },
    {
        "name": "Meera Iyer",
        "email": "meera.iyer@gmail.com",
        "title": "Cloud & DevOps Engineer",
        "location": "Bangalore",
        "current_project": "Cloud Migration",
        "is_available": False,
        "skills": [
            {"name": "AWS", "category": "platform", "proficiency": "expert", "years_experience": 6.0},
            {"name": "GCP", "category": "platform", "proficiency": "expert", "years_experience": 3.0},
            {"name": "Jenkins", "category": "tool", "proficiency": "expert", "years_experience": 4.0},
            {"name": "Docker", "category": "platform", "proficiency": "expert", "years_experience": 5.0},
            {"name": "Kubernetes", "category": "platform", "proficiency": "intermediate", "years_experience": 3.0},
        ],
        "inferred": [],
    },
    {
        "name": "Siddharth Rao",
        "email": "siddharth.rao@gmail.com",
        "title": "Senior Frontend Architect",
        "location": "Mumbai",
        "current_project": None,
        "is_available": True,
        "skills": [
            {"name": "React", "category": "framework", "proficiency": "expert", "years_experience": 6.0},
            {"name": "TypeScript", "category": "language", "proficiency": "expert", "years_experience": 5.0},
            {"name": "GraphQL", "category": "tool", "proficiency": "expert", "years_experience": 4.0},
            {"name": "Next.js", "category": "framework", "proficiency": "expert", "years_experience": 4.0},
            {"name": "WebSocket", "category": "tool", "proficiency": "expert", "years_experience": 3.0},
        ],
        "inferred": [
            {"name": "JavaScript", "category": "language", "proficiency": "expert", "years_experience": 6.0, "is_inferred": True, "confidence": 0.95},
        ],
    },
    {
        "name": "Pooja Sharma",
        "email": "pooja.sharma@gmail.com",
        "title": "Senior QA Engineer",
        "location": "Pune",
        "current_project": None,
        "is_available": True,
        "skills": [
            {"name": "Selenium", "category": "tool", "proficiency": "expert", "years_experience": 5.0},
            {"name": "Python", "category": "language", "proficiency": "expert", "years_experience": 3.0},
            {"name": "Cypress", "category": "tool", "proficiency": "expert", "years_experience": 3.0},
            {"name": "JavaScript", "category": "language", "proficiency": "intermediate", "years_experience": 3.0},
            {"name": "Docker", "category": "platform", "proficiency": "intermediate", "years_experience": 2.0},
        ],
        "inferred": [],
    },
    {
        "name": "Nikhil Verma",
        "email": "nikhil.verma@gmail.com",
        "title": "Backend Architect",
        "location": "Hyderabad",
        "current_project": None,
        "is_available": True,
        "skills": [
            {"name": "Java", "category": "language", "proficiency": "expert", "years_experience": 5.0},
            {"name": "Kafka", "category": "platform", "proficiency": "expert", "years_experience": 3.0},
            {"name": "Microservices", "category": "domain", "proficiency": "expert", "years_experience": 4.0},
            {"name": "Spring Boot", "category": "framework", "proficiency": "expert", "years_experience": 4.0},
            {"name": "Docker", "category": "platform", "proficiency": "expert", "years_experience": 3.0},
        ],
        "inferred": [],
    },
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if db.query(User).filter(User.email == "hr@skillshub.com").first():
            print("Already seeded — re-indexing ChromaDB...")
            employees = db.query(Employee).all()
            for emp in employees:
                if emp.skills:
                    index_employee(emp)
            print(f"Re-indexed {len(employees)} employees.")
            return

        print("Seeding database...")

        hr1 = User(email="hr@skillshub.com", hashed_password=hash_password("hr123456"), role="hr")
        hr2 = User(email="hr2@skillshub.com", hashed_password=hash_password("hr123456"), role="hr")
        db.add_all([hr1, hr2])
        db.flush()
        print("  Created HR users")

        for emp_data in EMPLOYEES_DATA:
            emp = Employee(
                name=emp_data["name"],
                email=emp_data["email"],
                title=emp_data["title"],
                location=emp_data["location"],
                current_project=emp_data["current_project"],
                is_available=emp_data["is_available"],
            )
            db.add(emp)
            db.flush()

            for s in emp_data["skills"]:
                db.add(Skill(employee_id=emp.id, **s))
            for s in emp_data.get("inferred", []):
                db.add(Skill(employee_id=emp.id, **s))

            db.add(User(
                email=emp_data["email"],
                hashed_password=hash_password("emp123456"),
                role="employee",
                employee_id=emp.id,
            ))
            db.add(EmployeeProfile(
                employee_id=emp.id,
                status="approved",
                raw_text=f"{emp_data['name']} — {emp_data['title']}",
                extracted_json=json.dumps({"personal_info": {"name": emp_data["name"], "title": emp_data["title"], "location": emp_data["location"]}}),
            ))

            db.flush()
            print(f"  Created: {emp_data['name']}")

        db.commit()

        print("\nIndexing in ChromaDB...")
        employees = db.query(Employee).all()
        for emp in employees:
            if emp.skills:
                index_employee(emp)
        print(f"  Indexed {len(employees)} employees")

        print("\n✓ Done!")
        print("\nDefault credentials:")
        print("  HR:       hr@skillshub.com      / hr123456")
        print("  HR2:      hr2@skillshub.com     / hr123456")
        print("  Employee: rahul.sharma@gmail.com / emp123456")
        print("  (all 15 employees use password: emp123456)")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
