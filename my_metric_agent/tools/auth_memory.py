"""
AuthMemoryTool - Custom tool for persistent storage of GitHub PAT and tracked repositories.

This tool provides SQLite-based persistent storage for user configurations including
GitHub Personal Access Tokens and tracked repository lists. Data persists across
sessions and application restarts.
"""

import os
import json
import logging
from sqlite_utils import Database
from pydantic import BaseModel
from typing import List, Optional

from my_metric_agent.config import METRICS_DB_PATH, ensure_data_directory

# Set up logging
logger = logging.getLogger(__name__)

# Get the DB path from config
DB_FILE = METRICS_DB_PATH


class UserConfig(BaseModel):
    """Pydantic model for structured user configuration."""
    token: str
    repos: List[str]


class AuthMemoryTool:
    """
    Custom tool for persistent storage of PAT and tracked repositories.
    
    This class manages SQLite-based storage for user configurations. It provides
    methods to save and retrieve GitHub PAT tokens and tracked repository lists
    that persist across sessions.
    """

    def __init__(self):
        """
        Initialize AuthMemoryTool with SQLite database.
        
        Creates the database file and user_config table if they don't exist.
        """
        logger.info(f"Initializing AuthMemoryTool with database: {DB_FILE}")
        ensure_data_directory()
        
        # Initialize database and table (user_id is the primary key)
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        self.db = Database(DB_FILE)
        self.db["user_config"].create(
            {"user_id": str, "token": str, "repos": str},
            pk="user_id",
            if_not_exists=True
        )
        logger.info("AuthMemoryTool initialized successfully")

    def save_initial_config(self, user_id: str, token: Optional[str] = None) -> str:
        """
        Save the GitHub PAT from environment or provided token to persistent storage.
        
        Args:
            user_id: User identifier (e.g., "user1")
            token: Optional GitHub PAT. If not provided, reads from GITHUB_PAT env var.
        
        Returns:
            Success or error message string
        """
        logger.info(f"Saving initial config for user: {user_id}")
        
        # Get token from parameter or environment
        pat = token or os.getenv("GITHUB_PAT")
        
        if not pat:
            error_msg = "Error: GITHUB_PAT environment variable is not set and no token provided."
            logger.warning(error_msg)
            return error_msg
        
        try:
            # Store configuration
            self.db["user_config"].insert(
                {
                    "user_id": user_id,
                    "token": pat,
                    "repos": json.dumps([])
                },
                replace=True
            )
            logger.info(f"GitHub PAT successfully saved for user: {user_id}")
            return "GitHub PAT successfully loaded and saved to persistent memory."
        except Exception as e:
            error_msg = f"Error saving config: {e}"
            logger.error(error_msg, exc_info=True)
            return error_msg

    def get_user_config(self, user_id: str) -> UserConfig:
        """
        Retrieve the user's PAT and tracked repositories.
        
        Args:
            user_id: User identifier
        
        Returns:
            UserConfig object with token and repos list
        """
        logger.debug(f"Retrieving config for user: {user_id}")
        
        try:
            config = self.db["user_config"].get(user_id)
            if config:
                # Parse JSON string from DB
                repos = json.loads(config["repos"]) if config["repos"] else []
                logger.debug(f"Found config for user {user_id} with {len(repos)} tracked repos")
                return UserConfig(token=config["token"], repos=repos)
        except Exception as e:
            # NotFoundError is expected for new users, don't log as error
            from sqlite_utils.db import NotFoundError
            if isinstance(e, NotFoundError):
                logger.debug(f"No config found for user: {user_id} (new user)")
            else:
                logger.error(f"Error retrieving config for user {user_id}: {e}", exc_info=True)
        
        # Return empty/default config if not found
        logger.debug(f"No config found for user: {user_id}")
        return UserConfig(token="", repos=[])

    def add_tracked_repo(self, repo_name: str, user_id: str) -> str:
        """
        Add a new repository to the user's tracked list.
        
        Args:
            repo_name: Full repository name (e.g., "owner/repo")
            user_id: User identifier
        
        Returns:
            Success or error message string
        """
        logger.info(f"Adding tracked repo '{repo_name}' for user: {user_id}")
        
        try:
            config = self.db["user_config"].get(user_id)
            if not config:
                error_msg = "Configuration not found. Please run authentication first."
                logger.warning(error_msg)
                return error_msg
            
            # Parse existing repos
            repos = json.loads(config["repos"]) if config["repos"] else []
            
            if repo_name not in repos:
                repos.append(repo_name)
                # Update database
                self.db["user_config"].update(user_id, {"repos": json.dumps(repos)})
                logger.info(f"Repository '{repo_name}' added successfully")
                return f"Repository '{repo_name}' is now tracked."
            else:
                logger.debug(f"Repository '{repo_name}' already tracked")
                return f"Repository '{repo_name}' is already tracked."
        except Exception as e:
            error_msg = f"Error adding tracked repo: {e}"
            logger.error(error_msg, exc_info=True)
            return error_msg

    def get_tracked_repos(self, user_id: str) -> List[str]:
        """
        Get list of tracked repositories for a user.
        
        Args:
            user_id: User identifier
        
        Returns:
            List of repository names
        """
        logger.debug(f"Getting tracked repos for user: {user_id}")
        config = self.get_user_config(user_id)
        return config.repos

    def remove_tracked_repo(self, repo_name: str, user_id: str) -> str:
        """
        Remove a repository from the user's tracked list.
        
        Args:
            repo_name: Full repository name to remove
            user_id: User identifier
        
        Returns:
            Success or error message string
        """
        logger.info(f"Removing tracked repo '{repo_name}' for user: {user_id}")
        
        try:
            config = self.db["user_config"].get(user_id)
            if not config:
                error_msg = "Configuration not found."
                logger.warning(error_msg)
                return error_msg
            
            repos = json.loads(config["repos"]) if config["repos"] else []
            
            if repo_name in repos:
                repos.remove(repo_name)
                self.db["user_config"].update(user_id, {"repos": json.dumps(repos)})
                logger.info(f"Repository '{repo_name}' removed successfully")
                return f"Repository '{repo_name}' is no longer tracked."
            else:
                logger.debug(f"Repository '{repo_name}' not found in tracked repos")
                return f"Repository '{repo_name}' is not in the tracked list."
        except Exception as e:
            error_msg = f"Error removing tracked repo: {e}"
            logger.error(error_msg, exc_info=True)
            return error_msg

    def list_all_users(self) -> List[str]:
        """
        List all user IDs in the database.
        
        Returns:
            List of user IDs
        """
        logger.debug("Listing all users")
        try:
            users = [row["user_id"] for row in self.db["user_config"].rows]
            logger.debug(f"Found {len(users)} users")
            return users
        except Exception as e:
            logger.error(f"Error listing users: {e}", exc_info=True)
            return []
