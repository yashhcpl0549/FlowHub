from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Cookie, Response, BackgroundTasks, Form
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
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

# File storage
UPLOADS_DIR = ROOT_DIR / 'uploads'
OUTPUTS_DIR = ROOT_DIR / 'outputs'
UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ MODELS ============

class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: str
    role: str = "user"  # user or admin
    agent_access: List[str] = []  # List of agent_ids user can access
    created_at: datetime

class UserSession(BaseModel):
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime

class SessionRequest(BaseModel):
    session_id: str

class Agent(BaseModel):
    agent_id: str
    name: str
    description: str
    required_files: List[str]
    tag: Optional[str] = None  # Category tag (e.g., "Finance", "Marketing")
    agent_type: Optional[str] = None  # "iframe" for chat agents, None for file-based agents
    iframe_url: Optional[str] = None  # URL to embed for iframe agents
    validation_script: Optional[str] = None  # Path to validation script
    main_script: Optional[str] = None  # Path to main processing script
    status: str = "active"
    created_at: datetime
    created_by: Optional[str] = None  # user_id of creator

class Job(BaseModel):
    job_id: str
    agent_id: str
    user_id: str
    status: str  # pending, processing, completed, failed
    input_files: List[str]
    output_files: List[str]
    error_message: Optional[str] = None
    validation_output: Optional[str] = None  # Validation script output
    execution_output: Optional[str] = None   # Main script output
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

# ============ AUTH HELPER ============

async def get_current_user(session_token: Optional[str] = Cookie(None), authorization: Optional[str] = None) -> User:
    """Get current user from session_token cookie or Authorization header"""
    token = session_token
    
    # Fallback to Authorization header if cookie not present
    if not token and authorization:
        if authorization.startswith('Bearer '):
            token = authorization[7:]
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Find session
    session_doc = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Check expiry
    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Get user
    user_doc = await db.users.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Convert ISO string to datetime if needed
    if isinstance(user_doc['created_at'], str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    
    return User(**user_doc)

# ============ AUTH ROUTES ============

@api_router.post("/auth/session")
async def create_session(request: SessionRequest, response: Response):
    """Exchange session_id for session_token"""
    try:
        # Call Emergent Auth API
        async with httpx.AsyncClient() as client:
            auth_response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": request.session_id},
                timeout=10.0
            )
        
        if auth_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session_id")
        
        data = auth_response.json()
        
        # Create or update user
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        existing_user = await db.users.find_one({"email": data["email"]}, {"_id": 0})
        
        if existing_user:
            user_id = existing_user["user_id"]
            # Update user info
            await db.users.update_one(
                {"user_id": user_id},
                {"$set": {
                    "name": data["name"],
                    "picture": data["picture"]
                }}
            )
        else:
            # Check if this should be an admin
            admin_emails = ["yash.b@mamaearth.in", "sameer.c@mamaearth.in"]
            is_admin = data["email"] in admin_emails
            
            # Create new user
            user_doc = {
                "user_id": user_id,
                "email": data["email"],
                "name": data["name"],
                "picture": data["picture"],
                "role": "admin" if is_admin else "user",
                "agent_access": [],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(user_doc)
        
        # Create session
        session_token = data["session_token"]
        session_doc = {
            "user_id": user_id,
            "session_token": session_token,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.user_sessions.insert_one(session_doc)
        
        # Set cookie
        # REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="none",
            path="/",
            max_age=7*24*60*60
        )
        
        # Get user data
        user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if isinstance(user_doc['created_at'], str):
            user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
        
        return {"user": User(**user_doc), "session_token": session_token}
    
    except Exception as e:
        logger.error(f"Session creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/auth/me")
async def get_me(session_token: Optional[str] = Cookie(None)):
    """Get current user info"""
    user = await get_current_user(session_token=session_token)
    return user

@api_router.post("/auth/logout")
async def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    """Logout user"""
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out successfully"}

# ============ AGENT ROUTES ============

# Admin middleware
async def require_admin(session_token: Optional[str] = Cookie(None)) -> User:
    """Verify user is admin"""
    user = await get_current_user(session_token=session_token)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# Admin: Get all users
@api_router.get("/admin/users")
async def get_all_users(session_token: Optional[str] = Cookie(None)):
    """Get all users (admin only)"""
    await require_admin(session_token=session_token)
    
    users = await db.users.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO strings to datetime
    for user in users:
        if isinstance(user.get('created_at'), str):
            user['created_at'] = datetime.fromisoformat(user['created_at'])
    
    return users

# Admin: Update user agent access
@api_router.put("/admin/users/{user_id}/access")
async def update_user_access(
    user_id: str,
    agent_ids: List[str],
    session_token: Optional[str] = Cookie(None)
):
    """Update user's agent access (admin only)"""
    await require_admin(session_token=session_token)
    
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"agent_access": agent_ids}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User access updated", "agent_ids": agent_ids}

# Admin: Update user role
class UpdateRoleRequest(BaseModel):
    role: str  # "admin" or "user"

@api_router.put("/admin/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    request: UpdateRoleRequest,
    session_token: Optional[str] = Cookie(None)
):
    """Update user's role (admin only)"""
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

# Admin: Create new agent
@api_router.post("/admin/agents")
async def create_agent(
    name: str = Form(...),
    description: str = Form(...),
    required_files: str = Form(...),  # Comma-separated
    validation_file: Optional[UploadFile] = File(None),
    main_file: Optional[UploadFile] = File(None),
    session_token: Optional[str] = Cookie(None)
):
    """Create new agent (admin only)"""
    user = await require_admin(session_token=session_token)
    
    agent_id = f"agent_{uuid.uuid4().hex[:12]}"
    
    # Save uploaded scripts
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
    
    # Parse required files
    required_files_list = [f.strip() for f in required_files.split(",") if f.strip()]
    
    # Create agent
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

# Admin: Get all agents (including inactive)
@api_router.get("/admin/agents")
async def get_all_agents_admin(session_token: Optional[str] = Cookie(None)):
    """Get all agents including inactive (admin only)"""
    await require_admin(session_token=session_token)
    
    agents = await db.agents.find({}, {"_id": 0}).to_list(100)
    
    # Convert ISO strings to datetime
    for agent in agents:
        if isinstance(agent['created_at'], str):
            agent['created_at'] = datetime.fromisoformat(agent['created_at'])
    
    return agents

# Admin: Delete agent
@api_router.delete("/admin/agents/{agent_id}")
async def delete_agent(agent_id: str, session_token: Optional[str] = Cookie(None)):
    """Delete agent (admin only)"""
    await require_admin(session_token=session_token)
    
    result = await db.agents.delete_one({"agent_id": agent_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"message": "Agent deleted successfully"}


# Admin: Update agent iframe URL
@api_router.put("/admin/agents/{agent_id}/iframe-url")
async def update_agent_iframe_url(
    agent_id: str,
    iframe_url: str,
    session_token: Optional[str] = Cookie(None)
):
    """Update agent's iframe URL (admin only)"""
    await require_admin(session_token=session_token)
    
    result = await db.agents.update_one(
        {"agent_id": agent_id},
        {"$set": {"iframe_url": iframe_url}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"message": "Iframe URL updated successfully"}


@api_router.get("/agents", response_model=List[Agent])
async def get_agents(session_token: Optional[str] = Cookie(None)):
    """Get all agents that user has access to"""
    user = await get_current_user(session_token=session_token)
    
    # Admins see all agents
    if user.role == "admin":
        agents = await db.agents.find({}, {"_id": 0}).to_list(100)
    else:
        # Regular users only see agents they have access to
        if user.agent_access:
            agents = await db.agents.find({"agent_id": {"$in": user.agent_access}}, {"_id": 0}).to_list(100)
        else:
            agents = []
    
    # Convert ISO strings to datetime
    for agent in agents:
        if isinstance(agent['created_at'], str):
            agent['created_at'] = datetime.fromisoformat(agent['created_at'])
    
    return agents

@api_router.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str, session_token: Optional[str] = Cookie(None)):
    """Get agent details"""
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
    """Upload input files for an agent - stores locally"""
    user = await get_current_user(session_token=session_token)
    
    # Verify agent exists
    agent = await db.agents.find_one({"agent_id": agent_id}, {"_id": 0})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Create job
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    job_dir = UPLOADS_DIR / job_id
    job_dir.mkdir(exist_ok=True)
    
    uploaded_files = []
    file_metadata = []
    
    for idx, file in enumerate(files):
        file_id = f"file_{uuid.uuid4().hex[:8]}"
        file_path = job_dir / file.filename
        
        # Save file locally
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Store file info
        file_doc = {
            "file_id": file_id,
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
        file_metadata.append({
            "filename": file.filename,
            "local_path": str(file_path)
        })
    
    logger.info(f"Uploaded {len(files)} files to local storage for job {job_id}")
    
    # Create job record
    job_doc = {
        "job_id": job_id,
        "agent_id": agent_id,
        "user_id": user.user_id,
        "status": "pending",
        "input_files": uploaded_files,
        "file_metadata": file_metadata,
        "output_files": [],
        "error_message": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.jobs.insert_one(job_doc)
    
    return {
        "job_id": job_id,
        "uploaded_files": uploaded_files,
        "storage_type": "local"
    }

async def run_agent_script(job_id: str, agent_id: str, user_email: str):
    """Wrapper for agent script execution"""
    agent = await db.agents.find_one({"agent_id": agent_id}, {"_id": 0})
    await execute_agent_script(
        job_id=job_id,
        agent_id=agent_id,
        user_email=user_email,
        db=db,
        agent=agent,
        ROOT_DIR=ROOT_DIR,
        OUTPUTS_DIR=OUTPUTS_DIR,
        RESEND_API_KEY=RESEND_API_KEY,
        SENDER_EMAIL=SENDER_EMAIL,
        resend_module=resend
    )

class ExecuteRequest(BaseModel):
    job_id: str

# ... existing models ...

@api_router.post("/agents/{agent_id}/execute")
async def execute_agent(
    agent_id: str,
    request: ExecuteRequest,
    background_tasks: BackgroundTasks,
    session_token: Optional[str] = Cookie(None)
):
    """Execute agent script"""
    user = await get_current_user(session_token=session_token)
    
    # Verify job exists and belongs to user
    job = await db.jobs.find_one({"job_id": request.job_id, "user_id": user.user_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] != "pending":
        raise HTTPException(status_code=400, detail="Job already processed")
    
    # Start background task
    background_tasks.add_task(run_agent_script, request.job_id, agent_id, user.email)
    
    return {"message": "Job execution started", "job_id": request.job_id}

@api_router.get("/jobs", response_model=List[Job])
async def get_jobs(session_token: Optional[str] = Cookie(None)):
    """Get user's job history"""
    user = await get_current_user(session_token=session_token)
    
    jobs = await db.jobs.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    # Convert ISO strings to datetime
    for job in jobs:
        if isinstance(job['created_at'], str):
            job['created_at'] = datetime.fromisoformat(job['created_at'])
        if isinstance(job['updated_at'], str):
            job['updated_at'] = datetime.fromisoformat(job['updated_at'])
    
    return jobs

@api_router.get("/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str, session_token: Optional[str] = Cookie(None)):
    """Get job details"""
    user = await get_current_user(session_token=session_token)
    
    job = await db.jobs.find_one({"job_id": job_id, "user_id": user.user_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Convert ISO strings to datetime
    if isinstance(job['created_at'], str):
        job['created_at'] = datetime.fromisoformat(job['created_at'])
    if isinstance(job['updated_at'], str):
        job['updated_at'] = datetime.fromisoformat(job['updated_at'])
    
    return Job(**job)

@api_router.get("/jobs/{job_id}/download/{filename}")
async def download_output(
    job_id: str,
    filename: str,
    session_token: Optional[str] = Cookie(None),
    token: Optional[str] = None  # Allow token in query param for downloads
):
    """Download output file"""
    # Try query param token first, then cookie
    auth_token = token or session_token
    user = await get_current_user(session_token=auth_token)
    
    # Verify job belongs to user
    job = await db.jobs.find_one({"job_id": job_id, "user_id": user.user_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if file exists in job outputs
    if filename not in job.get("output_files", []):
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = OUTPUTS_DIR / job_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    # Set proper headers for download
    return FileResponse(
        file_path, 
        filename=filename,
        media_type='application/octet-stream',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )

# ============ SEED DATA ============

@api_router.post("/seed-agents")
async def seed_agents():
    """Seed initial agents (for demo purposes)"""
    existing_count = await db.agents.count_documents({})
    if existing_count > 0:
        return {"message": "Agents already seeded"}
    
    agents = [
        {
            "agent_id": "agent_ke30",
            "name": "KE30 Sales Register Generator",
            "description": "Automates the generation of Sales Register for Financial Declaration. Performs column mapping (MRP & GST from ZSDR01), customer group standardization, and freebie reallocation to generate the final output with Power Pivot configuration.",
            "required_files": ["KE30 Export", "Customer Mapping", "ZMRP Report"],
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "agent_id": "agent_inventory",
            "name": "Inventory Reconciliation Agent",
            "description": "Reconciles inventory data from multiple sources, identifies discrepancies, and generates detailed reports with variance analysis and recommendations.",
            "required_files": ["SAP Inventory Export", "Warehouse Stock File"],
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "agent_id": "agent_expense",
            "name": "Expense Report Processor",
            "description": "Processes expense reports from various departments, validates against policy rules, categorizes expenses, and generates summary reports for finance approval.",
            "required_files": ["Expense Data", "Policy Rules File"],
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
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type", "Content-Length"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
