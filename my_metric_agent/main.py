"""
Main entry point for the DevOps Metrics Agent application.

This module initializes the root agent, sets up persistent session management
with context compaction, and provides the entry point for `adk web .` command.
"""

import logging
import sys
from dotenv import load_dotenv

from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService

from my_metric_agent.config import (
    DB_URL,
    DEFAULT_USER_ID,
    COMPACTION_INTERVAL,
    COMPACTION_OVERLAP_SIZE,
    get_github_token,
    ensure_data_directory,
    LOG_LEVEL,
    LOG_FORMAT,
)
from my_metric_agent.agent import create_root_agent
from my_metric_agent.tools.auth_memory import AuthMemoryTool

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def initialize_default_user(auth_memory_tool: AuthMemoryTool) -> None:
    """
    Initialize default user configuration.
    
    Checks if user1 config exists, and if GITHUB_PAT is available in environment,
    automatically sets up GitHub configuration.
    
    Args:
        auth_memory_tool: AuthMemoryTool instance for persistent storage
    """
    logger.info(f"Initializing default user: {DEFAULT_USER_ID}")
    
    try:
        # Check if user config already exists
        user_config = auth_memory_tool.get_user_config(DEFAULT_USER_ID)
        
        if user_config.token:
            logger.info(f"User {DEFAULT_USER_ID} already has GitHub PAT configured")
            return
        
        # Try to setup GitHub config from environment
        github_token = get_github_token()
        if github_token:
            logger.info(f"Found GITHUB_PAT in environment, setting up for {DEFAULT_USER_ID}")
            result = auth_memory_tool.save_initial_config(DEFAULT_USER_ID, github_token)
            if "Error" not in result:
                logger.info(f"Successfully initialized GitHub config for {DEFAULT_USER_ID}")
            else:
                logger.warning(f"Failed to initialize GitHub config: {result}")
        else:
            logger.info(f"No GITHUB_PAT found in environment for {DEFAULT_USER_ID}")
            logger.info("User can setup GitHub config later via the agent")
    except Exception as e:
        logger.error(f"Error initializing default user: {e}", exc_info=True)


def create_app() -> App:
    """
    Create and configure the ADK App with context compaction.
    
    Returns:
        Configured App instance with root agent and compaction settings
    """
    logger.info("Creating ADK App with context compaction")
    
    # Ensure data directory exists
    ensure_data_directory()
    
    # Initialize AuthMemoryTool
    auth_memory_tool = AuthMemoryTool()
    
    # Initialize default user
    initialize_default_user(auth_memory_tool)
    
    # Create root agent
    root_agent = create_root_agent(auth_memory_tool)
    
    # Create App with EventsCompactionConfig
    app = App(
        name="devops_metrics_app",
        root_agent=root_agent,
        events_compaction_config=EventsCompactionConfig(
            compaction_interval=COMPACTION_INTERVAL,  # Compact every N turns
            overlap_size=COMPACTION_OVERLAP_SIZE,  # Keep N previous turns for context
        ),
    )
    
    logger.info(f"App created with compaction interval: {COMPACTION_INTERVAL}, overlap: {COMPACTION_OVERLAP_SIZE}")
    return app


def create_runner() -> Runner:
    """
    Create Runner with DatabaseSessionService for persistent sessions.
    
    Returns:
        Configured Runner instance
    """
    logger.info("Creating Runner with DatabaseSessionService")
    
    # Ensure data directory exists
    ensure_data_directory()
    
    # Create DatabaseSessionService with SQLite
    session_service = DatabaseSessionService(db_url=DB_URL)
    logger.info(f"DatabaseSessionService initialized with: {DB_URL}")
    
    # Create App
    app = create_app()
    
    # Create Runner
    runner = Runner(
        app=app,
        session_service=session_service,
    )
    
    logger.info("Runner created successfully")
    return runner


def main():
    """
    Main entry point for the application.
    
    This function is called when running `adk web .` or when the module is executed directly.
    """
    logger.info("=" * 60)
    logger.info("DevOps Metrics Agent - Starting Application")
    logger.info("=" * 60)
    
    try:
        # Create runner (this also initializes everything)
        runner = create_runner()
        
        logger.info("Application initialized successfully")
        logger.info(f"Default user: {DEFAULT_USER_ID}")
        logger.info(f"Session DB: {DB_URL}")
        logger.info("=" * 60)
        
        # Return runner for adk web command
        return runner
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}", exc_info=True)
        sys.exit(1)


# Export runner for adk web command
if __name__ == "__main__":
    runner = main()
else:
    # When imported by adk web, create the runner
    runner = create_runner()

