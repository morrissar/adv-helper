import aiosqlite
from datetime import datetime

DATABASE_PATH = 'adv_helper.db'

async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                channel_id TEXT NOT NULL,
                channel_username TEXT,
                title TEXT,
                FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                text_content TEXT,
                media_type TEXT,
                media_file_id TEXT,
                caption TEXT,
                status TEXT DEFAULT 'pending',
                scheduled_at TIMESTAMP,
                duration_hours INTEGER,
                sent_at TIMESTAMP,
                sent_message_id INTEGER,
                FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE
            )
        ''')
        await db.commit()

async def add_user(user_id: int, username: str = None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            'INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)',
            (user_id, username)
        )
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)) as cursor:
            return await cursor.fetchone()

async def add_channel(owner_id: int, channel_id: str, channel_username: str = None, title: str = None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            'INSERT INTO channels (owner_id, channel_id, channel_username, title) VALUES (?, ?, ?, ?)',
            (owner_id, channel_id, channel_username, title)
        )
        await db.commit()

async def get_user_channels(owner_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            'SELECT id, channel_id, channel_username, title FROM channels WHERE owner_id = ?',
            (owner_id,)
        ) as cursor:
            return await cursor.fetchall()

async def get_channel_by_id(channel_db_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            'SELECT id, channel_id, channel_username, title FROM channels WHERE id = ?',
            (channel_db_id,)
        ) as cursor:
            return await cursor.fetchone()

async def add_post(channel_db_id: int, text_content: str = None, media_type: str = None,
                   media_file_id: str = None, caption: str = None,
                   scheduled_at: datetime = None, duration_hours: int = None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            '''INSERT INTO posts 
               (channel_id, text_content, media_type, media_file_id, caption, scheduled_at, duration_hours, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')''',
            (channel_db_id, text_content, media_type, media_file_id, caption, scheduled_at, duration_hours)
        )
        await db.commit()
        return cursor.lastrowid

async def get_pending_posts():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            'SELECT id, channel_id, text_content, media_type, media_file_id, caption, sent_message_id '
            'FROM posts WHERE status = "pending" AND scheduled_at <= datetime("now")'
        ) as cursor:
            return await cursor.fetchall()

async def get_sent_posts_to_delete():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            '''SELECT id, channel_id, sent_message_id, scheduled_at, duration_hours
               FROM posts
               WHERE status = 'sent'
                 AND datetime(sent_at, '+' || duration_hours || ' hours') <= datetime("now")'''
        ) as cursor:
            return await cursor.fetchall()

async def update_post_sent(post_id: int, sent_message_id: int, sent_at: datetime):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            'UPDATE posts SET status = "sent", sent_message_id = ?, sent_at = ? WHERE id = ?',
            (sent_message_id, sent_at, post_id)
        )
        await db.commit()

async def delete_post(post_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('DELETE FROM posts WHERE id = ?', (post_id,))
        await db.commit()

async def get_user_stats(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            '''SELECT COUNT(*) FROM posts p
               JOIN channels c ON p.channel_id = c.id
               WHERE c.owner_id = ?''',
            (user_id,)
        ) as cursor:
            posts_count = (await cursor.fetchone())[0]
        channels = await get_user_channels(user_id)
        return posts_count, channels
