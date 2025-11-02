#!/usr/bin/env python3
"""
Terminal chat interface for ML Engineer Agent with Kaggle integration

Simulates the frontend chat experience in terminal.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add backend to Python path
sys.path.insert(0, str(Path(__file__).parent))

from ml_engineer.agent import MLEngineerAgent

def print_header():
    """Print chat interface header"""
    print("\n" + "=" * 70)
    print("🤖 ML ENGINEER AGENT - TERMINAL CHAT")
    print("=" * 70)
    print("💬 Chat with your ML Engineer Agent")
    print("🏆 Supports Kaggle competitions automatically!")
    print("📝 Just describe what you want and include a Kaggle URL")
    print("-" * 70)

def print_system_message(message):
    """Print system message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{timestamp}] 🖥️  SYSTEM: {message}")

def print_user_message(message):
    """Print user message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{timestamp}] 👤 YOU: {message}")

def print_assistant_message(message):
    """Print assistant message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{timestamp}] 🤖 AGENT: {message}")

def print_step_info(step, description):
    """Print execution step info"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] 🔄 STEP {step}: {description}")

def detect_kaggle_url(message):
    """Detect Kaggle competition URL in message"""
    import re
    
    # More specific patterns to avoid false matches
    patterns = [
        r'https?://(?:www\.)?kaggle\.com/(?:competitions|c)/([^/\s?#]+)',
        r'kaggle\.com/(?:competitions|c)/([^/\s?#]+)',
    ]
    
    # First try URL patterns
    for pattern in patterns:
        matches = re.findall(pattern, message.lower())
        if matches:
            competition_id = matches[0].strip()
            if competition_id and len(competition_id) > 2:
                return competition_id
    
    # Then try known competition names
    known_competitions = [
        'titanic', 
        'house-prices-advanced-regression-techniques',
        'spaceship-titanic',
        'digit-recognizer',
        'nlp-getting-started'
    ]
    
    message_lower = message.lower()
    for comp in known_competitions:
        if comp in message_lower:
            return comp
    
    return None

def get_user_input():
    """Get multiline input from user"""
    print("\n💭 Your prompt (press Enter twice to send, 'quit' to exit):")
    print("-" * 50)
    
    lines = []
    empty_lines = 0
    
    while True:
        try:
            line = input()
            
            if line.lower().strip() == 'quit':
                return None
                
            if line.strip() == '':
                empty_lines += 1
                if empty_lines >= 2:  # Two consecutive empty lines
                    break
            else:
                empty_lines = 0
                lines.append(line)
                
        except KeyboardInterrupt:
            return None
    
    return '\n'.join(lines).strip()

def run_agent_workflow(user_prompt, kaggle_competition=None):
    """Run the agent with logging"""
    
    print_system_message("Initializing ML Engineer Agent...")
    
    # Create agent
    agent = MLEngineerAgent(
        model_name="gpt-4o-mini",
        max_iterations=52,
        verbose=True,  # Show detailed execution
        reasoning_effort="medium"
    )
    
    print_system_message("Agent ready! Starting analysis...")
    print_step_info(1, "Processing your request")
    
    try:
        if kaggle_competition:
            # Kaggle competition mode
            print_system_message(f"🏆 Detected Kaggle competition: {kaggle_competition}")
            print_step_info(2, f"Switching to Kaggle competition mode")
            
            # Create full Kaggle URL if just ID provided
            if not kaggle_competition.startswith('http'):
                kaggle_url = f"https://www.kaggle.com/competitions/{kaggle_competition}"
            else:
                kaggle_url = kaggle_competition
            
            print_step_info(3, f"Running Kaggle workflow for: {kaggle_url}")
            print_system_message("This will download data, build models, and generate submissions")
            print("-" * 70)
            
            # Run Kaggle workflow
            result = agent.run_kaggle_competition(kaggle_url, user_prompt)
            
        else:
            # Standard dataset mode
            print_system_message("No Kaggle competition detected - using standard mode")
            print_step_info(2, "Note: Upload CSV files first for dataset analysis")
            print_step_info(3, "Running standard ML workflow")
            print("-" * 70)
            
            # Run standard workflow  
            result = agent.run(user_prompt)
        
        # Show results
        print("\n" + "=" * 70)
        print("🎉 AGENT EXECUTION COMPLETED!")
        print("=" * 70)
        
        # Show execution summary
        print_assistant_message("Task completed successfully!")
        
        if result.get('solution'):
            print(f"\n📋 SOLUTION:\n{result['solution']}")
        
        # Show artifacts
        artifacts_dir = result.get('artifacts_dir')
        if artifacts_dir and Path(artifacts_dir).exists():
            print(f"\n📁 GENERATED ARTIFACTS:")
            artifacts_path = Path(artifacts_dir)
            for file in sorted(artifacts_path.iterdir()):
                if file.is_file():
                    size = file.stat().st_size
                    if 'submission' in file.name.lower():
                        print(f"   🎯 {file.name} ({size} bytes) <- SUBMISSION FILE")
                    elif file.suffix == '.png':
                        print(f"   📊 {file.name} ({size} bytes)")
                    elif file.suffix == '.ipynb':
                        print(f"   📓 {file.name} ({size} bytes)")
                    else:
                        print(f"   📄 {file.name} ({size} bytes)")
        
        # Show execution stats
        print(f"\n📊 EXECUTION STATS:")
        print(f"   Run ID: {result.get('run_id')}")
        print(f"   Iterations: {result.get('iterations')}")
        print(f"   Artifacts: {artifacts_dir}")
        if kaggle_competition:
            print(f"   Competition: {result.get('kaggle_competition_id')}")
        
        return True
        
    except KeyboardInterrupt:
        print_system_message("⚠️ Execution interrupted by user")
        return False
    except Exception as e:
        import traceback
        print_system_message(f"❌ Error: {str(e)}")
        print_system_message(f"📝 Full error details:")
        print(traceback.format_exc())
        return False

def show_example_prompts():
    """Show example prompts to help user"""
    print("\n💡 EXAMPLE PROMPTS:")
    print("-" * 40)
    
    print("\n🏆 KAGGLE COMPETITION EXAMPLES:")
    print("""
1. "Solve the Titanic competition https://www.kaggle.com/competitions/titanic
   Build a classification model to predict passenger survival. Focus on feature 
   engineering and try multiple algorithms."

2. "I want to compete in house-prices-advanced-regression-techniques
   Build an ensemble model using advanced techniques. Optimize for RMSE."

3. "Help me with https://www.kaggle.com/c/spaceship-titanic
   This is a sci-fi classification problem. Use creative feature engineering."
""")
    
    print("\n📊 DATASET ANALYSIS EXAMPLES:")
    print("""
1. "Analyze my sales dataset and build a forecasting model. Focus on seasonal 
   patterns and provide business insights."

2. "I have customer data - help me segment customers and predict churn. 
   Create visualizations and recommendations."

3. "Build a recommendation system for my e-commerce data. Use collaborative 
   filtering and content-based approaches."
""")

def main():
    """Main chat loop"""
    
    print_header()
    show_example_prompts()
    
    print(f"\n🚀 Ready to chat! (Type 'quit' to exit)")
    
    while True:
        # Get user input
        user_prompt = get_user_input()
        
        if user_prompt is None:
            print_system_message("Goodbye! 👋")
            break
            
        if not user_prompt.strip():
            print_system_message("Please enter a prompt")
            continue
        
        print_user_message(user_prompt)
        
        # Detect Kaggle competition
        kaggle_competition = detect_kaggle_url(user_prompt)
        
        if kaggle_competition:
            print_system_message(f"🎯 Kaggle competition detected: {kaggle_competition}")
            
        # Run agent
        success = run_agent_workflow(user_prompt, kaggle_competition)
        
        if success:
            print(f"\n{'='*70}")
            print("✅ Ready for next task! What would you like to do?")
        else:
            print(f"\n{'='*70}")
            print("❌ Something went wrong. Try a different approach?")

if __name__ == "__main__":
    main()
