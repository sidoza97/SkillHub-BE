"""
Generate sample PDF resumes for SkillsHub demo testing.
Run: source venv/bin/activate && python3 generate_sample_resumes.py
Output: sample_resumes/ directory with 5 PDF files
"""

import os
from fpdf import FPDF, XPos, YPos

os.makedirs("sample_resumes", exist_ok=True)

W = 170   # usable page width after margins


class ResumePDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_margins(20, 20, 20)
        self.set_auto_page_break(auto=True, margin=18)

    def header(self):
        pass

    def draw_header(self, name: str, role: str, email: str, phone: str, location: str):
        self.set_font("Helvetica", "B", 17)
        self.set_text_color(15, 23, 42)
        self.cell(W, 9, name, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "I", 10)
        self.set_text_color(79, 70, 229)
        self.cell(W, 5, role, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(80, 80, 80)
        self.cell(W, 5, f"{email}   |   {phone}   |   {location}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(3)

    def sec(self, title: str):
        self.ln(3)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(30, 64, 175)
        self.cell(W, 6, title.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(30, 64, 175)
        self.set_line_width(0.35)
        self.line(self.l_margin, self.get_y(), self.l_margin + W, self.get_y())
        self.set_draw_color(0, 0, 0)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def job(self, title: str, company: str, period: str, bullets: list):
        self.set_font("Helvetica", "B", 9)
        self.cell(W, 5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(80, 80, 80)
        self.cell(W, 4, f"{company}  |  {period}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "", 8.5)
        for b in bullets:
            self.set_x(self.l_margin + 4)
            self.cell(4, 4, "-", new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.cell(W - 4, 4, "", new_x=XPos.LMARGIN, new_y=YPos.TOP)
            # Use cell with fixed width for bullet text
            self.set_x(self.l_margin + 8)
            txt = b
            # Wrap long bullets manually
            while txt:
                chars = min(len(txt), 90)
                line = txt[:chars]
                if chars < len(txt) and txt[chars] != ' ':
                    sp = line.rfind(' ')
                    if sp > 0:
                        line = txt[:sp]
                        chars = sp + 1
                self.cell(W - 8, 4, line.strip(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                txt = txt[chars:].strip()
                if txt:
                    self.set_x(self.l_margin + 8)
        self.ln(1)

    def skl(self, label: str, items: list):
        self.set_font("Helvetica", "B", 8.5)
        self.set_x(self.l_margin)
        self.cell(28, 4, f"{label}:", new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_font("Helvetica", "", 8.5)
        txt = ", ".join(items)
        self.cell(W - 28, 4, txt, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def cert(self, text: str):
        self.set_font("Helvetica", "", 8.5)
        self.set_x(self.l_margin)
        self.cell(W, 4, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)


# ── Resume 1: Siddharth Oza ──────────────────────────────────────────────────
def resume_siddharth():
    p = ResumePDF()
    p.add_page()
    p.draw_header("Siddharth Oza", "Full Stack Developer",
        "siddharthoza1997@gmail.com", "+91 9049733391", "Pune")

    p.set_font("Helvetica", "", 8.5)
    p.set_text_color(60, 60, 60)
    p.multi_cell(W, 4,
        "Full Stack Developer with 1.8+ years of experience building web applications. "
        "Proficient in React, Vue.js, NestJS, Spring Boot. Agile/Scrum practitioner.")
    p.set_text_color(0, 0, 0)

    p.sec("Work Experience")
    p.job("Associate Software Developer", "ValueAdd SoftTech & Systems Pvt Ltd", "Apr 2024 - Present", [
        "Built frontend features with Vue.js and Nuxt.js for ATC real estate platform.",
        "Delivered user management, role-based access, calendar and email template features in Scrum teams.",
        "Contributed to requirement gathering and technical specification writing.",
    ])
    p.job("Trainee Software Developer", "Cuembux Software Solutions, Pune", "Jun 2022 - Dec 2022", [
        "Full-stack dev using HTML, CSS, JavaScript, Angular, .NET and MS SQL Server.",
        "Bug fixing, enhancements, and daily design/analysis meetings.",
    ])

    p.sec("Skills")
    p.skl("Languages", ["JavaScript", "HTML", "CSS", "Java", "SQL"])
    p.skl("Frameworks", ["React.js", "Vue.js", "Nuxt.js", "Next.js", "NestJS", "Spring Boot"])
    p.skl("Databases", ["MySQL", "MongoDB"])
    p.skl("Tools", ["GitHub", "GitLab", "Postman", "Jira", "VS Code", "Cursor AI"])

    p.sec("Projects")
    p.job("Agent Transaction Control (ATC)", "Real Estate Platform", "Oct 2024 - Present", [
        "Real estate disclosure platform with RBAC for Sellers, Agents, Buyers and Transaction Controllers.",
        "Features: user management, multi-document handling, calendar, email templates.",
        "Stack: Vue.js + Nuxt.js frontend.",
    ])
    p.job("Exam Portal", "Under-Graduate Practice Platform", "Nov 2023", [
        "Free exam practice platform with profile, product and order management.",
    ])

    p.sec("Certifications")
    p.cert("MERN Stack Certificate (Apr 2024 - Oct 2024) - React, NestJS, NextJS")
    p.cert("Java Full Stack - Symbiosis University (Jan 2023 - May 2023) - Spring Boot, Angular")

    p.sec("Education")
    p.job("B.E. Mechanical Engineering - 7.2/10", "Sinhgad Institutes, Pune", "Jun 2015 - Jun 2020", [])

    p.output("sample_resumes/siddharth_oza_resume.pdf")
    print("  sample_resumes/siddharth_oza_resume.pdf")


# ── Resume 2: Ananya Krishnan (ML Engineer) ──────────────────────────────────
def resume_ananya():
    p = ResumePDF()
    p.add_page()
    p.draw_header("Ananya Krishnan", "Senior ML/AI Engineer",
        "ananya.krishnan@gmail.com", "+91 9876543210", "Bangalore")

    p.set_font("Helvetica", "", 8.5)
    p.set_text_color(60, 60, 60)
    p.multi_cell(W, 4,
        "Senior ML Engineer with 6+ years building production AI systems. Expert in deep learning, "
        "NLP, and MLOps. Led 5-person teams; models serving 10M+ requests/day.")
    p.set_text_color(0, 0, 0)

    p.sec("Work Experience")
    p.job("Senior ML Engineer", "TechCorp India Pvt Ltd, Bangalore", "Jan 2021 - Present", [
        "Designed NLP models for sentiment analysis using PyTorch and HuggingFace Transformers.",
        "Built MLOps pipelines with Kubeflow, MLflow and AWS SageMaker; 60% faster deployments.",
        "Led team of 5 to deliver recommendation engine for 10M users.",
    ])
    p.job("ML Engineer", "DataStream Analytics, Chennai", "Jul 2018 - Dec 2020", [
        "Built CV models for defect detection using TensorFlow and OpenCV.",
        "Deployed models as REST APIs with FastAPI and Docker.",
    ])

    p.sec("Skills")
    p.skl("Languages", ["Python", "R", "SQL", "Scala"])
    p.skl("ML/AI", ["PyTorch", "TensorFlow", "HuggingFace", "Scikit-learn", "LangChain"])
    p.skl("Data Eng", ["Apache Spark", "Pandas", "PostgreSQL", "MongoDB", "Airflow"])
    p.skl("MLOps", ["MLflow", "Kubeflow", "SageMaker", "Docker", "Kubernetes"])
    p.skl("Tools", ["Git", "Jupyter", "Grafana", "Jira"])

    p.sec("Projects")
    p.job("Real-Time Fraud Detection", "Production ML System", "2022 - Present", [
        "Ensemble model (XGBoost + Neural Net); 99.2% precision, 50K transactions/minute.",
    ])
    p.job("Multilingual NLP Pipeline", "NLP Research", "2021", [
        "Text classification in 12 Indian languages. Published at ACL 2021 workshop.",
    ])

    p.sec("Education")
    p.job("M.Tech Computer Science (AI Specialization)", "IIT Madras", "2016 - 2018", [])
    p.job("B.Tech Computer Science", "NIT Trichy", "2012 - 2016", [])

    p.output("sample_resumes/ananya_krishnan_resume.pdf")
    print("  sample_resumes/ananya_krishnan_resume.pdf")


# ── Resume 3: Rahul Sharma (Senior React Dev) ─────────────────────────────────
def resume_rahul():
    p = ResumePDF()
    p.add_page()
    p.draw_header("Rahul Sharma", "Senior React Developer",
        "rahul.sharma@gmail.com", "+91 9012345678", "Pune")

    p.set_font("Helvetica", "", 8.5)
    p.set_text_color(60, 60, 60)
    p.multi_cell(W, 4,
        "Senior Frontend Developer with 6+ years building high-performance React apps. "
        "Expert in TypeScript, Next.js and real-time web systems.")
    p.set_text_color(0, 0, 0)

    p.sec("Work Experience")
    p.job("Senior React Developer", "FinTech Solutions Ltd, Pune", "Mar 2021 - Present", [
        "Led frontend for e-commerce platform (2M+ users) using React, TypeScript and Next.js.",
        "Real-time order tracking via WebSockets + Redux Toolkit; 35% fewer support tickets.",
        "Mentored 3 junior devs; established coding standards and review processes.",
    ])
    p.job("Frontend Developer", "Webcraft India, Pune", "Aug 2018 - Feb 2021", [
        "Built 15+ responsive apps with React and Redux; integrated REST and GraphQL APIs.",
        "Improved Core Web Vitals from 45 to 92 via bundle optimization and lazy loading.",
    ])

    p.sec("Skills")
    p.skl("Languages", ["JavaScript", "TypeScript", "HTML5", "CSS3", "GraphQL"])
    p.skl("Frameworks", ["React.js", "Next.js", "Redux", "React Query", "Tailwind CSS"])
    p.skl("Testing", ["Jest", "React Testing Library", "Cypress"])
    p.skl("Tools", ["GitHub", "Webpack", "Vite", "Figma", "Storybook", "Jira"])

    p.sec("Projects")
    p.job("E-Commerce Platform Overhaul", "FinTech Solutions", "2023", [
        "Migrated legacy jQuery to Next.js 14. Load time from 4.2s to 0.8s; Lighthouse 98.",
    ])
    p.job("Real-Time Trading Dashboard", "Financial Analytics", "2022", [
        "WebSocket-powered live trading charts with React + D3.js; 200ms data refresh.",
    ])

    p.sec("Education")
    p.job("B.E. Information Technology", "Pune University", "2014 - 2018", [])

    p.output("sample_resumes/rahul_sharma_resume.pdf")
    print("  sample_resumes/rahul_sharma_resume.pdf")


# ── Resume 4: Priya Patel (Backend Python) ────────────────────────────────────
def resume_priya():
    p = ResumePDF()
    p.add_page()
    p.draw_header("Priya Patel", "Senior Backend Engineer",
        "priya.patel@gmail.com", "+91 8765432109", "Bangalore")

    p.set_font("Helvetica", "", 8.5)
    p.set_text_color(60, 60, 60)
    p.multi_cell(W, 4,
        "Backend engineer with 7 years in Python, Django and distributed systems. "
        "APIs serving 50M requests/day. Passionate about system design and performance.")
    p.set_text_color(0, 0, 0)

    p.sec("Work Experience")
    p.job("Senior Backend Engineer", "CloudBase Technologies, Bangalore", "Jun 2020 - Present", [
        "Microservices architecture for B2B SaaS using Python, FastAPI and PostgreSQL.",
        "Reduced API latency by 70% with query optimization and Redis caching.",
        "CI/CD pipelines with GitHub Actions; deployed to AWS ECS via Terraform.",
    ])
    p.job("Backend Developer", "Infosys Ltd, Bangalore", "Jul 2017 - May 2020", [
        "RESTful APIs for banking using Django REST Framework; 99.9% uptime SLA.",
        "ETL pipelines for 10GB+ daily data with Celery and Apache Airflow.",
    ])

    p.sec("Skills")
    p.skl("Languages", ["Python", "SQL", "Bash"])
    p.skl("Frameworks", ["FastAPI", "Django", "Flask", "Celery"])
    p.skl("Databases", ["PostgreSQL", "MongoDB", "Redis", "Elasticsearch"])
    p.skl("Cloud/Ops", ["AWS EC2/S3/RDS/ECS", "Docker", "Kubernetes", "Terraform"])
    p.skl("Tools", ["GitHub", "Postman", "Grafana", "Prometheus", "Jira"])

    p.sec("Projects")
    p.job("Multi-Tenant SaaS API", "CloudBase Technologies", "2021", [
        "Row-level security multi-tenancy in PostgreSQL; 50M requests/day, P99 < 120ms.",
    ])

    p.sec("Education")
    p.job("B.E. Computer Science", "RV College of Engineering, Bangalore", "2013 - 2017", [])

    p.output("sample_resumes/priya_patel_resume.pdf")
    print("  sample_resumes/priya_patel_resume.pdf")


# ── Resume 5: Vikram Nair (DevOps / Cloud) ────────────────────────────────────
def resume_vikram():
    p = ResumePDF()
    p.add_page()
    p.draw_header("Vikram Nair", "Senior DevOps Engineer",
        "vikram.nair@gmail.com", "+91 7654321098", "Mumbai")

    p.set_font("Helvetica", "", 8.5)
    p.set_text_color(60, 60, 60)
    p.multi_cell(W, 4,
        "DevOps Engineer with 5+ years automating cloud infra and CI/CD pipelines. "
        "AWS Certified Solutions Architect. Expert in Kubernetes, Terraform and GitOps.")
    p.set_text_color(0, 0, 0)

    p.sec("Work Experience")
    p.job("Senior DevOps Engineer", "StartupBase India, Mumbai", "Sep 2021 - Present", [
        "Managed Kubernetes clusters on AWS EKS for 200+ microservices.",
        "Cut infra costs by 40% with spot instances; GitOps via ArgoCD.",
        "Centralized observability: ELK stack + Grafana dashboards.",
    ])
    p.job("Cloud Infrastructure Engineer", "TechOps Solutions, Mumbai", "Jan 2019 - Aug 2021", [
        "Migrated on-prem infra to AWS; 99.95% uptime.",
        "IaC with Terraform and Ansible; multi-region DR with RTO < 15 min.",
    ])

    p.sec("Skills")
    p.skl("Cloud", ["AWS EKS/EC2/S3/RDS/Lambda", "GCP"])
    p.skl("Containers", ["Docker", "Kubernetes", "Helm", "ArgoCD", "Istio"])
    p.skl("IaC", ["Terraform", "Ansible", "CloudFormation"])
    p.skl("CI/CD", ["GitHub Actions", "Jenkins", "GitLab CI"])
    p.skl("Monitoring", ["Grafana", "Prometheus", "ELK Stack", "Datadog"])
    p.skl("Languages", ["Bash", "Python", "YAML"])

    p.sec("Certifications")
    p.cert("AWS Certified Solutions Architect - Professional (2023)")
    p.cert("Certified Kubernetes Administrator (CKA) (2022)")

    p.sec("Education")
    p.job("B.E. Electronics & Telecommunication", "VJTI Mumbai", "2014 - 2018", [])

    p.output("sample_resumes/vikram_nair_resume.pdf")
    print("  sample_resumes/vikram_nair_resume.pdf")


if __name__ == "__main__":
    print("Generating sample resumes...")
    resume_siddharth()
    resume_ananya()
    resume_rahul()
    resume_priya()
    resume_vikram()
    print("\nAll 5 sample resumes in sample_resumes/")
    print("Use these PDFs to test HR Import and Employee Upload flows.")
