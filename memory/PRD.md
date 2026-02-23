# FlowHub (Honasa Flow Hub) - Product Requirements Document

## Overview
FlowHub is a web-based automation platform that allows users to run Python-based automation "agents" through a simple UI. Users can upload input files, trigger processing scripts, and download output files.

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

3. **Job Execution**
   - File upload interface
   - Background script execution
   - Live output capture (stdout/stderr)
   - Job status tracking (pending, processing, completed, failed)
   - Output file download

4. **Admin Panel**
   - User management (view all users, toggle admin status)
   - Agent management (create, delete agents)
   - Initial admins: yash.b@mamaearth.in, sameer.c@mamaearth.in

5. **UI/Branding**
   - Renamed to "Honasa Flow Hub" (updated Feb 2026)
   - Clean, professional interface with TailwindCSS

### Available Agents

1. **KE30 Sales Register Generator** (Seed data)
   - Generates Sales Register for Financial Declaration
   - Required files: KE30 Export, Customer Mapping, ZMRP Report

2. **Inventory Reconciliation Agent** (Seed data)
   - Reconciles inventory from multiple sources

3. **Expense Report Processor** (Seed data)
   - Processes expense reports

4. **Diversity Score Checker** (NEW - Feb 2026)
   - Analyzes influencer script PDFs
   - Uses Gemini AI to extract:
     - Hook (0-5s attention grabber)
     - Creative Framework (narrative structure)
     - Message Angle (reason to buy)
   - Outputs Excel report with diversity analysis

## Technical Architecture

### Stack
- **Frontend**: React, React Router, TailwindCSS, Shadcn/UI
- **Backend**: FastAPI, Python 3.x
- **Database**: MongoDB
- **File Storage**: Local filesystem

### Key Files
- `/app/backend/server.py` - Main API server
- `/app/backend/agent_executor.py` - Script execution logic
- `/app/frontend/src/pages/Login.js` - Login page
- `/app/frontend/src/pages/Dashboard.js` - Agent list
- `/app/frontend/src/pages/AgentDetailPage.js` - File upload/execution
- `/app/frontend/src/pages/JobDetailPage.js` - Job results
- `/app/backend/scripts/diversity_checker/` - Diversity Score Checker agent

### Key Technical Notes
- Scripts must be executed using `sys.executable` to ensure correct Python environment
- All file storage is local (GCS integration was removed)
- EMERGENT_LLM_KEY used for AI-powered agents

## Backlog / Future Tasks

### P1 (High Priority)
- Email notifications for job completion (original requirement, deferred)
- Agent-specific user permissions (granular access control)

### P2 (Medium Priority)
- Multiple file processing for Diversity Checker
- Batch job management
- Job scheduling/automation

### P3 (Low Priority)
- Agent script versioning
- Job retry mechanism
- Analytics dashboard

## Changelog

### Feb 23, 2026
- Updated login branding: "FlowHub" → "Honasa Flow Hub"
- Added "Diversity Score Checker" agent
  - PDF document analysis using Gemini AI
  - Extracts marketing insights (hooks, frameworks, message angles)
  - Generates Excel diversity report
- Added EMERGENT_LLM_KEY for AI integrations

### Previous Sessions
- Built core FlowHub application
- Implemented JWT authentication (later replaced with Google SSO)
- Created admin panel for user and agent management
- Removed GCS integration (reverted to local storage)
- Fixed script execution environment issues
