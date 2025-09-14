import os
import re
import json
import requests
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
BRAVE_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")

# Configuration
MODEL = "gpt-3.5-turbo"

# Fixed prompt - tells LLM to STOP after Action
SYSTEM_PROMPT = """You are a helpful assistant that can search the web when needed.

You have access to:
- web_search(query): Search the web for current information

IMPORTANT: Follow these rules exactly:

1. If you NEED current/recent information (weather, news, prices, etc.):
   Output ONLY:
   Thought: [why you need to search]
   Action: web_search("your search query")
   
   Then STOP. Wait for the observation.

2. If you DON'T need to search (math, general knowledge, creative tasks):
   Output:
   Thought: [your reasoning]
   Answer: [complete answer]

3. After receiving an Observation from a search:
   Output:
   Thought: [analyze the search results]
   Answer: [answer based on the results]

Examples:

Example 1 - Needs search:
Human: What's the weather in Tokyo?
Assistant: Thought: I need to search for current weather information in Tokyo.
Action: web_search("Tokyo weather today")
[STOP AND WAIT]

[After observation provided]
Assistant: Thought: Based on the search results, I can see Tokyo's current weather conditions.
Answer: The weather in Tokyo is 22°C with partly cloudy skies.

Example 2 - No search needed:
Human: What is 2 + 2?
Assistant: Thought: This is a simple math problem I can solve directly.
Answer: 2 + 2 equals 4."""

def web_search(query):
    """
    Search the web using Brave Search API
    Returns formatted search results
    """
    try:
        headers = {"X-Subscription-Token": BRAVE_API_KEY}
        response = requests.get(
            f"https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": 3},  # Get top 3 results
            headers=headers
        )
        
        if response.status_code == 200:
            results = response.json()
            
            # Format the top results nicely
            formatted_results = []
            for i, result in enumerate(results.get("web", {}).get("results", [])[:3], 1):
                title = result.get("title", "")
                description = result.get("description", "")
                url = result.get("url", "")
                formatted_results.append(f"{i}. {title}\n   {description}\n   URL: {url}")
            
            return "\n".join(formatted_results) if formatted_results else "No results found"
        else:
            return f"Search error: {response.status_code}"
            
    except Exception as e:
        return f"Search failed: {str(e)}"

def parse_action(text):
    """
    Parse the action from the agent's response
    Returns: (action_type, parameters) or (None, None)
    """
    action_match = re.search(r'Action:\s*(.*?)(?:\n|$)', text)
    
    if not action_match:
        return None, None
    
    action_line = action_match.group(1).strip()
    
    # Check if it's "none"
    if action_line.lower() == "none":
        return "none", None
    
    # Parse function call format: web_search("query") or web_search('query')
    func_match = re.match(r'(\w+)\(["\']([^"\']+)["\']\)', action_line)
    if func_match:
        return func_match.group(1), func_match.group(2)
    
    return None, None

def extract_final_answer(text):
    """Extract the final answer from the agent's response"""
    answer_match = re.search(r'Answer:\s*(.*?)$', text, re.DOTALL)
    return answer_match.group(1).strip() if answer_match else None

def react_agent(user_query, verbose=True):
    """
    ReAct agent with proper stop-and-wait pattern
    """
    
    # Start the conversation
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query}
    ]
    
    if verbose:
        print("\n" + "="*60)
        print(f"💭 Query: {user_query}")
        print("="*60)
    
    max_iterations = 3  # Usually only need 2: one for action, one for answer
    
    for iteration in range(max_iterations):
        # Get LLM response
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0
        )
        
        agent_response = response.choices[0].message.content
        
        if verbose:
            print(f"\n🤖 Step {iteration + 1}:")
            print(agent_response)
        
        # Add the assistant's response to history
        messages.append({"role": "assistant", "content": agent_response})
        
        # Check if we have a final answer
        if "Answer:" in agent_response:
            final_answer = extract_final_answer(agent_response)
            if verbose:
                print("\n" + "="*60)
                print(f"✅ Complete!")
            return final_answer
        
        # Parse and execute action if present
        action_type, action_param = parse_action(agent_response)
        
        if action_type == "web_search" and action_param:
            if verbose:
                print(f"\n🔍 Searching: '{action_param}'...")
            
            # Execute the search
            search_results = web_search(action_param)
            
            if verbose:
                print(f"\n📊 Results found:")
                # Show truncated results for readability
                if len(search_results) > 300:
                    print(search_results[:300] + "...")
                else:
                    print(search_results)
            
            # Add observation as a new user message
            # This is the key: we're continuing the conversation
            observation_message = f"Observation from web search:\n{search_results}\n\nNow provide your thought about these results and the final answer."
            messages.append({"role": "user", "content": observation_message})
            
        elif action_type == "none":
            # No action was needed, but if no answer was provided, ask for it
            if verbose:
                print("⚠️ No action taken but no answer provided")
            messages.append({"role": "user", "content": "Please provide your final answer."})
        else:
            # No action found and no answer - something went wrong
            if verbose:
                print("⚠️ No action or answer found")
            break
    
    return "I couldn't complete this request properly. Please try rephrasing."

def main():
    """Interactive ReAct Agent with Web Search"""
    
    print("="*60)
    print("🤖 ReAct Agent - Step 2: Web Search Enabled")
    print(f"📦 Model: {MODEL}")
    print("🔧 Tools: web_search")
    print("="*60)
    print("Commands: 'quit' to exit | 'test' for test queries\n")
    
    test_queries = [
        "What's the weather in Tokyo today?",
        "What is 2 + 2?",
        "What's the current price of Bitcoin?",
        "Explain what photosynthesis is"
    ]
    
    while True:
        try:
            # Get user input
            user_input = input("\n🧑 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if user_input.lower() == 'test':
                print("\n📝 Test Queries:")
                for i, q in enumerate(test_queries, 1):
                    print(f"{i}. {q}")
                print("\nPick a number or type your own query:")
                continue
            
            # Check if user selected a test query by number
            if user_input.isdigit():
                idx = int(user_input) - 1
                if 0 <= idx < len(test_queries):
                    user_input = test_queries[idx]
                    print(f"Selected: {user_input}")
                else:
                    print("Invalid number")
                    continue
            
            if not user_input:
                continue
            
            # Process with the ReAct agent
            result = react_agent(user_input, verbose=True)
            
            print(f"\n💬 Final: {result}\n")
            print("-"*60)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()