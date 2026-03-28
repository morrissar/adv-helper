import logging
import asyncio
from database import init_db
from config import TOKEN
from aiogram import Bot, Dispatcher
from handlers import router, scheduler

logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await init_db()
    asyncio.create_task(scheduler(bot))
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())