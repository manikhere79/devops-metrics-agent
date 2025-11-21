import os
import json
import requests
from dotenv import load_dotenv

# --- Correct ADK Imports ---
from google.adk.agents import Agent
# Remove 'from google.adk.tools import tool' - it is not needed/valid

load_dotenv()

# --- 1. Tool Definitions (Standard Functions) ---

def fetch_pr_data(token: str, repo_name: str) -> str:
    """Fetches raw Pull Request data for a given repository.
    
    Args:
        token: GitHub Personal Access Token.
        repo_name: Full repository name (e.g., 'owner/repo').
    """
    # Ensure repo_name is clean
    repo_name = repo_name.strip()
    
    url = f"https://api.github.com/repos/{repo_name}/pulls?state=closed&per_page=10&sort=updated&direction=desc"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        pr_data = []
        for pr in response.json():
            pr_data.append({
                "number": pr["number"],
                "created_at": pr.get("created_at"),
                "merged_at": pr.get("merged_at"),
                "closed_at": pr.get("closed_at"),
            })

        return json.dumps(pr_data)
    except Exception as e:
        return f"Error fetching data for {repo_name}: {e}. Ensure the token has 'repo' scope."

# --- 2. Agent Definition ---

# 2.1. Metric Calculator Agent
metric_calculator_agent = Agent(
    name="MetricCalculatorAgent",
    description="Calculates time-based metrics from raw JSON data.",
    instruction="""
        Your sole purpose is to execute Python code to calculate the average metric (in days or hours) 
        from the raw Pull Request JSON data. Return ONLY the final numerical result as a formatted string.
    """
)

def calculate_metrics_tool(user_prompt: str, raw_pr_data: str) -> str:
    """
    Executes the MetricCalculatorAgent to compute specific DevOps metrics 
    from raw Pull Request JSON data.
    """
    full_instruction = (
        f"The user wants you to calculate the metric based on this prompt: '{user_prompt}'. "
        f"The raw JSON data for the calculation is: ```json\n{raw_pr_data}\n```"
    )
    return metric_calculator_agent.run(full_instruction)

# 2.2. Coordinator Agent (Root Agent)
root_agent = Agent(
    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), 
    name="DevOpsMetricsAssistant",
    description="The primary assistant for tracking GitHub repositories and calculating DevOps metrics.",
    instruction="""
        You are the DevOps Metrics Assistant. 
        
        **WORKFLOW:**
        1. **Metric Request:** Always call `fetch_pr_data` first to get the raw JSON. Ask for the GitHub Token if you don't have it.
        2. **Computation:** Pass that raw JSON data to `calculate_metrics_tool` to get the answer.
    """,
    # Register functions directly in the list
    tools=[
        fetch_pr_data,
        calculate_metrics_tool 
    ]
)