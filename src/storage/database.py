"""SQLite 数据库 — 存储已处理的公告和信号，避免重复处理。"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

import aiosqlite

from src.models.announcement import Announcement
from src.models.signal import Signal

logger = logging.getLogger(__name__)

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS announcements (
    id TEXT PRIMARY KEY,
    stock_code TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT,
    publish_time TEXT,
    source TEXT,
    url TEXT,
    processed_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    announcement_id TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    action TEXT NOT NULL,
    strength TEXT NOT NULL,
    reason TEXT,
    key_data TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (announcement_id) REFERENCES announcements(id)
);

CREATE INDEX IF NOT EXISTS idx_ann_stock ON announcements(stock_code);
CREATE INDEX IF NOT EXISTS idx_ann_date ON announcements(publish_time);
CREATE INDEX IF NOT EXISTS idx_sig_stock ON signals(stock_code);
CREATE INDEX IF NOT EXISTS idx_sig_date ON signals(created_at);
"""


class Database:
    """异步 SQLite 数据库操作。"""

    def __init__(self, db_path: str = "data/filings.db"):
        self.db_path = db_path

    async def init(self) -> None:
        """初始化数据库表结构。"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(_INIT_SQL)
            await db.commit()
        logger.info("数据库初始化完成: %s", self.db_path)

    async def is_processed(self, announcement_id: str) -> bool:
        """检查公告是否已处理过。"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM announcements WHERE id = ?", (announcement_id,)
            )
            return await cursor.fetchone() is not None

    async def filter_new(self, announcements: list[Announcement]) -> list[Announcement]:
        """过滤出未处理的公告。"""
        new_ones = []
        for ann in announcements:
            if not await self.is_processed(ann.id):
                new_ones.append(ann)
        return new_ones

    async def save_announcement(self, announcement: Announcement) -> None:
        """保存已处理的公告。"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR IGNORE INTO announcements
                   (id, stock_code, stock_name, title, category, publish_time, source, url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    announcement.id,
                    announcement.stock_code,
                    announcement.stock_name,
                    announcement.title,
                    announcement.category.value,
                    announcement.publish_time.isoformat(),
                    announcement.source,
                    announcement.url,
                ),
            )
            await db.commit()

    async def save_signal(self, signal: Signal) -> None:
        """保存投资信号。"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO signals
                   (announcement_id, stock_code, stock_name, action, strength, reason, key_data)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    signal.announcement_id,
                    signal.stock_code,
                    signal.stock_name,
                    signal.action.value,
                    signal.strength.value,
                    signal.reason,
                    json.dumps(signal.key_data, ensure_ascii=False),
                ),
            )
            await db.commit()
