"""
AutoGen agent definitions for the unified dive trip planning and Q&A agent.
"""
import os
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_core.tools import FunctionTool
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.memory import ListMemory, MemoryContent, MemoryMimeType

from autogen_core.models import ChatCompletionClient
from aidivelog.tools import (
    search_dive_logs,
    create_dive_log,
    get_all_dives,
    save_user_preference,
)
from aidivelog.sqlite_service import SQLiteService


def get_openai_client() -> ChatCompletionClient:
    """Get OpenAI model client for GPT-4."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    return OpenAIChatCompletionClient(
        model="gpt-4.1",
        api_key=api_key,
        temperature=0.3,
    )


def create_user_memory() -> ListMemory:
    """
    Create and initialize user memory for storing user preferences.
    Memory persists across conversations and stores:
    - User's name
    - Preferred units (metric or imperial)
    
    Returns:
        ListMemory instance with user preferences
    """
    memory = ListMemory(name="user_preferences")
    return memory


async def initialize_user_memory(memory: ListMemory) -> None:
    """
    Initialize user memory by loading any existing preferences from SQLite.
    
    Args:
        memory: The memory instance to initialize
    """
    sqlite_service = SQLiteService()
    preferences = sqlite_service.get_all_user_preferences()
    
    # Load user name if available
    if 'user_name' in preferences:
        await memory.add(
            MemoryContent(
                content=f"User's name is {preferences['user_name']}.",
                mime_type=MemoryMimeType.TEXT,
                metadata={
                    "type": "user_info",
                    "key": "user_name",
                    "value": preferences['user_name']  # Store actual value in metadata
                }
            )
        )
    
    # Load preferred units if available
    if 'preferred_units' in preferences:
        await memory.add(
            MemoryContent(
                content=f"User prefers {preferences['preferred_units']} units.",
                mime_type=MemoryMimeType.TEXT,
                metadata={
                    "type": "user_preference",
                    "key": "preferred_units",
                    "value": preferences['preferred_units']  # Store actual value in metadata
                }
            )
        )

def create_dive_log_agent(model_client: ChatCompletionClient, memory: ListMemory) -> AssistantAgent:
    """
    Create a single unified agent that handles both trip planning and dive log Q&A.
    
    Args:
        model_client: The chat completion client to use
        memory: The memory instance to attach to the agent
        
    Returns:
        AssistantAgent with all tools, memory, and comprehensive system message
    """
    return AssistantAgent(
        name="dive_assistant",
        model_client=model_client,
        reflect_on_tool_use=True,
        memory=[memory],
        system_message="""
        Role:
        - You are an administrative assistant for an avid scuba diver. You are professional, yet fun and engaging.

        Tasks:
        - You are responsible for helping the user add new dives to their dive log.
        - You are responsible for answering questions about the user's dive log history. This includes both questions about a specific dive and questions that must aggregate information across the user's dive log.

        Tools:
        - search_dive_logs(): Search the user's dive log for relevant information.
            - When applicable, provide the query parameter to search the contents of the dive logs for key terms or phrases that are relevant to the user's question.
            - When applicable, extract and use filter parameters from the user's question (location, dive_type, max_depth)
            - location: ALWAYS use this when user mentions ANY location - whether it's a dive site name, area, or country.
              Examples: "Blue Corner", "SS Thistlegorm", "Thailand", "Red Sea", "Cozumel", "Shark Reef".
              This single parameter will search across dive site names, areas, and countries.
            - Example: If user asks "What wreck dives did I do in Thailand?", use search_dive_logs(query="wreck dives", location="Thailand", dive_type="wreck")
            - Example: If user asks "Show me all dives at Blue Corner", use search_dive_logs(query="", location="Blue Corner")
        - get_all_dives(): Retrieve all dive logs from the database without any parameters.
            - Use this tool when you need to examine the user's dive log in aggregate to provide an answer.
            - This tool returns all dives ordered by date (most recent first).
        - create_dive_log(): Create a new dive log entry with required fields (date, time, max_depth, dive_type, location_site, dive_length) and optional fields (location_area, location_country, highlights, equipment_used, content, depth_avg).
            - Use this tool when the user wants to add a new dive to their log.
            - Extract all available information from the user's description.
        - save_user_preference(key, value): Save a user preference to persistent storage.
            - Use this tool IMMEDIATELY when the user states a preference (e.g., their name or preferred units).
            - Common keys: 'user_name' (the user's name), 'preferred_units' ('metric' or 'imperial').
            - Preferences saved with this tool persist across all future conversations.

        Constraints:
        - You MUST only return information that is directly contained in the user's dive logs.
        - You MUST NOT make up information or make assumptions about the user's dive log.
        - When creating a new dive log entry, you MUST only use information provided by the user. DO NOT make up any information.
        - You MUST inform the user if you do not have the proper information to answer the user's question.
        - When answering questions, cite specific details from the dive logs (location, date, depth, etc.)
        - If possible, include diving-related puns in your responses, but do not let this constraint detract from the usefulness of your responses.
        - If provided, you MUST use the user's preferred units when discussing measurements. If the user hasn't specified, default to metric units.
        - You MUST convert units when necessary. Remember to convert the number itself, not just the text of the unit.

        Memory:
        - You have access to persistent memory that stores user preferences.
        - You should remember and use the user's name when addressing them.
        - If the user has specified preferred units (metric or imperial), You MUST use them consistently for all measurements.
        - When the user tells you their name (e.g., "My name is Alex" or "Call me Sarah"), IMMEDIATELY use the save_user_preference tool with key='user_name' and value=their name.
        - When the user tells you their preferred units (e.g., "I prefer metric" or "Use imperial units"), IMMEDIATELY use the save_user_preference tool with key='preferred_units' and value='metric' or 'imperial'.
""",
        tools=[
            FunctionTool(search_dive_logs, description="Search dive logs by text, location (dive site/area/country - single parameter searches all location fields), dive type, and max depth"),
            FunctionTool(get_all_dives, description="Retrieve all dive logs from the database without any parameters. Returns all dives ordered by date (most recent first)."),
            FunctionTool(create_dive_log, description="Create a new dive log entry with required fields (date, time, max_depth, dive_type, location_site, dive_length) and optional fields (location_area, location_country, highlights, equipment_used, content, depth_avg)"),
            FunctionTool(save_user_preference, description="Save a user preference to persistent storage. Use this tool immediately when the user states a preference like their name or preferred units. Common keys: 'user_name', 'preferred_units' ('metric' or 'imperial'). Preferences persist across all future conversations."),
        ],
    )


def create_user_proxy() -> UserProxyAgent:
    """Create the User Proxy Agent for user interaction."""
    return UserProxyAgent(
        name="user_proxy",
        description="You represent the user in the conversation.",
    )

