# 🔧 MCP Client Connection Fix - Setup Instructions

## 🎯 **What This Fix Solves**

**Original Error:**
```
AttributeError: 'MemoryObjectReceiveStream' object has no attribute 'call_tool'
```

**Root Cause:** The MCP client initialization was incorrectly extracting I/O streams instead of creating the proper ClientSession object.

## 📋 **Step-by-Step Fix Instructions**

### 1. Install MCP Atlassian (Critical Step)

The `mcp-atlassian` package must be installed via `uvx`, not pip:

```bash
# Install mcp-atlassian from the correct repository
uvx install git+https://github.com/sooperset/mcp-atlassian.git

# Verify installation
uvx list | grep mcp-atlassian
```

### 2. Update Your Environment File

**Fix your `.env` file** (copy from `.env.example`):

```bash
# Copy the corrected example
cp .env.example .env

# Edit with your actual credentials
nano .env
```

**Critical**: Make sure your `.env` file has:
- No spaces around `=` signs
- Your actual Jira API token (not `your_jira_api_token_here`)
- Correct Jira URL format

### 3. Install Dependencies

```bash
# Install Python dependencies
uv sync

# Or if using pip
pip install -r requirements.txt
```

### 4. Test MCP Connection (Optional)

Add this test script to verify the fix works:

```python
# test_mcp.py
import asyncio
import os
from dotenv import load_dotenv
from src.beeai_agents.agent import initialize_mcp_client

load_dotenv()

async def test_connection():
    """Test MCP connection independently"""
    try:
        client = await initialize_mcp_client()
        if client and hasattr(client, 'call_tool'):
            print("✅ MCP connection successful!")
            print(f"✅ Client type: {type(client)}")
            print(f"✅ Has call_tool method: {hasattr(client, 'call_tool')}")
            
            # Test a simple call
            result = await client.call_tool("mcp-atlassian:jira_get_all_projects", {})
            print(f"✅ Test call successful: {len(result.content)} results")
        else:
            print("❌ MCP client initialization failed")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
```

Run the test:
```bash
python test_mcp.py
```

### 5. Start Your Agent

```bash
uv run python src/beeai_agents/agent.py
```

## 🔍 **Expected Output After Fix**

You should now see:

```
🔄 Initializing Jira MCP connection...
📝 JIRA_URL: https://jsw.ibm.com/
📝 JIRA_USERNAME: matus.vavro@sk.ibm.com  
📝 JIRA_TOKEN: **************************************
🔗 Connecting to MCP server...
✅ Connected to Jira MCP server successfully
🔧 Debug: Final client type: <class 'mcp.ClientSession'>
🔧 Debug: Client methods: ['call_tool', 'initialize', 'close', ...]
```

**Instead of the old error:**
```
🔧 Debug: Final client type: <class 'anyio.streams.memory.MemoryObjectReceiveStream'>
❌ Error: 'MemoryObjectReceiveStream' object has no attribute 'call_tool'
```

## 🔧 **Technical Changes Made**

### Fixed `initialize_mcp_client()` function:

**Before (Broken):**
```python
connection_result = await _mcp_context_manager.__aenter__()
if isinstance(connection_result, tuple):
    jira_mcp_client = connection_result[0]  # ← This was just a stream!
```

**After (Fixed):**
```python  
read_stream, write_stream = await _mcp_context_manager.__aenter__()
jira_mcp_client = ClientSession(read_stream, write_stream)  # ← Proper client!
await jira_mcp_client.initialize()
```

### Environment Variables vs CLI Args:

**Before:** Passing credentials as command-line arguments
**After:** Using environment variables (mcp-atlassian's preferred method)

## 🚨 **Common Issues & Solutions**

### Issue: "uvx command not found"
**Solution:** Install uvx: `pip install uvx`

### Issue: "mcp-atlassian not found"  
**Solution:** Install from git: `uvx install git+https://github.com/sooperset/mcp-atlassian.git`

### Issue: "Authentication failed"
**Solution:** 
- Check your Jira API token is valid
- Verify your username/email is correct
- Ensure you have proper Jira permissions

### Issue: "Still getting MemoryObjectReceiveStream"
**Solution:** Make sure you've updated the `initialize_mcp_client()` function with the fixed version

### Issue: "dotenv parsing warnings"
**Solution:** Use the corrected `.env.example` format (no spaces around `=`)

## 🎯 **Verification Checklist**

- [ ] `uvx install git+https://github.com/sooperset/mcp-atlassian.git` completed
- [ ] `.env` file properly formatted with actual credentials  
- [ ] Updated `initialize_mcp_client()` function
- [ ] No `MemoryObjectReceiveStream` error in logs
- [ ] Seeing `<class 'mcp.ClientSession'>` in debug output
- [ ] Jira calls working without `call_tool` attribute errors

## 📞 **Support**

If you still encounter issues after following these steps:

1. Check the debug output shows `ClientSession` type
2. Verify `uvx list` shows mcp-atlassian installed
3. Test Jira credentials work in browser
4. Review the complete error traceback

The key insight: **MCP stdio_client returns streams, not a client. You must create ClientSession with those streams.**
