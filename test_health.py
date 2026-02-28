import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
from app.main import get_facial_system

async def test():
    try:
        sys = get_facial_system()
        print("Got system:", sys)
        if not sys.is_initialized:
            success = sys.initialize({
                'MASTER_KEY': os.getenv('MASTER_KEY'),
                'FERNET_KEY': os.getenv('FERNET_KEY'),
                'DATABASE_URL': os.getenv('DATABASE_URL')
            })
            print("Initialized:", success)
        
        from app.database import get_db
        db = next(get_db())
        from app.models.user import User
        count = db.query(User).count()
        print("DB Users:", count)
        
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test())
