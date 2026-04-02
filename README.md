# NightBite AI — Mobile-First Late-Night Food Risk Analyzer

## 🌙 Project Overview
NightBite AI is a polished, premium, mobile-first Flutter application paired with a robust FastAPI backend. Its primary mission is to help users make better, healthier choices when ordering food late at night. 

By capturing food orders via Android notification listeners or manual entry, NightBite AI delivers real-time smart nudges and healthier alternatives exactly at the moment of decision.

## 🤔 Problem Statement
Late-night food cravings often lead to high-calorie, low-nutrition choices. People frequently order food impulsively when tired or stressed, exacerbating the negative metabolic impact of eating late. While general health apps track calories after the fact, they fail to intervene when the decision is actually being made.

## 💡 Solution Summary
NightBite AI intervenes at the point of action. It silently monitors delivery app notifications (or accepts manual input) to identify what is being ordered. It then calculates a time-aware, deterministic risk score for the food item and provides a targeted, supportive "smart nudge" offering a healthier swap. 

**Primary Value Proposition:** Real-time smart nudges at the moment of decision. Analytics and heatmaps are secondary secondary features designed to track long-term trends without cluttering the primary mobile experience.

## ✨ Feature List
*   **Real-time Smart Nudges:** Context-aware, supportive suggestions based on food choice and time of day.
*   **Automated Ingestion (Android):** Listens to notifications from apps like Swiggy, Zomato, Blinkit (Android only).
*   **Manual Entry Fallback:** Users can manually log their cravings or orders.
*   **Risk Scoring Engine:** Deterministic algorithm taking into account food base risk, time multiplier, and user behavior.
*   **Personal History:** Tracks past entries for user reflection.
*   **Secondary Analytics:** Dashboard summaries and heatmaps (for aggregate/admin/population health views).

## 🛠️ Tech Stack
*   **Frontend (Mobile):** Flutter (Mobile-First), Riverpod (State Management), GoRouter (Navigation).
*   **Backend:** Python 3.11+, FastAPI.
*   **Database:** PostgreSQL, SQLAlchemy (ORM), Alembic (Migrations).
*   **Intelligence:** spaCy (NLP parsing), Deterministic Rule Engine for Risk Scoring.

## 🔄 System Workflow & Architecture
NightBite AI uses an **Adapter-Style Ingestion Architecture** built for future expansion:

1.  **Ingestion:** Data enters via `ManualEntryAdapter` or `NotificationCaptureAdapter` (future: `PartnerApiAdapter`).
2.  **NLP Pipeline:** Text is parsed (spaCy + regex fallback) to extract food categories, items, and risk tags.
3.  **Risk Engine:** Calculates `FinalRisk = BaseFoodRisk × TimeMultiplier × BehaviorMultiplier`.
4.  **Nudge Generator:** Creates a personalized, non-moralizing nudge and suggests healthier swaps.
5.  **Persistence:** Raw events, processed classifications, risk scores, and nudges are stored in PostgreSQL.
6.  **Presentation (Flutter app):** Displays the analysis cleanly to the user.

## 🚀 Setup & Run Instructions
For detailed step-by-step setup guides, refer to the documentation folder:
*   [Setup Guide](docs/setup_guide.md): Covers Flutter, Backend, and Database setup.
*   [Environment Variables](docs/env_guide.md): Details required `.env` configurations.

## 🧪 Testing & Demo
*   [Testing Checklist](docs/testing_and_demo.md#testing-checklist): Steps to verify core flows.
*   [Demo Script](docs/testing_and_demo.md#demo-script): Step-by-step instructions for demonstrating the app, including fallbacks.

## 📚 Documentation Links
*   [Architecture Summary](docs/architecture.md)
*   [API Documentation](docs/api_docs.md)
*   [Troubleshooting Guide](docs/troubleshooting.md)
*   [Daily Progress & Changelog](docs/progress_log.md)

## ⚠️ Known Limitations
*   **Platform Dependency:** Notification listener ingestion is Android-only.
*   **NLP Constraints:** Extracting perfect item details from truncated notification text is best-effort. The app gracefully degrades to generic alerts on partial parses.
*   **Rule-Based MVP:** The current risk engine is deterministic (MVP baseline) rather than an evolving ML model.
*   **Analytics Data:** Some heatmap density depends on seeded/anonymized data for demonstration purposes.

## 🔭 Future Scope
*   **AI Coach Integration:** Deeper conversational interface for personalized coaching.
*   **Direct API Integrations:** Official webhooks from Swiggy/Zomato/UberEats to bypass notification reading.
*   **Public Health Dashboards:** Exposing heatmap patterns for macro-level health analysis.
*   **Wearable Integration:** Factoring in Apple Watch/Garmin activity data to modulate the `BehaviorMultiplier` in risk scoring.
