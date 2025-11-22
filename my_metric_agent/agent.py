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
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from my_metric_agent.config import (
    get_model_name, 
    DEFAULT_USER_ID,
    COMPACTION_INTERVAL,
    COMPACTION_OVERLAP_SIZE,
    DB_URL,
    ensure_data_directory,
)
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


# Create module-level agent for internal use
logger.info("Initializing module-level agent for adk web")

# Ensure data directory exists
ensure_data_directory()

# Initialize AuthMemoryTool and create the root agent at module import time
_auth_memory_tool = AuthMemoryTool()
_root_agent = create_root_agent(_auth_memory_tool)

# Export root_agent for adk web (it requires this)
# adk web will wrap this and create a runner, but we also export our own runner below
root_agent = _root_agent

# Create App with EventsCompactionConfig for session management
# Note: We create this internally but don't export it at module level
# because exporting 'app' causes adk web to ignore our 'runner' export
_app = App(
    name="my_metric_agent",
    root_agent=_root_agent,
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=COMPACTION_INTERVAL,  # Compact every N turns
        overlap_size=COMPACTION_OVERLAP_SIZE,  # Keep N previous turns for context
    ),
)

logger.info("Module-level app created with EventsCompactionConfig")


def create_runner_with_persistent_sessions() -> Runner:
    """
    Create a runner with DatabaseSessionService for persistent sessions.
    
    This function creates the session service which will initialize lazily
    when first used in an async context.
    
    Returns:
        Runner with DatabaseSessionService
    """
    try:
        logger.info(f"Creating DatabaseSessionService with: {DB_URL}")
        
        # Create DatabaseSessionService - it will initialize lazily on first async use
        session_service = DatabaseSessionService(db_url=DB_URL)
        
        # Create runner with persistent sessions
        runner = Runner(
            app=_app,
            session_service=session_service,
        )
        
        logger.info("Runner created with DatabaseSessionService for persistent sessions")
        return runner
        
    except Exception as e:
        logger.error(f"Failed to create runner with DatabaseSessionService: {e}", exc_info=True)
        logger.warning("Falling back to runner without explicit session service")
        # Fallback to default (InMemorySessionService)
        return Runner(app=_app)


# Create and export runner with DatabaseSessionService
# NOTE: adk web command does NOT use this runner export when root_agent is present.
# To use persistent sessions with adk web, run:
#   adk web . --session_service_uri=sqlite:///path/to/sessions.db
# Or use the helper script: .\scripts\start_adk_web.ps1
#
# This runner export is useful for:
#   1. Custom deployments that import the runner directly
#   2. Testing session persistence programmatically
#   3. Alternative entry points that don't use adk web
runner = create_runner_with_persistent_sessions()
