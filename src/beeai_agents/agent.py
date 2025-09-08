"""
BeeAI Platform Jira Scrum Master Agent
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

# BeeAI Platform imports
from beeai_sdk.server import Server
from beeai_sdk.server.context import Context
from a2a.types import Message
from beeai_sdk.a2a.types import AgentMessage
from beeai_sdk.utils.message import get_message_text
from beeai_sdk.models import PlatformUIAnnotation, PlatformUIType, AgentToolInfo

# MCP imports for Jira integration
from mcp import ClientSession
from mcp.types import StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global MCP client for Jira
jira_mcp_client: Optional[ClientSession] = None

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
        logger.info("Connected to Jira MCP server successfully")

    except Exception as e:
        logger.error(f"Failed to connect to Jira MCP: {e}")
        jira_mcp_client = None

    yield

    if jira_mcp_client:
        try:
            await jira_mcp_client.__aexit__(None, None, None)
            logger.info("Disconnected from Jira MCP server")
        except Exception as e:
            logger.error(f"Error cleaning up Jira MCP: {e}")

# Initialize the server with lifespan
server = Server(lifespan=lifespan)
app = server.app

async def call_jira_mcp(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to call Jira MCP tools"""
    if not jira_mcp_client:
        return {"error": "Jira MCP client not initialized"}
    
    try:
        result = await jira_mcp_client.call_tool(tool_name, arguments)
        
        if result.content and len(result.content) > 0:
            content = result.content[0]
            if hasattr(content, 'text'):
                try:
                    return json.loads(content.text)
                except json.JSONDecodeError:
                    return {"text_content": content.text}
            else:
                return {"content": str(content)}
        else:
            return {"error": "No content returned from MCP tool"}
            
    except Exception as e:
        logger.error(f"Error calling Jira MCP tool {tool_name}: {e}")
        return {"error": str(e)}

@server.agent(
    details={
        "name": "jira-sprint-analyzer",
        "description": "Analyzes sprint health, progress, and provides actionable insights using live Jira data",
        "ui": PlatformUIAnnotation(
            ui_type=PlatformUIType.CHAT,
            display_name="Sprint Health Analyzer",
            user_greeting="Hi! I'm your Sprint Health Analyzer. I can check your current sprint progress, identify blockers, and provide actionable recommendations. What would you like to know about your sprint?",
            tools=[
                AgentToolInfo(
                    name="Sprint Analysis",
                    description="Real-time sprint health monitoring with progress metrics and risk assessment"
                )
            ]
        )
    }
)
async def jira_sprint_analyzer(input: Message, context: Context):
    """Analyzes sprint health and provides detailed insights"""
    user_message = get_message_text(input)
    
    try:
        # Extract sprint ID from message or use active sprint
        sprint_id = await _extract_sprint_id(user_message)
        
        # Get sprint information
        sprint_info = await call_jira_mcp("get_sprint", {"sprint_id": sprint_id})
        if "error" in sprint_info:
            yield AgentMessage(f"Error getting sprint info: {sprint_info['error']}")
            return
        
        # Get sprint issues
        sprint_issues = await call_jira_mcp("search_issues", {
            "jql": f"sprint = {sprint_id}",
            "fields": ["status", "summary", "assignee", "customfield_10016", "labels", "priority"]
        })
        
        if "error" in sprint_issues:
            yield AgentMessage(f"Error getting sprint issues: {sprint_issues['error']}")
            return
        
        # Analyze sprint health
        analysis = await _analyze_sprint_health(sprint_info, sprint_issues)
        
        # Format response
        response = _format_sprint_analysis(analysis)
        yield AgentMessage(response)
        
    except Exception as e:
        logger.error(f"Error in sprint analyzer: {e}")
        yield AgentMessage(f"I encountered an error analyzing the sprint: {str(e)}")

@server.agent(
    details={
        "name": "jira-velocity-tracker",
        "description": "Tracks team velocity trends and provides capacity planning insights",
        "ui": PlatformUIAnnotation(
            ui_type=PlatformUIType.CHAT,
            display_name="Velocity Tracker",
            user_greeting="Hello! I'm your Velocity Tracker. I analyze your team's velocity patterns and help with capacity planning. Ask me about velocity trends, sprint predictions, or team performance!",
            tools=[
                AgentToolInfo(
                    name="Velocity Analysis",
                    description="Historical velocity analysis with trend detection and capacity predictions"
                )
            ]
        )
    }
)
async def jira_velocity_tracker(input: Message, context: Context):
    """Tracks and analyzes team velocity trends"""
    user_message = get_message_text(input)
    
    try:
        # Extract parameters from message
        sprint_count = _extract_sprint_count(user_message)
        board_id = _extract_board_id(user_message)
        
        # Get completed sprints
        completed_sprints = await call_jira_mcp("get_board_sprints", {
            "board_id": board_id,
            "state": "closed"
        })
        
        if "error" in completed_sprints:
            yield AgentMessage(f"Error getting sprints: {completed_sprints['error']}")
            return
        
        # Calculate velocity for recent sprints
        velocity_data = await _calculate_velocity_trends(completed_sprints, sprint_count)
        
        # Generate predictions
        predictions = _generate_velocity_predictions(velocity_data)
        
        # Format response
        response = _format_velocity_analysis(velocity_data, predictions)
        yield AgentMessage(response)
        
    except Exception as e:
        logger.error(f"Error in velocity tracker: {e}")
        yield AgentMessage(f"I encountered an error analyzing velocity: {str(e)}")

@server.agent(
    details={
        "name": "jira-standup-facilitator",
        "description": "Generates daily standup reports and facilitates team coordination",
        "ui": PlatformUIAnnotation(
            ui_type=PlatformUIType.CHAT,
            display_name="Standup Facilitator",
            user_greeting="Good morning! I'm your Standup Facilitator. I can generate today's standup report, identify team coordination needs, and help facilitate your daily meetings. Ready to get started?",
            tools=[
                AgentToolInfo(
                    name="Standup Generation",
                    description="Daily standup reports with team updates and coordination guidance"
                )
            ]
        )
    }
)
async def jira_standup_facilitator(input: Message, context: Context):
    """Generates standup reports and facilitates team coordination"""
    user_message = get_message_text(input)
    
    try:
        # Get active sprint issues
        active_issues = await call_jira_mcp("search_issues", {
            "jql": "sprint in openSprints() AND assignee is not EMPTY",
            "fields": ["summary", "status", "assignee", "updated", "priority"]
        })
        
        if "error" in active_issues:
            yield AgentMessage(f"Error getting active issues: {active_issues['error']}")
            return
        
        # Generate standup data
        standup_data = await _generate_standup_data(active_issues)
        
        # Format response
        response = _format_standup_report(standup_data)
        yield AgentMessage(response)
        
    except Exception as e:
        logger.error(f"Error in standup facilitator: {e}")
        yield AgentMessage(f"I encountered an error generating standup data: {str(e)}")

@server.agent(
    details={
        "name": "jira-impediment-manager",
        "description": "Identifies and manages sprint impediments and blockers",
        "ui": PlatformUIAnnotation(
            ui_type=PlatformUIType.CHAT,
            display_name="Impediment Manager",
            user_greeting="Hi! I'm your Impediment Manager. I help identify blockers, categorize impediments, and suggest resolution strategies. What impediments are you facing?",
            tools=[
                AgentToolInfo(
                    name="Impediment Analysis",
                    description="Smart blocker detection with categorization and resolution strategies"
                )
            ]
        )
    }
)
async def jira_impediment_manager(input: Message, context: Context):
    """Identifies and manages sprint impediments"""
    user_message = get_message_text(input)
    
    try:
        # Get blocked issues
        blocked_issues = await call_jira_mcp("search_issues", {
            "jql": "sprint in openSprints() AND (status = 'Blocked' OR labels = 'blocked')",
            "fields": ["summary", "assignee", "status", "priority", "updated", "labels"]
        })
        
        if "error" in blocked_issues:
            yield AgentMessage(f"Error getting blocked issues: {blocked_issues['error']}")
            return
        
        # Analyze impediments
        impediment_analysis = await _analyze_impediments(blocked_issues)
        
        # Format response
        response = _format_impediment_analysis(impediment_analysis)
        yield AgentMessage(response)
        
    except Exception as e:
        logger.error(f"Error in impediment manager: {e}")
        yield AgentMessage(f"I encountered an error analyzing impediments: {str(e)}")

# Helper functions for data processing

async def _extract_sprint_id(message: str) -> str:
    """Extract sprint ID from user message or return active sprint"""
    # Simple extraction - could be enhanced with NLP
    if "sprint" in message.lower() and any(char.isdigit() for char in message):
        # Extract numeric sprint ID
        import re
        numbers = re.findall(r'\d+', message)
        if numbers:
            return numbers[0]
    
    # Default to finding active sprint
    active_sprints = await call_jira_mcp("search_issues", {
        "jql": "sprint in openSprints()",
        "fields": ["sprint"]
    })
    
    if "issues" in active_sprints and active_sprints["issues"]:
        # Extract sprint ID from first issue - simplified logic
        return "1"  # Fallback - would extract from actual sprint field
    
    return "1"  # Fallback sprint ID

def _extract_sprint_count(message: str) -> int:
    """Extract number of sprints to analyze from message"""
    import re
    numbers = re.findall(r'(\d+)\s*sprints?', message.lower())
    return int(numbers[0]) if numbers else 5

def _extract_board_id(message: str) -> str:
    """Extract board ID from message or use default"""
    return os.getenv("JIRA_BOARD_ID", "1")

async def _analyze_sprint_health(sprint_info: Dict, sprint_issues: Dict) -> Dict:
    """Analyze sprint health metrics"""
    issues = sprint_issues.get("issues", [])
    total_issues = len(issues)
    
    if total_issues == 0:
        return {"status": "no_issues", "message": "No issues found in sprint"}
    
    # Calculate basic metrics
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
    
    # Calculate progress
    progress_percentage = (completed_issues / total_issues * 100) if total_issues > 0 else 0
    story_point_progress = (completed_story_points / total_story_points * 100) if total_story_points > 0 else 0
    
    # Identify blockers
    blockers = [issue for issue in issues 
               if "blocked" in issue.get("fields", {}).get("status", {}).get("name", "").lower() or
                  any("blocked" in label.lower() for label in issue.get("fields", {}).get("labels", []))]
    
    # Calculate health score
    health_score = _calculate_health_score(progress_percentage, len(blockers))
    
    return {
        "sprint_info": sprint_info,
        "metrics": {
            "total_issues": total_issues,
            "completed_issues": completed_issues,
            "total_story_points": total_story_points,
            "completed_story_points": completed_story_points,
            "progress_percentage": round(progress_percentage, 1),
            "story_point_progress": round(story_point_progress, 1)
        },
        "blockers": blockers,
        "health_score": health_score,
        "recommendations": _generate_sprint_recommendations(progress_percentage, len(blockers))
    }

def _calculate_health_score(progress: float, blocker_count: int) -> float:
    """Calculate sprint health score"""
    base_score = progress * 0.8
    blocker_penalty = min(blocker_count * 10, 30)
    return max(0, min(100, round(base_score - blocker_penalty, 1)))

def _generate_sprint_recommendations(progress: float, blocker_count: int) -> List[str]:
    """Generate actionable sprint recommendations"""
    recommendations = []
    
    if progress < 50:
        recommendations.append("Sprint progress is behind - consider daily check-ins and scope review")
    
    if blocker_count > 0:
        recommendations.append(f"{blocker_count} blockers need immediate attention")
    
    if blocker_count > 3:
        recommendations.append("High number of blockers - schedule impediment removal session")
    
    if progress > 80:
        recommendations.append("Sprint is on track - maintain current momentum")
    
    return recommendations

async def _calculate_velocity_trends(completed_sprints: Dict, sprint_count: int) -> List[Dict]:
    """Calculate velocity trends for recent sprints"""
    sprints = completed_sprints.get("values", [])[:sprint_count]
    velocity_data = []
    
    for sprint in sprints:
        sprint_id = sprint.get("id")
        sprint_issues = await call_jira_mcp("search_issues", {
            "jql": f"sprint = {sprint_id} AND status = Done",
            "fields": ["customfield_10016"]
        })
        
        velocity = sum(
            issue.get("fields", {}).get("customfield_10016", 0) or 0
            for issue in sprint_issues.get("issues", [])
        )
        
        velocity_data.append({
            "sprint_id": sprint_id,
            "sprint_name": sprint.get("name"),
            "velocity": velocity,
            "start_date": sprint.get("startDate"),
            "end_date": sprint.get("endDate")
        })
    
    return velocity_data

def _generate_velocity_predictions(velocity_data: List[Dict]) -> Dict:
    """Generate velocity predictions"""
    velocities = [s["velocity"] for s in velocity_data if s["velocity"] > 0]
    
    if not velocities:
        return {"error": "No velocity data available"}
    
    avg_velocity = sum(velocities) / len(velocities)
    
    return {
        "next_sprint": {
            "conservative": int(avg_velocity * 0.8),
            "realistic": int(avg_velocity * 0.9),
            "optimistic": int(avg_velocity * 1.1)
        },
        "average_velocity": round(avg_velocity, 1),
        "confidence": "high" if len(velocities) >= 5 else "medium"
    }

async def _generate_standup_data(active_issues: Dict) -> Dict:
    """Generate standup data from active issues"""
    issues = active_issues.get("issues", [])
    
    # Organize by team member
    team_updates = {}
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    for issue in issues:
        fields = issue.get("fields", {})
        assignee = fields.get("assignee", {}).get("displayName", "Unassigned")
        updated_date = fields.get("updated", "")
        status_category = fields.get("status", {}).get("statusCategory", {}).get("key")
        
        if assignee not in team_updates:
            team_updates[assignee] = {
                "completed_yesterday": [],
                "planned_today": [],
                "in_progress": []
            }
        
        # Check if updated yesterday (completed work)
        if yesterday in updated_date and status_category == "done":
            team_updates[assignee]["completed_yesterday"].append({
                "key": issue.get("key"),
                "summary": fields.get("summary")
            })
        
        # Issues in progress (planned for today)
        if status_category == "indeterminate":
            team_updates[assignee]["in_progress"].append({
                "key": issue.get("key"),
                "summary": fields.get("summary")
            })
    
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "team_updates": team_updates,
        "summary": {
            "active_team_members": len(team_updates),
            "total_in_progress": sum(len(update["in_progress"]) for update in team_updates.values())
        }
    }

async def _analyze_impediments(blocked_issues: Dict) -> Dict:
    """Analyze impediments and categorize them"""
    issues = blocked_issues.get("issues", [])
    
    impediments = []
    categories = {"technical": 0, "external": 0, "process": 0, "resource": 0}
    
    for issue in issues:
        fields = issue.get("fields", {})
        summary = fields.get("summary", "").lower()
        
        # Simple categorization based on keywords
        category = "technical"
        if any(keyword in summary for keyword in ["waiting", "dependency", "external"]):
            category = "external"
        elif any(keyword in summary for keyword in ["approval", "process", "review"]):
            category = "process"
        elif any(keyword in summary for keyword in ["resource", "capacity", "availability"]):
            category = "resource"
        
        categories[category] += 1
        
        impediments.append({
            "key": issue.get("key"),
            "summary": fields.get("summary"),
            "category": category,
            "assignee": fields.get("assignee", {}).get("displayName", "Unassigned"),
            "priority": fields.get("priority", {}).get("name", "Medium")
        })
    
    return {
        "total_impediments": len(impediments),
        "impediments": impediments,
        "categories": categories,
        "resolution_strategies": _generate_resolution_strategies(categories)
    }

def _generate_resolution_strategies(categories: Dict) -> List[str]:
    """Generate resolution strategies based on impediment categories"""
    strategies = []
    
    if categories["technical"] > 0:
        strategies.append("Technical impediments: Assign senior developers or create technical spikes")
    
    if categories["external"] > 0:
        strategies.append("External dependencies: Follow up with external teams and escalate if needed")
    
    if categories["process"] > 0:
        strategies.append("Process blockers: Review approval workflows and expedite where possible")
    
    if categories["resource"] > 0:
        strategies.append("Resource constraints: Reassign work or bring in additional capacity")
    
    return strategies

# Response formatting functions

def _format_sprint_analysis(analysis: Dict) -> str:
    """Format sprint analysis into readable response"""
    metrics = analysis["metrics"]
    health_score = analysis["health_score"]
    blockers = analysis["blockers"]
    recommendations = analysis["recommendations"]
    
    response = f"""## Sprint Health Analysis

**Health Score: {health_score}/100** {'🟢' if health_score > 70 else '🟡' if health_score > 40 else '🔴'}

### Progress Metrics
- **Issues**: {metrics['completed_issues']}/{metrics['total_issues']} ({metrics['progress_percentage']}%)
- **Story Points**: {metrics['completed_story_points']}/{metrics['total_story_points']} ({metrics['story_point_progress']}%)

### Blockers
{f"**{len(blockers)} Active Blockers**" if blockers else "✅ No active blockers"}
"""

    if blockers:
        for blocker in blockers[:3]:  # Show top 3 blockers
            response += f"\n- {blocker.get('key')}: {blocker.get('fields', {}).get('summary', 'No summary')}"

    if recommendations:
        response += "\n\n### Recommendations\n"
        for rec in recommendations:
            response += f"- {rec}\n"

    return response

def _format_velocity_analysis(velocity_data: List[Dict], predictions: Dict) -> str:
    """Format velocity analysis into readable response"""
    velocities = [s["velocity"] for s in velocity_data]
    avg_velocity = sum(velocities) / len(velocities) if velocities else 0
    
    response = f"""## Velocity Analysis

### Recent Sprint Velocities
"""
    
    for sprint in velocity_data[-5:]:  # Show last 5 sprints
        response += f"- **{sprint['sprint_name']}**: {sprint['velocity']} story points\n"
    
    response += f"\n**Average Velocity**: {avg_velocity:.1f} story points\n"
    
    if "next_sprint" in predictions:
        pred = predictions["next_sprint"]
        response += f"""
### Next Sprint Predictions
- **Conservative**: {pred['conservative']} story points
- **Realistic**: {pred['realistic']} story points  
- **Optimistic**: {pred['optimistic']} story points

**Confidence Level**: {predictions.get('confidence', 'medium')}
"""
    
    return response

def _format_standup_report(standup_data: Dict) -> str:
    """Format standup data into readable response"""
    team_updates = standup_data["team_updates"]
    summary = standup_data["summary"]
    
    response = f"""## Daily Standup Report - {standup_data['date']}

### Team Summary
- **Active Members**: {summary['active_team_members']}
- **Work in Progress**: {summary['total_in_progress']} items

### Team Updates
"""
    
    for member, updates in team_updates.items():
        if member != "Unassigned":
            response += f"\n**{member}**:\n"
            
            if updates["completed_yesterday"]:
                response += "  ✅ *Completed yesterday*:\n"
                for item in updates["completed_yesterday"]:
                    response += f"    - {item['key']}: {item['summary'][:50]}...\n"
            
            if updates["in_progress"]:
                response += "  🔄 *Working on today*:\n"
                for item in updates["in_progress"]:
                    response += f"    - {item['key']}: {item['summary'][:50]}...\n"
    
    return response

def _format_impediment_analysis(analysis: Dict) -> str:
    """Format impediment analysis into readable response"""
    impediments = analysis["impediments"]
    categories = analysis["categories"]
    strategies = analysis["resolution_strategies"]
    
    response = f"""## Impediment Analysis

### Summary
- **Total Impediments**: {analysis['total_impediments']}
- **By Category**: Technical ({categories['technical']}), External ({categories['external']}), Process ({categories['process']}), Resource ({categories['resource']})

### Active Impediments
"""
    
    for imp in impediments:
        response += f"- **{imp['key']}** ({imp['category']}): {imp['summary'][:60]}...\n"
        response += f"  *Assigned to: {imp['assignee']} | Priority: {imp['priority']}*\n"
    
    if strategies:
        response += "\n### Resolution Strategies\n"
        for strategy in strategies:
            response += f"- {strategy}\n"
    
    return response

# Keep the original multi-agent approach as a comprehensive agent
@server.agent(
    details={
        "name": "jira-scrum-master",
        "description": "Comprehensive AI Scrum Master with all functionality integrated",
        "ui": PlatformUIAnnotation(
            ui_type=PlatformUIType.CHAT,
            display_name="Jira Scrum Master",
            user_greeting="Hello! I'm your comprehensive AI Scrum Master. I can help with sprint analysis, velocity tracking, standup facilitation, and impediment management. What would you like to explore today?",
            tools=[
                AgentToolInfo(name="Sprint Analysis", description="Complete sprint health monitoring"),
                AgentToolInfo(name="Velocity Tracking", description="Team velocity analysis and predictions"),
                AgentToolInfo(name="Standup Facilitation", description="Daily standup reports and coordination"),
                AgentToolInfo(name="Impediment Management", description="Blocker identification and resolution")
            ]
        )
    }
)
async def jira_scrum_master(input: Message, context: Context):
    """Comprehensive Scrum Master agent that routes to appropriate functionality"""
    user_message = get_message_text(input).lower()
    
    try:
        # Route based on user intent
        if any(keyword in user_message for keyword in ["sprint", "health", "progress", "status"]):
            async for response in jira_sprint_analyzer(input, context):
                yield response
                
        elif any(keyword in user_message for keyword in ["velocity", "capacity", "prediction", "planning"]):
            async for response in jira_velocity_tracker(input, context):
                yield response
                
        elif any(keyword in user_message for keyword in ["standup", "daily", "meeting", "coordination"]):
            async for response in jira_standup_facilitator(input, context):
                yield response
                
        elif any(keyword in user_message for keyword in ["blocker", "impediment", "blocked", "stuck"]):
            async for response in jira_impediment_manager(input, context):
                yield response
                
        else:
            # Default overview response
            yield AgentMessage("""## Jira Scrum Master - How can I help?

I can assist you with:

**Sprint Analysis** - Check sprint health, progress, and get recommendations
*Try: "What's our sprint status?" or "How is our current sprint doing?"*

**Velocity Tracking** - Analyze team velocity trends and capacity planning  
*Try: "Show me our velocity trends" or "What's our capacity for next sprint?"*

**Standup Facilitation** - Generate daily standup reports and team coordination
*Try: "Generate today's standup report" or "What's the team working on?"*

**Impediment Management** - Identify blockers and resolution strategies
*Try: "What blockers do we have?" or "Show me current impediments"*

What would you like to explore?""")
            
    except Exception as e:
        logger.error(f"Error in comprehensive scrum master: {e}")
        yield AgentMessage(f"I encountered an error: {str(e)}. Please try again or be more specific about what you need.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(server.app, host="0.0.0.0", port=8000)
