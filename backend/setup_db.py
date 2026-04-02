"""
NightBite AI — Database Setup Script
Creates PostgreSQL database + user, then runs Alembic migrations.
Run this instead of manual psql commands.
"""
import subprocess
import sys
import os

DB_NAME = "nightbite_db"
DB_USER = "nightbite_user"
DB_PASS = "nightbite_pass"


def run(cmd, check=True):
    print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(f"    {result.stdout.strip()}")
    if result.returncode != 0 and check:
        print(f"  ⚠ Error: {result.stderr.strip()}")
    return result


def setup():
    print("🗄️  NightBite AI — Database Setup\n")

    # Try to create user and database
    print("Creating PostgreSQL user and database...")
    run(f'psql -U postgres -c "CREATE USER {DB_USER} WITH PASSWORD \'{DB_PASS}\';" 2>NUL', check=False)
    run(f'psql -U postgres -c "CREATE DATABASE {DB_NAME} OWNER {DB_USER};" 2>NUL', check=False)
    run(f'psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER};" 2>NUL', check=False)

    print("\nRunning Alembic migrations...")
    result = run(r".\venv\Scripts\alembic upgrade head")
    if result.returncode != 0:
        print("\n❌ Migration failed. Make sure PostgreSQL is running and credentials are correct.")
        print("   Check .env for DATABASE_URL")
        sys.exit(1)

    print("\n✅ Database ready!")
    print("\nNext: Run seed.py for demo data, then start the server:")
    print("  .\\venv\\Scripts\\python seed.py")
    print("  .\\venv\\Scripts\\uvicorn app.main:app --reload")


if __name__ == "__main__":
    setup()
