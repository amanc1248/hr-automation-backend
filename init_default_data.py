#!/usr/bin/env python3
"""
Initialize default data only
"""

import asyncio
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def main():
    """Initialize default data"""
    print("📊 Initializing Default Data")
    print("=" * 30)
    
    try:
        from core.migrations import init_default_data
        
        success = await init_default_data()
        
        if success:
            print("\n🎉 SUCCESS: Default data initialized!")
        else:
            print("\n❌ FAILED: Could not initialize default data")
            
        return success
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
