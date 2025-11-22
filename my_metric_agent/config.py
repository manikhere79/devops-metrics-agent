"""
Configuration management for the DevOps Metrics Agent.

This module provides centralized configuration for database paths, default user,
context compaction settings, and environment variable handling.
"""

import os
from pathlib import Path
from typing import Optional

# Base directory for data storage
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Database paths
SESSIONS_DB_PATH = str(DATA_DIR / "sessions.db")
METRICS_DB_PATH = str(DATA_DIR / "metrics_db.sqlite")
# Use aiosqlite for async SQLite support (required by DatabaseSessionService)
DB_URL = f"sqlite+aiosqlite:///{SESSIONS_DB_PATH}"

# Default user configuration
DEFAULT_USER_ID = "user1"

# Context compaction configuration
COMPACTION_INTERVAL = 5  # Compact every 5 turns
COMPACTION_OVERLAP_SIZE = 2  # Keep 2 previous turns for context

# Model configuration
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# GitHub configuration
GITHUB_PAT_ENV = "GITHUB_PAT"

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def get_github_token() -> Optional[str]:
    """
    Retrieve GitHub Personal Access Token from environment.
    
    Returns:
        GitHub PAT if available, None otherwise
    """
    return os.getenv(GITHUB_PAT_ENV)


def get_model_name() -> str:
    """
    Get the Gemini model name from environment or default.
    
    Returns:
        Model name string
    """
    return DEFAULT_MODEL


def ensure_data_directory() -> None:
    """
    Ensure the data directory exists for database storage.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

