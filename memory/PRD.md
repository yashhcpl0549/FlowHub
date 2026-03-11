# Honasa Task Force - Product Requirements Document

## Overview
Honasa Task Force is a web-based automation platform that allows users to run Python-based automation "agents" through a simple UI. Users can upload input files, trigger processing scripts, and download output files.

## Original Problem Statement
Create a frontend wrapper for Python scripts that automate business processes (initially KE30 Sales Register for Financial Declaration). The platform should support:
- SSO/Google authentication
- Agent management (admin can create/configure agents)
- File upload and processing
- Job status tracking with live script output
- Output file download
- User access management

## Core Features

### Implemented
1. **Authentication System**
   - Google SSO via Emergent Auth
   - Session-based authentication with cookies
   - Admin role management

2. **Agent Management**
   - Admin panel to create new agents
   - Upload validation and main Python scripts
   - Define required input files
   - Tag-based categorization

3. **Job Execution**
   - File upload interface (supports multiple files)
   - Background script execution with async polling
   - Live output capture (stdout/stderr)
   - Job status tracking (pending, processing, completed, failed, queued)
   - Output file download (StreamingResponse + fetch/blob)

4. **Agent Queue System**
   - Max 10 concurrent agent executions (configurable via MAX_CONCURRENT_AGENTS)
   - Queue status endpoint at /api/queue/status
   - Automatic queuing when limit reached

5. **Storage**
   - Local filesystem storage (default)
   - GCS bucket support (optional, configurable)

6. **Admin Panel**
   - User management (view all users, toggle admin status)
   - Agent management (create, delete agents)
   - Initial admins: yash.b@mamaearth.in, sameer.c@mamaearth.in, rahul.gupta@mamaearth.in

7. **UI/Branding**
   - Platform name: "Honasa Task Force"
   - Clean, professional interface with TailwindCSS
   - Tag-based categorization with color coding

## Technical Architecture

### Stack
- **Frontend**: React, React Router, TailwindCSS, Shadcn/UI
- **Backend**: FastAPI, Python 3.x
- **Database**: MongoDB
- **File Storage**: Local filesystem or GCS (configurable)
- **AI Integration**: Gemini via Emergent LLM Key (for specific agents)

### Key Files
- `/app/backend/server.py` - Main API server
- `/app/backend/agent_executor.py` - Script execution logic with GCS support
- `/app/frontend/src/pages/Login.js` - Login page
- `/app/frontend/src/pages/Dashboard.js` - Agent list
- `/app/frontend/src/pages/AgentDetail.js` - File upload/execution
- `/app/frontend/src/pages/JobDetail.js` - Job results & download
- `/app/frontend/src/pages/Admin/ManageAgents.js` - Admin agent management

### Routes
- `/` - Login page
- `/dashboard` - Agent list
- `/agent/:agentId` - Agent detail page
- `/jobs` - Job history
- `/jobs/:jobId` - Job detail
- `/admin` - Admin dashboard
- `/admin/users` - User management
- `/admin/agents` - Agent management

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| MONGO_URL | MongoDB connection string | Required |
| DB_NAME | Database name | Required |
| CORS_ORIGINS | Allowed CORS origins | * |
| GCS_BUCKET | GCS bucket for storage | (empty = local) |
| GCS_CREDENTIALS_PATH | Path to GCS credentials | (empty) |
| MAX_CONCURRENT_AGENTS | Max concurrent executions | 10 |
| RESEND_API_KEY | Email notifications | (optional) |
| EMERGENT_LLM_KEY | AI integrations | (optional) |

### Deployment
- Docker support: Dockerfile.backend, Dockerfile.frontend, docker-compose.yml
- Production guide: DEPLOYMENT_GUIDE.md
- AWS ready (EC2, ECS, or any Docker environment)

## Backlog / Future Tasks

### P1 (High Priority)
- Agent-specific user permissions (granular access control)
- Attach scripts to placeholder agents

### P2 (Medium Priority)
- Batch job management
- Job scheduling/automation

### P3 (Low Priority)
- Agent script versioning
- Job retry mechanism
- Analytics dashboard

## Changelog

### Dec 2025 (Latest - Production Ready)
- **REMOVED**: BigQuery Chat Agent and all related code
- **REMOVED**: Settings page and GCP credentials management
- **FIXED**: P0 Download button bug - now uses StreamingResponse + fetch/blob
- **ADDED**: Agent queue system with configurable max concurrent (default 10)
- **ADDED**: GCS bucket support (optional, configurable)
- **ADDED**: Docker configuration (Dockerfile.backend, Dockerfile.frontend, docker-compose.yml)
- **ADDED**: Production deployment guide (DEPLOYMENT_GUIDE.md)
- **ADDED**: Queue status endpoint (/api/queue/status)
- Cleaned up orphan iframe agents from database

### Previous Sessions
- Built core application with Google SSO
- Created admin panel for user and agent management
- Added multiple agents (KE30, Inventory, Expense, etc.)
- Tag-based categorization with color coding
- Fixed script execution environment issues
