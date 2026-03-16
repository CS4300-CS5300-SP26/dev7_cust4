"""
AI code review script that reads the diff, sends prompt to openAI, and gives feedback
"""

import os
import sys
from openai import OpenAI


def main():
    print("Starting AI Code Review...")
    
    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set!")
        with open("feedback.md", "w") as f:
            f.write("# AI Code Review\n\n")
            f.write("Error: OpenAI API key not configured. Please add OPENAI_API_KEY to GitHub Secrets.")
        sys.exit(1)
    
    # Read the diff file
    try:
        with open("diff.txt", "r") as f:
            diff_content = f.read()
        
        if not diff_content.strip():
            print("Warning: diff.txt is empty")
            with open("feedback.md", "w") as f:
                f.write("# AI Code Review\n\nNo code changes to review in this pull request.")
            sys.exit(0)
            
    except FileNotFoundError:
        print("Error: diff.txt not found!")
        with open("feedback.md", "w") as f:
            f.write("# AI Code Review\n\nError: Could not find diff.txt. Make sure the 'Get PR Diff' step ran successfully.")
        sys.exit(1)
    
    # Truncate if too long (OpenAI has token limits)
    if len(diff_content) > 5000:
        print(f"Diff is large ({len(diff_content)} chars), truncating...")
        diff_content = diff_content[:5000] + "\n\n...[diff truncated due to length]..."
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Prepare the prompt
    prompt = f"""You are an expert code reviewer. Review the following code changes:

{diff_content}

Please provide feedback on:
- Potential bugs or errors
- Code quality issues
- Security concerns
- Performance improvements
- Suggestions for better practices

Format your response in Markdown."""

    # Get review from OpenAI
    try:
        print("Sending to OpenAI for review...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert code reviewer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        review = response.choices[0].message.content
        print("Received review from OpenAI")
        
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        review = f"Error generating AI review: {str(e)}"
    
    # Write feedback to file
    with open("feedback.md", "w") as f:
        f.write("# AI Code Review\n\n")
        f.write(review)
    
    print("AI Code Review complete - feedback.md written")

if __name__ == "__main__":
    main()

