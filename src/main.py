from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

# Import our modules
import sys
import os
sys.path.append(os.path.dirname(__file__))

from core.config import settings, validate_settings
from core.database import check_database_connection, close_database
from api import auth, users, gmail, workflows, emails, approvals, jobs, candidates

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))

# Disable SQLAlchemy engine logging for performance
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("🚀 Starting HR Automation Backend...")
    
    try:
        # Validate configuration
        validate_settings()
        
        # Test database connection
        print("🔌 Testing database connection...")
        db_success = await check_database_connection()
        
        if db_success:
            print("✅ Database connection successful!")
        else:
            print("⚠️  Database connection failed, but continuing...")
        
        print("✅ Backend startup complete!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        print(f"❌ Startup failed: {e}")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down HR Automation Backend...")
    await close_database()
    print("✅ Shutdown complete!")

# Create FastAPI app
app = FastAPI(
    title="HR Automation Backend",
    description="AI-powered hiring automation system with Portia integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:5173",  # Local development
        "https://hiring-automation-frontend.vercel.app",  # Vercel production
        "https://hiring-automation-frontend-3ly6vhsk0-amanc1248s-projects.vercel.app",  # Vercel deployment URL
        "https://*.vercel.app",  # All Vercel preview deployments
        "https://hiring-automation-frontend.vercel.app",  # Main Vercel domain
        "https://hiring-automation-frontend-git-main-amanc124s-projects.vercel.app",  # Git main branch
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Force HTTPS in production
if os.getenv("FORCE_HTTPS", "false").lower() == "true":
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    
    # Add HTTPS redirect middleware
    from fastapi import Request
    from fastapi.responses import RedirectResponse
    
    @app.middleware("http")
    async def https_redirect(request: Request, call_next):
        if request.url.scheme == "http":
            # Redirect HTTP to HTTPS
            url = str(request.url)
            url = url.replace("http://", "https://", 1)
            return RedirectResponse(url, status_code=301)
        return await call_next(request)

# Include API routers
app.include_router(auth.router, prefix="/api", tags=["authentication"])
app.include_router(users.router, tags=["users"])
app.include_router(gmail.router, tags=["gmail"])
app.include_router(workflows.router, tags=["workflows"])
app.include_router(emails.router, tags=["emails"])
app.include_router(approvals.router, tags=["approvals"])
app.include_router(candidates.router, tags=["candidates"])

# Health check endpoint for Railway
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "service": "hr-automation-backend"}

# HTTPS test endpoint
@app.get("/https-test")
async def https_test():
    """Test endpoint to verify HTTPS configuration"""
    return {
        "message": "HTTPS is working!",
        "scheme": "https",
        "force_https": os.getenv("FORCE_HTTPS", "false"),
        "timestamp": "2025-08-26T16:17:47Z"
    }
app.include_router(jobs.router, tags=["jobs"])

# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "HR Automation Backend",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
        "features": [
            "Company Registration",
            "User Authentication",
            "Job Management",
            "Candidate Tracking",
            "AI Interviews",
            "Workflow Automation",
            "Email Integration"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db_status = await check_database_connection()
        
        return {
            "status": "healthy" if db_status else "degraded",
            "database": "connected" if db_status else "disconnected",
            "version": "1.0.0",
            "services": {
                "authentication": "active",
                "database": "connected" if db_status else "disconnected",
                "api": "active"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "version": "1.0.0"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
