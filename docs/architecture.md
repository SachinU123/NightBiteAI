# NightBite AI — Architecture Overview

NightBite AI follows a clean, decoupled client-server architecture.

## 📱 Frontend (Mobile App - Flutter)

The Flutter mobile application is designed to be mobile-first and deeply integrated with the Android operating system (specifically, the Notification Listener Service).

*   **State Management:** `flutter_riverpod` (v3 compatible) provides reactive dependency injection and state tracking.
*   **Routing:** `go_router` handles navigation and route guards (e.g., Auth vs Main Shell).
*   **Design System:** Built using an exclusive, premium dark-themed color palette (`AppColors`, `AppTheme`).
*   **Components:** Organized by feature (Auth, Permissions, Main flows).

## ⚙️ Backend (API Server - FastAPI)

The backend is built in Python (FastAPI) prioritizing speed, typing, and modularity.

*   **Framework:** FastAPI for rapid API development and auto-generated OpenAPI documentation.
*   **Database:** PostgreSQL.
*   **ORM Layer:** SQLAlchemy.
*   **Migrations:** Alembic.

### 🧠 Intelligence Layer
The backend decouples raw data ingestion from AI/computation.

1.  **Ingestion Adapters (`ingestion_adapters.py`):** An Adapter pattern standardizes incoming food events.
    *   `ManualEntryAdapter`
    *   `NotificationCaptureAdapter`
2.  **NLP Service (`nlp_service.py`):** Uses **spaCy** (with a graceful regex fallback) to extract the primary food item, identify its category (e.g., `fast_food`, `indian_fried`), and attach risk tags (e.g., `high_sugar`).
3.  **Risk Engine (`risk_engine.py`):** Computes a deterministic score across three axes:
    *   **Base Risk:** Inherited from the food category/tags.
    *   **Time Multiplier:** Scales the risk based on the hour of the day (e.g., eating at 2 AM applies a 1.4x penalty).
    *   **Behavior Multiplier:** (Future) Scales risk based on recent user habits.
    *   **Formula:** `FinalRisk = BaseFoodRisk × TimeMultiplier × BehaviorMultiplier`
4.  **Nudge Generator (`nudge_generator.py`):** Uses a template-based system to select specific, supportive feedback and suggest healthier swaps depending on the user's `risk_band`.

---

## 📂 Folder Structure

### Backend
```text
backend/
├── app/
│   ├── api/        # FastAPI routers (auth, devices, food_events, insights, analytics)
│   ├── core/       # Config, JWT security, dependency injection
│   ├── db/         # SQLAlchemy base + session factory
│   ├── models/     # 8-table schema (Users, Devices, FoodEvents, Analytics...)
│   ├── schemas/    # Pydantic data contracts (e.g., FoodAnalysisResponse)
│   ├── services/   # Business logic (NLP, Risk Engine, Ingestion Adapters)
│   └── main.py     # FastAPI app instantiation
├── alembic/        # Migration scripts
├── seed.py         # DB population script
└── setup_db.py     # Initialization utility
```

### Frontend
```text
nightbite/
├── lib/
│   ├── core/
│   │   ├── router/    # go_router configuration
│   │   ├── theme/     # App colors, text styles, dark theme
│   ├── features/
│   │   ├── auth/          # Login, Registration, Auth Provider
│   │   ├── main/          # Tab Navigation Shell
│   │   ├── permissions/   # Android notification onboarding
│   └── main.dart      # Flutter entry point
```
