# NightBite AI — Troubleshooting Guide

## 🛠️ Common Setup Issues

### "Failed to build iOS app" or "No valid signing identity"
*   **Cause:** Standard iOS development hurdles. As NightBite AI targets Android primary listeners, we recommend using Android.
*   **Fix:** Launch on a physical Android device or a fully featured Android emulator.

### Flutter compilation issues (e.g. `Riverpod` errors)
*   **Cause:** Misaligned dependency versions or deprecated properties.
*   **Fix:** Run `flutter clean && flutter pub get`. The codebase is verified against Dart SDK `>=3.0.0` and `flutter_riverpod` `^3.0.0`.

## 🌐 Backend Connection Issues

### Flutter App says "Network Error" or "Connection Refused"
*   **Cause:** The emulator cannot access `localhost` or the physical device isn't on the same network.
*   **Fix:** Ensure your `API_BASE_URL` in `.env` is set to `http://10.0.2.2:8000/api/v1` for Android emulators. For physical devices, find your IPv4 address (e.g., `http://192.168.1.50:8000/api/v1`) and ensure both are on the same WiFi.

### Backend fails to start: `ModuleNotFoundError`
*   **Cause:** Virtual environment isn't activated, or dependencies are missing.
*   **Fix:** Activate your venv (`venv\Scripts\activate`) and run `pip install -r requirements.txt`. Install `pydantic[email]` if specifically missing.

### Backend fails to start: `bcrypt ValueError`
*   **Cause:** `passlib` is incompatible with `bcrypt==5.0.0`.
*   **Fix:** The environment must have `bcrypt==4.0.1` installed.
    ```bash
    pip install "bcrypt==4.0.1" --force-reinstall
    ```

### Error: `[Errno 13] Permission denied: ...\venv\Scripts\python.exe`
*   **Cause:** You are trying to recreate the virtual environment (`python -m venv venv`) while the FastAPI server is already running. Windows locks the `python.exe` file while it is in use.
*   **Fix:** The virtual environment is already created! You can skip the setup steps and simply activate it (`venv\Scripts\activate`) or stop the running server (Ctrl+C) if you genuinely need to recreate it.

## 🗄️ Database & Migration Issues

### `sqlalchemy.exc.OperationalError`
*   **Cause:** PostgreSQL server is not running or credentials are wrong.
*   **Fix:** Start your local PostgreSQL server. Ensure `DATABASE_URL` matches your local setup `postgresql://user:pass@localhost:5432/db`. Consider using the automated setup script (`python setup_db.py`).

### Alembic `Target database is not up to date`
*   **Cause:** The database was modified outside of migrations.
*   **Fix:** Usually, you can stamp the head or drop the tables and restart: `alembic stamp head`.

## 🔔 Android Notification Issues

### App isn't catching notifications
*   **Cause:** Android strictly disables Notification Access by default for security. The system kills background tasks without proper onboarding.
*   **Fix:** 
    1.  Ensure you passed the `PermissionOnboardingScreen` and toggled the setting ON.
    2.  Check if battery optimization is enabled (Android kills listeners if not whitelisted). Go to App Info > Battery > Unrestricted.
    3.  Confirm the incoming notification is from a supported app (`zomato`, `swiggy`, `blinkit` etc.).

## 🎭 Pre-Demo Verification Checklist

Before taking the app live, ALWAYS verify:
1.  **Backend is running:** `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
2.  **Health Check Passes:** Open `http://localhost:8000/health` in your browser.
3.  **Logs are clean:** The backend terminal isn't throwing auth warnings.
4.  **Device IP Match:** The mobile app's `.env` URL points to the correct network location of the backend.
5.  **Seeded Data:** If showing the analytics view, confirm you previously ran `python seed.py` so the heatmaps aren't empty.
