"""
Main application for the Unified Dive Assistant.
Single agent handles both trip planning and dive log Q&A.
"""
import asyncio
import os
import sys

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from aidivelog.agents import (
    create_dive_log_agent,
    get_openai_client,
    create_user_memory,
    initialize_user_memory,
)


def print_welcome():
    """Print welcome message."""
    print("\n" + "="*80)
    print("DIVE LOG ASSISTANT")
    print("="*80)
    print("\nType 'quit' or 'exit' to end the conversation.\n")
    print("="*80 + "\n")

async def run_conversation(agent:AssistantAgent):
    """Run a conversational loop with the agent."""
    print("""Hey there! I'm your dive log assistant. How can I help you today?

Ask me anything about your dive log. I can answer questions about your dives, tell you about your dive history, and help you add new dives to your log.
    
    """)
    
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            # Check for exit commands
            if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                print("\nGoodbye! Happy diving!")
                break
            
            # Run the agent with the user's input (agent will use tools as needed)
            print("\nAssistant: ", end="", flush=True)
            show_tool_calls = os.environ.get("SHOW_TOOL_CALLS", 'False').lower() in ('true', '1')
            if show_tool_calls:
                await Console(agent.run_stream(task=user_input))
            else:
                result = await agent.run(task=user_input)
                
                # Extract and print the response
                if result and hasattr(result, 'messages') and result.messages:
                    response = result.messages[-1]
                    if hasattr(response, 'content'):
                        print(response.content)
                    elif hasattr(response, 'text'):
                        print(response.text)
                    else:
                        print(str(response))
                else:
                    print("I'm processing your request...")
                
                print()  # Empty line for readability
            
        except KeyboardInterrupt:
            print("\n\nConversation interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
            print("\nPlease try again or type 'quit' to exit.\n")


def main():
    """Main function to run the unified dive assistant."""
    try:
        print_welcome()
                
        # Create model client
        model_client = get_openai_client()
        
        # Create user memory
        user_memory = create_user_memory()
        
        # Initialize memory (load any existing preferences)
        asyncio.run(initialize_user_memory(user_memory))
        
        # Create unified agent with memory
        agent = create_dive_log_agent(model_client, user_memory)
        
            
        # Run conversational loop
        asyncio.run(run_conversation(agent))
        
    except KeyboardInterrupt:
        print("\n\nConversation interrupted. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

