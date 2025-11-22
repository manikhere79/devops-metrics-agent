#!/usr/bin/env python3
"""
Memory Inspection Script - Utility to query and display information from persistent memory.

This script provides a command-line interface to inspect the contents of the
AuthMemoryTool SQLite database, including user configurations, GitHub PAT status,
and tracked repositories.

Usage:
    python scripts/inspect_memory.py --user user1 --no-token
    python scripts/inspect_memory.py --all-users
    python scripts/inspect_memory.py --repos-only --user user1
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path to import my_metric_agent
sys.path.insert(0, str(Path(__file__).parent.parent))

from my_metric_agent.tools.auth_memory import AuthMemoryTool, UserConfig
from my_metric_agent.config import DEFAULT_USER_ID


def format_token(token: str, hide: bool = False) -> str:
    """
    Format token for display, optionally hiding it.
    
    Args:
        token: Token string to format
        hide: If True, hide the token value
    
    Returns:
        Formatted token string
    """
    if not token:
        return "(not set)"
    
    if hide:
        if len(token) > 8:
            return f"{token[:4]}...{token[-4:]} (hidden)"
        return "**** (hidden)"
    
    return token


def display_user_config(user_id: str, auth_memory_tool: AuthMemoryTool, hide_token: bool = False) -> None:
    """
    Display configuration for a specific user.
    
    Args:
        user_id: User identifier
        auth_memory_tool: AuthMemoryTool instance
        hide_token: Whether to hide the token value
    """
    print(f"\n{'=' * 60}")
    print(f"User Configuration: {user_id}")
    print(f"{'=' * 60}")
    
    try:
        config = auth_memory_tool.get_user_config(user_id)
        
        print(f"User ID:        {user_id}")
        print(f"GitHub PAT:     {format_token(config.token, hide_token)}")
        print(f"Tracked Repos:  {len(config.repos)}")
        
        if config.repos:
            print("\nTracked Repositories:")
            for i, repo in enumerate(config.repos, 1):
                print(f"  {i}. {repo}")
        else:
            print("\nNo tracked repositories.")
        
        print()
    except Exception as e:
        print(f"Error retrieving config for user {user_id}: {e}", file=sys.stderr)
        sys.exit(1)


def display_all_users(auth_memory_tool: AuthMemoryTool, hide_token: bool = False) -> None:
    """
    Display configuration for all users.
    
    Args:
        auth_memory_tool: AuthMemoryTool instance
        hide_token: Whether to hide token values
    """
    print(f"\n{'=' * 60}")
    print("All Users")
    print(f"{'=' * 60}")
    
    try:
        users = auth_memory_tool.list_all_users()
        
        if not users:
            print("No users found in database.")
            return
        
        print(f"Total users: {len(users)}\n")
        
        for user_id in users:
            display_user_config(user_id, auth_memory_tool, hide_token)
    except Exception as e:
        print(f"Error listing users: {e}", file=sys.stderr)
        sys.exit(1)


def display_repos_only(user_id: str, auth_memory_tool: AuthMemoryTool) -> None:
    """
    Display only tracked repositories for a user.
    
    Args:
        user_id: User identifier
        auth_memory_tool: AuthMemoryTool instance
    """
    print(f"\nTracked Repositories for {user_id}:")
    print(f"{'=' * 60}")
    
    try:
        repos = auth_memory_tool.get_tracked_repos(user_id)
        
        if not repos:
            print("No tracked repositories.")
            return
        
        for i, repo in enumerate(repos, 1):
            print(f"  {i}. {repo}")
        print()
    except Exception as e:
        print(f"Error retrieving repos for user {user_id}: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for the memory inspection script."""
    parser = argparse.ArgumentParser(
        description="Inspect persistent memory (AuthMemoryTool SQLite database)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show user1 config with hidden token
  python scripts/inspect_memory.py --user user1 --no-token
  
  # List all users
  python scripts/inspect_memory.py --all-users
  
  # Show only tracked repos for user1
  python scripts/inspect_memory.py --repos-only --user user1
        """
    )
    
    parser.add_argument(
        "--user",
        type=str,
        default=DEFAULT_USER_ID,
        help=f"User ID to inspect (default: {DEFAULT_USER_ID})"
    )
    
    parser.add_argument(
        "--all-users",
        action="store_true",
        help="List all users in the database"
    )
    
    parser.add_argument(
        "--repos-only",
        action="store_true",
        help="Show only tracked repositories (no token info)"
    )
    
    parser.add_argument(
        "--no-token",
        action="store_true",
        help="Hide token values for security"
    )
    
    args = parser.parse_args()
    
    # Initialize AuthMemoryTool
    try:
        auth_memory_tool = AuthMemoryTool()
    except Exception as e:
        print(f"Error initializing AuthMemoryTool: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Execute based on arguments
    try:
        if args.all_users:
            display_all_users(auth_memory_tool, args.no_token)
        elif args.repos_only:
            display_repos_only(args.user, auth_memory_tool)
        else:
            display_user_config(args.user, auth_memory_tool, args.no_token)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

