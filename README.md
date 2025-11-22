# DevOps Metrics Agent

**A Multi-Agent System for GitHub DevOps Metrics**

DevOps Metrics Agent is an intelligent AI-powered assistant that calculates and analyzes key DevOps metrics from GitHub repositories using natural language. Built with Google's Agent Development Kit (ADK), it demonstrates advanced multi-agent architecture, persistent memory, code execution, and session management.

![Demo Screenshot](output/result.png)

## 🎯 Project Summary

This project serves as a comprehensive demonstration of Google ADK capabilities, featuring:

- **Natural Language Interface**: Ask questions about your DevOps metrics in plain English
- **Automated Metric Calculation**: Calculate cycle time, PR review time, and custom metrics
- **Persistent Memory**: Configurations and tracked repositories persist across sessions
- **Multi-Agent Architecture**: Specialized agents for GitHub API interaction and metric calculations
- **Code Generation**: Dynamically generates and executes Python code for metric analysis
- **Session Management**: Maintains conversation context with automatic compaction

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface                          │
│                   (ADK Web / Chat UI)                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Root Agent (Orchestrator)                  │
│  - GitHub PAT setup & validation                            │
│  - Repository tracking management                           │
│  - Metric request routing                                   │
│  - Session state management                                 │
└───┬─────────────────┬────────────────────┬──────────────────┘
    │                 │                    │
    ▼                 ▼                    ▼
┌──────────┐   ┌─────────────┐   ┌────────────────────┐
│  GitHub  │   │   Auth      │   │  Metric Calculator │
│  Tools   │   │   Memory    │   │     Agent          │
│          │   │   Tool      │   │                    │
│ - PRs    │   │             │   │ - Code Generation  │
│ - Reviews│   │ - SQLite    │   │ - Code Execution   │
│ - Data   │   │ - Persist   │   │ - Analysis         │
└──────────┘   └─────────────┘   └────────────────────┘
     │                │                     │
     ▼                ▼                     ▼
┌─────────────────────────────────────────────────┐
│            Persistent Storage Layer             │
│  - sessions.db (conversation history)           │
│  - metrics_db.sqlite (user configs & repos)     │
└─────────────────────────────────────────────────┘
```

### Component Breakdown

#### 1. **Root Agent (DevOps Metrics Assistant)**
- **Purpose**: Main orchestrator that handles user requests
- **Responsibilities**:
  - Interprets user queries about DevOps metrics
  - Routes requests to appropriate tools
  - Manages GitHub authentication flow
  - Coordinates multi-step metric calculations
- **Technology**: Google ADK `LlmAgent` with Gemini 2.5 Flash

#### 2. **GitHub Tools**
- `setup_github_config`: Initialize GitHub PAT from environment
- `add_tracked_repo`: Add repositories to tracking list
- `get_tracked_repos`: Retrieve tracked repositories
- `fetch_pr_data`: Fetch pull request data with filters (open/closed/all)
- `fetch_pr_review_data`: Fetch PR review timestamps for review time metrics
- `fetch_cycle_time_data`: Fetch data for cycle time calculations

#### 3. **Auth Memory Tool**
- **Purpose**: Persistent storage for user configurations
- **Storage**: SQLite database (`metrics_db.sqlite`)
- **Persists**:
  - GitHub Personal Access Tokens (PAT)
  - Tracked repository lists per user
  - User preferences and settings

#### 4. **Metric Calculator Agent**
- **Purpose**: Specialized agent for metric computations
- **Capabilities**:
  - Generates Python code dynamically based on metric requests
  - Executes code in a secure sandboxed environment
  - Calculates time differences, averages, aggregations
  - Handles date parsing and statistical analysis
- **Technology**: ADK `BuiltInCodeExecutor` with `AgentTool` wrapper

#### 5. **Session Management**
- **DatabaseSessionService**: Stores conversation history in `sessions.db`
- **EventsCompactionConfig**: Automatically compacts long conversations
  - Compaction Interval: Every 2 turns
  - Overlap Size: Keeps 1 previous turn for context
- **Benefits**: Manages token limits, maintains context, enables conversation continuity

## 🔧 How It Works

### Workflow Example: "Calculate average PR review time"

1. **User Query**: "What's the average PR review time for my repository?"

2. **Root Agent Processing**:
   - Checks if GitHub PAT is configured
   - Retrieves tracked repositories from Auth Memory
   - Identifies metric type: PR review time

3. **Data Fetching**:
   - Calls `fetch_pr_review_data` tool
   - GitHub Tools fetch PRs and review timestamps via GitHub API
   - Returns JSON data with `created_at` and `first_review_at` fields

4. **Metric Calculation**:
   - Root Agent invokes Metric Calculator Agent via `AgentTool`
   - Passes user question + raw JSON data
   - Metric Calculator Agent generates Python code:
     ```python
     import json
     from datetime import datetime
     
     data = json.loads('''<json_data>''')
     review_times = []
     
     for pr in data:
         if pr['first_review_at']:
             created = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
             reviewed = datetime.fromisoformat(pr['first_review_at'].replace('Z', '+00:00'))
             hours = (reviewed - created).total_seconds() / 3600
             review_times.append(hours)
     
     avg = sum(review_times) / len(review_times) if review_times else 0
     print(f"Average PR review time: {avg:.2f} hours")
     ```
   - Code executes in sandboxed environment
   - Result returned to Root Agent

5. **Response**: Root Agent formats and returns the answer to the user

## 🛠️ Tools & Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **AI Framework** | Google ADK 1.18.0+ | Multi-agent orchestration, tool execution |
| **Language Model** | Gemini 2.5 Flash | Natural language understanding, code generation |
| **Code Execution** | ADK BuiltInCodeExecutor | Secure Python code execution for metrics |
| **Session Storage** | SQLite + DatabaseSessionService | Persistent conversation history |
| **Configuration Storage** | SQLite + sqlite-utils | User configs, tokens, tracked repos |
| **HTTP Server** | FastAPI + Uvicorn | Web UI and API endpoints |
| **API Integration** | GitHub REST API v3 | Fetch PRs, reviews, repository data |
| **Package Management** | UV (ultraviolet) | Fast Python dependency management |
| **Language** | Python 3.10+ | Core implementation |

### Key ADK Features Used

1. **LlmAgent**: Main agent with instructions and tool orchestration
2. **AgentTool**: Wraps nested agents for seamless communication
3. **BuiltInCodeExecutor**: Safe code generation and execution
4. **DatabaseSessionService**: Persistent session storage
5. **EventsCompactionConfig**: Automatic context window management
6. **ToolContext**: Access to session state across tool calls
7. **App Export**: Web UI deployment with custom configuration

## 📋 Prerequisites

- **Python**: 3.10 or higher
- **UV**: Fast Python package manager ([installation](https://docs.astral.sh/uv/getting-started/installation/))
- **GitHub PAT**: Personal Access Token with `repo` scope ([create token](https://github.com/settings/tokens))
- **Google AI API Key**: For Gemini models ([get key](https://aistudio.google.com/apikey))

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/manikhere79/devops-metrics-agent.git
cd devops-metrics-agent
```

### 2. Install Dependencies with UV

UV is a fast Python package manager. Install dependencies:

```bash
# Install UV if not already installed
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies (creates virtual environment + installs packages)
uv sync
```

This command:
- Creates a virtual environment in `.venv/`
- Installs all dependencies from `pyproject.toml`
- Locks versions in `uv.lock`

### 3. Set Environment Variables

Create a `.env` file or export variables:

```bash
# GitHub Personal Access Token (required)
export GITHUB_PAT="ghp_your_token_here"

# Google AI API Key (required)
export GOOGLE_API_KEY="your_google_api_key"

# Optional: Specify Gemini model
export GEMINI_MODEL="gemini-2.5-flash"
```

**Windows PowerShell:**
```powershell
$env:GITHUB_PAT = "ghp_your_token_here"
$env:GOOGLE_API_KEY = "your_google_api_key"
```

### 4. Run the Agent with ADK Web

Start the web interface with persistent sessions:

```bash
# Activate virtual environment
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

# Run ADK web server with session persistence
adk web . --session_service_uri=sqlite:///C:\Github\devops-metrics-agent\my_metric_agent\data\sessions.db
```

**Adjust the path** to your actual project location. For example:
- Windows: `sqlite:///C:\Users\YourName\Projects\devops-metrics-agent\my_metric_agent\data\sessions.db`
- macOS/Linux: `sqlite:////home/yourname/projects/devops-metrics-agent/my_metric_agent/data/sessions.db`

### 5. Access the Web UI

Open your browser to:
```
http://127.0.0.1:8000
```

## 💬 Usage Examples

### Initial Setup

**User**: "Setup my GitHub configuration"

**Agent**: Initializes GitHub PAT from environment, stores in database

---

**User**: "Track the repository manikhere79/devops-metrics-agent"

**Agent**: Adds repository to tracked list, persists to database

### Metric Queries

**User**: "What's the cycle time for my tracked repository?"

**Agent**: 
1. Fetches PRs with creation and merge timestamps
2. Generates code to calculate time differences
3. Returns: "Average cycle time: 3.5 days"

---

**User**: "Calculate average PR review time"

**Agent**:
1. Fetches PRs with review data
2. Calculates time from PR creation to first review
3. Returns: "Average PR review time: 12.3 hours across 5 PRs"

---

**User**: "Show me PR stats for open pull requests only"

**Agent**: Fetches and displays statistics for open PRs with state filter

## 📁 Project Structure

```
devops-metrics-agent/
├── my_metric_agent/           # Main package
│   ├── __init__.py
│   ├── agent.py               # Root agent definition
│   ├── config.py              # Configuration management
│   ├── main.py                # Entry point
│   ├── data/                  # Persistent storage
│   │   ├── sessions.db        # Conversation history (auto-created)
│   │   └── metrics_db.sqlite  # User configs & repos (auto-created)
│   └── tools/                 # Tool implementations
│       ├── __init__.py
│       ├── auth_memory.py     # Persistent memory tool
│       ├── github_tools.py    # GitHub API integration
│       └── metrics_tools.py   # Metric calculator agent
├── docs/                      # Documentation
│   └── PERSISTENT_SESSIONS.md # Session management guide
├── output/                    # Screenshots & outputs
│   └── result.png            # Demo screenshot
├── scripts/                   # Helper scripts
│   ├── start_adk_web.ps1     # PowerShell launch script
│   └── inspect_sessions.py   # Session database viewer
├── kaggle_notebooks/          # Tutorial notebooks
├── .gitignore
├── pyproject.toml            # Project metadata & dependencies
├── README.md                 # This file
└── uv.lock                   # Locked dependency versions
```

## 🔍 Advanced Features

### Session Persistence

Sessions are stored in SQLite and persist across server restarts:

```bash
# Inspect session database
python scripts/inspect_sessions.py
```

### Custom Metrics

The Metric Calculator Agent can handle custom metric requests:

**User**: "Calculate the median time between PR creation and merge for closed PRs in the last month"

The agent will dynamically generate code to filter, calculate, and return the result.

### Helper Scripts

**Start with one command (Windows)**:
```powershell
.\scripts\start_adk_web.ps1
```

## 🐛 Troubleshooting

### Issue: `adk: command not found`

**Solution**: Ensure virtual environment is activated:
```bash
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux
```

### Issue: "GitHub PAT not configured"

**Solution**: Set `GITHUB_PAT` environment variable before running

### Issue: Sessions not persisting

**Solution**: Verify `--session_service_uri` parameter points to correct absolute path

### Issue: Import errors

**Solution**: Run `uv sync` to reinstall dependencies

## 📚 Learn More

- **Google ADK Documentation**: [https://google.github.io/adk/](https://google.github.io/adk/)
- **Gemini API**: [https://ai.google.dev/](https://ai.google.dev/)
- **UV Package Manager**: [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)
- **GitHub API**: [https://docs.github.com/en/rest](https://docs.github.com/en/rest)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📄 License

This project is open source and available for educational purposes.

## 👤 Author

**Manikandan Sukumaran**
- GitHub: [@manikhere79](https://github.com/manikhere79)

---

**Built with ❤️ using Google ADK**
