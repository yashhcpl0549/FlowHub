"""
Honasa Task Force API Tests
Tests backend APIs including:
- Health check
- Authentication
- Agents CRUD
- Jobs management
- Queue status
- Download functionality
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test session token - set via env var or MongoDB
TEST_SESSION_TOKEN = os.environ.get('TEST_SESSION_TOKEN', '')

@pytest.fixture(scope="module")
def session_token():
    """Get test session token"""
    if not TEST_SESSION_TOKEN:
        pytest.skip("No TEST_SESSION_TOKEN set")
    return TEST_SESSION_TOKEN

@pytest.fixture
def api_client(session_token):
    """Shared requests session with cookies"""
    session = requests.Session()
    session.cookies.set('session_token', session_token)
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture
def unauth_client():
    """Requests session without auth"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestHealthCheck:
    """Health check and API status tests"""
    
    def test_api_root_returns_correct_message(self, unauth_client):
        """Test that API root returns Honasa Task Force API message"""
        response = unauth_client.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Honasa Task Force API"
        print("✓ API health check returns correct message: 'Honasa Task Force API'")


class TestAuthenticationFlow:
    """Authentication endpoint tests"""
    
    def test_auth_me_without_token_returns_401(self, unauth_client):
        """Test that /auth/me requires authentication"""
        response = unauth_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        print("✓ /auth/me returns 401 without token")
    
    def test_auth_me_with_invalid_token_returns_401(self):
        """Test that /auth/me rejects invalid tokens"""
        session = requests.Session()
        session.cookies.set('session_token', 'invalid_token_12345')
        response = session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        print("✓ /auth/me returns 401 with invalid token")
    
    def test_auth_me_with_valid_token(self, api_client):
        """Test that /auth/me returns user data with valid token"""
        response = api_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "email" in data
        assert "name" in data
        print(f"✓ /auth/me returns user: {data.get('name')}")


class TestAgentsEndpoints:
    """Agent management tests"""
    
    def test_get_agents_without_auth_returns_401(self, unauth_client):
        """Test that /agents requires authentication"""
        response = unauth_client.get(f"{BASE_URL}/api/agents")
        assert response.status_code == 401
        print("✓ /agents returns 401 without auth")
    
    def test_get_agents_with_auth(self, api_client):
        """Test that /agents returns list with valid auth"""
        response = api_client.get(f"{BASE_URL}/api/agents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ /agents returns {len(data)} agents")
        
        # Validate agent structure if any agents exist
        if len(data) > 0:
            agent = data[0]
            assert "agent_id" in agent
            assert "name" in agent
            assert "description" in agent
            assert "required_files" in agent
            print(f"  First agent: {agent.get('name')}")
    
    def test_get_agent_by_id(self, api_client):
        """Test getting specific agent by ID"""
        # First get list of agents
        response = api_client.get(f"{BASE_URL}/api/agents")
        if response.status_code != 200 or len(response.json()) == 0:
            pytest.skip("No agents available for testing")
        
        agent_id = response.json()[0]["agent_id"]
        
        # Get specific agent
        response = api_client.get(f"{BASE_URL}/api/agents/{agent_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == agent_id
        print(f"✓ Get agent by ID working: {agent_id}")
    
    def test_get_nonexistent_agent_returns_404(self, api_client):
        """Test that getting non-existent agent returns 404"""
        response = api_client.get(f"{BASE_URL}/api/agents/nonexistent_agent_12345")
        assert response.status_code == 404
        print("✓ Non-existent agent returns 404")


class TestQueueStatus:
    """Queue management tests"""
    
    def test_queue_status_without_auth_returns_401(self, unauth_client):
        """Test that /queue/status requires authentication"""
        response = unauth_client.get(f"{BASE_URL}/api/queue/status")
        assert response.status_code == 401
        print("✓ /queue/status returns 401 without auth")
    
    def test_queue_status_with_auth(self, api_client):
        """Test that /queue/status returns proper structure"""
        response = api_client.get(f"{BASE_URL}/api/queue/status")
        assert response.status_code == 200
        data = response.json()
        
        # Validate queue status structure
        assert "active_jobs" in data
        assert "max_concurrent" in data
        assert "queued_jobs" in data
        assert "available_slots" in data
        
        # Validate max concurrent is 10 (as per configuration)
        assert data["max_concurrent"] == 10
        
        print(f"✓ Queue status: active={data['active_jobs']}, max={data['max_concurrent']}, queued={data['queued_jobs']}, available={data['available_slots']}")


class TestJobsEndpoints:
    """Job management tests"""
    
    def test_get_jobs_without_auth_returns_401(self, unauth_client):
        """Test that /jobs requires authentication"""
        response = unauth_client.get(f"{BASE_URL}/api/jobs")
        assert response.status_code == 401
        print("✓ /jobs returns 401 without auth")
    
    def test_get_jobs_with_auth(self, api_client):
        """Test that /jobs returns list with valid auth"""
        response = api_client.get(f"{BASE_URL}/api/jobs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ /jobs returns {len(data)} jobs")
    
    def test_get_nonexistent_job_returns_404(self, api_client):
        """Test that getting non-existent job returns 404"""
        response = api_client.get(f"{BASE_URL}/api/jobs/nonexistent_job_12345")
        assert response.status_code == 404
        print("✓ Non-existent job returns 404")


class TestDownloadEndpoint:
    """Download endpoint tests - CRITICAL P0 BUG FIX VERIFICATION"""
    
    def test_download_without_auth_returns_401(self, unauth_client):
        """Test that download endpoint requires authentication"""
        response = unauth_client.get(f"{BASE_URL}/api/jobs/test_job/download/test.xlsx")
        assert response.status_code == 401
        print("✓ Download endpoint returns 401 without auth")
    
    def test_download_nonexistent_job_returns_404(self, api_client):
        """Test that downloading from non-existent job returns 404"""
        response = api_client.get(f"{BASE_URL}/api/jobs/nonexistent_job/download/test.xlsx")
        assert response.status_code == 404
        print("✓ Download from non-existent job returns 404")
    
    def test_download_with_query_token(self, session_token):
        """Test that download works with token in query parameter"""
        # This tests the alternative auth method used for downloads
        session = requests.Session()
        response = session.get(
            f"{BASE_URL}/api/jobs/nonexistent_job/download/test.xlsx?token={session_token}"
        )
        # Should be 404 (job not found) not 401 (unauthorized)
        assert response.status_code == 404
        print("✓ Download with query token param works (returns 404 for non-existent job, not 401)")


class TestAdminEndpoints:
    """Admin panel tests"""
    
    def test_admin_users_without_auth_returns_401(self, unauth_client):
        """Test that admin endpoints require authentication"""
        response = unauth_client.get(f"{BASE_URL}/api/admin/users")
        assert response.status_code == 401
        print("✓ Admin users endpoint returns 401 without auth")
    
    def test_admin_agents_without_auth_returns_401(self, unauth_client):
        """Test that admin agents endpoint requires authentication"""
        response = unauth_client.get(f"{BASE_URL}/api/admin/agents")
        assert response.status_code == 401
        print("✓ Admin agents endpoint returns 401 without auth")
    
    def test_admin_users_with_admin_role(self, api_client):
        """Test admin users endpoint with admin user"""
        response = api_client.get(f"{BASE_URL}/api/admin/users")
        # Our test user is admin, should return 200
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin users returns {len(data)} users")
    
    def test_admin_agents_with_admin_role(self, api_client):
        """Test admin agents endpoint with admin user"""
        response = api_client.get(f"{BASE_URL}/api/admin/agents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin agents returns {len(data)} agents")


class TestFileUploadAndExecution:
    """File upload and job execution tests"""
    
    def test_upload_without_auth_returns_401(self, unauth_client):
        """Test that upload endpoint requires authentication"""
        # Need to clear Content-Type header for multipart form data
        unauth_client.headers.pop('Content-Type', None)
        response = unauth_client.post(
            f"{BASE_URL}/api/agents/test_agent/upload",
            files={"files": ("test.txt", b"test content", "text/plain")}
        )
        assert response.status_code == 401
        print("✓ Upload endpoint returns 401 without auth")
    
    def test_upload_to_nonexistent_agent_returns_404(self, session_token):
        """Test that upload to non-existent agent returns 404"""
        session = requests.Session()
        session.cookies.set('session_token', session_token)
        response = session.post(
            f"{BASE_URL}/api/agents/nonexistent_agent/upload",
            files={"files": ("test.txt", b"test content", "text/plain")}
        )
        assert response.status_code == 404
        print("✓ Upload to non-existent agent returns 404")
    
    def test_execute_without_auth_returns_401(self, unauth_client):
        """Test that execute endpoint requires authentication"""
        response = unauth_client.post(
            f"{BASE_URL}/api/agents/test_agent/execute",
            json={"job_id": "test_job_123"}
        )
        assert response.status_code == 401
        print("✓ Execute endpoint returns 401 without auth")


class TestSettingsPageRemoval:
    """Verify Settings page route is removed"""
    
    def test_settings_api_does_not_exist(self, unauth_client):
        """Verify there's no /api/settings endpoint"""
        response = unauth_client.get(f"{BASE_URL}/api/settings")
        # Should return 404 or 405 (method not allowed)
        assert response.status_code in [404, 405, 422]
        print("✓ Settings API endpoint does not exist")


class TestSeedData:
    """Seed data tests"""
    
    def test_seed_agents_endpoint(self, unauth_client):
        """Test seed agents endpoint"""
        response = unauth_client.post(f"{BASE_URL}/api/seed-agents")
        # May return 200 (seeded) or 200 with "already seeded" message
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ Seed agents: {data['message']}")


class TestFullUploadExecuteFlow:
    """End-to-end file upload and execution flow"""
    
    def test_upload_files_to_agent(self, api_client, session_token):
        """Test uploading files to an actual agent"""
        # Get first available agent
        response = api_client.get(f"{BASE_URL}/api/agents")
        if response.status_code != 200 or len(response.json()) == 0:
            pytest.skip("No agents available for testing")
        
        agent = response.json()[0]
        agent_id = agent["agent_id"]
        
        # Upload test file
        upload_session = requests.Session()
        upload_session.cookies.set('session_token', session_token)
        
        response = upload_session.post(
            f"{BASE_URL}/api/agents/{agent_id}/upload",
            files={"files": ("test_file.csv", b"col1,col2\n1,2\n3,4", "text/csv")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert "uploaded_files" in data
        print(f"✓ Files uploaded successfully, job_id: {data['job_id']}")
        
        # Verify job was created
        job_response = api_client.get(f"{BASE_URL}/api/jobs/{data['job_id']}")
        assert job_response.status_code == 200
        job_data = job_response.json()
        assert job_data["status"] == "pending"
        print(f"✓ Job created with status: {job_data['status']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
