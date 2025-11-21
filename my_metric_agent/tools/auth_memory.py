import os
import json
from google.adk import CustomTool # FIX: Assuming CustomTool is available at the base level
from sqlite_utils import Database
from pydantic import BaseModel
from typing import List

# Get the DB path from the environment defined in docker_compose
DB_FILE = os.environ.get("DB_FILE_PATH", "data/metrics_db.sqlite")

class AuthMemoryTool(CustomTool):
    """Custom tool for persistent storage of PAT and tracked repositories."""

    def __init__(self):
        # Good practice: initialize parent with name/description
        super().__init__(name="AuthMemoryTool", description="Manages GitHub PAT and tracked repositories in persistent storage")
        
        # Initialize database and table (user_id is the primary key)
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        self.db = Database(DB_FILE)
        self.db["user_config"].create({
            "user_id": str, "token": str, "repos": str
        }, pk="user_id", if_not_exists=True)

    def save_initial_config(self, user_id: str = "default_user") -> str:
        """Saves the GitHub PAT from the environment to the long-term storage."""
        pat = os.getenv("GITHUB_PAT")

        if not pat:
            return "Error: GITHUB_PAT environment variable is not set."
        
        # Stores configuration
        self.db["user_config"].insert({
            "user_id": user_id,
            "token": pat,
            "repos": json.dumps([])
        }, replace=True)

        return "GitHub PAT successfully loaded and saved to persistent memory."
    
    # Pydantic model for structured output/input
    class UserConfig(BaseModel):
        token: str
        repos: List[str]

    def get_user_config(self, user_id: str = "default_user") -> UserConfig:
        """Retrieves the user's PAT and tracked repositories."""
        
        config = self.db["user_config"].get(user_id)
        if config:
            # FIX: Use json.loads to parse JSON string from DB
            return self.UserConfig(token=config["token"], repos=json.loads(config["repos"]))

        # Return empty/default config if not found
        return self.UserConfig(token="", repos=[])
    
    def add_tracked_repo(self, repo_name: str, user_id: str = "default_user") -> str:
        """Adds a new repository to the user's tracked list."""
        config = self.db["user_config"].get(user_id)
        if not config:
            return "Configuration not found. Please run authentication first."
        
        # FIX: Use json.loads to parse JSON string from DB
        repos = json.loads(config["repos"])
        if repo_name not in repos:
            repos.append(repo_name)
            # FIX: Use colon (:) and json.dumps
            self.db["user_config"].update(user_id, {"repos": json.dumps(repos)}) 
            return f"Repository '{repo_name}' is now tracked."
        return f"Repository '{repo_name}' is already tracked."