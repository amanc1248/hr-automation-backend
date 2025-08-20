# HR Automation Backend

AI-powered hiring automation system built with FastAPI and Portia AI framework.

## Features

- **FastAPI Backend** - Modern, fast web framework with automatic API documentation
- **Portia AI Integration** - Multi-agent workflows for hiring automation
- **Supabase Database** - PostgreSQL database with real-time capabilities
- **Human-in-the-Loop** - AI automation with human oversight at critical points
- **Multi-LLM Support** - OpenAI, Anthropic, Google GenAI compatibility

## Quick Start

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp env.example .env

# Edit .env with your API keys:
# - Supabase credentials
# - Portia API key
# - LLM API key (OpenAI/Anthropic/Google)
# - External service keys (LinkedIn, Gmail, etc.)
```

### 3. Database Setup

1. Create a Supabase project at https://supabase.com
2. Run the database schema from `../database_schema.sql`
3. Update `.env` with your Supabase credentials

### 4. Run Development Server

```bash
# Start FastAPI server
python -m src.main

# Or with uvicorn directly
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Project Structure

```
backend/
├── src/
│   ├── main.py              # FastAPI application entry point
│   ├── config/              # Configuration management
│   │   ├── settings.py      # Environment variables and settings
│   │   └── database.py      # Supabase connection
│   ├── api/                 # FastAPI route handlers
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── jobs.py          # Job management endpoints
│   │   ├── candidates.py    # Candidate processing endpoints
│   │   ├── interviews.py    # Interview management endpoints
│   │   └── plan_runs.py     # Portia workflow endpoints
│   ├── services/            # Business logic services
│   │   └── portia_service.py # Portia AI orchestration
│   ├── agents/              # Portia AI agents (TODO)
│   ├── tools/               # Custom Portia tools (TODO)
│   ├── models/              # Pydantic data models (TODO)
│   └── utils/               # Utility functions (TODO)
├── requirements.txt         # Python dependencies
├── env.example             # Environment variables template
└── README.md               # This file
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user
- `POST /api/auth/logout` - User logout

### Jobs
- `POST /api/jobs/` - Create job posting
- `GET /api/jobs/` - List jobs
- `GET /api/jobs/{id}` - Get job details
- `POST /api/jobs/{id}/publish` - Publish job to platforms

### Candidates
- `GET /api/candidates/` - List candidates
- `GET /api/candidates/{id}` - Get candidate details
- `POST /api/candidates/{id}/screen` - Screen candidate with AI
- `POST /api/candidates/{id}/approve` - Approve candidate
- `POST /api/candidates/{id}/reject` - Reject candidate

### Interviews
- `POST /api/interviews/` - Create interview
- `GET /api/interviews/` - List interviews
- `POST /api/interviews/{id}/schedule` - Schedule interview
- `POST /api/interviews/{id}/conduct-ai` - Conduct AI interview

### Plan Runs (Portia Workflows)
- `POST /api/plan-runs/` - Create workflow
- `GET /api/plan-runs/` - List workflows
- `GET /api/plan-runs/{id}` - Get workflow status
- `POST /api/plan-runs/{id}/resolve-clarification` - Resolve human approval

## Environment Variables

### Required
```bash
# Supabase
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# Portia AI
PORTIA_API_KEY=your_portia_api_key

# LLM (choose one)
OPENAI_API_KEY=your_openai_api_key
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key
# OR  
GOOGLE_API_KEY=your_google_api_key

# Security
SECRET_KEY=your_secret_key_here
```

### Optional
```bash
# External integrations
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
GMAIL_CLIENT_ID=your_gmail_client_id
GMAIL_CLIENT_SECRET=your_gmail_client_secret
ELEVENLABS_API_KEY=your_elevenlabs_api_key

# Application settings
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO
```

## Development

### Code Quality
```bash
# Format code
black src/

# Lint code  
flake8 src/

# Type checking
mypy src/
```

### Testing
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src
```

## Deployment

### Production Configuration
1. Set `ENVIRONMENT=production`
2. Set `DEBUG=False`
3. Use strong `SECRET_KEY`
4. Configure proper CORS origins
5. Use production database

### Docker (Optional)
```bash
# Build image
docker build -t hr-automation-backend .

# Run container
docker run -p 8000:8000 --env-file .env hr-automation-backend
```

## Next Steps

This is the foundation setup. Next todos:
1. ✅ **Backend Environment Setup** - COMPLETED
2. **Portia Configuration** - Configure Portia SDK with environment variables
3. **Supabase Integration** - Set up database connectivity  
4. **Pydantic Models** - Create data models
5. **Custom Portia Tools** - Build hiring-specific tools
6. **Portia Agents** - Create specialized agents
7. **Complete API Implementation** - Implement all endpoints
8. **Testing** - Add comprehensive tests

## Support

For issues or questions:
1. Check the logs: `tail -f logs/app.log`
2. Verify environment variables are set correctly
3. Ensure all services (Supabase, Portia) are accessible
4. Check API documentation at `/docs`
