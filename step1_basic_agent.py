import os
import re
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configuration
MODEL = "gpt-3.5-turbo"  # or "gpt-4o-mini" for better reasoning

# The "brain" of our agent
SYSTEM_PROMPT = """You are a helpful assistant that thinks step by step.

For EVERY query, you MUST follow this exact format:

Thought: [Think about what the user is asking]
Answer: [Provide your answer]

Example:
Human: What is the capital of France?
Thought: The user is asking about the capital city of France. This is a straightforward geography question.
Answer: The capital of France is Paris.

Now you try:"""

def parse_agent_response(response):
    """Extract thought and answer from the response"""
    
    thought_match = re.search(r'Thought: (.*?)(?=Answer:|$)', response, re.DOTALL)
    answer_match = re.search(r'Answer: (.*?)$', response, re.DOTALL)
    
    thought = thought_match.group(1).strip() if thought_match else None
    answer = answer_match.group(1).strip() if answer_match else None
    
    return {
        'thought': thought,
        'answer': answer,
        'raw': response
    }

def simple_agent(user_query, verbose=True):
    """Basic agent that thinks and answers"""
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_query}
            ],
            temperature=0
        )
        
        agent_response = response.choices[0].message.content
        parsed = parse_agent_response(agent_response)
        
        if verbose:
            print("="*50)
            print(f"🤔 Thought: {parsed['thought']}")
            print(f"💡 Answer: {parsed['answer']}")
            print("="*50)
        
        return parsed
        
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    """Interactive ReAct Agent with clean display"""
    
    print("="*60)
    print(f"🤖 Basic ReAct Agent (using {MODEL})")
    print("="*60)
    print("Commands: 'quit' to exit | 'help' for examples | 'clear' to clear screen")
    print("-"*60)
    
    import os  # For clearing screen
    
    conversation_history = []
    
    while True:
        try:
            # Get user input
            user_input = input("\n🧑 You: ").strip()
            
            # Check for commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if user_input.lower() == 'help':
                print("\n📚 Example queries:")
                print("  • What is 2 + 2?")
                print("  • Why is the sky blue?")
                print("  • What's the capital of Japan?")
                print("  • Explain how airplanes fly")
                print("  • What's 15% of 250?")
                continue
            
            if user_input.lower() == 'clear':
                os.system('cls' if os.name == 'nt' else 'clear')
                print("🤖 Basic ReAct Agent")
                print("-"*60)
                continue
            
            if not user_input:
                continue
            
            # Show thinking indicator
            print("\n⏳ Thinking...", end='', flush=True)
            
            # Get response
            result = simple_agent(user_input, verbose=False)  # Set verbose=False for cleaner output
            
            # Clear thinking indicator and show response
            print("\r" + " "*50 + "\r", end='')  # Clear the "Thinking..." line
            
            # Display formatted response
            print("\n🤖 Agent:")
            print(f"   💭 {result['thought']}")
            print(f"   💡 {result['answer']}")
            
            # Store in history
            conversation_history.append({
                'query': user_input,
                'thought': result['thought'],
                'answer': result['answer']
            })
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted! Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()