# BeeAI Jira Scrum Master Agent

[![CI/CD](https://github.com/Matfejbat/jira-scrum-master-agent/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/Matfejbat/jira-scrum-master-agent/actions)
[![Docker](https://ghcr.io/matfejbat/jira-scrum-master-agent/badge.svg)](https://ghcr.io/matfejbat/jira-scrum-master-agent)

An intelligent AI Scrum Master agent built for the BeeAI Platform with native Jira integration through MCP (Model Context Protocol).

## 🚀 Features

- **📊 Real-time Sprint Analysis** - Monitor sprint health, progress, and risk assessment with live Jira data
- **📈 Velocity Intelligence** - Track team velocity trends and generate capacity predictions  
- **🤝 Automated Standup Facilitation** - Generate daily standup reports and coordinate team activities
- **🚫 Smart Impediment Management** - Detect, categorize, and resolve blockers automatically
- **🔗 Native Jira Integration** - Direct connection to Jira through MCP for real-time data access
- **🤖 BeeAI Platform Ready** - Built for seamless integration with BeeAI's agent ecosystem

## 🏗️ Architecture

```
BeeAI UI ↔ Agent Server ↔ Jira MCP ↔ Jira API
```

This agent leverages:
- **BeeAI Platform SDK** for agent registration and communication
- **MCP (Model Context Protocol)** for direct Jira integration via `mcp-atlassian`
- **Multi-agent Architecture** with specialized agents for different Scrum functions

## 🛠️ Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Jira Cloud/Server with API access
- BeeAI Platform (optional for local development)

### Using BeeAI Platform

```bash
# Add the agent to your BeeAI instance
beeai add https://github.com/Matfejbat/jira-scrum-master-agent

# Run the agent
beeai run jira-scrum-master "What's our sprint status?"
```

### Local Development

```bash
# Clone the repository
git clone https://github.com/Matfejbat/jira-scrum-master-agent.git
cd jira-scrum-master-agent

# Install dependencies
uv sync

# Set up environment
cp .env.example .env
# Edit .env with your Jira credentials

# Install MCP dependencies
uv tool install uvx
uvx install mcp-atlassian

# Run the agent server
uv run uvicorn src.beeai_agents.agent:server.app --reload --host 0.0.0.0 --port 8000
```

## ⚙️ Configuration

### Required Environment Variables

```bash
# Jira Configuration
JIRA_URL=https://your-company.atlassian.net
JIRA_USERNAME=your.email@company.com
JIRA_TOKEN=your_jira_api_token
JIRA_BOARD_ID=1
JIRA_PROJECT_KEY=PROJ

# Agent Configuration  
AGENT_NAME=jira-scrum-master
LOG_LEVEL=INFO
```

### Jira Setup

1. **Generate API Token**:
   - Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
   - Create a new API token
   - Copy the token for `JIRA_TOKEN` environment variable

2. **Required Permissions**:
   - Browse projects
   - Edit issues
   - View development tools
   - Administer projects (for board access)

3. **Find Your Board ID**:
   - Go to your Jira board
   - Check the URL: `https://your-domain.atlassian.net/secure/RapidBoard.jspa?rapidView=123`
   - The number after `rapidView=` is your board ID

## 🤖 Available Agents

The system provides multiple specialized agents:

### 1. Sprint Health Analyzer (`jira-sprint-analyzer`)
Analyzes current sprint progress and provides health insights.

**Example Usage:**
```
"What's our sprint status?"
"How is our current sprint doing?"
"Give me a sprint health report"
```

### 2. Velocity Tracker (`jira-velocity-tracker`)  
Tracks team velocity trends and provides capacity planning.

**Example Usage:**
```
"Show me our velocity trends"
"What's our capacity for next sprint?"
"Analyze our team velocity over the last 5 sprints"
```

### 3. Standup Facilitator (`jira-standup-facilitator`)
Generates daily standup reports and coordination guidance.

**Example Usage:**
```
"Generate today's standup report"
"What's the team working on?"
"Create a standup summary"
```

### 4. Impediment Manager (`jira-impediment-manager`)
Identifies and manages sprint blockers and impediments.

**Example Usage:**
```
"What blockers do we have?"
"Show me current impediments"
"Analyze our sprint blockers"
```

### 5. Comprehensive Scrum Master (`jira-scrum-master`)
Main agent that routes to appropriate functionality based on your request.

**Example Usage:**
```
"Help me with our sprint"
"I need Scrum Master assistance"
"What should I focus on as a Scrum Master?"
```

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test categories
uv run pytest -k "not integration"

# Run integration tests (requires Jira setup)
uv run pytest -k "integration" -v
```

## 🐳 Docker Deployment

### Build Locally

```bash
# Build the image
podman build -t jira-scrum-master .

# Run the container
podman run -p 8000:8000 \
  -e JIRA_URL=https://your-company.atlassian.net \
  -e JIRA_USERNAME=your.email@company.com \
  -e JIRA_TOKEN=your_token \
  -e JIRA_BOARD_ID=1 \
  jira-scrum-master
```

### Using GitHub Container Registry

```bash
# Pull the latest image
docker pull ghcr.io/matfejbat/jira-scrum-master-agent:latest

# Run with environment file
docker run -p 8000:8000 --env-file .env ghcr.io/matfejbat/jira-scrum-master-agent:latest
```

## 🔄 CI/CD Pipeline

This repository includes a comprehensive GitHub Actions pipeline that:

- ✅ **Code Quality Checks** - Runs Black, isort, and mypy
- ✅ **Automated Testing** - Executes pytest test suite
- ✅ **Multi-platform Docker Builds** - Builds for AMD64 and ARM64
- ✅ **Container Registry Push** - Pushes to GitHub Container Registry
- ✅ **Security Scanning** - Runs Trivy vulnerability scans
- ✅ **Deployment Ready** - Automated deployment notifications

The pipeline is triggered on:
- Push to `main` or `develop` branches
- Pull requests to `main`

## 🔧 Development

### Project Structure

```
jira-scrum-master-agent/
├── src/beeai_agents/           # Main agent code
│   ├── __init__.py             # Package initialization
│   └── agent.py                # BeeAI agent implementation
├── tests/                      # Test suite
│   └── test_agent.py          # Agent tests
├── .github/workflows/          # CI/CD pipelines
│   └── ci-cd.yml              # Main CI/CD workflow
├── Dockerfile                  # Container configuration
├── pyproject.toml             # Project metadata and dependencies
├── .env.example               # Environment variable template
└── README.md                  # Project documentation
```

### Adding New Functionality

1. **Create new agent function** in `src/beeai_agents/agent.py`:
   ```python
   @server.agent(
       details={
           "name": "my-new-agent",
           "description": "Description of functionality",
           "ui": PlatformUIAnnotation(...)
       }
   )
   async def my_new_agent(input: Message, context: Context):
       # Implementation here
       yield AgentMessage("Response")
   ```

2. **Add tests** in `tests/test_agent.py`
3. **Update documentation** in README.md
4. **Test locally** with `uv run pytest`
5. **Commit and push** - CI/CD will handle the rest

### Code Quality

The project uses:
- **Black** for code formatting
- **isort** for import sorting  
- **mypy** for type checking
- **pytest** for testing

Run quality checks:
```bash
uv run black src/ tests/
uv run isort src/ tests/
uv run mypy src/
```

## 📊 Monitoring & Observability

### Health Checks

The agent provides health endpoints:
- `GET /health` - Basic health status
- `GET /agents` - List available agents

### Logs

Structured logging is available at different levels:
```bash
# Set log level
export LOG_LEVEL=DEBUG

# Run with debug logging
uv run uvicorn src.beeai_agents.agent:server.app --log-level debug
```

### Metrics

Key metrics tracked:
- Agent response times
- Jira MCP connection status  
- Request success rates
- Error rates by agent type

## 🚀 Deployment Options

### BeeAI Platform

The easiest way to deploy is through the BeeAI Platform:

```bash
# Add from GitHub repository
beeai add https://github.com/Matfejbat/jira-scrum-master-agent

# Or add with specific version tag
beeai add https://github.com/Matfejbat/jira-scrum-master-agent@v1.0.0
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jira-scrum-master
spec:
  replicas: 1
  selector:
    matchLabels:
      app: jira-scrum-master
  template:
    metadata:
      labels:
        app: jira-scrum-master
    spec:
      containers:
      - name: agent
        image: ghcr.io/matfejbat/jira-scrum-master-agent:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: jira-credentials
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

### Docker Compose

```yaml
version: '3.8'

services:
  jira-scrum-master:
    image: ghcr.io/matfejbat/jira-scrum-master-agent:latest
    ports:
      - "8000:8000"
    environment:
      - JIRA_URL=${JIRA_URL}
      - JIRA_USERNAME=${JIRA_USERNAME}
      - JIRA_TOKEN=${JIRA_TOKEN}
      - JIRA_BOARD_ID=${JIRA_BOARD_ID}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## 🛡️ Security

- **API Token Security** - Store Jira tokens securely using environment variables or secrets management
- **Container Scanning** - Automated vulnerability scanning with Trivy
- **Non-root Container** - Docker image runs as non-root user for security
- **Minimal Dependencies** - Only includes required packages to reduce attack surface

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run the test suite: `uv run pytest`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📄 License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support & Troubleshooting

### Common Issues

**"Jira MCP client not initialized"**
- Verify `JIRA_URL`, `JIRA_USERNAME`, and `JIRA_TOKEN` are set correctly
- Ensure `mcp-atlassian` is installed: `uvx install mcp-atlassian`
- Check Jira API token permissions

**"No active sprint found"**
- Verify `JIRA_BOARD_ID` points to the correct board
- Ensure there's an active sprint in your Jira board
- Check user permissions for board access

**CI/CD Pipeline Failures**
- Check GitHub Actions logs for specific error messages
- Verify all required secrets are configured
- Ensure Docker build context is correct

### Getting Help

- 📖 Check the [BeeAI Documentation](https://docs.beeai.dev)
- 🐛 Report issues on [GitHub Issues](https://github.com/Matfejbat/jira-scrum-master-agent/issues)
- 💬 Join the [BeeAI Community Discord](https://discord.gg/beeai)

---

**Built with ❤️ for agile teams everywhere**
