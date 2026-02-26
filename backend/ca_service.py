"""
BigQuery Conversational Analytics Service
Integrates with Google Cloud's Gemini Data Analytics API
"""
import os
import logging
from typing import List, Optional
from google.cloud import geminidataanalytics
from google.api_core import exceptions as google_exceptions
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

class ConversationalAnalyticsService:
    """Service for interacting with BigQuery Conversational Analytics API"""
    
    def __init__(self, project_id: str, credentials_path: Optional[str] = None):
        self.project_id = project_id
        self.parent = f"projects/{project_id}/locations/global"
        
        # Initialize clients
        # Use service account credentials if provided, otherwise ADC
        if credentials_path and os.path.exists(credentials_path):
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            self.agent_client = geminidataanalytics.DataAgentServiceClient(credentials=credentials)
            self.chat_client = geminidataanalytics.DataChatServiceClient(credentials=credentials)
        else:
            # Use Application Default Credentials
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
                msg = msg_wrapper.message
                messages.append({
                    "name": msg_wrapper.name if hasattr(msg_wrapper, 'name') else None,
                    "author": msg.author if hasattr(msg, 'author') else 'unknown',
                    "content": self._extract_message_content(msg),
                    "create_time": msg.create_time.isoformat() if hasattr(msg, 'create_time') and msg.create_time else None
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
            # Create the message
            message = geminidataanalytics.Message()
            message.author = "user"
            
            # Set the text content
            text_content = geminidataanalytics.TextContent()
            text_content.text = message_text
            message.text = text_content
            
            request = geminidataanalytics.CreateMessageRequest(
                parent=conversation_name,
                message=message,
            )
            
            # Send and get response
            response = self.chat_client.create_message(request=request)
            
            return {
                "name": response.name if hasattr(response, 'name') else None,
                "response": self._extract_response_content(response)
            }
        except google_exceptions.GoogleAPICallError as e:
            logger.error(f"API error sending message: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending message: {e}")
            raise
    
    def _extract_message_content(self, msg) -> dict:
        """Extract content from a message object"""
        content = {
            "text": None,
            "sql": None,
            "table": None,
            "chart": None
        }
        
        if hasattr(msg, 'text') and msg.text:
            content["text"] = msg.text.text if hasattr(msg.text, 'text') else str(msg.text)
        
        if hasattr(msg, 'generated_sql') and msg.generated_sql:
            content["sql"] = msg.generated_sql.sql if hasattr(msg.generated_sql, 'sql') else str(msg.generated_sql)
        
        if hasattr(msg, 'query_result') and msg.query_result:
            # Extract table data if present
            result = msg.query_result
            if hasattr(result, 'rows'):
                content["table"] = {
                    "columns": [col.name for col in result.schema.fields] if hasattr(result, 'schema') and result.schema else [],
                    "rows": [[str(cell) for cell in row.values] for row in result.rows] if result.rows else []
                }
        
        return content
    
    def _extract_response_content(self, response) -> dict:
        """Extract content from a response object"""
        content = {
            "text": None,
            "sql": None,
            "table": None,
            "suggestions": []
        }
        
        if hasattr(response, 'message'):
            msg = response.message
            content = self._extract_message_content(msg)
        
        if hasattr(response, 'suggestions') and response.suggestions:
            content["suggestions"] = [s.text for s in response.suggestions if hasattr(s, 'text')]
        
        return content
