"""
Script to check and fix user roles in the database
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import get_async_session
from app.models.user import UserModel, UserRole


async def check_and_fix_roles():
    """Check all users and fix role case issues"""
    
    async for session in get_async_session():
        # Get all users
        result = await session.execute(select(UserModel))
        users = result.scalars().all()
        
        print(f"\n{'='*60}")
        print(f"Found {len(users)} users in database")
        print(f"{'='*60}\n")
        
        for user in users:
            print(f"User: {user.username}")
            print(f"  ID: {user.id}")
            print(f"  Email: {user.email}")
            print(f"  Role (raw): {user.role}")
            print(f"  Role (type): {type(user.role)}")
            print(f"  Role (value): {user.role.value if isinstance(user.role, UserRole) else 'N/A'}")
            print(f"  Is Admin: {user.is_admin()}")
            print(f"  Is Active: {user.is_active}")
            print()


async def main():
    """Main function"""
    try:
        await check_and_fix_roles()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
