# NightBite AI — Setup Guide

This guide covers everything you need to run NightBite AI locally for development and demonstration.

## 📥 General Prerequisites

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-repo/nightbite-ai.git
    cd nightbite-ai
    ```
2.  **Environment Files:** Ensure you properly configure both frontend and backend environment variables. Refer to [Environment Guide](env_guide.md).

## 📱 Frontend (Flutter app)

### Prerequisites
*   Flutter SDK (stable channel, >= 3.0)
*   Dart SDK
*   Android Studio (with Android SDK and emulator set up)
*   *(Optional)* physical Android device for real notification-listener testing

### Setup Steps
1.  Navigate to the flutter app folder:
    ```bash
    cd nightbite
    ```
2.  Install dependencies:
    ```bash
    flutter pub get
    ```
3.  Configure Environment:
    Create `.env` based on `.env.example` in the root of the flutter project.

### Running the App
1.  Start an Android Emulator or connect a physical Android device.
2.  Run the app:
    ```bash
    flutter run
    ```
*Note: iOS is supported for the UI, but the core notification-listener feature is strictly Android-only due to OS-level sandboxing.*

## ⚙️ Backend (FastAPI)

### Prerequisites
*   Python 3.11+
*   PostgreSQL 14+ running locally or in Docker

### Setup Steps
1.  Navigate to the backend folder:
    ```bash
    cd backend
    ```
2.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Install NLP Core:
    ```bash
    python -m spacy download en_core_web_sm
    ```
    *(If spaCy fails to install or load, the app has a graceful fallback to regex-based categorization).*

### Database Setup & Migrations
You can use the helper script or run commands manually.

**Using Helper Script:**
```bash
python setup_db.py
```

**Manual Creation:**
```sql
CREATE USER nightbite_user WITH PASSWORD 'nightbite_pass';
CREATE DATABASE nightbite_db OWNER nightbite_user;
GRANT ALL PRIVILEGES ON DATABASE nightbite_db TO nightbite_user;
```
Then run migrations:
```bash
alembic upgrade head
```

### Seeding Demo Data (Highly Recommended)
To populate the database with fake users, food events, and hotspot densities:
```bash
python seed.py
```

### Running the Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
View testing docs at: `http://localhost:8000/docs`

## 🔔 Notes on Notification Listener (Android)
To test the real notification capture:
1. You must run the app on a physical Android device or a fully configured emulator with Google Play Services.
2. The user must manually grant "Notification Access" in Android System Settings. The app's `PermissionOnboardingScreen` directs users to this page.
3. Once granted, simulate a food delivery notification (e.g., via `adb` or an app like Zomato/Swiggy).

*If you do not have target apps, fall back to the "Manual Entry" flow during demo.*
