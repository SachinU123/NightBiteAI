# NightBite AI — Environment Variables Guide

The application requires environment variables for both the Flutter frontend and FastAPI backend.

## 📱 Frontend (`.env`)

Place this `.env` file in the root of the `nightbite/` flutter project.

```ini
# The base URL of your FastAPI backend.
# For Android Emulators, use 10.0.2.2 instead of localhost
API_BASE_URL=http://10.0.2.2:8000/api/v1

# Enable detailed logging and development features
DEBUG=true
```

## ⚙️ Backend (`.env`)

Place this `.env` file in the root of the `backend/` project.

```ini
# PostgreSQL Connection URL
DATABASE_URL=postgresql://nightbite_user:nightbite_pass@localhost:5432/nightbite_db

# JWT Secret Key (generate a strong random string in production)
SECRET_KEY=dev_secret_key_nightbite
ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 7 days

# CORS Settings (allow Flutter app to connect)
ALLOWED_ORIGINS=["*"]

# App Settings
APP_NAME="NightBite AI"
APP_ENV=development
DEBUG=True

# Firebase push notification keys (Future implementation)
FCM_SERVER_KEY=your_fcm_key_here
```
