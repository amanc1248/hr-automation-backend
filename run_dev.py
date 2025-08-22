#!/usr/bin/env python3
"""
Development server with hot reload
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting HR Automation Backend (Development Mode)")
    print("📍 Server will be available at: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔄 Hot reload enabled - changes will restart the server")
    print("=" * 60)
    
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["src"],
        log_level="info"
    )
