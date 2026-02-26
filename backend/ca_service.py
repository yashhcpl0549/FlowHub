"""
BigQuery Conversational Analytics Service
Integrates with Google Cloud's Gemini Data Analytics API
"""
import os
import json
import logging
from typing import List, Optional
from google.cloud import geminidataanalytics
from google.api_core import exceptions as google_exceptions
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as UserCredentials

logger = logging.getLogger(__name__)

class ConversationalAnalyticsService:
    """Service for interacting with BigQuery Conversational Analytics API"""
    
    def __init__(self, project_id: str, credentials_path: Optional[str] = None):
        self.project_id = project_id
        self.parent = f"projects/{project_id}/locations/global"
        
        credentials = None
        
        # Load credentials if path provided
        if credentials_path and os.path.exists(credentials_path):
            with open(credentials_path, 'r') as f:
                cred_data = json.load(f)
            
            cred_type = cred_data.get('type', '')
            
            if cred_type == 'authorized_user':
                # Handle ADC authorized_user credentials
                credentials = UserCredentials(
                    token=None,
                    refresh_token=cred_data.get('refresh_token'),
                    client_id=cred_data.get('client_id'),
                    client_secret=cred_data.get('client_secret'),
                    token_uri='https://oauth2.googleapis.com/token'
                )
                logger.info("Using authorized_user credentials")
            elif cred_type == 'service_account':
                # Handle service account credentials
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                logger.info("Using service_account credentials")
        
        # Initialize clients
        if credentials:
            self.agent_client = geminidataanalytics.DataAgentServiceClient(credentials=credentials)
            self.chat_client = geminidataanalytics.DataChatServiceClient(credentials=credentials)
        else:
            # Fall back to ADC
            self.agent_client = geminidataanalytics.DataAgentServiceClient()
            self.chat_client = geminidataanalytics.DataChatServiceClient()
    
    def list_agents(self) -> List[dict]:
        """List all data agents"""
        try:
            request = geminidataanalytics.ListDataAgentsRequest(parent=self.parent)
            agents = list(self.agent_client.list_data_agents(request=request))
            
            return [
                {
                    "name": agent.name,
                    "display_name": agent.display_name,
                    "description": getattr(agent, 'description', ''),
                    "state": str(agent.state) if hasattr(agent, 'state') else 'ACTIVE'
                }
                for agent in agents
            ]
        except google_exceptions.GoogleAPICallError as e:
            logger.error(f"API error fetching agents: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing agents: {e}")
            raise
    
    def get_agent(self, agent_name: str) -> Optional[dict]:
        """Get a specific data agent"""
        try:
            request = geminidataanalytics.GetDataAgentRequest(name=agent_name)
            agent = self.agent_client.get_data_agent(request=request)
            
            return {
                "name": agent.name,
                "display_name": agent.display_name,
                "description": getattr(agent, 'description', ''),
                "state": str(agent.state) if hasattr(agent, 'state') else 'ACTIVE'
            }
        except google_exceptions.NotFound:
            return None
        except Exception as e:
            logger.error(f"Error getting agent: {e}")
            raise
    
    def list_conversations(self, agent_name: str, page_size: int = 50) -> List[dict]:
        """List conversations for a specific agent"""
        try:
            request = geminidataanalytics.ListConversationsRequest(
                parent=self.parent,
                page_size=page_size,
            )
            
            convos = list(self.chat_client.list_conversations(request=request))
            # Filter by agent
            convos = [c for c in convos if agent_name in c.agents]
            
            return [
                {
                    "name": convo.name,
                    "agents": list(convo.agents),
                    "create_time": convo.create_time.isoformat() if hasattr(convo, 'create_time') and convo.create_time else None
                }
                for convo in convos
            ]
        except google_exceptions.GoogleAPICallError as e:
            logger.error(f"API error fetching conversations: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing conversations: {e}")
            raise
    
    def create_conversation(self, agent_name: str) -> dict:
        """Create a new conversation with an agent"""
        try:
            conversation = geminidataanalytics.Conversation()
            conversation.agents = [agent_name]
            
            request = geminidataanalytics.CreateConversationRequest(
                parent=self.parent,
                conversation=conversation,
            )
            
            convo = self.chat_client.create_conversation(request=request)
            
            return {
                "name": convo.name,
                "agents": list(convo.agents),
                "create_time": convo.create_time.isoformat() if hasattr(convo, 'create_time') and convo.create_time else None
            }
        except google_exceptions.GoogleAPICallError as e:
            logger.error(f"API error creating conversation: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating conversation: {e}")
            raise
    
    def get_messages(self, conversation_name: str) -> List[dict]:
        """Get all messages in a conversation"""
        try:
            request = geminidataanalytics.ListMessagesRequest(parent=conversation_name)
            msgs = list(self.chat_client.list_messages(request=request))
            
            messages = []
            for msg_wrapper in msgs:
                msg = msg_wrapper.message if hasattr(msg_wrapper, 'message') else msg_wrapper
                
                # Determine if it's user or system message
                if hasattr(msg, 'user_message') and msg.user_message and msg.user_message.text:
                    messages.append({
                        "name": msg_wrapper.name if hasattr(msg_wrapper, 'name') else None,
                        "author": "user",
                        "content": {"text": msg.user_message.text},
                        "create_time": msg.timestamp.isoformat() if hasattr(msg, 'timestamp') and msg.timestamp else None
                    })
                elif hasattr(msg, 'system_message') and msg.system_message:
                    sm = msg.system_message
                    content = self._extract_system_message_content(sm)
                    messages.append({
                        "name": msg_wrapper.name if hasattr(msg_wrapper, 'name') else None,
                        "author": "assistant",
                        "content": content,
                        "create_time": msg.timestamp.isoformat() if hasattr(msg, 'timestamp') and msg.timestamp else None
                    })
            
            # Return in chronological order (oldest first)
            return list(reversed(messages))
        except google_exceptions.GoogleAPICallError as e:
            logger.error(f"API error fetching messages: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting messages: {e}")
            raise
    
    def send_message(self, conversation_name: str, message_text: str) -> dict:
        """Send a message in a conversation and get the response"""
        try:
            # Create the user message
            message = geminidataanalytics.Message()
            message.user_message.text = message_text
            
            # Create the chat request
            request = geminidataanalytics.ChatRequest(
                parent=conversation_name,
                messages=[message]
            )
            
            # Send and get streamed response
            response_stream = self.chat_client.chat(request=request)
            
            # Collect all response messages
            responses = []
            for response_msg in response_stream:
                if hasattr(response_msg, 'system_message') and response_msg.system_message:
                    content = self._extract_system_message_content(response_msg.system_message)
                    responses.append(content)
            
            # Merge all response content
            merged_response = {
                "text": None,
                "sql": None,
                "table": None,
                "suggestions": []
            }
            
            for resp in responses:
                if resp.get("text"):
                    merged_response["text"] = (merged_response["text"] or "") + resp["text"]
                if resp.get("sql"):
                    merged_response["sql"] = resp["sql"]
                if resp.get("table"):
                    merged_response["table"] = resp["table"]
                if resp.get("suggestions"):
                    merged_response["suggestions"].extend(resp["suggestions"])
            
            return {
                "name": None,
                "response": merged_response
            }
        except google_exceptions.GoogleAPICallError as e:
            logger.error(f"API error sending message: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending message: {e}")
            raise
    
    def _extract_system_message_content(self, sm) -> dict:
        """Extract content from a system message"""
        content = {
            "text": None,
            "sql": None,
            "table": None,
            "suggestions": []
        }
        
        if hasattr(sm, 'text') and sm.text:
            content["text"] = sm.text
        
        if hasattr(sm, 'analysis') and sm.analysis:
            if hasattr(sm.analysis, 'sql') and sm.analysis.sql:
                content["sql"] = sm.analysis.sql
        
        if hasattr(sm, 'data') and sm.data:
            # Extract table data
            data = sm.data
            if hasattr(data, 'rows') and data.rows:
                columns = []
                if hasattr(data, 'schema') and data.schema and hasattr(data.schema, 'fields'):
                    columns = [f.name for f in data.schema.fields]
                
                rows = []
                for row in data.rows:
                    if hasattr(row, 'values'):
                        rows.append([str(v) for v in row.values])
                
                if rows:
                    content["table"] = {
                        "columns": columns,
                        "rows": rows
                    }
        
        if hasattr(sm, 'example_queries') and sm.example_queries:
            content["suggestions"] = list(sm.example_queries)
        
        return content
