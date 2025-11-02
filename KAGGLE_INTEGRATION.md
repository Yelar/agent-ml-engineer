# Kaggle Competition Integration

Complete integration for automatically solving Kaggle competitions with the ML Engineer Agent.

## 🎯 Overview

The ML Engineer Agent can now:
- **Search** Kaggle competitions by query/status
- **Download** competition data automatically  
- **Analyze** competition requirements and metrics
- **Build** complete ML pipelines for competitions
- **Generate** submission-ready CSV files
- **Upload** submissions directly to Kaggle

## 🚀 Quick Start

### 1. Prerequisites
```bash
# Install dependencies
pip install kaggle>=1.6.0

# Configure Kaggle API
# Download kaggle.json from https://www.kaggle.com/account
# Place in ~/.kaggle/kaggle.json
chmod 600 ~/.kaggle/kaggle.json
```

### 2. Basic Usage

```python
from ml_engineer.agent import MLEngineerAgent

# Create agent for Kaggle competition
agent = MLEngineerAgent(
    model_name="gpt-4o-mini",
    max_iterations=15,
    verbose=True
)

# Solve competition automatically
result = agent.run_kaggle_competition(
    "https://www.kaggle.com/competitions/titanic",
    "Build the best model possible for this classification task"
)

print(f"Submission saved to: {result['artifacts_dir']}")
```

## 📋 Backend Implementation

### New Kaggle Tools

Located in `backend/ml_engineer/tools.py`:

1. **`kaggle_search_competitions`** - Search competitions by query/status
2. **`kaggle_get_competition_details`** - Get competition info, metrics, rules
3. **`kaggle_download_competition_data`** - Download datasets, sample submissions
4. **`kaggle_submit_to_competition`** - Upload CSV submissions
5. **`kaggle_parse_url`** - Extract competition ID from URLs

### Enhanced MLEngineerAgent

New features in `backend/ml_engineer/agent.py`:

- **Kaggle Mode**: `kaggle_mode=True` enables competition-specific workflow
- **Competition ID**: Automatic extraction from URLs
- **Specialized System Prompt**: Kaggle-aware instructions and workflow
- **Tool Integration**: Automatic tool loading in Kaggle mode
- **`run_kaggle_competition()`**: One-method solution for competitions

### Backend API Enhancements 

New endpoints in `backend/server.py`:

```http
POST /kaggle-session
# Creates session for Kaggle mode (no file upload needed)

POST /chat
{
  "session_id": "abc123",
  "message": "Solve this competition", 
  "kaggle_competition_url": "https://www.kaggle.com/c/titanic"
}
```

### MCP Server Extensions

Enhanced `backend/kaggle-mcp-main/src/server.py`:
- All Kaggle tools implemented as MCP tools
- Competition search, details, download, submission
- JSON-formatted responses for easy parsing

## 🔧 Technical Details

### Agent Workflow

When `run_kaggle_competition()` is called:

1. **URL Parsing**: Extract competition ID from URL
2. **Mode Switch**: Enable Kaggle mode and load specialized tools
3. **System Prompt**: Use competition-specific prompt template
4. **Execution**: Follow structured workflow:
   - Get competition details and download data
   - Perform EDA appropriate for problem type  
   - Build models optimized for competition metric
   - Generate submission CSV matching required format
   - Validate submission format
   - Optionally upload to Kaggle

### Kaggle-Specific System Prompt

The agent uses a specialized prompt that:
- Understands competition workflows
- Focuses on evaluation metrics
- Emphasizes submission format validation
- Includes competition-specific best practices
- Guides through complete pipeline creation

### Tool Integration

```python
# Tools loaded based on mode
tools = create_tool_list(kaggle_mode=True)  # 7 tools
# vs 
tools = create_tool_list(kaggle_mode=False)  # 2 tools

# Tools available in Kaggle mode:
# - dataset_info
# - execute_python  
# - kaggle_search_competitions
# - kaggle_get_competition_details
# - kaggle_download_competition_data
# - kaggle_submit_to_competition
# - kaggle_parse_url
```

## 📁 File Structure

```
backend/
├── ml_engineer/
│   ├── agent.py              # Enhanced with Kaggle mode
│   └── tools.py              # New Kaggle tools
├── kaggle-mcp-main/src/
│   └── server.py             # Enhanced MCP server  
├── server.py                 # New API endpoints
├── requirements.txt          # Added kaggle>=1.6.0
├── test_kaggle_integration.py      # Test suite
└── example_kaggle_competition.py   # Usage examples
```

## 🧪 Testing

### Run Tests
```bash
cd backend
python test_kaggle_integration.py    # Basic import/tool tests
python example_kaggle_competition.py # Usage examples
```

### Manual Testing
```python
# Test individual tools
from ml_engineer.tools import kaggle_search_competitions
result = await kaggle_search_competitions.ainvoke({
    "query": "regression", 
    "status": "active"
})

# Test agent creation
agent = MLEngineerAgent(
    kaggle_mode=True,
    kaggle_competition_id="titanic"
)
```

## 🌐 API Usage

### Create Kaggle Session
```bash
curl -X POST http://localhost:8000/kaggle-session
# Response: {"session_id": "abc123", "datasets": []}
```

### Send Competition Request
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc123",
    "message": "Solve this Titanic competition",
    "kaggle_competition_url": "https://www.kaggle.com/c/titanic"
  }'
```

### WebSocket Events
```javascript
const ws = new WebSocket('ws://localhost:8000/sessions/abc123/events')
// Receives: status, code, plots, artifacts, metadata
```

## 🔄 Workflow Examples

### Classification Competition
```python
agent.run_kaggle_competition(
    "https://www.kaggle.com/c/titanic",
    """
    1. Download and explore the Titanic dataset
    2. Perform feature engineering for passenger data
    3. Build classification models (focus on accuracy)
    4. Generate submission with PassengerId and Survived columns
    """
)
```

### Regression Competition  
```python
agent.run_kaggle_competition(
    "house-prices-advanced-regression-techniques", 
    """
    Build regression model for house prices.
    Focus on RMSE metric and handle missing values carefully.
    """
)
```

## 📈 Features Implemented

### ✅ Completed
- [x] Kaggle API integration
- [x] Competition search and details
- [x] Data download automation
- [x] Agent Kaggle mode and workflow
- [x] Specialized system prompts
- [x] Submission generation 
- [x] Backend API endpoints
- [x] MCP server tools
- [x] Testing and examples

### 🚧 Next Steps (Frontend)
- [ ] Kaggle URL input in frontend
- [ ] Competition mode toggle  
- [ ] Submission status display
- [ ] Competition details preview

## 🐛 Known Issues

1. **Kaggle API Warnings**: File permission warnings (fix with `chmod 600 ~/.kaggle/kaggle.json`)
2. **Competition Access**: Some competitions require acceptance of rules
3. **Rate Limits**: Kaggle API has rate limits for downloads/submissions

## 💡 Usage Tips

1. **Test with Public Competitions**: Use completed competitions for testing
2. **Monitor Rate Limits**: Kaggle limits API calls per hour  
3. **Validate Submissions**: Always check submission format before upload
4. **Use Appropriate Models**: Different competitions need different approaches
5. **Check Evaluation Metrics**: Optimize for the specific competition metric

---

🎉 **Ready to automatically solve Kaggle competitions!**

The agent can now handle the complete workflow from URL to submission, making it a powerful tool for competitive machine learning.
