"""
Metrics Calculation Tools - Tools for calculating DevOps metrics using code execution.

This module provides tools that use a specialized MetricCalculatorAgent with
BuiltInCodeExecutor to generate and execute Python code for metric calculations.
"""

import logging
from typing import Dict, Any

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import AgentTool
from google.adk.code_executors import BuiltInCodeExecutor
from google.genai import types

from my_metric_agent.config import get_model_name

# Set up logging
logger = logging.getLogger(__name__)

# Configure retry options for LLM calls
retry_config = types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],  # Retry on these HTTP errors
)


# Create Metric Calculator Agent with BuiltInCodeExecutor
metric_calculator_agent = LlmAgent(
    name="MetricCalculatorAgent",
    model=Gemini(model=get_model_name(), retry_options=retry_config),
    description="Calculates time-based DevOps metrics from raw JSON data using Python code execution. Provide the user's metric question and the raw JSON data.",
    instruction="""
    You are a specialized metric calculator that generates and executes Python code.
    
    Your task is to take a request for a metric calculation and translate it into
    Python code that calculates the answer from the provided JSON data.
    
    **RULES:**
    1. Generate a Python code block that performs the calculation.
    2. The Python code MUST parse the provided JSON data.
    3. The Python code MUST calculate the requested metric.
    4. The Python code MUST print the final result to stdout.
    5. Handle common metrics:
       - Cycle time: Time from PR creation to merge (in days or hours)
       - PR review time: Time from PR creation to first review (in days or hours)
       - Average metrics: Calculate mean, median, or other statistics as requested
       - When asked for "average" without specifying mean/median, use mean (arithmetic average)
    6. Parse dates using datetime and calculate time differences accurately.
    7. Handle missing or null values gracefully.
    8. For PR review time: Calculate time difference between 'created_at' and 'first_review_at'
    9. When calculating averages across multiple PRs, show both the individual values and the average
    10. After the code executes, explain the result clearly to the user with units (hours/days).
    
    The user's input will contain both their question and the JSON data to analyze.
    """,
    code_executor=BuiltInCodeExecutor(),  # Enable code execution capability
)


# Create AgentTool wrapper for use in the root agent
# This handles all session management and agent-to-agent communication automatically
calculate_metrics_tool = AgentTool(agent=metric_calculator_agent)

