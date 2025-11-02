# Comprehensive Guide to Metorial API Integration

## 🎯 Overview

Metorial provides a cloud platform for deploying and managing MCP (Model Context Protocol) servers. This guide covers everything needed to work with the Metorial API for data retrieval and server management.

## 📚 Table of Contents

1. [Authentication](#authentication)
2. [Python SDK Usage](#python-sdk-usage)
3. [Server Management](#server-management)
4. [Session Management](#session-management)
5. [MCP Communication](#mcp-communication)
6. [Error Handling](#error-handling)
7. [Best Practices](#best-practices)
8. [Common Patterns](#common-patterns)
9. [Troubleshooting](#troubleshooting)

## 🔐 Authentication

### API Key Format
```
metorial_sk_[52_character_string]
```

### Environment Setup
```python
import os
os.environ["METORIAL_API_KEY"] = "metorial_sk_RFal8orFITjN0TXs0YAMKCk873ZT3f3UbxP1Pk2ftr8m9M1fnVK0trLhw6MG4bnX7G6OgTddJPq0hGQhkrWQVzwyi66DZo7ZT3v1"
```

### SDK Initialization
```python
from metorial import Metorial

# Initialize client
metorial = Metorial(api_key=os.environ["METORIAL_API_KEY"])
```

## 🐍 Python SDK Usage

### Installation
```bash
pip install metorial
```

### Basic Client Setup
```python
from metorial import Metorial
import os

class MetorialClient:
    def __init__(self):
        self.api_key = os.getenv("METORIAL_API_KEY")
        if not self.api_key:
            raise ValueError("METORIAL_API_KEY environment variable required")
        
        self.client = Metorial(api_key=self.api_key)
        self.session = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    def cleanup(self):
        if self.session:
            try:
                self.client.sessions.delete(self.session.id)
            except Exception:
                pass  # Ignore cleanup errors
```

## 🖥️ Server Management

### Server Information Structure
```python
# Server object properties
server = {
    "id": "srv_0mhiauf69ZUpSMIYJyWyBC",
    "name": "kaggle-mcp-server", 
    "type": "custom",
    "status": "active",  # active, inactive, deleted
    "created_at": "2025-11-02T21:41:34.757Z",
    "variants": [
        {
            "id": "sva_0mhi8kib1gQfcLNFMWECoX",
            "identifier": "krxpjpd9",
            "status": "active"
        }
    ]
}
```

### Server Operations
```python
class ServerManager:
    def __init__(self, metorial_client):
        self.client = metorial_client
    
    def get_server_info(self, server_id):
        """Get server information"""
        try:
            # Note: Direct server info endpoint may not be available
            # Server info is typically retrieved through session creation
            return {"server_id": server_id, "status": "unknown"}
        except Exception as e:
            return {"error": str(e)}
    
    def list_servers(self):
        """List available servers (if endpoint exists)"""
        # This endpoint may not be publicly available
        # Servers are typically managed through the Metorial dashboard
        pass
```

## 🔄 Session Management

### Session Lifecycle
```python
class SessionManager:
    def __init__(self, metorial_client):
        self.client = metorial_client
        self.active_sessions = {}
    
    def create_session(self, server_id, config=None):
        """Create a new MCP session"""
        try:
            session = self.client.sessions.create(
                server_deployments=[{
                    "server_id": server_id,
                    "config": config or {}
                }]
            )
            
            self.active_sessions[session.id] = session
            return session
            
        except Exception as e:
            raise Exception(f"Failed to create session: {e}")
    
    def get_session_info(self, session_id):
        """Get session information"""
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        
        return {
            "id": session.id,
            "status": session.status,
            "connection_status": session.connection_status,
            "server_deployments": [
                {
                    "id": dep.id,
                    "connection_urls": {
                        "streamable_http": dep.connection_urls.streamable_http
                    }
                }
                for dep in session.server_deployments
            ],
            "client_secret": session.client_secret.secret
        }
    
    def delete_session(self, session_id):
        """Delete a session"""
        try:
            self.client.sessions.delete(session_id)
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            return True
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False
    
    def cleanup_all_sessions(self):
        """Clean up all active sessions"""
        for session_id in list(self.active_sessions.keys()):
            self.delete_session(session_id)
```

### Session Configuration Examples
```python
# Basic session (no config)
session = metorial.sessions.create(
    server_deployments=[{
        "server_id": "srv_0mhiauf69ZUpSMIYJyWyBC"
    }]
)

# Session with configuration
session = metorial.sessions.create(
    server_deployments=[{
        "server_id": "srv_0mhiauf69ZUpSMIYJyWyBC",
        "config": {
            "kaggleUsername": "your_username",
            "kaggleKey": "your_api_key",
            "customSetting": "value"
        }
    }]
)
```

## 🔌 MCP Communication

### Connection Setup
```python
import requests
import json

class MCPCommunicator:
    def __init__(self, session):
        self.session = session
        self.connection_url = session.server_deployments[0].connection_urls.streamable_http
        self.headers = {
            "Authorization": f"Bearer {session.client_secret.secret}",
            "Content-Type": "application/json"
        }
        self.request_id = 1
    
    def send_request(self, method, params=None, timeout=30):
        """Send MCP request"""
        payload = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
        
        self.request_id += 1
        
        try:
            response = requests.post(
                self.connection_url,
                headers=self.headers,
                json=payload,
                timeout=timeout
            )
            
            return self._parse_response(response)
            
        except requests.exceptions.Timeout:
            return {"error": "Request timeout"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {e}"}
    
    def _parse_response(self, response):
        """Parse MCP response (handles Server-Sent Events)"""
        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
        
        # Handle Server-Sent Events format
        events = self._parse_sse(response.text)
        
        for event in events:
            if 'event' in event and event['event'] == 'error':
                return {"error": event.get('data', 'Unknown error')}
            elif 'data' in event and isinstance(event['data'], dict):
                if 'result' in event['data']:
                    return event['data']['result']
                elif 'error' in event['data']:
                    return {"error": event['data']['error']}
        
        return {"error": "No valid response"}
    
    def _parse_sse(self, response_text):
        """Parse Server-Sent Events format"""
        lines = response_text.strip().split('\n')
        events = []
        current_event = {}
        
        for line in lines:
            if line.startswith('data: '):
                data = line[6:]  # Remove 'data: ' prefix
                try:
                    current_event['data'] = json.loads(data)
                except json.JSONDecodeError:
                    current_event['data'] = data
            elif line.startswith('event: '):
                current_event['event'] = line[7:]  # Remove 'event: ' prefix
            elif line.startswith('id: '):
                current_event['id'] = line[4:]  # Remove 'id: ' prefix
            elif line == '':
                if current_event:
                    events.append(current_event)
                    current_event = {}
        
        if current_event:
            events.append(current_event)
        
        return events
```

### MCP Protocol Methods
```python
class MCPProtocol:
    def __init__(self, communicator):
        self.comm = communicator
    
    def initialize(self):
        """Initialize MCP connection"""
        return self.comm.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": {
                "name": "metorial-client",
                "version": "1.0.0"
            }
        })
    
    def list_tools(self):
        """List available tools"""
        return self.comm.send_request("tools/list")
    
    def call_tool(self, tool_name, arguments):
        """Call a specific tool"""
        return self.comm.send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
```

## 🛠️ Complete Integration Class

```python
class MetorialMCPClient:
    def __init__(self, api_key, server_id, config=None):
        self.api_key = api_key
        self.server_id = server_id
        self.config = config or {}
        self.metorial = Metorial(api_key=api_key)
        self.session = None
        self.mcp = None
    
    async def _ensure_session(self):
        """Ensure session is created and initialized"""
        if self.session is None:
            # Create session
            self.session = self.metorial.sessions.create(
                server_deployments=[{
                    "server_id": self.server_id,
                    "config": self.config
                }]
            )
            
            # Initialize MCP communication
            communicator = MCPCommunicator(self.session)
            self.mcp = MCPProtocol(communicator)
            
            # Initialize MCP protocol
            init_result = self.mcp.initialize()
            if "error" in init_result:
                raise Exception(f"MCP initialization failed: {init_result['error']}")
    
    async def call_tool(self, tool_name, arguments):
        """Call a tool on the MCP server"""
        await self._ensure_session()
        return self.mcp.call_tool(tool_name, arguments)
    
    async def list_tools(self):
        """List available tools"""
        await self._ensure_session()
        return self.mcp.list_tools()
    
    def close(self):
        """Clean up session"""
        if self.session:
            try:
                self.metorial.sessions.delete(self.session.id)
            except Exception:
                pass
            self.session = None
            self.mcp = None
```

## ❌ Error Handling

### Common Error Types
```python
class MetorialErrors:
    # HTTP Status Codes
    BAD_REQUEST = 400  # Invalid request format
    UNAUTHORIZED = 401  # Invalid API key
    FORBIDDEN = 403    # Access denied
    NOT_FOUND = 404    # Resource not found
    
    # Common Error Messages
    DELETED_SERVER = "Cannot create a server deployment for a deleted server"
    INVALID_API_KEY = "Invalid API key"
    SESSION_NOT_FOUND = "Session not found"
    INTERNAL_SERVER_ERROR = "An internal server error occurred"

def handle_metorial_error(error_response):
    """Handle common Metorial API errors"""
    if isinstance(error_response, dict):
        error_msg = error_response.get('error', str(error_response))
        
        if 'deleted server' in error_msg.lower():
            return "Server has been deleted. Please redeploy or use a different server ID."
        elif 'unauthorized' in error_msg.lower():
            return "Invalid API key. Please check your METORIAL_API_KEY."
        elif 'not found' in error_msg.lower():
            return "Resource not found. Check server ID or session ID."
        elif 'internal server error' in error_msg.lower():
            return "Server-side error. Check server logs or redeploy server."
        else:
            return f"Metorial API error: {error_msg}"
    
    return str(error_response)
```

### Retry Logic
```python
import time
import random

def with_retry(max_retries=3, backoff_factor=1.0):
    """Decorator for retrying failed requests"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    
                    # Exponential backoff with jitter
                    delay = backoff_factor * (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(delay)
            
        return wrapper
    return decorator

# Usage
@with_retry(max_retries=3, backoff_factor=0.5)
def create_session_with_retry(metorial, server_id, config):
    return metorial.sessions.create(
        server_deployments=[{
            "server_id": server_id,
            "config": config
        }]
    )
```

## 🎯 Best Practices

### 1. Resource Management
```python
# Always use context managers
class MetorialContext:
    def __init__(self, api_key, server_id, config=None):
        self.client = MetorialMCPClient(api_key, server_id, config)
    
    def __enter__(self):
        return self.client
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

# Usage
with MetorialContext(api_key, server_id, config) as client:
    result = await client.call_tool("search_kaggle_datasets", {"query": "titanic"})
```

### 2. Configuration Management
```python
class MetorialConfig:
    def __init__(self):
        self.api_key = self._get_required_env("METORIAL_API_KEY")
        self.server_id = self._get_required_env("METORIAL_KAGGLE_SERVER_ID")
        self.kaggle_username = self._get_required_env("KAGGLE_USERNAME")
        self.kaggle_key = self._get_required_env("KAGGLE_KEY")
    
    def _get_required_env(self, key):
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable {key} not set")
        return value
    
    def get_server_config(self):
        return {
            "kaggleUsername": self.kaggle_username,
            "kaggleKey": self.kaggle_key
        }
```

### 3. Logging and Monitoring
```python
import logging

class MetorialLogger:
    def __init__(self):
        self.logger = logging.getLogger("metorial_client")
        self.logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_session_created(self, session_id, server_id):
        self.logger.info(f"Session created: {session_id} for server {server_id}")
    
    def log_tool_call(self, tool_name, arguments, result):
        self.logger.info(f"Tool call: {tool_name} with args {arguments}")
        if "error" in str(result):
            self.logger.error(f"Tool call failed: {result}")
        else:
            self.logger.info(f"Tool call succeeded: {len(str(result))} chars")
    
    def log_error(self, error, context=""):
        self.logger.error(f"Error {context}: {error}")
```

## 🔄 Common Patterns

### Pattern 1: Simple Tool Call
```python
async def simple_tool_call(api_key, server_id, tool_name, arguments, config=None):
    """Execute a single tool call"""
    client = MetorialMCPClient(api_key, server_id, config)
    try:
        result = await client.call_tool(tool_name, arguments)
        return result
    finally:
        client.close()
```

### Pattern 2: Batch Tool Calls
```python
async def batch_tool_calls(api_key, server_id, tool_calls, config=None):
    """Execute multiple tool calls in one session"""
    client = MetorialMCPClient(api_key, server_id, config)
    results = []
    
    try:
        for tool_name, arguments in tool_calls:
            result = await client.call_tool(tool_name, arguments)
            results.append({
                "tool": tool_name,
                "arguments": arguments,
                "result": result
            })
    finally:
        client.close()
    
    return results
```

### Pattern 3: Long-Running Session
```python
class LongRunningSession:
    def __init__(self, api_key, server_id, config=None):
        self.client = MetorialMCPClient(api_key, server_id, config)
        self.initialized = False
    
    async def ensure_ready(self):
        if not self.initialized:
            await self.client._ensure_session()
            self.initialized = True
    
    async def call_tool(self, tool_name, arguments):
        await self.ensure_ready()
        return await self.client.call_tool(tool_name, arguments)
    
    def close(self):
        self.client.close()
        self.initialized = False
```

## 🐛 Troubleshooting

### Common Issues and Solutions

#### 1. "Buffer is not defined"
```typescript
// Problem: Using Node.js Buffer in browser environment
const auth = Buffer.from(credentials).toString('base64');

// Solution: Use browser-compatible base64 encoding
function encodeBase64(str: string): string {
  if (typeof btoa !== 'undefined') {
    return btoa(str);  // Browser
  } else if (typeof Buffer !== 'undefined') {
    return Buffer.from(str).toString('base64');  // Node.js
  } else {
    // Manual implementation
    return manualBase64Encode(str);
  }
}
```

#### 2. "Cannot create a server deployment for a deleted server"
```python
# Problem: Server was deleted
# Solution: Check server status and redeploy if needed
def check_server_status(server_id):
    try:
        # Try to create a test session
        session = metorial.sessions.create(
            server_deployments=[{"server_id": server_id}]
        )
        metorial.sessions.delete(session.id)
        return "active"
    except Exception as e:
        if "deleted server" in str(e):
            return "deleted"
        return "unknown"
```

#### 3. "Internal server error"
```python
# Problem: Server-side execution error
# Solution: Check server logs and validate server code
def diagnose_server_error(client, tool_name, arguments):
    try:
        result = await client.call_tool(tool_name, arguments)
        return result
    except Exception as e:
        if "internal server error" in str(e).lower():
            return {
                "error": "Server-side execution error",
                "suggestions": [
                    "Check server logs in Metorial dashboard",
                    "Verify server code has no runtime errors",
                    "Ensure all dependencies are available",
                    "Check tool input validation"
                ]
            }
        raise e
```

## 📊 Usage Examples

### Example 1: Kaggle Dataset Search
```python
async def search_kaggle_datasets(query):
    config = MetorialConfig()
    
    async with MetorialContext(
        config.api_key, 
        config.server_id, 
        config.get_server_config()
    ) as client:
        result = await client.call_tool("search_kaggle_datasets", {
            "query": query
        })
        
        if "error" in result:
            print(f"Error: {result['error']}")
            return []
        
        return result.get("results", [])

# Usage
datasets = await search_kaggle_datasets("titanic")
for dataset in datasets:
    print(f"- {dataset['title']} ({dataset['ref']})")
```

### Example 2: Competition Analysis
```python
async def analyze_competition(competition_id):
    config = MetorialConfig()
    
    async with MetorialContext(
        config.api_key,
        config.server_id,
        config.get_server_config()
    ) as client:
        # Get competition details
        details = await client.call_tool("get_competition_details", {
            "competition_id": competition_id
        })
        
        # Get data files
        files = await client.call_tool("download_competition_data", {
            "competition_id": competition_id
        })
        
        return {
            "details": details,
            "files": files
        }

# Usage
analysis = await analyze_competition("titanic")
print(f"Competition: {analysis['details']['title']}")
print(f"Files: {len(analysis['files']['files'])} available")
```

## 🎉 Summary

This guide covers the complete workflow for integrating with Metorial API:

1. **Authentication**: API key setup and client initialization
2. **Session Management**: Creating, managing, and cleaning up sessions
3. **MCP Communication**: Protocol implementation and tool calling
4. **Error Handling**: Robust error handling and retry logic
5. **Best Practices**: Resource management, logging, and monitoring
6. **Common Patterns**: Reusable patterns for different use cases
7. **Troubleshooting**: Solutions for common issues

The key to successful Metorial integration is proper session management, robust error handling, and understanding the MCP protocol flow. Always clean up resources and handle edge cases gracefully.

---

**Remember**: Metorial provides the infrastructure, but the quality of your MCP server implementation determines the success of your integration!