"""
BeeAI Platform Jira Scrum Master Agent - Reworked using BeeAI Framework
"""

import os
import json
import re
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Annotated
from textwrap import dedent
from contextlib import asynccontextmanager

# BeeAI Framework imports
from beeai_framework.adapters.openai import OpenAIChatModel
from beeai_framework.backend.types import ChatModelParameters
from beeai_framework.agents.experimental import RequirementAgent
from beeai_framework.agents.experimental.requirements.conditional import ConditionalRequirement
from beeai_framework.agents.types import AgentExecutionConfig
from beeai_framework.backend.message import UserMessage, AssistantMessage
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.tools import Tool
from beeai_framework.tools.think import ThinkTool
from dotenv import load_dotenv

# BeeAI SDK imports
from a2a.types import AgentSkill, Message
from beeai_sdk.server import Server
from beeai_sdk.server.context import RunContext
from beeai_sdk.a2a.extensions import (
    AgentDetail, AgentDetailTool, 
    CitationExtensionServer, CitationExtensionSpec,
    TrajectoryExtensionServer, TrajectoryExtensionSpec,
    LLMServiceExtensionServer, LLMServiceExtensionSpec
)

# MCP imports for Jira integration
from mcp import ClientSession
from mcp.types import StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

# Global MCP client for Jira
jira_mcp_client: Optional[ClientSession] = None

# Server and memory management
server = Server()
memories = {}

def get_memory(context: RunContext) -> UnconstrainedMemory:
    """Get or create session memory"""
    context_id = getattr(context, "context_id", getattr(context, "session_id", "default"))
    return memories.setdefault(context_id, UnconstrainedMemory())

@asynccontextmanager
async def lifespan(app):
    """Application lifespan manager for MCP connections"""
    global jira_mcp_client

    try:
        jira_url = os.getenv("JIRA_URL", "https://your-company.atlassian.net")
        jira_username = os.getenv("JIRA_USERNAME", "your.email@company.com")
        jira_token = os.getenv("JIRA_TOKEN", "your_api_token")

        server_params = StdioServerParameters(
            command="uvx",
            args=[
                "mcp-atlassian",
                f"--jira-url={jira_url}",
                f"--jira-username={jira_username}",
                f"--jira-token={jira_token}",
            ],
        )

        jira_mcp_client = await stdio_client(server_params)
        await jira_mcp_client.__aenter__()
        print("✅ Connected to Jira MCP server successfully")

    except Exception as e:
        print(f"❌ Failed to connect to Jira MCP: {e}")
        jira_mcp_client = None

    yield

    if jira_mcp_client:
        try:
            await jira_mcp_client.__aexit__(None, None, None)
            print("✅ Disconnected from Jira MCP server")
        except Exception as e:
            print(f"❌ Error cleaning up Jira MCP: {e}")

# Custom Jira tool for BeeAI Framework
class JiraTool(Tool):
    """Jira integration tool using MCP"""
    
    name = "jira"
    description = "Access Jira data for sprint analysis, velocity tracking, standup reports, and impediment management"
    
    async def __call__(self, action: str, **kwargs) -> str:
        """Execute Jira actions through MCP"""
        if not jira_mcp_client:
            return "❌ Jira MCP client not initialized. Please check your Jira credentials."
        
        try:
            # Map common actions to MCP tool calls
            if action == "get_sprint_info":
                sprint_id = kwargs.get("sprint_id", "active")
                if sprint_id == "active":
                    # Get active sprint
                    result = await jira_mcp_client.call_tool("mcp-atlassian:jira_search", {
                        "jql": "sprint in openSprints()",
                        "fields": "sprint,summary,status,assignee,priority,customfield_10016"
                    })
                else:
                    result = await jira_mcp_client.call_tool("mcp-atlassian:jira_get_sprint_issues", {
                        "sprint_id": sprint_id
                    })
            
            elif action == "get_velocity_data":
                board_id = kwargs.get("board_id", os.getenv("JIRA_BOARD_ID", "1"))
                result = await jira_mcp_client.call_tool("mcp-atlassian:jira_get_sprints_from_board", {
                    "board_id": board_id,
                    "state": "closed"
                })
            
            elif action == "get_blocked_issues":
                result = await jira_mcp_client.call_tool("mcp-atlassian:jira_search", {
                    "jql": "sprint in openSprints() AND (status = 'Blocked' OR labels = 'blocked')",
                    "fields": "summary,assignee,status,priority,updated,labels"
                })
            
            elif action == "search_issues":
                jql = kwargs.get("jql", "")
                fields = kwargs.get("fields", "summary,status,assignee,priority")
                result = await jira_mcp_client.call_tool("mcp-atlassian:jira_search", {
                    "jql": jql,
                    "fields": fields
                })
            
            else:
                return f"❌ Unknown Jira action: {action}"
            
            # Parse MCP result
            if result.content and len(result.content) > 0:
                content = result.content[0]
                if hasattr(content, 'text'):
                    try:
                        data = json.loads(content.text)
                        return self._format_jira_response(action, data)
                    except json.JSONDecodeError:
                        return f"✅ Jira {action}: {content.text}"
                else:
                    return f"✅ Jira {action}: {str(content)}"
            else:
                return f"❌ No content returned from Jira {action}"
                
        except Exception as e:
            return f"❌ Error calling Jira {action}: {str(e)}"
    
    def _format_jira_response(self, action: str, data: Dict) -> str:
        """Format Jira response based on action type"""
        try:
            if action == "get_sprint_info":
                return self._format_sprint_analysis(data)
            elif action == "get_velocity_data":
                return self._format_velocity_data(data)
            elif action == "get_blocked_issues":
                return self._format_impediments(data)
            elif action == "search_issues":
                return self._format_search_results(data)
            else:
                return json.dumps(data, indent=2)
        except Exception as e:
            return f"✅ Raw data: {json.dumps(data, indent=2)}"
    
    def _format_sprint_analysis(self, data: Dict) -> str:
        """Format sprint analysis data"""
        issues = data.get("issues", [])
        total_issues = len(issues)
        
        if total_issues == 0:
            return "📊 **Sprint Analysis**: No issues found in current sprint"
        
        # Calculate metrics
        completed_issues = sum(1 for issue in issues 
                             if issue.get("fields", {}).get("status", {}).get("statusCategory", {}).get("key") == "done")
        
        total_story_points = sum(
            issue.get("fields", {}).get("customfield_10016", 0) or 0 
            for issue in issues
        )
        
        completed_story_points = sum(
            issue.get("fields", {}).get("customfield_10016", 0) or 0 
            for issue in issues 
            if issue.get("fields", {}).get("status", {}).get("statusCategory", {}).get("key") == "done"
        )
        
        progress_percentage = (completed_issues / total_issues * 100) if total_issues > 0 else 0
        story_point_progress = (completed_story_points / total_story_points * 100) if total_story_points > 0 else 0
        
        # Health score
        health_score = max(0, min(100, progress_percentage * 0.8))
        health_emoji = "🟢" if health_score > 70 else "🟡" if health_score > 40 else "🔴"
        
        return f"""📊 **Sprint Health Analysis**

**Health Score: {health_score:.1f}/100** {health_emoji}

**Progress Metrics:**
• Issues: {completed_issues}/{total_issues} ({progress_percentage:.1f}%)
• Story Points: {completed_story_points}/{total_story_points} ({story_point_progress:.1f}%)

**Recommendations:**
{self._generate_recommendations(progress_percentage)}"""
    
    def _format_velocity_data(self, data: Dict) -> str:
        """Format velocity analysis data"""
        sprints = data.get("values", [])[:5]  # Last 5 sprints
        
        if not sprints:
            return "📈 **Velocity Analysis**: No completed sprints found"
        
        sprint_data = []
        for sprint in sprints:
            sprint_data.append({
                "name": sprint.get("name", "Unknown"),
                "velocity": "TBD"  # Would need to calculate from sprint issues
            })
        
        return f"""📈 **Velocity Analysis**

**Recent Sprints:**
{chr(10).join(f"• {s['name']}: {s['velocity']} story points" for s in sprint_data)}

**Next Sprint Prediction:**
• Conservative: TBD story points
• Realistic: TBD story points
• Optimistic: TBD story points"""
    
    def _format_impediments(self, data: Dict) -> str:
        """Format impediments data"""
        issues = data.get("issues", [])
        
        if not issues:
            return "✅ **Impediment Analysis**: No blockers found in current sprint"
        
        impediments = []
        for issue in issues[:5]:  # Top 5 impediments
            fields = issue.get("fields", {})
            impediments.append({
                "key": issue.get("key"),
                "summary": fields.get("summary", "No summary")[:50] + "...",
                "assignee": fields.get("assignee", {}).get("displayName", "Unassigned")
            })
        
        return f"""🚫 **Impediment Analysis**

**Active Blockers ({len(issues)}):**
{chr(10).join(f"• {imp['key']}: {imp['summary']} (Assigned: {imp['assignee']})" for imp in impediments)}

**Resolution Strategies:**
• Review blockers in daily standup
• Escalate external dependencies
• Consider scope adjustments if needed"""
    
    def _format_search_results(self, data: Dict) -> str:
        """Format general search results"""
        issues = data.get("issues", [])
        
        if not issues:
            return "🔍 **Search Results**: No issues found matching criteria"
        
        results = []
        for issue in issues[:10]:  # Top 10 results
            fields = issue.get("fields", {})
            results.append({
                "key": issue.get("key"),
                "summary": fields.get("summary", "No summary")[:60] + "...",
                "status": fields.get("status", {}).get("name", "Unknown"),
                "assignee": fields.get("assignee", {}).get("displayName", "Unassigned")
            })
        
        return f"""🔍 **Search Results ({len(issues)} found):**

{chr(10).join(f"• **{r['key']}**: {r['summary']} [{r['status']}] ({r['assignee']})" for r in results)}"""
    
    def _generate_recommendations(self, progress: float) -> str:
        """Generate sprint recommendations"""
        if progress < 30:
            return "• ⚠️ Sprint significantly behind - urgent scope review needed\n• Consider daily check-ins and impediment removal"
        elif progress < 60:
            return "• 📊 Sprint progress moderate - monitor closely\n• Focus on completing in-progress items"
        else:
            return "• ✅ Sprint on track - maintain current momentum\n• Consider taking on additional scope if capacity allows"

def extract_citations(text: str) -> tuple[list[dict], str]:
    """Extract citations and clean text"""
    citations, offset = [], 0
    pattern = r"\[([^\]]+)\]\(([^)]+)\)"
    
    for match in re.finditer(pattern, text):
        content, url = match.groups()
        start = match.start() - offset

        citations.append({
            "url": url,
            "title": url.split("/")[-1].replace("-", " ").title() or content[:50],
            "description": content[:100] + ("..." if len(content) > 100 else ""),
            "start_index": start, 
            "end_index": start + len(content)
        })
        offset += len(match.group(0)) - len(content)

    return citations, re.sub(pattern, r"\1", text)

def is_casual_greeting(msg: str) -> bool:
    """Check if message is casual greeting"""
    casual_words = {'hey', 'hi', 'hello', 'thanks', 'bye', 'cool', 'nice', 'ok', 'yes', 'no'}
    words = msg.lower().strip().split()
    return len(words) <= 3 and any(w in casual_words for w in words)

@server.agent(
    name="Jira Scrum Master",
    default_input_modes=["text", "text/plain"],
    default_output_modes=["text", "text/plain"],
    detail=AgentDetail(
        interaction_mode="multi-turn",
        user_greeting="Hi! I'm your AI Scrum Master. I can help with sprint analysis, velocity tracking, standup reports, and impediment management using live Jira data. What would you like to explore?",
        version="2.0.0",
        tools=[
            AgentDetailTool(
                name="Sprint Analysis", 
                description="Real-time sprint health monitoring with progress metrics, blocker detection, and actionable recommendations."
            ),
            AgentDetailTool(
                name="Velocity Tracking", 
                description="Historical velocity analysis with trend detection and capacity predictions for future sprints."
            ),
            AgentDetailTool(
                name="Standup Facilitation", 
                description="Daily standup reports with team updates, coordination guidance, and meeting facilitation."
            ),
            AgentDetailTool(
                name="Impediment Management", 
                description="Smart blocker detection, categorization, and resolution strategies for sprint impediments."
            ),
            AgentDetailTool(
                name="Advanced Reasoning", 
                description="Thoughtful analysis and structured recommendations for complex Scrum situations."
            )
        ],
        framework="BeeAI",
        author={
            "name": "Matfej"
        },
        source_code_url="https://github.com/Matfejbat/jira-scrum-master-agent"
    ),
    skills=[
        AgentSkill(
            id="sprint-analysis",
            name="Sprint Analysis",
            description=dedent(
                """\
                Analyzes current sprint health using live Jira data, providing progress metrics,
                blocker identification, and actionable recommendations for sprint success.
                """
            ),
            tags=["Sprint", "Health", "Progress", "Analysis"],
            examples=[
                "What's our current sprint status?",
                "How is our sprint doing?",
                "Give me a sprint health report",
                "What's our sprint progress?",
                "Are we on track for sprint completion?"
            ]
        ),
        AgentSkill(
            id="velocity-tracking",
            name="Velocity Tracking",
            description=dedent(
                """\
                Tracks team velocity trends across multiple sprints and provides capacity
                planning insights with predictions for future sprint planning.
                """
            ),
            tags=["Velocity", "Planning", "Capacity", "Trends"],
            examples=[
                "Show me our velocity trends",
                "What's our average velocity?",
                "How much can we commit to next sprint?",
                "Analyze our team velocity over the last 5 sprints",
                "What's our capacity for the upcoming sprint?"
            ]
        ),
        AgentSkill(
            id="standup-facilitation",
            name="Standup Facilitation",
            description=dedent(
                """\
                Generates daily standup reports and provides team coordination guidance
                by analyzing current work distribution and progress.
                """
            ),
            tags=["Standup", "Daily", "Coordination", "Team"],
            examples=[
                "Generate today's standup report",
                "What's the team working on?",
                "Create a standup summary",
                "Who's working on what today?",
                "Prepare our daily standup meeting"
            ]
        ),
        AgentSkill(
            id="impediment-management",
            name="Impediment Management",
            description=dedent(
                """\
                Identifies, categorizes, and provides resolution strategies for sprint
                blockers and impediments to ensure smooth sprint execution.
                """
            ),
            tags=["Impediments", "Blockers", "Resolution", "Management"],
            examples=[
                "What blockers do we have?",
                "Show me current impediments",
                "Analyze our sprint blockers",
                "What's blocking our progress?",
                "Help me resolve these impediments"
            ]
        )
    ],
)
async def jira_scrum_master(
    input: Message, 
    context: RunContext,
    citation: Annotated[CitationExtensionServer, CitationExtensionSpec()],
    trajectory: Annotated[TrajectoryExtensionServer, TrajectoryExtensionSpec()],
    llm: Annotated[
        LLMServiceExtensionServer, 
        LLMServiceExtensionSpec.single_demand(
            suggested=("ibm/granite-3-3-8b-instruct", "llama3.1", "gpt-4o-mini")
        )
    ]
):
    """
    AI Scrum Master agent built with BeeAI Framework and native Jira integration through MCP.
    
    ### Features
    
    - **Sprint Analysis:** Real-time sprint health monitoring with progress metrics and risk assessment
    - **Velocity Intelligence:** Team velocity trends tracking and capacity predictions
    - **Standup Facilitation:** Automated daily standup reports and team coordination
    - **Impediment Management:** Smart blocker detection with categorization and resolution strategies
    - **Native Jira Integration:** Direct connection to Jira through MCP for real-time data access
    
    ### BeeAI Framework Integration
    
    - **RequirementAgent:** Uses experimental agent with conditional tool requirements
    - **JiraTool:** Custom tool implementing MCP integration for Jira operations
    - **ThinkTool:** Advanced reasoning for complex Scrum situations
    - **Memory Management:** Maintains conversation context with session persistence
    - **Extension Servers:** Full integration with trajectory and citation metadata
    """
    
    user_msg = ""
    
    # Extract text from message parts
    for part in input.parts:
        part_root = part.root
        if part_root.kind == "text":
            user_msg = part_root.text
            break
    
    if not user_msg:
        user_msg = "Hello"
    
    memory = get_memory(context)
    
    yield trajectory.trajectory_metadata(
        title="Processing Request",
        content=f"💬 Analyzing Scrum request: '{user_msg}'"
    )
    
    try:
        await memory.add(UserMessage(user_msg))
        
        if not llm or not llm.data:
            raise ValueError("LLM service extension is required but not available")
            
        llm_config = llm.data.llm_fulfillments.get("default")
        
        if not llm_config:
            raise ValueError("LLM service extension provided but no fulfillment available")
        
        llm_client = OpenAIChatModel(
            model_id=llm_config.api_model,
            base_url=llm_config.api_base,
            api_key=llm_config.api_key,
            parameters=ChatModelParameters(temperature=0.1),
            tool_choice_support=set(),
        )
        
        # Create agent with Jira-specific tools and requirements
        agent = RequirementAgent(
            llm=llm_client, 
            memory=memory,
            tools=[ThinkTool(), JiraTool()],
            requirements=[
                # Always think first for complex analysis
                ConditionalRequirement(
                    ThinkTool, 
                    force_at_step=1, 
                    consecutive_allowed=False,
                    custom_checks=[lambda state: not is_casual_greeting(user_msg)]
                ),
                # Use Jira tool for data-driven requests
                ConditionalRequirement(
                    JiraTool, 
                    max_invocations=3, 
                    consecutive_allowed=False,
                    custom_checks=[lambda state: any(
                        keyword in user_msg.lower() 
                        for keyword in ['sprint', 'velocity', 'standup', 'blocker', 'impediment', 'jira', 'status', 'progress']
                    )]
                )
            ],
            instructions=f"""You are an experienced AI Scrum Master with deep expertise in agile methodologies and Jira data analysis.

Your role is to:
1. **Sprint Analysis**: Monitor sprint health, track progress, identify risks
2. **Velocity Intelligence**: Analyze team velocity trends and provide capacity planning
3. **Standup Facilitation**: Generate daily reports and coordinate team activities  
4. **Impediment Management**: Detect blockers, categorize impediments, suggest resolutions

When using the Jira tool, choose the appropriate action:
- `get_sprint_info`: For sprint status, progress, and health analysis
- `get_velocity_data`: For velocity trends and capacity planning
- `get_blocked_issues`: For impediment and blocker analysis
- `search_issues`: For general Jira queries with custom JQL

Always provide:
- **Data-driven insights** from live Jira information
- **Actionable recommendations** for sprint success
- **Clear metrics** and progress indicators
- **Professional Scrum guidance** based on best practices

Be concise but thorough. Focus on practical advice that helps teams deliver successfully.

Current JIRA Board ID: {os.getenv('JIRA_BOARD_ID', 'not configured')}
Current JIRA Project: {os.getenv('JIRA_PROJECT_KEY', 'not configured')}"""
        )
        
        yield trajectory.trajectory_metadata(
            title="Agent Ready",
            content="🛠️ Scrum Master ready with Jira integration and advanced reasoning"
        )
        
        response_text = ""
        
        # Execute agent with specific configuration for Scrum Master tasks
        async for event, meta in agent.run(
            user_msg,
            execution=AgentExecutionConfig(max_iterations=15, max_retries_per_step=2, total_max_retries=3),
            expected_output="Professional Scrum Master guidance with specific Jira data insights and actionable recommendations."
        ):
            if meta.name == "success" and event.state.steps:
                step = event.state.steps[-1]
                if not step.tool:
                    continue
                    
                tool_name = step.tool.name
                
                if tool_name == "final_answer":
                    response_text += step.input["response"]
                elif tool_name == "jira":
                    action = step.input.get("action", "Unknown")
                    yield trajectory.trajectory_metadata(
                        title="Jira Integration",
                        content=f"🔗 Executed Jira action: {action}"
                    )
                elif tool_name == "think":
                    yield trajectory.trajectory_metadata(
                        title="Analysis",
                        content=f"🧠 {step.input['thoughts']}"
                    )
        
        await memory.add(AssistantMessage(response_text))
        
        # Extract citations if any
        citations, clean_text = extract_citations(response_text)
        
        yield clean_text
        
        if citations:
            yield citation.citation_metadata(citations=citations)
            
        yield trajectory.trajectory_metadata(
            title="Completion",
            content="✅ Scrum Master analysis completed"
        )

    except Exception as e:
        print(f"❌ Error: {e}\n{traceback.format_exc()}")
        yield trajectory.trajectory_metadata(
            title="Error",
            content=f"❌ Error: {e}"
        )
        yield f"🚨 I encountered an error processing your Scrum request: {e}\n\nPlease ensure your Jira credentials are configured correctly and try again."

def run():
    """Start the server"""
    server.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", 8000)))

if __name__ == "__main__":
    run()
