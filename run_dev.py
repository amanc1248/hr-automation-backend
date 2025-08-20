#!/usr/bin/env python3
"""
Development server runner for HR Automation Backend.
Provides easy way to start the development server with proper configuration.
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    """Run the development server"""
    
    # Check if .env file exists
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        print("❌ .env file not found!")
        print("📝 Please copy env.example to .env and configure your API keys")
        print("   cp env.example .env")
        return 1
    
    print("🚀 Starting HR Automation Backend...")
    print("📊 API Documentation will be available at:")
    print("   • Swagger UI: http://localhost:8001/docs")
    print("   • ReDoc: http://localhost:8001/redoc")
    print("   • Health Check: http://localhost:8001/health")
    print()
    
    # Run the server
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    exit(main())
