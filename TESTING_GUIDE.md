# FlowHub Complete Testing Guide

## System Status Check

### 1. Verify All Services Running

```bash
sudo supervisorctl status
```

Expected output:
```
backend    RUNNING
frontend   RUNNING
mongodb    RUNNING
```

### 2. Check Backend Health

```bash
BACKEND_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)
curl "$BACKEND_URL/api/"
```

Expected: `{"message":"FlowHub API"}`

### 3. Check Backend Logs

```bash
# Check for errors
tail -50 /var/log/supervisor/backend.err.log

# Check activity
tail -50 /var/log/supervisor/backend.out.log
```

---

## Authentication Testing

### Method 1: Create Test Users (Quickest)

```bash
# Create admin user
mongosh --eval "
use('test_database');
var adminId = 'admin-yash';
var adminId2 = 'admin-sameer';
var adminToken = 'admin_session_' + Date.now();

db.users.deleteOne({email: 'yash.b@mamaearth.in'});
db.user_sessions.deleteMany({user_id: adminId});

db.users.deleteOne({email: 'sameer.c@mamaearth.in'});
db.user_sessions.deleteMany({user_id: adminId2});

db.users.insertOne({
  user_id: adminId,
  email: 'yash.b@mamaearth.in',
  name: 'Yash Bansal',
  picture: 'https://via.placeholder.com/150',
  role: 'admin',
  agent_access: [],
  created_at: new Date()
});

db.users.insertOne({
  user_id: adminId,
  email: 'sameer.c@mamaearth.in',
  name: 'Sameer Chaturvedi',
  picture: 'https://via.placeholder.com/151',
  role: 'admin',
  agent_access: [],
  created_at: new Date()
});

db.user_sessions.insertOne({
  user_id: adminId,
  session_token: adminToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
db.user_sessions.insertOne({
  user_id: adminId2,
  session_token: adminToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
print('Admin Token: ' + adminToken);
" | grep "Admin Token:"
```

**Copy the admin token** from output.

```bash
# Create regular user
mongosh --eval "
use('test_database');
var userId = 'user-regular';
var userToken = 'user_session_' + Date.now();

db.users.deleteOne({email: 'john.doe@example.com'});
db.user_sessions.deleteMany({user_id: userId});

db.users.insertOne({
  user_id: userId,
  email: 'john.doe@example.com',
  name: 'John Doe',
  picture: 'https://via.placeholder.com/150',
  role: 'user',
  agent_access: ['agent_ke30'],
  created_at: new Date()
});

db.user_sessions.insertOne({
  user_id: userId,
  session_token: userToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});

print('User Token: ' + userToken);
" | grep "User Token:"
```

**Copy the user token** from output.

### Test Authentication API

```bash
BACKEND_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)

# Replace YOUR_ADMIN_TOKEN with actual token
curl -X GET "$BACKEND_URL/api/auth/me" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

Expected: User data JSON with `role: "admin"`

### Test via Browser (Recommended)

1. Open browser DevTools (F12)
2. Go to Application → Cookies
3. Add cookie:
   - Name: `session_token`
   - Value: `YOUR_ADMIN_TOKEN` (from above)
   - Domain: `ke30-automation-hub.preview.emergentagent.com`
   - Path: `/`
   - HttpOnly: ✓
   - Secure: ✓
   - SameSite: `None`
4. Navigate to: `https://ke30-automation-hub.preview.emergentagent.com/dashboard`

**Should see:** Dashboard with "Admin Panel" button

---

## Core Functionality Testing

### Test 1: Admin Dashboard Access

**As Admin User (yash.b@mamaearth.in):**

```bash
BACKEND_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)
ADMIN_TOKEN="YOUR_ADMIN_TOKEN"

# Get all users
curl "$BACKEND_URL/api/admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Get all agents
curl "$BACKEND_URL/api/admin/agents" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Expected:** List of users and agents

### Test 2: Regular User Access Control

```bash
USER_TOKEN="YOUR_USER_TOKEN"

# Try admin route (should fail)
curl "$BACKEND_URL/api/admin/users" \
  -H "Authorization: Bearer $USER_TOKEN"

# Get accessible agents (should only see agent_ke30)
curl "$BACKEND_URL/api/agents" \
  -H "Authorization: Bearer $USER_TOKEN"
```

**Expected:** 
- Admin route returns 403 Forbidden
- Agents route returns only `agent_ke30`

### Test 3: Create New Agent (Admin Only)

```bash
BACKEND_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)
ADMIN_TOKEN="YOUR_ADMIN_TOKEN"

curl -X POST "$BACKEND_URL/api/admin/agents" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "name=Test CSV Agent" \
  -F "description=Processes CSV files" \
  -F "required_files=Input CSV"
```

**Expected:** `{"message":"Agent created successfully","agent_id":"agent_..."}`

### Test 4: Update User Access

```bash
# Give john.doe access to all agents
curl -X PUT "$BACKEND_URL/api/admin/users/user-regular/access" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '["agent_ke30", "agent_inventory", "agent_expense"]'
```

**Expected:** `{"message":"User access updated"}`

### Test 5: File Upload & Job Execution

```bash
# Create test CSV file
cat > /tmp/test_sales.csv << 'EOF'
Date,Product,Quantity,Revenue
2024-01-01,Widget A,100,5000
2024-01-02,Widget B,150,7500
EOF

# Upload file
RESPONSE=$(curl -X POST "$BACKEND_URL/api/agents/agent_ke30/upload" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "files=@/tmp/test_sales.csv")

echo "Upload response: $RESPONSE"

# Extract job_id
JOB_ID=$(echo $RESPONSE | grep -o '"job_id":"[^"]*' | cut -d'"' -f4)
echo "Job ID: $JOB_ID"

# Execute agent
curl -X POST "$BACKEND_URL/api/agents/agent_ke30/execute" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"job_id\":\"$JOB_ID\"}"

# Wait 5 seconds
sleep 5

# Check job status
curl "$BACKEND_URL/api/jobs/$JOB_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Expected:** Job status changes from `pending` → `processing` → `completed`

---

## Frontend Testing (Browser)

### Setup Browser Session

1. **Open DevTools** (F12)
2. **Clear existing data:**
   - Application → Cookies → Delete all
   - Application → Local Storage → Clear
3. **Add session cookie** (from earlier step)
4. **Refresh page**

### Test Checklist

#### ✅ Login & Auth
- [ ] Login page loads with "FlowHub" branding
- [ ] Google login button visible
- [ ] After setting cookie, redirect to dashboard works

#### ✅ Dashboard (Regular User)
- [ ] Dashboard shows welcome message with user name
- [ ] Shows only agents user has access to
- [ ] Can click agent card to view details
- [ ] Recent jobs section (if any jobs exist)
- [ ] No "Admin Panel" button visible

#### ✅ Dashboard (Admin User)
- [ ] "Admin Panel" button visible in header
- [ ] Shows all 3+ agents
- [ ] Can access admin dashboard

#### ✅ Admin Panel
- [ ] Admin dashboard shows stats (users, agents, system status)
- [ ] "Manage Users" link works
- [ ] "Manage Agents" link works

#### ✅ Manage Users (Admin)
- [ ] Lists all users with email, role, access count
- [ ] "Edit Access" button opens modal
- [ ] Can check/uncheck agents
- [ ] "Save Changes" updates user access
- [ ] Changes reflect in user's dashboard

#### ✅ Manage Agents (Admin)
- [ ] Shows all agents with details
- [ ] "Create Agent" button opens modal
- [ ] Can fill agent name, description, required files
- [ ] Can specify custom GCS bucket (optional)
- [ ] Can upload validation.py and main.py files
- [ ] "Create Agent" creates new agent
- [ ] New agent appears in list
- [ ] "Delete Agent" removes agent

#### ✅ Agent Detail Page
- [ ] Shows agent name, description
- [ ] Lists required files
- [ ] File upload zone works
- [ ] Selected files display with checkmarks
- [ ] "Upload Files" button uploads to backend
- [ ] Success message shows job ID
- [ ] "Execute Agent" button enabled after upload
- [ ] "Execute Agent" starts job
- [ ] Shows "Processing..." message
- [ ] Redirects to job detail page

#### ✅ Job Detail Page
- [ ] Shows job ID, status badge
- [ ] Displays agent info
- [ ] Lists input files
- [ ] Status updates automatically (polling)
- [ ] When completed: shows output files
- [ ] "Download" button works for output files
- [ ] Email notification mentioned
- [ ] Timeline shows created/updated times

#### ✅ Jobs List Page
- [ ] Lists all user's jobs
- [ ] Shows job ID, agent, status, date
- [ ] Status badges color-coded
- [ ] "View Details" links work
- [ ] Empty state if no jobs

---

## Common Issues & Fixes

### Issue: "401 Unauthorized" or "Not authenticated"

**Check:**
```bash
# Verify session token exists in DB
mongosh --eval "
use('test_database');
db.user_sessions.find({session_token: 'YOUR_TOKEN'}).pretty();
"

# Check expiry date
mongosh --eval "
use('test_database');
var session = db.user_sessions.findOne({session_token: 'YOUR_TOKEN'});
print('Expires: ' + session.expires_at);
print('Now: ' + new Date());
"
```

**Fix:** Recreate session with future expiry

### Issue: "403 Forbidden" on admin routes

**Check user role:**
```bash
mongosh --eval "
use('test_database');
db.users.find({email: 'yash.b@mamaearth.in'}, {role: 1, email: 1}).pretty();
"
```

**Expected:** `role: "admin"`

**Fix:**
```bash
mongosh --eval "
use('test_database');
db.users.updateOne(
  {email: 'yash.b@mamaearth.in'},
  {\$set: {role: 'admin'}}
);
"
```

### Issue: Regular user sees all agents

**Check agent_access:**
```bash
mongosh --eval "
use('test_database');
db.users.find({email: 'john.doe@example.com'}, {agent_access: 1, email: 1}).pretty();
"
```

**Fix:** Set specific agent access
```bash
mongosh --eval "
use('test_database');
db.users.updateOne(
  {email: 'john.doe@example.com'},
  {\$set: {agent_access: ['agent_ke30']}}
);
"
```

### Issue: Backend not responding

```bash
# Restart backend
sudo supervisorctl restart backend

# Check logs
tail -f /var/log/supervisor/backend.err.log
```

### Issue: Frontend not updating

```bash
# Clear browser cache
# Or restart frontend
sudo supervisorctl restart frontend
```

---

## Database Inspection

### View All Users
```bash
mongosh --eval "
use('test_database');
db.users.find({}, {_id: 0, user_id: 1, email: 1, role: 1, agent_access: 1}).pretty();
"
```

### View All Sessions
```bash
mongosh --eval "
use('test_database');
db.user_sessions.find({}, {_id: 0, user_id: 1, session_token: 1, expires_at: 1}).pretty();
"
```

### View All Agents
```bash
mongosh --eval "
use('test_database');
db.agents.find({}, {_id: 0, agent_id: 1, name: 1, status: 1, gcs_bucket: 1}).pretty();
"
```

### View All Jobs
```bash
mongosh --eval "
use('test_database');
db.jobs.find({}, {_id: 0, job_id: 1, agent_id: 1, user_id: 1, status: 1}).pretty();
"
```

### Clean Database (Reset)
```bash
mongosh --eval "
use('test_database');
db.users.deleteMany({});
db.user_sessions.deleteMany({});
db.jobs.deleteMany({});
db.files.deleteMany({});
print('Database cleaned');
"
```

---

## Performance Testing

### Upload Large File
```bash
# Create 10MB CSV
for i in {1..100000}; do
  echo "2024-01-$((i%28+1)),Product$((i%10)),100,5000" >> /tmp/large_sales.csv
done

# Upload
time curl -X POST "$BACKEND_URL/api/agents/agent_ke30/upload" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "files=@/tmp/large_sales.csv"
```

### Concurrent Requests
```bash
# Run 10 concurrent auth checks
for i in {1..10}; do
  curl -s "$BACKEND_URL/api/auth/me" \
    -H "Authorization: Bearer $ADMIN_TOKEN" &
done
wait
```

---

## Quick Health Check Script

Save as `/app/health_check.sh`:

```bash
#!/bin/bash

echo "=== FlowHub Health Check ==="
echo ""

# Services
echo "1. Services Status:"
sudo supervisorctl status | grep -E "(backend|frontend|mongodb)"
echo ""

# Backend API
echo "2. Backend API:"
BACKEND_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)
RESP=$(curl -s "$BACKEND_URL/api/")
if [[ $RESP == *"FlowHub"* ]]; then
  echo "✓ Backend responding"
else
  echo "✗ Backend not responding"
fi
echo ""

# Database
echo "3. Database:"
USERS=$(mongosh --quiet --eval "use('test_database'); db.users.countDocuments()")
AGENTS=$(mongosh --quiet --eval "use('test_database'); db.agents.countDocuments()")
echo "Users: $USERS"
echo "Agents: $AGENTS"
echo ""

# GCS Config
echo "4. GCS Configuration:"
if [ -f "/app/backend/.env" ]; then
  GCS_BUCKET=$(grep GCS_DEFAULT_BUCKET /app/backend/.env | cut -d '=' -f2 | tr -d '"')
  GCS_CREDS=$(grep GOOGLE_APPLICATION_CREDENTIALS /app/backend/.env | cut -d '=' -f2 | tr -d '"')
  
  if [ -n "$GCS_BUCKET" ]; then
    echo "✓ GCS Bucket: $GCS_BUCKET"
  else
    echo "⚠ GCS Bucket not configured (will use local storage)"
  fi
  
  if [ -n "$GCS_CREDS" ] && [ -f "$GCS_CREDS" ]; then
    echo "✓ GCS Credentials: $GCS_CREDS"
  elif [ -n "$GCS_CREDS" ]; then
    echo "✗ GCS Credentials file not found: $GCS_CREDS"
  else
    echo "⚠ GCS Credentials not configured"
  fi
fi
echo ""

echo "=== Health Check Complete ==="
```

Run: `bash /app/health_check.sh`

---

## Next Steps After Testing

1. **If auth works:** Proceed to test agent creation
2. **If agent creation works:** Upload real scripts
3. **If scripts work:** Configure GCS for production
4. **If GCS works:** Grant user access and onboard team

## Support

If issues persist:
1. Share backend logs: `tail -100 /var/log/supervisor/backend.err.log`
2. Share browser console errors (F12 → Console)
3. Share specific error messages
