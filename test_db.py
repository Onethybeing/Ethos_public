import os
from dotenv import load_dotenv
load_dotenv('C:/Users/soura/ethos/Ethos/backend/.env')
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
async def test():
    e=create_async_engine(os.getenv('POSTGRES_URL'))
    async with e.connect() as c:
        await c.execute(text('SELECT 1'))
        print('DB Works!')
asyncio.run(test())
