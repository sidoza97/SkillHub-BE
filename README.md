# SkillsHub — Backend

FastAPI backend for **SkillsHub**, an AI-powered skills intelligence platform that extracts employee skills from resumes, enables semantic search, and helps HR teams build the right teams.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI + Uvicorn |
| Database | SQLite via SQLAlchemy ORM |
| Vector Store | ChromaDB (semantic employee search) |
| AI / LLM | Azure OpenAI (Gemma 4), HuggingFace Router (DeepSeek V4 Pro, Llama 3 8B) |
| Auth | JWT (python-jose + passlib/bcrypt) |
| Conversation | LangGraph stateful chat graph |
| PDF Parsing | pdfplumber |

---

## Prerequisites

- Python 3.11+
- `pip` or `pip3`

---

## Setup

### 1. Clone and enter the backend directory

```bash
cd SkillHub-BE
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your API keys:

```env
# HuggingFace token — powers DeepSeek V4 Pro and Llama 3 8B
HF_TOKEN=your_hf_token_here          # https://huggingface.co/settings/tokens
HF_MODEL=deepseek-ai/DeepSeek-V4-Pro:novita
HF_BASE_URL=https://router.huggingface.co/v1

# Azure OpenAI — powers Gemma 4 (gpt-4.1 deployment)
GEMMA_API_KEY=your_azure_key_here
GEMMA_ENDPOINT=https://your-resource.openai.azure.com/
GEMMA_API_VERSION=2024-05-01-preview
GEMMA_DEPLOYMENT=gpt-4.1            # your actual Azure deployment name

# Llama 3 8B via HuggingFace Router
LLAMA_MODEL=meta-llama/Meta-Llama-3-8B-Instruct:novita

# App secrets (defaults are fine for local dev)
SECRET_KEY=skillshub-super-secret-key-change-in-production
DATABASE_URL=sqlite:///./skillshub.db
CHROMA_PATH=./chroma_db
```

> **Minimum to run:** You need at least one LLM configured. The app defaults to **Gemma 4** (Azure). If you only have a HuggingFace token, switch the default provider to `deepseek` in the UI.

### 5. Seed the database

```bash
python seed_data.py
```

This creates:
- 2 HR manager accounts
- 15 sample employees with realistic skills across Frontend, Backend, Data, DevOps domains
- All employees indexed in ChromaDB for semantic search

### 6. Start the server

```bash
uvicorn app.main:app --reload --port 8000
```

API docs (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Default Login Credentials

| Role | Email | Password |
|---|---|---|
| HR Manager | hr@skillshub.com | hr123456 |
| HR Manager | hr2@skillshub.com | hr123456 |
| Employee | rahul.sharma@example.com | emp123456 |
| Employee | priya.patel@example.com | emp123456 |
| Employee | (any seeded employee) | emp123456 |

> Employees created via HR import get the default password **SkillsHub@123** when their profile is approved.

---

## API Endpoints

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/login` | Login, returns JWT |
| POST | `/auth/register` | Register new user |
| GET | `/auth/me` | Get current user info |

### Employees
| Method | Endpoint | Description |
|---|---|---|
| GET | `/employees` | List all active employees with skills |
| GET | `/employees/{id}` | Get single employee |
| POST | `/employees` | Create employee (HR only) |
| PUT | `/employees/{id}` | Update employee |
| DELETE | `/employees/{id}` | Delete employee (HR only) |

### Resume Ingestion (AI-powered)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/ingestion/upload` | Upload PDF resume → AI extracts skills |
| POST | `/ingestion/text` | Paste resume text → AI extracts skills |
| POST | `/ingestion/bulk` | Bulk import employees from CSV (HR only) |

### HR Review Queue
| Method | Endpoint | Description |
|---|---|---|
| GET | `/review/queue` | Pending profiles awaiting approval |
| GET | `/review/all` | All submitted profiles |
| PUT | `/review/{id}/approve` | Approve → index in ChromaDB, create employee login |
| PUT | `/review/{id}/reject` | Reject profile |
| PUT | `/review/{id}` | Edit extracted JSON before approving |

### Search & Analytics
| Method | Endpoint | Description |
|---|---|---|
| POST | `/search/nl` | Natural language search with AI ranking |
| POST | `/search/chat` | Stateful conversational search (LangGraph) |
| GET | `/search/gaps` | Skill gap analysis across the organisation |
| POST | `/search/team-builder` | AI-powered team composition suggestions |

---

## LLM Selection

Pass the `X-LLM-Provider` header on any AI endpoint to select the model:

| Header value | Model | Provider |
|---|---|---|
| `gemma` | GPT-4.1 (branded Gemma 4) | Azure OpenAI |
| `deepseek` | DeepSeek V4 Pro | HuggingFace / Novita |
| `llama` | Meta Llama 3 8B Instruct | HuggingFace / Novita |

The frontend LLM selector in the sidebar sends this header automatically.

---

## Project Structure

```
SkillHub-BE/
├── app/
│   ├── main.py              # FastAPI app, CORS, router registration
│   ├── config.py            # Pydantic settings (reads .env)
│   ├── database.py          # SQLAlchemy engine + ChromaDB client
│   ├── models/
│   │   └── db_models.py     # Employee, Skill, User, EmployeeProfile ORM models
│   ├── routers/
│   │   ├── auth.py          # Login / register / JWT
│   │   ├── employees.py     # CRUD + active employee filtering
│   │   ├── ingestion.py     # PDF/text upload, AI extraction
│   │   ├── review.py        # HR approval workflow
│   │   └── search.py        # Semantic search, gaps, team builder, chat
│   └── services/
│       ├── llm_service.py   # Unified LLM client (Azure + HuggingFace)
│       ├── search_service.py# ChromaDB query + LLM ranking
│       └── chat_graph.py    # LangGraph stateful conversation graph
├── seed_data.py             # Database seeding script
├── requirements.txt
└── .env.example
```
