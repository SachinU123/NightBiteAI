# NightBite AI — Daily Progress & Changelog

## 🚀 Milestone: Phases 0–5 Complete
**Date:** 2026-03-30
**Status:** Backend Live, App Shell Functional

### 🟢 Completed
*   **Foundation:** Full project scaffolding for Flutter and FastAPI.
*   **Database:** PostgreSQL 8-table schema live, Alembic migrations configured.
*   **API:** All 12 endpoints (Auth, Devices, Food Events, Insights, Analytics) registered and verified.
*   **Intelligence:** 
    *   NLP Parsing implemented (regex fallback enabled).
    *   Risk Engine active (`FinalRisk = Base × Time × Behavior`).
    *   Template-based Smart Nudge generator complete.
    *   Ingestion pipeline complete (`ManualEntryAdapter`, `NotificationCaptureAdapter`).
*   **Frontend UI:** Built an exclusive dark-themed Flutter interface.
*   **Frontend Logic:** Connected `go_router` and Riverpod 3.x for auth and navigation state mapping. Designed the `PermissionOnboardingScreen` and Tab Shell.

### 🟡 In Progress
*   **Frontend Integration:** The Flutter app is still wired to mock providers (e.g., `SharedPreferences`) for authentication. APIs are stable, but the frontend layer needs to hook up Dio for networking.
*   **Phase 6 (Analytics Dashboard):** Backend aggregates are running efficiently using Pandas, but UI screens for heatmap display need to be created in the main app.

### 🔴 Blockers / Known Limitations
*   *Limitation:* Notification listener works strictly on physical Android devices.
*   *Limitation:* spaCy's English core model currently faces latency loading; temporary regex categorization is handling fallback natively. 

### 🐛 Errors Found & Fixed
*   **Error:** Riverpod 3 `StateProvider` incompatibility. **Fix:** Refactored Auth to use standard Riverpod `Notifier` classes.
*   **Error:** Deprecated standard Flutter themes mapping badly to premium palette. **Fix:** Adopted `surface` vs `background` according to the new `ThemeData`.
*   **Error:** Missing `email-validator` generated a Pydantic module error. **Fix:** Installed `pydantic[email]` within backend constraints.
*   **Error:** `bcrypt` 5.x incompatibilities with `passlib` broke auth startup. **Fix:** Pinned backend to `bcrypt==4.0.1`.

### ➡️ Next Steps (Phase 6 & 7)
1.  **Frontend:** Replace `MockAuthProvider` with genuine API calls to `$API_BASE_URL/auth/login`.
2.  **App State:** Link the Manual Entry frontend flow specifically parsing `FoodAnalysisResponse` to view scores.
3.  **Android Test:** Push an APK to an Android test device to verify background listening hooks correctly into `NotificationCaptureAdapter`.
4.  **Admin View:** Expose the seeded heatmap and summary JSON directly inside an analytics-tab interface.
