import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.database import AsyncSessionLocal
from models.user import Profile, User
from sqlalchemy import select

async def check_profiles():
    async with AsyncSessionLocal() as db:
        # Check profiles
        result = await db.execute(select(Profile))
        profiles = result.scalars().all()
        
        print(f"Found {len(profiles)} profiles:")
        for profile in profiles:
            print(f'Profile: {profile.email}')
            print(f'  ID: {profile.id}')
            print(f'  Password Hash: {"SET" if profile.password_hash else "NOT SET"}')
            print(f'  Active: {profile.is_active}')
            print('---')
        
        # Check old User table
        try:
            result = await db.execute(select(User))
            users = result.scalars().all()
            
            print(f"\nFound {len(users)} users in old User table:")
            for user in users:
                print(f'User: {user.email}')
                print(f'  ID: {user.id}')
                print(f'  Password Hash: {"SET" if user.password_hash else "NOT SET"}')
                print(f'  Profile ID: {user.profile_id}')
                print(f'  Active: {user.is_active}')
                print('---')
        except Exception as e:
            print(f"Error checking User table: {e}")

if __name__ == "__main__":
    asyncio.run(check_profiles())
