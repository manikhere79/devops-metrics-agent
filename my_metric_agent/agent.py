"""
Root Agent Definition - DevOps Metrics Assistant.

This module defines the main root agent that orchestrates GitHub repository tracking
and DevOps metrics calculation. The agent uses multiple tools for GitHub API interaction,
repository management, and metric calculations.
"""

import logging
from functools import partial
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import AgentTool
from google.genai import types

from my_metric_agent.config import get_model_name, DEFAULT_USER_ID
from my_metric_agent.tools.github_tools import (
    setup_github_config,
    add_tracked_repo,
    get_tracked_repos,
    fetch_pr_data,
    fetch_cycle_time_data,
    fetch_pr_review_data,
)
from my_metric_agent.tools.metrics_tools import calculate_metrics_tool
from my_metric_agent.tools.auth_memory import AuthMemoryTool

# Set up logging
logger = logging.getLogger(__name__)

# Configure retry options for LLM calls
retry_config = types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],  # Retry on these HTTP errors
)


def create_root_agent(auth_memory_tool: AuthMemoryTool) -> LlmAgent:
    """
    Create the root agent with all tools registered.
    
    This function creates a root agent that orchestrates GitHub repository tracking
    and DevOps metrics calculation. All tools are bound with the AuthMemoryTool instance.
    
    Args:
        auth_memory_tool: AuthMemoryTool instance for persistent storage
    
    Returns:
        Configured LlmAgent instance
    """
    logger.info("Creating root agent with all tools")
    
    # Create wrapper functions that bind auth_memory_tool
    # These wrappers match the function signatures expected by ADK tools
    
    def setup_github_config_wrapper(tool_context, user_id: str = DEFAULT_USER_ID):
        """Wrapper for setup_github_config tool."""
        return setup_github_config(tool_context, auth_memory_tool, user_id)
    
    def add_tracked_repo_wrapper(tool_context, repo_name: str, user_id: str = DEFAULT_USER_ID):
        """Wrapper for add_tracked_repo tool."""
        return add_tracked_repo(tool_context, repo_name, auth_memory_tool, user_id)
    
    def get_tracked_repos_wrapper(tool_context, user_id: str = DEFAULT_USER_ID):
        """Wrapper for get_tracked_repos tool."""
        return get_tracked_repos(tool_context, auth_memory_tool, user_id)
    
    def fetch_pr_data_wrapper(tool_context, repo_name: str, user_id: str = DEFAULT_USER_ID, per_page: int = 10):
        """Wrapper for fetch_pr_data tool."""
        return fetch_pr_data(tool_context, repo_name, auth_memory_tool, user_id, per_page)
    
    def fetch_cycle_time_data_wrapper(tool_context, repo_name: Optional[str] = None, user_id: str = DEFAULT_USER_ID):
        """Wrapper for fetch_cycle_time_data tool."""
        return fetch_cycle_time_data(tool_context, repo_name, auth_memory_tool, user_id)
    
    def fetch_pr_review_data_wrapper(tool_context, repo_name: Optional[str] = None, user_id: str = DEFAULT_USER_ID, pr_number: Optional[int] = None):
        """Wrapper for fetch_pr_review_data tool."""
        return fetch_pr_review_data(tool_context, repo_name, auth_memory_tool, user_id, pr_number)
    
    # Create root agent with all tools
    root_agent = LlmAgent(
        model=Gemini(model=get_model_name(), retry_options=retry_config),
        name="DevOpsMetricsAssistant",
        description="The primary assistant for tracking GitHub repositories and calculating DevOps metrics.",
        instruction="""
        You are the DevOps Metrics Assistant, an intelligent agent that helps track GitHub repositories
        and calculate DevOps metrics like cycle time and PR review time.
        
        **WORKFLOW:**
        
        1. **Initial Setup:**
           - When a user first interacts, check if GitHub configuration exists using `get_tracked_repos`.
           - If no configuration exists, use `setup_github_config` to initialize GitHub PAT from environment.
           - Store the user_id in session state for future reference.
        
        2. **Repository Management:**
           - Users can add repositories for tracking using `add_tracked_repo`.
           - Use `get_tracked_repos` to retrieve the list of tracked repositories.
           - Tracked repositories are persisted across sessions.
        
        3. **Metrics Calculation Requests:**
           When a user asks about metrics (cycle time, PR review time, etc.):
           
           a. **Identify the metric type:**
              - Cycle time: Time from PR creation to merge
              - PR review time: Time from PR creation to first review
              - Other metrics as requested
           
           b. **Fetch the required data:**
              - For cycle time: Use `fetch_cycle_time_data` (or `fetch_pr_data` if specific repo mentioned)
              - For PR review time: Use `fetch_pr_review_data`
              - If no repo specified, use tracked repositories from `get_tracked_repos`
           
           c. **Calculate the metric:**
              - Use the `MetricCalculatorAgent` tool to calculate metrics from raw data
              - Provide a clear prompt with both the user's question and the JSON data
              - The agent will generate and execute Python code to compute the result
              - Return the calculated result to the user
        
        4. **Error Handling:**
           - If GitHub PAT is not configured, guide the user to run setup
           - If no repositories are tracked, suggest adding repositories
           - If API calls fail, provide helpful error messages
        
        5. **Best Practices:**
           - Always check tool response status before proceeding
           - Provide clear explanations of what metrics mean
           - Format results in a user-friendly way
           - Remember user preferences from session state
        
        **IMPORTANT:**
        - Always use the `MetricCalculatorAgent` tool for metric calculations - never calculate manually
        - Store user_id in session state after setup: `tool_context.state["user_id"] = "user1"`
        - Tracked repositories persist across sessions via AuthMemoryTool
        - When invoking MetricCalculatorAgent, provide: "Calculate [metric] from this data: [JSON]"
        """,
        tools=[
            setup_github_config_wrapper,
            add_tracked_repo_wrapper,
            get_tracked_repos_wrapper,
            fetch_pr_data_wrapper,
            fetch_cycle_time_data_wrapper,
            fetch_pr_review_data_wrapper,
            calculate_metrics_tool,  # AgentTool for metric calculations
        ]
    )
    
    logger.info("Root agent created successfully")
    return root_agent


# Create module-level root_agent for adk web command
# This is required because adk web expects 'my_metric_agent.agent.root_agent' to exist
# Initialize AuthMemoryTool and create the root agent at module import time
_auth_memory_tool = AuthMemoryTool()
root_agent = create_root_agent(_auth_memory_tool)
