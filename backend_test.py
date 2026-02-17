import requests
import sys
import os
import json
from datetime import datetime, timezone
import time

class AutomationHubAPITester:
    def __init__(self, base_url="https://ke30-automation-hub.preview.emergentagent.com"):
        self.base_url = base_url
        self.session_token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.job_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {}
        cookies = {}
        
        if self.session_token:
            cookies['session_token'] = self.session_token

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, cookies=cookies)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, headers=headers, cookies=cookies)
                else:
                    headers['Content-Type'] = 'application/json'
                    response = requests.post(url, json=data, headers=headers, cookies=cookies)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if response.content:
                    try:
                        response_data = response.json()
                        print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                        return True, response_data
                    except:
                        print(f"   Response: {response.text[:200]}")
                        return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:300]}")

            return success, response.json() if success and response.content else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test basic API health"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "",
            200
        )
        return success

    def test_seed_agents(self):
        """Seed initial agents"""
        success, response = self.run_test(
            "Seed Agents",
            "POST",
            "seed-agents",
            200
        )
        return success

    def create_test_session(self):
        """Create test session using MongoDB direct insertion"""
        print("\n🔧 Creating test session via MongoDB...")
        
        # Use mongosh to create test user and session
        import subprocess
        user_id = f"test_user_{datetime.now().strftime('%H%M%S')}"
        session_token = f"test_session_{datetime.now().strftime('%H%M%S%f')}"
        
        mongo_cmd = f'''mongosh --eval "
use('test_database');
var userId = '{user_id}';
var sessionToken = '{session_token}';
db.users.insertOne({{
  user_id: userId,
  email: 'test.user.{datetime.now().strftime('%H%M%S')}@example.com',
  name: 'Test User {datetime.now().strftime('%H%M%S')}',
  picture: 'https://via.placeholder.com/150',
  created_at: '{datetime.now(timezone.utc).isoformat()}'
}});
db.user_sessions.insertOne({{
  user_id: userId,
  session_token: sessionToken,
  expires_at: '{(datetime.now(timezone.utc)).isoformat()}',
  created_at: '{datetime.now(timezone.utc).isoformat()}'
}});
print('Session token: ' + sessionToken);
print('User ID: ' + userId);
"'''

        try:
            result = subprocess.run(mongo_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                self.session_token = session_token
                self.user_id = user_id
                print(f"✅ Test session created - User: {user_id}, Token: {session_token[:20]}...")
                return True
            else:
                print(f"❌ Failed to create session: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ MongoDB session creation failed: {str(e)}")
            return False

    def test_auth_me(self):
        """Test /auth/me endpoint"""
        if not self.session_token:
            print("❌ No session token available")
            return False

        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200
        )
        return success

    def test_get_agents(self):
        """Test getting agents list"""
        success, response = self.run_test(
            "Get Agents",
            "GET",
            "agents",
            200
        )
        if success:
            print(f"   Found {len(response)} agents")
        return success

    def test_get_agent_detail(self, agent_id):
        """Test getting specific agent details"""
        success, response = self.run_test(
            f"Get Agent Detail ({agent_id})",
            "GET",
            f"agents/{agent_id}",
            200
        )
        return success, response

    def test_file_upload(self, agent_id):
        """Test file upload functionality"""
        # Create a test file
        test_file_content = f"Test file content for {agent_id}\nCreated at: {datetime.now()}\n"
        test_files = {
            'files': ('test_file.txt', test_file_content, 'text/plain')
        }
        
        success, response = self.run_test(
            f"Upload Files for Agent {agent_id}",
            "POST",
            f"agents/{agent_id}/upload",
            200,
            files=test_files
        )
        
        if success and 'job_id' in response:
            self.job_id = response['job_id']
            print(f"   Job ID: {self.job_id}")
        
        return success, response

    def test_job_execution(self, agent_id):
        """Test job execution"""
        if not self.job_id:
            print("❌ No job_id available for execution")
            return False

        success, response = self.run_test(
            f"Execute Agent {agent_id}",
            "POST",
            f"agents/{agent_id}/execute",
            200,
            data={"job_id": self.job_id}
        )
        return success

    def test_job_status(self):
        """Test job status retrieval"""
        if not self.job_id:
            print("❌ No job_id available for status check")
            return False

        success, response = self.run_test(
            f"Get Job Status ({self.job_id})",
            "GET",
            f"jobs/{self.job_id}",
            200
        )
        
        if success:
            status = response.get('status', 'unknown')
            print(f"   Job Status: {status}")
            
            # Wait for completion if processing
            if status == 'processing':
                print("   Waiting for job completion...")
                for i in range(10):  # Wait up to 30 seconds
                    time.sleep(3)
                    success2, response2 = self.run_test(
                        f"Check Job Status - Attempt {i+1}",
                        "GET",
                        f"jobs/{self.job_id}",
                        200
                    )
                    if success2:
                        new_status = response2.get('status', 'unknown')
                        print(f"   Job Status Update: {new_status}")
                        if new_status in ['completed', 'failed']:
                            return success2, response2
                    
        return success, response

    def test_jobs_list(self):
        """Test getting user's job history"""
        success, response = self.run_test(
            "Get Job History",
            "GET",
            "jobs",
            200
        )
        if success:
            print(f"   Found {len(response)} jobs in history")
        return success

    def test_file_download(self, filename):
        """Test file download functionality"""
        if not self.job_id:
            print("❌ No job_id available for download test")
            return False

        url = f"{self.base_url}/api/jobs/{self.job_id}/download/{filename}"
        headers = {}
        cookies = {}
        
        if self.session_token:
            cookies['session_token'] = self.session_token

        print(f"\n🔍 Testing File Download ({filename})...")
        print(f"   URL: {url}")
        
        try:
            response = requests.get(url, headers=headers, cookies=cookies)
            success = response.status_code == 200
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Downloaded {len(response.content)} bytes")
            else:
                print(f"❌ Failed - Status: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
            
            self.tests_run += 1
            return success
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.tests_run += 1
            return False

def main():
    print("🚀 Starting KE30 Automation Hub API Tests")
    print("=" * 60)
    
    tester = AutomationHubAPITester()
    
    # Test 1: Health Check
    if not tester.test_health_check():
        print("❌ Health check failed, stopping tests")
        return 1

    # Test 2: Seed agents
    if not tester.test_seed_agents():
        print("⚠️ Agent seeding failed, but continuing...")

    # Test 3: Create test session
    if not tester.create_test_session():
        print("❌ Session creation failed, stopping tests")
        return 1

    # Test 4: Auth verification
    if not tester.test_auth_me():
        print("❌ Auth verification failed, stopping tests")
        return 1

    # Test 5: Get agents
    if not tester.test_get_agents():
        print("❌ Get agents failed, stopping tests")
        return 1

    # Test 6: Get agent details and test workflow
    agent_id = "agent_ke30"  # Test with the first seeded agent
    
    success, agent_data = tester.test_get_agent_detail(agent_id)
    if not success:
        print(f"❌ Get agent detail failed for {agent_id}")
        return 1

    # Test 7: File upload
    upload_success, upload_data = tester.test_file_upload(agent_id)
    if not upload_success:
        print("❌ File upload failed")
        return 1

    # Test 8: Job execution
    if not tester.test_job_execution(agent_id):
        print("❌ Job execution failed")
        return 1

    # Test 9: Job status tracking
    status_success, job_data = tester.test_job_status()
    if not status_success:
        print("❌ Job status check failed")
        return 1

    # Test 10: Jobs list
    if not tester.test_jobs_list():
        print("❌ Jobs list failed")
        return 1

    # Test 11: File download (if job completed)
    if job_data.get('status') == 'completed' and job_data.get('output_files'):
        output_file = job_data['output_files'][0]
        if not tester.test_file_download(output_file):
            print("❌ File download failed")
    else:
        print("⚠️ Skipping file download test - job not completed or no output files")

    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 Tests completed: {tester.tests_passed}/{tester.tests_run} passed")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())