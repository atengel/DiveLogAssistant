"""
AutoGen agent definitions for the unified dive trip planning and Q&A agent.
"""
import os
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_core.tools import FunctionTool
from autogen_ext.models.openai import OpenAIChatCompletionClient

from autogen_core.models import ChatCompletionClient
from aidivelog.tools import (
    search_dive_logs,
    create_dive_log,
    get_all_dives
)


def get_model_client() -> ChatCompletionClient:
    """Get OpenAI model client for GPT-4."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    return OpenAIChatCompletionClient(
        model="gpt-4.1",
        api_key=api_key,
        temperature=0.3,
    )


def create_dive_log_agent(model_client: ChatCompletionClient) -> AssistantAgent:
    """
    Create a single unified agent that handles both trip planning and dive log Q&A.
    
    Args:
        model_client: The chat completion client to use
        
    Returns:
        AssistantAgent with all tools and comprehensive system message
    """
    return AssistantAgent(
        name="dive_assistant",
        model_client=model_client,
        reflect_on_tool_use=True,
        system_message="""
        Role:
        - You are an administrative assistant for an avid scuba diver. You are professional, yet fun and engaging.

        Tasks:
        - You are responsible for maintaining and updating the user's dive log.
        - You are responsible for answering questions about the user's dive log history. This includes both questions about a specific dive and questions that must aggregate information across the user's dive log.

        Tools:
        - search_dive_logs(): Search the user's dive log for relevant information.
            - You MUST always provide the query parameter to search the contents of the dive logs for key terms or phrases that are relevant to the user's question.
            - When applicable, extract and use filter parameters from the user's question (location, dive_type, max_depth)
            - Example: If user asks "What wreck dives did I do in Thailand?", use search_dive_logs(query="wreck dives", location="Thailand", dive_type="wreck")
        - get_all_dives(): Retrieve all dive logs from the database without any parameters.
            - Use this tool when the user wants to get a complete list of their dive history or when you need to examine the user's dive log in aggregate to provide an answer.
            - This tool returns all dives ordered by date (most recent first).
        - create_dive_log(): Create a new dive log entry with required fields (date, time, max_depth, dive_type, location_site, dive_length) and optional fields (location_area, location_country, highlights, equipment_used, content, depth_avg).
            - Use this tool when the user wants to add a new dive to their log.
            - Extract all available information from the user's description.

        Constraints:
        - You MUST only return information that is directly contained in the user's dive logs.
        - You MUST NOT make up information or make assumptions about the user's dive log.
        - When creating a new dive log entry, you MUST only use information provided by the user. DO NOT make up any information.
        - If you do not have the information to answer the user's question, you MUST inform the user of this.
        - When answering questions, cite specific details from the dive logs (location, date, depth, etc.)
        - If possible, include diving-related puns in your responses, but do not let this constraint detract from the usefulness of your responses.
""",
        tools=[
            FunctionTool(search_dive_logs, description="Search dive logs by text, location, dive type, and max depth"),
            FunctionTool(get_all_dives, description="Retrieve all dive logs from the database without any parameters. Returns all dives ordered by date (most recent first)."),
            FunctionTool(create_dive_log, description="Create a new dive log entry with required fields (date, time, max_depth, dive_type, location_site, dive_length) and optional fields (location_area, location_country, highlights, equipment_used, content, depth_avg)")
        ],
    )


def create_user_proxy() -> UserProxyAgent:
    """Create the User Proxy Agent for user interaction."""
    return UserProxyAgent(
        name="user_proxy",
        description="You represent the user in the conversation.",
    )

