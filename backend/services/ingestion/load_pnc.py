import asyncio
import json
import os
from sqlalchemy.dialects.postgresql import insert
from db.postgres import UserConstitution, AsyncSessionLocal

async def load_mock():
    async with AsyncSessionLocal() as session:
        path = r"C:\Users\soura\ethos\Ethos\ethosnews\pnc_onboarding\mock_db_pnc.json"
        if not os.path.exists(path):
            print("File not found")
            return
            
        with open(path) as f:
            data = json.load(f)
            
        for user_data in data:
            stmt = insert(UserConstitution).values(
                user_id=user_data['user_id'],
                constitution=user_data
            )
            # Update if exists
            stmt = stmt.on_conflict_do_update(
                index_elements=['user_id'],
                set_={'constitution': stmt.excluded.constitution}
            )
            await session.execute(stmt)
            
        await session.commit()
        print('Mock user loaded successfully!')

if __name__ == "__main__":
    asyncio.run(load_mock())
