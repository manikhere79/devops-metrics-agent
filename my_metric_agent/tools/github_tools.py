"""
GitHub Tools - Tools for interacting with GitHub API and managing repository tracking.

These tools use ToolContext to access session state and AuthMemoryTool for
persistent storage of GitHub credentials and tracked repositories.
"""

import json
import logging
import requests
from typing import Dict, Any, Optional

from google.adk.tools.tool_context import ToolContext

from my_metric_agent.tools.auth_memory import AuthMemoryTool

# Set up logging
logger = logging.getLogger(__name__)


def setup_github_config(tool_context: ToolContext, auth_memory_tool: AuthMemoryTool, user_id: str = "user1") -> Dict[str, Any]:
    """
    Initialize GitHub PAT from environment and save via AuthMemoryTool.
    
    This tool reads the GITHUB_PAT environment variable and stores it in
    persistent memory for the specified user.
    
    Args:
        tool_context: ADK ToolContext providing access to session state
        auth_memory_tool: AuthMemoryTool instance for persistent storage
        user_id: User identifier (default: "user1")
    
    Returns:
        Dictionary with status and message
    """
    logger.info(f"Setting up GitHub config for user: {user_id}")
    
    try:
        result = auth_memory_tool.save_initial_config(user_id)
        
        if "Error" in result:
            logger.warning(f"Failed to setup GitHub config: {result}")
            return {"status": "error", "message": result}
        
        logger.info(f"GitHub config setup successful for user: {user_id}")
        # Store user_id in session state for future reference
        tool_context.state["user_id"] = user_id
        return {"status": "success", "message": result}
    except Exception as e:
        error_msg = f"Error setting up GitHub config: {e}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "message": error_msg}


def add_tracked_repo(
    tool_context: ToolContext,
    repo_name: str,
    auth_memory_tool: AuthMemoryTool,
    user_id: str = "user1"
) -> Dict[str, Any]:
    """
    Add a repository to the tracking list.
    
    The repository name is persisted to SQLite storage via AuthMemoryTool
    and will be available across sessions.
    
    Args:
        tool_context: ADK ToolContext providing access to session state
        repo_name: Full repository name (e.g., "owner/repo")
        auth_memory_tool: AuthMemoryTool instance for persistent storage
        user_id: User identifier (default: "user1")
    
    Returns:
        Dictionary with status and message
    """
    logger.info(f"Adding tracked repo '{repo_name}' for user: {user_id}")
    
    # Get user_id from session state if available, otherwise use parameter
    user_id = tool_context.state.get("user_id", user_id)
    
    try:
        result = auth_memory_tool.add_tracked_repo(repo_name, user_id)
        
        if "Error" in result or "not found" in result.lower():
            logger.warning(f"Failed to add tracked repo: {result}")
            return {"status": "error", "message": result}
        
        logger.info(f"Successfully added tracked repo: {repo_name}")
        return {"status": "success", "message": result}
    except Exception as e:
        error_msg = f"Error adding tracked repo: {e}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "message": error_msg}


def get_tracked_repos(
    tool_context: ToolContext,
    auth_memory_tool: AuthMemoryTool,
    user_id: str = "user1"
) -> Dict[str, Any]:
    """
    Retrieve tracked repositories from persistent memory.
    
    Args:
        tool_context: ADK ToolContext providing access to session state
        auth_memory_tool: AuthMemoryTool instance for persistent storage
        user_id: User identifier (default: "user1")
    
    Returns:
        Dictionary with status and list of repositories
    """
    logger.debug(f"Getting tracked repos for user: {user_id}")
    
    # Get user_id from session state if available
    user_id = tool_context.state.get("user_id", user_id)
    
    try:
        repos = auth_memory_tool.get_tracked_repos(user_id)
        logger.info(f"Found {len(repos)} tracked repos for user: {user_id}")
        return {
            "status": "success",
            "repos": repos,
            "count": len(repos)
        }
    except Exception as e:
        error_msg = f"Error getting tracked repos: {e}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "message": error_msg, "repos": []}


def fetch_pr_data(
    tool_context: ToolContext,
    repo_name: str,
    auth_memory_tool: AuthMemoryTool,
    user_id: str = "user1",
    per_page: int = 10,
    state: str = "all"
) -> Dict[str, Any]:
    """
    Fetch Pull Request data from GitHub API for a given repository.
    
    Retrieves the GitHub PAT from persistent storage and uses it to fetch
    PR data from the GitHub API.
    
    Args:
        tool_context: ADK ToolContext providing access to session state
        repo_name: Full repository name (e.g., "owner/repo")
        auth_memory_tool: AuthMemoryTool instance for persistent storage
        user_id: User identifier (default: "user1")
        per_page: Number of PRs to fetch (default: 10)
        state: PR state filter - "open", "closed", or "all" (default: "all")
    
    Returns:
        Dictionary with status and PR data (JSON string)
    """
    logger.info(f"Fetching PR data for repo: {repo_name}")
    
    # Get user_id from session state if available
    user_id = tool_context.state.get("user_id", user_id)
    
    try:
        # Get GitHub token from persistent storage
        user_config = auth_memory_tool.get_user_config(user_id)
        
        if not user_config.token:
            error_msg = "GitHub PAT not configured. Please run setup_github_config first."
            logger.warning(error_msg)
            return {"status": "error", "message": error_msg}
        
        # Ensure repo_name is clean
        repo_name = repo_name.strip()
        
        # Fetch PR data from GitHub API
        url = f"https://api.github.com/repos/{repo_name}/pulls"
        params = {
            "state": state,
            "per_page": per_page,
            "sort": "updated",
            "direction": "desc"
        }
        headers = {
            "Authorization": f"token {user_config.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        logger.debug(f"Making GitHub API request to: {url}")
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        pr_data = []
        for pr in response.json():
            pr_data.append({
                "number": pr["number"],
                "title": pr.get("title", ""),
                "created_at": pr.get("created_at"),
                "merged_at": pr.get("merged_at"),
                "closed_at": pr.get("closed_at"),
                "state": pr.get("state"),
                "user": pr.get("user", {}).get("login", "") if pr.get("user") else ""
            })
        
        logger.info(f"Successfully fetched {len(pr_data)} PRs for repo: {repo_name}")
        return {
            "status": "success",
            "data": json.dumps(pr_data),
            "count": len(pr_data)
        }
    except requests.exceptions.RequestException as e:
        error_msg = f"Error fetching PR data for {repo_name}: {e}. Ensure the token has 'repo' scope."
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "message": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error fetching PR data: {e}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "message": error_msg}


def fetch_cycle_time_data(
    tool_context: ToolContext,
    repo_name: Optional[str] = None,
    auth_memory_tool: Optional[AuthMemoryTool] = None,
    user_id: str = "user1"
) -> Dict[str, Any]:
    """
    Fetch data needed for cycle time calculation.
    
    Cycle time is the time from when work starts (branch creation or first commit)
    until it's merged. This fetches PRs with their creation and merge times.
    
    Args:
        tool_context: ADK ToolContext providing access to session state
        repo_name: Optional repository name. If not provided, uses tracked repos.
        auth_memory_tool: AuthMemoryTool instance for persistent storage
        user_id: User identifier (default: "user1")
    
    Returns:
        Dictionary with status and cycle time data
    """
    logger.info(f"Fetching cycle time data for repo: {repo_name}")
    
    # Get user_id from session state if available
    user_id = tool_context.state.get("user_id", user_id)
    
    # If repo_name not provided, get from tracked repos
    if not repo_name:
        if not auth_memory_tool:
            error_msg = "auth_memory_tool required when repo_name not provided"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        
        repos = auth_memory_tool.get_tracked_repos(user_id)
        if not repos:
            error_msg = "No tracked repositories found. Please add repositories first."
            logger.warning(error_msg)
            return {"status": "error", "message": error_msg}
        
        # Use first tracked repo or combine data from all repos
        repo_name = repos[0]
        logger.info(f"Using tracked repo: {repo_name}")
    
    # Fetch PR data (cycle time uses same data as PR data)
    return fetch_pr_data(tool_context, repo_name, auth_memory_tool, user_id, per_page=50)


def fetch_pr_review_data(
    tool_context: ToolContext,
    repo_name: Optional[str] = None,
    auth_memory_tool: Optional[AuthMemoryTool] = None,
    user_id: str = "user1",
    pr_number: Optional[int] = None,
    state: str = "all"
) -> Dict[str, Any]:
    """
    Fetch PR review time data from GitHub API.
    
    PR review time is calculated from when PR is opened until first approval/review.
    This fetches PR details including review events.
    
    Args:
        tool_context: ADK ToolContext providing access to session state
        repo_name: Optional repository name. If not provided, uses tracked repos.
        auth_memory_tool: AuthMemoryTool instance for persistent storage
        user_id: User identifier (default: "user1")
        pr_number: Optional specific PR number. If not provided, fetches multiple PRs.
        state: PR state filter - "open", "closed", or "all" (default: "all")
    
    Returns:
        Dictionary with status and review time data
    """
    logger.info(f"Fetching PR review data for repo: {repo_name}, PR: {pr_number}")
    
    # Get user_id from session state if available
    user_id = tool_context.state.get("user_id", user_id)
    
    # If repo_name not provided, get from tracked repos
    if not repo_name:
        if not auth_memory_tool:
            error_msg = "auth_memory_tool required when repo_name not provided"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        
        repos = auth_memory_tool.get_tracked_repos(user_id)
        if not repos:
            error_msg = "No tracked repositories found. Please add repositories first."
            logger.warning(error_msg)
            return {"status": "error", "message": error_msg}
        
        repo_name = repos[0]
        logger.info(f"Using tracked repo: {repo_name}")
    
    try:
        # Get GitHub token from persistent storage
        if not auth_memory_tool:
            error_msg = "auth_memory_tool is required"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        
        user_config = auth_memory_tool.get_user_config(user_id)
        
        if not user_config.token:
            error_msg = "GitHub PAT not configured. Please run setup_github_config first."
            logger.warning(error_msg)
            return {"status": "error", "message": error_msg}
        
        repo_name = repo_name.strip()
        headers = {
            "Authorization": f"token {user_config.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        review_data = []
        
        if pr_number:
            # Fetch specific PR with reviews
            pr_url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}"
            reviews_url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}/reviews"
            
            logger.debug(f"Fetching PR {pr_number} from: {pr_url}")
            pr_response = requests.get(pr_url, headers=headers, timeout=30)
            pr_response.raise_for_status()
            pr = pr_response.json()
            
            logger.debug(f"Fetching reviews from: {reviews_url}")
            reviews_response = requests.get(reviews_url, headers=headers, timeout=30)
            reviews_response.raise_for_status()
            reviews = reviews_response.json()
            
            review_data.append({
                "pr_number": pr["number"],
                "created_at": pr.get("created_at"),
                "merged_at": pr.get("merged_at"),
                "first_review_at": reviews[0].get("submitted_at") if reviews else None,
                "review_count": len(reviews),
                "reviews": [
                    {
                        "state": r.get("state"),
                        "submitted_at": r.get("submitted_at"),
                        "reviewer": r.get("user", {}).get("login", "") if r.get("user") else ""
                    }
                    for r in reviews
                ]
            })
        else:
            # Fetch multiple PRs with review data
            prs_url = f"https://api.github.com/repos/{repo_name}/pulls"
            params = {
                "state": state,
                "per_page": 20,
                "sort": "updated",
                "direction": "desc"
            }
            
            logger.debug(f"Fetching PRs from: {prs_url}")
            prs_response = requests.get(prs_url, headers=headers, params=params, timeout=30)
            prs_response.raise_for_status()
            prs = prs_response.json()
            
            for pr in prs[:10]:  # Limit to 10 PRs for performance
                reviews_url = f"https://api.github.com/repos/{repo_name}/pulls/{pr['number']}/reviews"
                try:
                    reviews_response = requests.get(reviews_url, headers=headers, timeout=30)
                    reviews_response.raise_for_status()
                    reviews = reviews_response.json()
                    
                    # Only include PRs that have at least one review for review time calculation
                    if reviews:
                        review_data.append({
                            "pr_number": pr["number"],
                            "created_at": pr.get("created_at"),
                            "merged_at": pr.get("merged_at"),
                            "first_review_at": reviews[0].get("submitted_at"),
                            "review_count": len(reviews)
                        })
                    else:
                        logger.debug(f"PR {pr['number']} has no reviews, skipping for review time calculation")
                except Exception as e:
                    logger.warning(f"Error fetching reviews for PR {pr['number']}: {e}")
                    continue
        
        if not review_data:
            warning_msg = (
                "No PRs with reviews found. PR review time can only be calculated "
                "for pull requests that have at least one review."
            )
            logger.warning(warning_msg)
            return {
                "status": "error",
                "message": warning_msg,
                "data": json.dumps([]),
                "count": 0
            }
        
        logger.info(f"Successfully fetched review data for {len(review_data)} PRs")
        return {
            "status": "success",
            "data": json.dumps(review_data),
            "count": len(review_data)
        }
    except requests.exceptions.RequestException as e:
        error_msg = f"Error fetching PR review data: {e}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "message": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error fetching PR review data: {e}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "message": error_msg}

