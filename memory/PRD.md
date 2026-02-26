# Honasa Task Force - Product Requirements Document

## Overview
Honasa Task Force is a web-based automation platform that allows users to run Python-based automation "agents" through a simple UI. Users can upload input files, trigger processing scripts, and download output files. The platform also supports iframe-based chat agents for conversational analytics.

## Original Problem Statement
Create a frontend wrapper for Python scripts that automate business processes (initially KE30 Sales Register for Financial Declaration). The platform should support:
- SSO/Google authentication
- Agent management (admin can create/configure agents)
- File upload and processing
- Job status tracking with live script output
- Output file download
- User access management

## Core Features

### Implemented ✅
1. **Authentication System**
   - Google SSO via Emergent Auth
   - Session-based authentication with cookies
   - Admin role management

2. **Agent Management**
   - Admin panel to create new agents
   - Upload validation and main Python scripts
   - Define required input files
   - **NEW: Iframe-based chat agents** (for BigQuery Conversational Analytics)

3. **Job Execution**
   - File upload interface (supports multiple files)
   - Background script execution with async polling
   - Live output capture (stdout/stderr)
   - Job status tracking (pending, processing, completed, failed)
   - Output file download (fetch + blob method)

4. **Admin Panel**
   - User management (view all users, toggle admin status)
   - Agent management (create, delete agents)
   - **NEW: Configure iframe URLs** for chat agents
   - Initial admins: yash.b@mamaearth.in, sameer.c@mamaearth.in

5. **UI/Branding**
   - Platform name: "Honasa Task Force"
   - Clean, professional interface with TailwindCSS
   - Email mentions removed from UI
   - Tag-based categorization with color coding

### Agent Types

**File-Based Agents** (Traditional)
- Upload required files
- Execute Python scripts
- Download output files

**Iframe Chat Agents** (NEW)
- Opens directly in iframe
- BigQuery Conversational Analytics integration
- No file upload required
- Uses Google SSO for authentication

### Available Agents

| Agent | Tag | Type | Required Files |
|-------|-----|------|----------------|
| KE30 Sales Register Generator | Finance | File | KE30 Export, Customer Mapping, ZMRP Report |
| Diversity Score Checker | Marketing | File | PDF Document |
| Google Geo Level Search Volume | Marketing | File | List of Keywords, Time Period, Zone/Tier/State/City |
| KYC Calling | HR | File | SKU, Time Period, Zone/Tier/State/City |
| ORM Actionability Center | Customer Support | File | Comment Dump from QuickMatrix |
| FBT Creator | Revenue | File | Brand, Time Period, Coupon Code, Subcategory |
| Data Query Assistant | Analytics | Iframe | None (Chat) |

## Technical Architecture

### Stack
- **Frontend**: React, React Router, TailwindCSS, Shadcn/UI
- **Backend**: FastAPI, Python 3.x
- **Database**: MongoDB
- **File Storage**: Local filesystem
- **AI Integration**: Gemini via Emergent LLM Key

### Key Files
- `/app/backend/server.py` - Main API server
- `/app/backend/agent_executor.py` - Script execution logic
- `/app/frontend/src/pages/Login.js` - Login page
- `/app/frontend/src/pages/Dashboard.js` - Agent list
- `/app/frontend/src/pages/AgentDetail.js` - File upload/execution
- `/app/frontend/src/pages/IframeAgentPage.js` - Chat agent iframe
- `/app/frontend/src/pages/JobDetail.js` - Job results & download
- `/app/frontend/src/pages/ManageAgents.js` - Admin agent management
- `/app/backend/scripts/diversity_checker/` - Diversity Score Checker agent

### Routes
- `/` - Login page
- `/dashboard` - Agent list
- `/agent/:agentId` - File-based agent detail
- `/chat/:agentId` - Iframe chat agent
- `/jobs` - Job history
- `/jobs/:jobId` - Job detail
- `/admin` - Admin dashboard
- `/admin/users` - User management
- `/admin/agents` - Agent management

### Key Technical Notes
- Scripts executed using `sys.executable` for correct Python environment
- All file storage is local (GCS removed)
- EMERGENT_LLM_KEY for AI-powered agents
- Download uses fetch + blob for cross-origin compatibility
- Iframe agents route to `/chat/:agentId`

## Backlog / Future Tasks

### P1 (High Priority)
- Agent-specific user permissions (granular access control)
- Deploy BigQuery Conversational Analytics app and configure iframe URL

### P2 (Medium Priority)
- Batch job management
- Job scheduling/automation

### P3 (Low Priority)
- Agent script versioning
- Job retry mechanism
- Analytics dashboard

## Changelog

### Feb 26, 2026 (Latest)
- Added "Data Query Assistant" iframe agent for BigQuery Conversational Analytics
- Created IframeAgentPage component for chat agents
- Added iframe URL configuration in admin panel
- Updated routing for iframe vs file-based agents
- Added Analytics tag with cyan color

### Feb 23, 2026
- Renamed platform to "Honasa Task Force"
- Fixed download button using fetch + blob
- Removed email notification mentions
- Added multiple new agents (Google Geo Level Search Volume, KYC Calling, ORM Actionability Center, FBT Creator)
- Added tag colors for Finance, Marketing, HR, Customer Support, Revenue, Analytics

### Previous Sessions
- Built core application with Google SSO
- Created admin panel for user and agent management
- Removed GCS integration
- Fixed script execution environment issues

