"""
Main application for the Unified Dive Assistant.
Single agent handles both trip planning and dive log Q&A.
"""
import asyncio
import sys
from aidivelog.agents import (
    create_dive_log_agent,
    create_user_proxy,
    get_model_client,
)


def print_welcome():
    """Print welcome message."""
    print("\n" + "="*80)
    print("DIVE ASSISTANT - Dive Log Q&A")
    print("="*80)
    print("\nType 'quit' or 'exit' to end the conversation.\n")
    print("="*80 + "\n")

async def run_conversation(agent, user_proxy):
    """Run a conversational loop with the agent."""
    print("Assistant ready! How can I help you today?\n")
    
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
        
        print("Initializing assistant...")
        
        # Create model client
        model_client = get_model_client()
        
        # Create unified agent
        agent = create_dive_log_agent(model_client)
        
        # Create user proxy
        user_proxy = create_user_proxy()
        
        print("Assistant initialized!\n")
        
        # Run conversational loop
        asyncio.run(run_conversation(agent, user_proxy))
        
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

