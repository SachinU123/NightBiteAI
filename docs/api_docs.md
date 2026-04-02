# NightBite AI — API Documentation

This outlines the key endpoints from the backend API.
The interactive Swagger configuration is available locally at `http://localhost:8000/docs` while the server is running.

## 🔐 AUTH

### `POST /api/v1/auth/register`
Creates a new user account.
*   **Request:** `{"name": "...", "email": "...", "password": "..."}`
*   **Response:** JWT Token and user info (Status 201). Returns 409 if email exists.

### `POST /api/v1/auth/login`
Authenticates a user.
*   **Request:** `{"email": "...", "password": "..."}`
*   **Response:** JWT Token (Status 200). Returns 401 on failure.

### `GET /api/v1/auth/me`
Retrieves current user. Requires Bearer Token.

---

## 📱 DEVICE

### `POST /api/v1/devices/register`
Saves FCM token and initial notification listener state.
*   **Request:** `{"platform": "android", "device_name": "...", "fcm_token": "...", "notification_listener_enabled": bool}`

### `POST /api/v1/devices/notification-status`
Updates notification listener status on demand.
*   **Request:** `{"notification_listener_enabled": bool, "device_id": int (optional)}`

---

## 🍔 FOOD EVENTS

### `POST /api/v1/food-events/manual-entry`
Manually ingest and score a food entry. Runs full NLP + Risk extraction synchronously.
*   **Request:** `{"food_text": "...", "meal_type": "...", "latitude": float, "longitude": float}`
*   **Response (FoodAnalysisResponse):**
```json
{
  "event_id": 1,
  "source_type": "manual",
  "source_app": null,
  "normalized_food_text": "cheese burst pizza",
  "food_category": "fast_food",
  "risk_tags": ["high_cheese", "category_fast_food"],
  "risk_score": 9.0,
  "risk_band": "critical",
  "smart_nudge": "This is flagged as critical-risk...",
  "healthier_swap": "Try a wrap instead.",
  "event_timestamp": "2026-03-30..."
}
```

### `POST /api/v1/food-events/notification-capture`
Android notification capture route. Accepts noisy raw descriptions (e.g., app order messages). Still attempts to extract food details via NLP and regex. 
*   **Request:** `{"source_app": "swiggy", "raw_notification_text": "...", "raw_food_text": "...", "event_timestamp": "..."}`
*   **Response:** Full `FoodAnalysisResponse` generated using NLP extraction heuristics. 

### `GET /api/v1/food-events/latest`
Gets the most recent food entry analysis for the logged-in user. Returns `null` if no records exist. 

### `GET /api/v1/food-events/history`
Retrieves a paginated list of food records.
*   **Params:** `?page=1&page_size=20`

---

## 📊 INSIGHTS

### `GET /api/v1/user-insights`
Provides 7-day personal analytics (risk trends, most common foods). 
*   **Response Example:**
```json
{
  "weekly_avg_risk": 5.4,
  "high_risk_count_this_week": 2,
  "total_events_this_week": 8,
  "common_food_category": "indian_fried",
  "risk_trend": "stable"
}
```

---

## 🗺️ ANALYTICS

### `GET /api/v1/analytics/heatmap`
Returns aggregated (anonymized) geospatial risk trends for the heatmap feature. Data is calculated via Pandas grouping.
*   **Params:** `?days=7`
*   **Response Example:**
```json
{
  "cells": [
    {
      "location_key": "pin:400001",
      "lat_bin": null,
      "lon_bin": null,
      "order_count": 12,
      "avg_risk": 7.4,
      "high_risk_count": 8,
      "hotspot_intensity": 4.93
    }
  ],
  "total_cells": 1
}
```

### `GET /api/v1/analytics/dashboard-summary`
Aggregates admin/system-wide stats (e.g. today's events, high risk thresholds).
