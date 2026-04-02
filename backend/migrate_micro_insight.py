"""Migration: add micro_insight column to nudges table"""
import sys
sys.path.insert(0, '.')
from app.db.session import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE nudges ADD COLUMN IF NOT EXISTS micro_insight TEXT"))
    conn.commit()
    print("✅ Migration OK: nudges.micro_insight added")
