import json
import re

from .llm_service import chat_completion

EXTRACTION_PROMPT = """You are an expert resume parser. Extract structured information from the resume text below.

Return ONLY a valid JSON object — no markdown, no code fences, no explanation.

JSON structure:
{{
  "personal_info": {{
    "name": "Full Name",
    "email": "email@example.com",
    "location": "City, Country",
    "title": "Job Title"
  }},
  "skills": [
    {{
      "name": "Skill Name",
      "category": "language|framework|platform|tool|domain",
      "proficiency": "novice|intermediate|expert",
      "years_experience": 3.5,
      "is_inferred": false,
      "confidence": 1.0
    }}
  ],
  "inferred_skills": [
    {{
      "name": "React",
      "category": "framework",
      "proficiency": "expert",
      "years_experience": 4.0,
      "is_inferred": true,
      "confidence": 0.9,
      "reason": "Inferred because Next.js requires React knowledge"
    }}
  ],
  "projects": [
    {{
      "name": "Project Name",
      "description": "What it does",
      "technologies": ["Tech1", "Tech2"],
      "duration": "6 months"
    }}
  ],
  "experience_years": 5,
  "current_project": "Project Name or null",
  "department": "Engineering",
  "summary": "Brief professional summary"
}}

Skill inference rules (apply these automatically):
- Next.js → infer React at same proficiency/years
- TypeScript → infer JavaScript at same proficiency/years
- React Native → infer React at same proficiency/years
- Angular or Vue.js → infer JavaScript
- Kubernetes → infer Docker
- Django or Flask or FastAPI → infer Python (if not already listed)
- Spring Boot → infer Java (if not already listed)

Resume text:
{resume_text}"""


def extract_skills_from_text(resume_text: str, provider: str = "deepseek") -> dict:
    prompt = EXTRACTION_PROMPT.format(resume_text=resume_text[:6000])
    response = ""
    try:
        response = chat_completion(
            messages=[{"role": "user", "content": prompt}],
            provider=provider,
            temperature=0.1,
        )
        cleaned = response.strip()
        # Strip markdown code fences if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"```(?:json)?\n?", "", cleaned).strip().rstrip("`").strip()
        result = json.loads(cleaned)
        # Remove inferred skills that already exist in explicit skills
        explicit_names = {s.get("name", "").strip().lower() for s in result.get("skills", [])}
        result["inferred_skills"] = [
            s for s in result.get("inferred_skills", [])
            if s.get("name", "").strip().lower() not in explicit_names
        ]
        return result
    except Exception as e:
        return {
            "error": str(e),
            "raw_response": response,
            "personal_info": {},
            "skills": [],
            "inferred_skills": [],
            "projects": [],
        }
