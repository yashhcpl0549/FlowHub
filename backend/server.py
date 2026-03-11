from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Cookie, Response, BackgroundTasks, Form
from fastapi.responses import FileResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import asyncio
import resend
import httpx
import shutil
import subprocess
from agent_executor import run_agent_script as execute_agent_script
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Resend API setup
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Google OAuth
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')

# File storage configuration
UPLOADS_DIR = ROOT_DIR / 'uploads'
OUTPUTS_DIR = ROOT_DIR / 'outputs'
UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

# GCS configuration (optional)
GCS_BUCKET = os.environ.get('GCS_BUCKET', '')
GCS_CREDENTIALS_PATH = os.environ.get('GCS_CREDENTIALS_PATH', '')

# Agent execution limits
MAX_CONCURRENT_AGENTS = int(os.environ.get('MAX_CONCURRENT_AGENTS', '10'))

# Track active jobs for queue management
active_jobs_lock = asyncio.Lock()
active_jobs_count = 0

# Initialize GCS client if configured
gcs_client = None
gcs_bucket = None
if GCS_BUCKET:
    try:
        from google.cloud import storage
        if GCS_CREDENTIALS_PATH and os.path.exists(GCS_CREDENTIALS_PATH):
            gcs_client = storage.Client.from_service_account_json(GCS_CREDENTIALS_PATH)
        else:
            gcs_client = storage.Client()
        gcs_bucket = gcs_client.bucket(GCS_BUCKET)
        logging.info(f"GCS configured with bucket: {GCS_BUCKET}")
    except Exception as e:
        logging.warning(f"GCS not available: {e}. Using local storage.")
        gcs_client = None
        gcs_bucket = None

# Create the main app
app = FastAPI(title="Honasa Task Force API", version="1.0.0")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ MODELS ============

class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: str = ""
    role: str = "user"
    agent_access: List[str] = []
    created_at: datetime

class UserSession(BaseModel):
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime

class SessionRequest(BaseModel):
    session_id: str

class GoogleAuthRequest(BaseModel):
    credential: str

class Agent(BaseModel):
    agent_id: str
    name: str
    description: str
    required_files: List[str]
    tag: Optional[str] = None
    agent_type: Optional[str] = None
    iframe_url: Optional[str] = None
    validation_script: Optional[str] = None
    main_script: Optional[str] = None
    status: str = "active"
    created_at: datetime
    created_by: Optional[str] = None

class Job(BaseModel):
    job_id: str
    agent_id: str
    user_id: str
    status: str
    input_files: List[str]
    output_files: List[str]
    error_message: Optional[str] = None
    validation_output: Optional[str] = None
    execution_output: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class FileInfo(BaseModel):
    file_id: str
    job_id: str
    user_id: str
    file_name: str
    file_path: str
    file_type: str
    uploaded_at: datetime

class EmailRequest(BaseModel):
    recipient_email: EmailStr
    subject: str
    html_content: str

class UpdateRoleRequest(BaseModel):
    role: str

# ============ AUTH HELPER ============

async def get_current_user(session_token: Optional[str] = Cookie(None), authorization: Optional[str] = None) -> User:
    token = session_token
    if not token and authorization:
        if authorization.startswith('Bearer '):
            token = authorization[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_doc = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")

    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    user_doc = await db.users.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    if isinstance(user_doc['created_at'], str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])

    return User(**user_doc)

# ============ AUTH ROUTES ============

@api_router.post("/auth/google")
async def google_login(request: GoogleAuthRequest, response: Response):
    """Verify Google OAuth token and create session"""
    try:
        if not GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=500, detail="Google OAuth not configured on server")

        idinfo = id_token.verify_oauth2_token(
            request.credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )

        email = idinfo['email']
        name = idinfo.get('name', email.split('@')[0])
        picture = idinfo.get('picture', '')
        admin_emails = ["yash.b@mamaearth.in", "sameer.c@mamaearth.in", "rahul.gupta@mamaearth.in"]

        existing_user = await db.users.find_one({"email": email}, {"_id": 0})
        if existing_user:
            user_id = existing_user["user_id"]
            await db.users.update_one(
                {"user_id": user_id},
                {"$set": {"name": name, "picture": picture}}
            )
        else:
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            await db.users.insert_one({
                "user_id": user_id,
                "email": email,
                "name": name,
                "picture": picture,
                "role": "admin" if email in admin_emails else "user",
                "agent_access": [],
                "created_at": datetime.now(timezone.utc).isoformat()
            })

        session_token = f"session_{uuid.uuid4().hex}"
        await db.user_sessions.insert_one({
            "user_id": user_id,
            "session_token": session_token,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        })

        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=False,
            samesite="lax",
            path="/",
            max_age=30 * 24 * 60 * 60
        )

        user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if isinstance(user_doc['created_at'], str):
            user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
        return {"user": User(**user_doc), "session_token": session_token}

    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")
    except Exception as e:
        logger.error(f"Google auth failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/auth/logout")
async def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out successfully"}

@api_router.get("/auth/me")
async def get_me(session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(session_token=session_token)
    return user

@api_router.get("/users/me")
async def get_current_user_profile(session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(session_token=session_token)
    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
    return user_doc

# ============ ADMIN MIDDLEWARE ============

async def require_admin(session_token: Optional[str] = Cookie(None)) -> User:
    user = await get_current_user(session_token=session_token)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# ============ ADMIN: USERS ============

@api_router.get("/admin/users")
async def get_all_users(session_token: Optional[str] = Cookie(None)):
    await require_admin(session_token=session_token)
    users = await db.users.find({}, {"_id": 0}).to_list(1000)
    for user in users:
        if isinstance(user.get('created_at'), str):
            user['created_at'] = datetime.fromisoformat(user['created_at'])
    return users

@api_router.put("/admin/users/{user_id}/access")
async def update_user_access(
    user_id: str,
    agent_ids: List[str],
    session_token: Optional[str] = Cookie(None)
):
    await require_admin(session_token=session_token)
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"agent_access": agent_ids}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User access updated", "agent_ids": agent_ids}

@api_router.put("/admin/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    request: UpdateRoleRequest,
    session_token: Optional[str] = Cookie(None)
):
    await require_admin(session_token=session_token)
    if request.role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'")
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"role": request.role}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": f"User role updated to {request.role}", "role": request.role}

# ============ ADMIN: AGENTS ============

@api_router.post("/admin/agents")
async def create_agent(
    name: str = Form(...),
    description: str = Form(...),
    required_files: str = Form(...),
    validation_file: Optional[UploadFile] = File(None),
    main_file: Optional[UploadFile] = File(None),
    session_token: Optional[str] = Cookie(None)
):
    user = await require_admin(session_token=session_token)
    agent_id = f"agent_{uuid.uuid4().hex[:12]}"
    validation_path = None
    main_path = None
    scripts_dir = ROOT_DIR / "scripts"
    scripts_dir.mkdir(exist_ok=True)

    if validation_file:
        validation_path = scripts_dir / agent_id / "validate.py"
        validation_path.parent.mkdir(parents=True, exist_ok=True)
        with open(validation_path, "wb") as f:
            shutil.copyfileobj(validation_file.file, f)

    if main_file:
        main_path = scripts_dir / agent_id / "main.py"
        main_path.parent.mkdir(parents=True, exist_ok=True)
        with open(main_path, "wb") as f:
            shutil.copyfileobj(main_file.file, f)

    required_files_list = [f.strip() for f in required_files.split(",") if f.strip()]
    agent_doc = {
        "agent_id": agent_id,
        "name": name,
        "description": description,
        "required_files": required_files_list,
        "validation_script": str(validation_path) if validation_path else None,
        "main_script": str(main_path) if main_path else None,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user.user_id
    }
    await db.agents.insert_one(agent_doc)
    return {"message": "Agent created successfully", "agent_id": agent_id}

@api_router.get("/admin/agents")
async def get_all_agents_admin(session_token: Optional[str] = Cookie(None)):
    await require_admin(session_token=session_token)
    agents = await db.agents.find({}, {"_id": 0}).to_list(100)
    for agent in agents:
        if isinstance(agent['created_at'], str):
            agent['created_at'] = datetime.fromisoformat(agent['created_at'])
    return agents

@api_router.delete("/admin/agents/{agent_id}")
async def delete_agent(agent_id: str, session_token: Optional[str] = Cookie(None)):
    await require_admin(session_token=session_token)
    result = await db.agents.delete_one({"agent_id": agent_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": "Agent deleted successfully"}

@api_router.put("/admin/agents/{agent_id}/iframe-url")
async def update_agent_iframe_url(
    agent_id: str,
    iframe_url: str,
    session_token: Optional[str] = Cookie(None)
):
    await require_admin(session_token=session_token)
    result = await db.agents.update_one(
        {"agent_id": agent_id},
        {"$set": {"iframe_url": iframe_url}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": "Iframe URL updated successfully"}

# ============ AGENT ROUTES ============

@api_router.get("/agents", response_model=List[Agent])
async def get_agents(session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(session_token=session_token)
    if user.role == "admin":
        agents = await db.agents.find({}, {"_id": 0}).to_list(100)
    else:
        if user.agent_access:
            agents = await db.agents.find({"agent_id": {"$in": user.agent_access}}, {"_id": 0}).to_list(100)
        else:
            agents = []
    for agent in agents:
        if isinstance(agent['created_at'], str):
            agent['created_at'] = datetime.fromisoformat(agent['created_at'])
    return agents

@api_router.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str, session_token: Optional[str] = Cookie(None)):
    await get_current_user(session_token=session_token)
    agent = await db.agents.find_one({"agent_id": agent_id}, {"_id": 0})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if isinstance(agent['created_at'], str):
        agent['created_at'] = datetime.fromisoformat(agent['created_at'])
    return Agent(**agent)

# ============ JOB ROUTES ============

@api_router.post("/agents/{agent_id}/upload")
async def upload_files(
    agent_id: str,
    files: List[UploadFile] = File(...),
    session_token: Optional[str] = Cookie(None)
):
    user = await get_current_user(session_token=session_token)
    agent = await db.agents.find_one({"agent_id": agent_id}, {"_id": 0})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    job_dir = UPLOADS_DIR / job_id
    job_dir.mkdir(exist_ok=True)

    uploaded_files = []
    file_metadata = []

    for file in files:
        file_path = job_dir / file.filename
        file_content = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)

        file_doc = {
            "file_id": f"file_{uuid.uuid4().hex[:8]}",
            "job_id": job_id,
            "user_id": user.user_id,
            "file_name": file.filename,
            "file_path": str(file_path),
            "file_type": file.content_type or "application/octet-stream",
            "storage_type": "local",
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        }
        await db.files.insert_one(file_doc)
        uploaded_files.append(file.filename)
        file_metadata.append({"filename": file.filename, "local_path": str(file_path)})

    job_doc = {
        "job_id": job_id,
        "agent_id": agent_id,
        "user_id": user.user_id,
        "status": "pending",
        "input_files": uploaded_files,
        "output_files": [],
        "file_metadata": file_metadata,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.jobs.insert_one(job_doc)

    return {"job_id": job_id, "uploaded_files": uploaded_files, "message": f"Uploaded {len(files)} file(s)"}

@api_router.post("/agents/{agent_id}/execute")
async def execute_agent(
    agent_id: str,
    background_tasks: BackgroundTasks,
    job_data: dict,
    session_token: Optional[str] = Cookie(None)
):
    user = await get_current_user(session_token=session_token)
    job_id = job_data.get("job_id")
    if not job_id:
        raise HTTPException(status_code=400, detail="job_id is required")

    job = await db.jobs.find_one({"job_id": job_id, "user_id": user.user_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    agent = await db.agents.find_one({"agent_id": agent_id}, {"_id": 0})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    global active_jobs_count
    async with active_jobs_lock:
        if active_jobs_count >= MAX_CONCURRENT_AGENTS:
            await db.jobs.update_one(
                {"job_id": job_id},
                {"$set": {"status": "queued", "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
            return {"job_id": job_id, "status": "queued", "message": "Job queued - max concurrent agents reached"}
        active_jobs_count += 1

    await db.jobs.update_one(
        {"job_id": job_id},
        {"$set": {"status": "processing", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    background_tasks.add_task(run_job_background, job_id, agent_id, job, agent)
    return {"job_id": job_id, "status": "processing", "message": "Job started"}

async def run_job_background(job_id: str, agent_id: str, job: dict, agent: dict):
    global active_jobs_count
    try:
        output_dir = OUTPUTS_DIR / job_id
        output_dir.mkdir(exist_ok=True)

        result = await execute_agent_script(
            agent_id=agent_id,
            job_id=job_id,
            file_metadata=job.get("file_metadata", []),
            output_dir=str(output_dir),
            validation_script=agent.get("validation_script"),
            main_script=agent.get("main_script")
        )

        output_files = []
        if output_dir.exists():
            output_files = [f.name for f in output_dir.iterdir() if f.is_file()]

        await db.jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "status": "completed" if result.get("success") else "failed",
                "output_files": output_files,
                "execution_output": result.get("output", ""),
                "error_message": result.get("error"),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        await db.jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "status": "failed",
                "error_message": str(e),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    finally:
        async with active_jobs_lock:
            active_jobs_count = max(0, active_jobs_count - 1)

@api_router.get("/jobs")
async def get_jobs(session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(session_token=session_token)
    jobs = await db.jobs.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    for job in jobs:
        for field in ['created_at', 'updated_at']:
            if isinstance(job.get(field), str):
                job[field] = datetime.fromisoformat(job[field])
    return jobs

@api_router.get("/jobs/{job_id}")
async def get_job(job_id: str, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(session_token=session_token)
    job = await db.jobs.find_one({"job_id": job_id, "user_id": user.user_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    for field in ['created_at', 'updated_at']:
        if isinstance(job.get(field), str):
            job[field] = datetime.fromisoformat(job[field])
    return job

@api_router.get("/jobs/{job_id}/download/{filename}")
async def download_file(
    job_id: str,
    filename: str,
    session_token: Optional[str] = Cookie(None),
    token: Optional[str] = None
):
    auth_token = token or session_token
    user = await get_current_user(session_token=auth_token)
    job = await db.jobs.find_one({"job_id": job_id, "user_id": user.user_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if filename not in job.get("output_files", []):
        raise HTTPException(status_code=404, detail="File not found")

    file_path = OUTPUTS_DIR / job_id / filename
    if file_path.exists():
        def iterfile():
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    yield chunk
        return StreamingResponse(
            iterfile(),
            media_type='application/octet-stream',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Length': str(file_path.stat().st_size)
            }
        )
    raise HTTPException(status_code=404, detail="File not found on disk")

# ============ QUEUE STATUS ============

@api_router.get("/queue/status")
async def get_queue_status(session_token: Optional[str] = Cookie(None)):
    await get_current_user(session_token=session_token)
    queued = await db.jobs.count_documents({"status": "queued"})
    return {
        "active_jobs": active_jobs_count,
        "max_concurrent": MAX_CONCURRENT_AGENTS,
        "queued_jobs": queued,
        "available_slots": max(0, MAX_CONCURRENT_AGENTS - active_jobs_count)
    }

# ============ SEED DATA ============

@api_router.post("/seed-agents")
async def seed_agents():
    existing_count = await db.agents.count_documents({})
    if existing_count > 0:
        return {"message": "Agents already seeded"}
    agents = [
        {
            "agent_id": "agent_ke30",
            "name": "KE30 Sales Register Generator",
            "description": "Automates the generation of Sales Register for Financial Declaration. Performs column mapping (MRP & GST from ZSDR01), customer group standardization, and freebie reallocation.",
            "required_files": ["KE30 Export", "Customer Mapping", "ZMRP Report"],
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    await db.agents.insert_many(agents)
    return {"message": f"Seeded {len(agents)} agents"}

# ============ HEALTH CHECK ============

@api_router.get("/")
async def root():
    return {"message": "Honasa Task Force API"}

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type", "Content-Length"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
