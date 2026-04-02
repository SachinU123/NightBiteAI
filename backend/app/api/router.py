"""
NightBite AI — API Router

Mounts all route modules under /api/v1.
"""
from fastapi import APIRouter
from app.api import auth, devices, food_events, insights, analytics, notifications, chat, ai_coach

api_router = APIRouter()

# Auth + device management
api_router.include_router(auth.router)
api_router.include_router(devices.router)

# Core food event flows
api_router.include_router(food_events.router)
api_router.include_router(notifications.router)

# Insights + analytics
api_router.include_router(insights.router)
api_router.include_router(analytics.router)

# AI Coach — new structured endpoints + legacy chat
api_router.include_router(ai_coach.router)
api_router.include_router(chat.router)
