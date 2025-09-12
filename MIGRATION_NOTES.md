# BeeAI Framework Migration Notes v2.0.0

## Overview

This document outlines the migration from BeeAI SDK v1.0 to BeeAI Framework v2.0 for the Jira Scrum Master Agent.

## Key Architectural Changes

### 1. Framework Migration
- **From**: Legacy BeeAI SDK with `@server.agent()` decorator  
- **To**: Modern BeeAI Framework with `RequirementAgent`
- **Impact**: Better tool control, conditional execution, enhanced memory management

### 2. Type System Updates
- **Old Types**: `Message`, `Context`, `AgentMessage`, `PlatformUIAnnotation`
- **New Types**: `RunContext`, `AgentDetail`, `AgentSkill`, Extension Servers
- **Impact**: More structured agent metadata and better UI integration

### 3. Tool Architecture
- **Old**: Direct MCP calls in agent functions
- **New**: Custom `JiraTool` class implementing `Tool` interface
- **Impact**: Cleaner separation of concerns, better error handling

### 4. Memory Management
- **Old**: Global state management
- **New**: Session-based `UnconstrainedMemory` with proper lifecycle
- **Impact**: Better conversation persistence and context retention

## New Features Added

### Extension Servers
- `CitationExtensionServer`: Structured citation handling
- `TrajectoryExtensionServer`: Agent decision tracking
- `LLMServiceExtensionServer`: Consistent model access

### Advanced Tool Requirements
- Conditional tool execution based on user input
- Smart routing to prevent unnecessary tool calls
- Maximum invocation limits for better performance

### Enhanced Error Handling
- Graceful MCP connection failure handling
- Better user feedback on configuration issues
- Comprehensive exception tracking

## Breaking Changes

### Import Changes
```python
# Old imports
from beeai_sdk.server.context import Context
from beeai_sdk.a2a.types import AgentMessage
from beeai_sdk.models import PlatformUIAnnotation

# New imports
from beeai_sdk.server.context import RunContext
from beeai_sdk.a2a.extensions import AgentDetail, AgentDetailTool
from beeai_framework.agents.experimental import RequirementAgent
```

### Configuration Structure
```python
# Old configuration
@server.agent(
    details={
        "ui": PlatformUIAnnotation(ui_type=PlatformUIType.CHAT)
    }
)

# New configuration  
@server.agent(
    detail=AgentDetail(
        interaction_mode="multi-turn",
        tools=[AgentDetailTool(name="...", description="...")]
    ),
    skills=[AgentSkill(id="...", name="...", description="...")]
)
```

## Dependencies Update

Update your `pyproject.toml`:

```toml
[project]
dependencies = [
    "beeai-framework>=0.1.0",  # New requirement
    "beeai-sdk>=0.1.0",        # Updated version
    "mcp>=1.0.0",               # MCP integration
    "mcp-atlassian>=0.1.0",     # Jira MCP client
    # ... other dependencies
]
```

## Migration Steps

1. **Update Dependencies**: Install BeeAI Framework packages
2. **Update Imports**: Replace old SDK imports with new Framework imports
3. **Refactor Agent**: Convert to new agent structure with extensions
4. **Create Tools**: Implement custom tool classes for external integrations
5. **Update Configuration**: Use new AgentDetail and AgentSkill structures
6. **Test Integration**: Verify all functionality works with new architecture

## Backwards Compatibility

This migration introduces breaking changes. The v1.0 agent will not work with v2.0 without code changes. However, all original functionality is preserved:

- ✅ Sprint Analysis
- ✅ Velocity Tracking  
- ✅ Standup Facilitation
- ✅ Impediment Management
- ✅ Jira MCP Integration

## Performance Improvements

- **Faster Tool Execution**: Conditional requirements prevent unnecessary calls
- **Better Memory Usage**: Session-based memory with proper cleanup
- **Enhanced Error Recovery**: Graceful fallbacks for connection issues
- **Smarter Routing**: Intent-based tool selection

## Testing the Migration

Verify these key scenarios work:

1. **Sprint Status**: "What's our current sprint status?"
2. **Velocity Analysis**: "Show me our velocity trends"
3. **Daily Standup**: "Generate today's standup report"
4. **Blocker Detection**: "What blockers do we have?"
5. **Casual Interaction**: "Hello" (should not trigger tools)

## Future Enhancements

The new architecture enables:
- Multi-modal input support
- Enhanced UI integrations
- Better agent composition
- Advanced requirement patterns
- Improved observability

---

**Migration Date**: 2025-01-XX  
**Version**: 1.0.0 → 2.0.0  
**Compatibility**: Breaking changes - full migration required
