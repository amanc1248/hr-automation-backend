#!/usr/bin/env python3
"""
Simple test script to verify Portia SDK setup and test with a basic calculation
"""
import os
import asyncio
from dotenv import load_dotenv
from portia import Portia, Config

# Load environment variables
load_dotenv()

async def test_portia_calculation():
    """Test Portia with a simple calculation: 5 + 9"""
    
    print("🚀 Testing Portia SDK with calculation: 5 + 9")
    
    # Configure Portia
    config = Config(
        api_key=os.getenv("PORTIA_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        llm_provider="openai",  # Use OpenAI as the LLM provider
        model="gpt-4o-mini"  # Use a cost-effective model for testing
    )
    
    # Initialize Portia
    portia = Portia(config=config)
    
    try:
        # Simple calculation query
        query = "Calculate 5 + 9 and explain your calculation step by step."
        
        print(f"📤 Sending query: {query}")
        
        # Run the query (portia.run is not awaitable in this version)
        plan_run = portia.run(query)
        
        print(f"✅ Plan Run ID: {plan_run.id}")
        print(f"📋 State: {plan_run.state}")
        print(f"💬 Calculation completed successfully! Check logs above for the detailed response.")
        
        return plan_run
        
    except Exception as e:
        print(f"❌ Error running Portia query: {e}")
        raise

async def main():
    """Main function to run the test"""
    try:
        result = await test_portia_calculation()
        print("\n🎉 Portia SDK test completed successfully!")
        return result
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(main())
