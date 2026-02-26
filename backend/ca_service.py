"""
BigQuery Conversational Analytics Service
Integrates with Google Cloud's Gemini Data Analytics API
Supports per-user dynamic credentials via OAuth tokens
"""
import os
import json
import logging
from typing import List, Optional, Dict, Any
from google.cloud import geminidataanalytics
from google.api_core import exceptions as google_exceptions
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as UserCredentials

# Import proto collections for conversion
try:
    from proto.marshal.collections.maps import MapComposite
    from proto.marshal.collections.repeated import RepeatedComposite
except ImportError:
    MapComposite = None
    RepeatedComposite = None

logger = logging.getLogger(__name__)

# Google OAuth client credentials (for token refresh)
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', 'd-FL95Q19q7MQmFpd7hHD0Ty')


def proto_to_dict(obj):
    """Recursively convert proto objects to dict for JSON serialization"""
    if MapComposite and isinstance(obj, MapComposite):
        return {key: proto_to_dict(obj[key]) for key in obj.keys()}
    elif RepeatedComposite and isinstance(obj, RepeatedComposite):
        return [proto_to_dict(item) for item in obj]
    elif isinstance(obj, (list, tuple)):
        return [proto_to_dict(item) for item in obj]
    elif hasattr(obj, 'WhichOneof'):
        # Protobuf Value type
        kind = obj.WhichOneof('kind')
        if kind == 'string_value':
            return obj.string_value
        elif kind == 'number_value':
            return obj.number_value
        elif kind == 'bool_value':
            return obj.bool_value
        elif kind == 'struct_value':
            return proto_to_dict(obj.struct_value.fields)
        elif kind == 'list_value':
            return [proto_to_dict(v) for v in obj.list_value.values]
        return None
    else:
        return obj


def create_credentials_from_oauth_tokens(oauth_tokens: Dict[str, Any]) -> Optional[UserCredentials]:
    """Create GCP credentials from OAuth tokens"""
    if not oauth_tokens:
        return None
    
    try:
        credentials = UserCredentials(
            token=oauth_tokens.get('access_token'),
            refresh_token=oauth_tokens.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET
        )
        return credentials
    except Exception as e:
        logger.error(f"Failed to create credentials from OAuth tokens: {e}")
        return None


class ConversationalAnalyticsService:
    """Service for interacting with BigQuery Conversational Analytics API"""
    
    def __init__(self, project_id: str, credentials_path: Optional[str] = None, user_credentials: Optional[Dict] = None):
        self.project_id = project_id
        self.parent = f"projects/{project_id}/locations/global"
        
        credentials = None
        
        # Priority 1: Use user's stored credentials if provided (per-user)
        if user_credentials:
            cred_type = user_credentials.get('type', '')
            
            if cred_type == 'authorized_user':
                credentials = UserCredentials(
                    token=None,
                    refresh_token=user_credentials.get('refresh_token'),
                    client_id=user_credentials.get('client_id', GOOGLE_CLIENT_ID),
                    client_secret=user_credentials.get('client_secret', GOOGLE_CLIENT_SECRET),
                    token_uri='https://oauth2.googleapis.com/token'
                )
                logger.info("Using per-user authorized_user credentials")
            elif cred_type == 'service_account':
                # For service account, we need to create credentials from dict
                credentials = service_account.Credentials.from_service_account_info(
                    user_credentials,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                logger.info("Using per-user service_account credentials")
        
        # Priority 2: Load credentials from file if path provided
        if not credentials and credentials_path and os.path.exists(credentials_path):
            with open(credentials_path, 'r') as f:
                cred_data = json.load(f)
            
            cred_type = cred_data.get('type', '')
            
            if cred_type == 'authorized_user':
                credentials = UserCredentials(
                    token=None,
                    refresh_token=cred_data.get('refresh_token'),
                    client_id=cred_data.get('client_id'),
                    client_secret=cred_data.get('client_secret'),
                    token_uri='https://oauth2.googleapis.com/token'
                )
                logger.info("Using authorized_user credentials from file")
            elif cred_type == 'service_account':
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                logger.info("Using service_account credentials from file")
        
        # Initialize clients
        if credentials:
            self.agent_client = geminidataanalytics.DataAgentServiceClient(credentials=credentials)
            self.chat_client = geminidataanalytics.DataChatServiceClient(credentials=credentials)
        else:
            # Fall back to ADC
            logger.info("Using Application Default Credentials")
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
            )
            
            convos = list(self.chat_client.list_conversations(request=request))
            # Filter by agent
            convos = [c for c in convos if agent_name in c.agents]
            
            result = []
            for convo in convos:
                # Try to get the first message as title
                title = None
                try:
                    msgs_request = geminidataanalytics.ListMessagesRequest(parent=convo.name)
                    msgs = list(self.chat_client.list_messages(request=msgs_request))
                    # Find first user message (messages come in reverse order)
                    for msg_wrapper in reversed(msgs):
                        msg = msg_wrapper.message if hasattr(msg_wrapper, 'message') else msg_wrapper
                        if hasattr(msg, 'user_message') and msg.user_message and msg.user_message.text:
                            title = msg.user_message.text[:50]  # Truncate to 50 chars
                            if len(msg.user_message.text) > 50:
                                title += "..."
                            break
                except Exception as e:
                    logger.debug(f"Could not fetch messages for conversation title: {e}")
                
                result.append({
                    "name": convo.name,
                    "title": title,
                    "agents": list(convo.agents),
                    "create_time": convo.create_time.isoformat() if hasattr(convo, 'create_time') and convo.create_time else None,
                    "last_used_time": convo.last_used_time.isoformat() if hasattr(convo, 'last_used_time') and convo.last_used_time else None
                })
            
            # Sort by last_used_time (most recent first)
            result.sort(key=lambda x: x.get('last_used_time') or x.get('create_time') or '', reverse=True)
            
            return result[:page_size]
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
            # Get the agent from the conversation
            convo = self.chat_client.get_conversation(name=conversation_name)
            agent_name = convo.agents[0] if convo.agents else None
            
            if not agent_name:
                raise ValueError("No agent associated with conversation")
            
            # Create the user message
            message = geminidataanalytics.Message()
            message.user_message.text = message_text
            
            # Create conversation reference with data agent context
            conv_ref = geminidataanalytics.ConversationReference()
            conv_ref.conversation = conversation_name
            conv_ref.data_agent_context.data_agent = agent_name
            
            # Create the chat request
            request = geminidataanalytics.ChatRequest(
                parent=self.parent,
                conversation_reference=conv_ref,
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
        
        # Extract text content
        if hasattr(sm, 'text') and sm.text:
            text_obj = sm.text
            if hasattr(text_obj, 'parts') and text_obj.parts:
                # Join all text parts
                content["text"] = " ".join(text_obj.parts)
            elif isinstance(text_obj, str):
                content["text"] = text_obj
        
        # Extract SQL from analysis
        if hasattr(sm, 'analysis') and sm.analysis:
            if hasattr(sm.analysis, 'sql') and sm.analysis.sql:
                content["sql"] = sm.analysis.sql
        
        # Extract table data
        if hasattr(sm, 'data') and sm.data:
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
        
        # Extract suggestions
        if hasattr(sm, 'example_queries') and sm.example_queries:
            eq = sm.example_queries
            if hasattr(eq, 'queries') and eq.queries:
                content["suggestions"] = list(eq.queries)
            elif hasattr(eq, '__iter__'):
                try:
                    content["suggestions"] = list(eq)
                except TypeError:
                    pass
        
        return content
