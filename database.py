"""
Database layer for user data, verification, and caching
Uses SQLite for simplicity (can be upgraded to PostgreSQL)
"""

import aiosqlite
import json
from typing import Optional, Dict, List
from datetime import datetime


class Database:
    """Handles all database operations for user management and caching"""
    
    def __init__(self, db_path: str = "bloxstake.db"):
        self.db_path = db_path
        self.connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        """Initialize database connection and create tables"""
        self.connection = await aiosqlite.connect(self.db_path)
        self.connection.row_factory = aiosqlite.Row
        await self._create_tables()
    
    async def close(self):
        """Close database connection"""
        if self.connection:
            await self.connection.close()
    
    async def _create_tables(self):
        """Create all necessary database tables"""
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                description TEXT,
                thumbnail_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id INTEGER NOT NULL UNIQUE,
                roblox_user_id INTEGER,
                verification_code TEXT NOT NULL,
                verified BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP,
                FOREIGN KEY (roblox_user_id) REFERENCES users(user_id)
            )
        """)
        
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roblox_user_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                game_name TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                asset_id TEXT,
                holder TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (roblox_user_id) REFERENCES users(user_id)
            )
        """)
        
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS trade_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roblox_user_id INTEGER NOT NULL,
                trade_type TEXT NOT NULL,
                items TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (roblox_user_id) REFERENCES users(user_id)
            )
        """)
        
        await self.connection.commit()
    
    # User Management
    async def insert_or_update_user(self, user_id: int, username: str) -> bool:
        """Insert or update Roblox user info"""
        try:
            await self.connection.execute("""
                INSERT INTO users (user_id, username, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, username))
            await self.connection.commit()
            return True
        except Exception as e:
            print(f"Error inserting/updating user: {e}")
            return False
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by Roblox user ID"""
        async with self.connection.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by Roblox username"""
        async with self.connection.execute(
            "SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def update_user_description(self, user_id: int, description: str) -> bool:
        """Update cached user description"""
        try:
            await self.connection.execute("""
                UPDATE users SET description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (description, user_id))
            await self.connection.commit()
            return True
        except Exception as e:
            print(f"Error updating description: {e}")
            return False
    
    async def get_user_description(self, user_id: int) -> Optional[str]:
        """Get cached user description"""
        async with self.connection.execute(
            "SELECT description FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["description"] if row else None
    
    async def update_user_thumbnail(self, user_id: int, thumbnail_url: str) -> bool:
        """Update cached user thumbnail"""
        try:
            await self.connection.execute("""
                UPDATE users SET thumbnail_url = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (thumbnail_url, user_id))
            await self.connection.commit()
            return True
        except Exception as e:
            print(f"Error updating thumbnail: {e}")
            return False
    
    async def get_user_thumbnail(self, user_id: int) -> Optional[str]:
        """Get cached user thumbnail"""
        async with self.connection.execute(
            "SELECT thumbnail_url FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["thumbnail_url"] if row else None
    
    # Verification Management
    async def create_verification(self, discord_id: int, roblox_user_id: int, code: str) -> bool:
        """Create verification entry"""
        try:
            await self.connection.execute("""
                INSERT INTO verifications (discord_id, roblox_user_id, verification_code)
                VALUES (?, ?, ?)
                ON CONFLICT(discord_id) DO UPDATE SET
                    roblox_user_id = excluded.roblox_user_id,
                    verification_code = excluded.verification_code,
                    verified = 0,
                    created_at = CURRENT_TIMESTAMP
            """, (discord_id, roblox_user_id, code))
            await self.connection.commit()
            return True
        except Exception as e:
            print(f"Error creating verification: {e}")
            return False
    
    async def get_verification(self, discord_id: int) -> Optional[Dict]:
        """Get verification entry by Discord ID"""
        async with self.connection.execute(
            "SELECT * FROM verifications WHERE discord_id = ?", (discord_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def mark_verified(self, discord_id: int) -> bool:
        """Mark user as verified"""
        try:
            await self.connection.execute("""
                UPDATE verifications 
                SET verified = 1, verified_at = CURRENT_TIMESTAMP
                WHERE discord_id = ?
            """, (discord_id,))
            await self.connection.commit()
            return True
        except Exception as e:
            print(f"Error marking verified: {e}")
            return False
    
    async def get_roblox_id_by_discord(self, discord_id: int) -> Optional[int]:
        """Get verified Roblox user ID from Discord ID"""
        async with self.connection.execute(
            "SELECT roblox_user_id FROM verifications WHERE discord_id = ? AND verified = 1",
            (discord_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["roblox_user_id"] if row else None
    
    # Inventory Management
    async def add_item_to_inventory(self, roblox_user_id: int, item_name: str, 
                                    game_name: str, quantity: int = 1, 
                                    asset_id: str = None, holder: str = None) -> bool:
        """Add item to user's inventory"""
        try:
            await self.connection.execute("""
                INSERT INTO inventory (roblox_user_id, item_name, game_name, quantity, asset_id, holder)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (roblox_user_id, item_name, game_name, quantity, asset_id, holder))
            await self.connection.commit()
            return True
        except Exception as e:
            print(f"Error adding item to inventory: {e}")
            return False
    
    async def get_inventory(self, roblox_user_id: int) -> List[Dict]:
        """Get user's inventory"""
        async with self.connection.execute(
            "SELECT * FROM inventory WHERE roblox_user_id = ? ORDER BY created_at DESC",
            (roblox_user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def remove_item_from_inventory(self, roblox_user_id: int, item_name: str, quantity: int = 1) -> bool:
        """Remove item from inventory (for withdrawals)"""
        try:
            await self.connection.execute("""
                DELETE FROM inventory 
                WHERE id IN (
                    SELECT id FROM inventory 
                    WHERE roblox_user_id = ? AND item_name = ?
                    LIMIT ?
                )
            """, (roblox_user_id, item_name, quantity))
            await self.connection.commit()
            return True
        except Exception as e:
            print(f"Error removing item from inventory: {e}")
            return False
    
    # Trade History
    async def create_trade_record(self, roblox_user_id: int, trade_type: str, items: list) -> bool:
        """Create trade history record"""
        try:
            items_json = json.dumps(items)
            await self.connection.execute("""
                INSERT INTO trade_history (roblox_user_id, trade_type, items)
                VALUES (?, ?, ?)
            """, (roblox_user_id, trade_type, items_json))
            await self.connection.commit()
            return True
        except Exception as e:
            print(f"Error creating trade record: {e}")
            return False
    
    async def complete_trade(self, trade_id: int) -> bool:
        """Mark trade as completed"""
        try:
            await self.connection.execute("""
                UPDATE trade_history 
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (trade_id,))
            await self.connection.commit()
            return True
        except Exception as e:
            print(f"Error completing trade: {e}")
            return False
