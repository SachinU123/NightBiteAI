# NightBite AI — Testing and Demo Guide

## ☑️ Testing Checklist

Before any demo, ensure these core flows are fully verified:

- [ ] **Auth Flow:** Can a user register and successfully log in?
- [ ] **Permission Onboarding:** Does the Android notification permission screen properly detect status?
- [ ] **Manual Entry Flow:** Does submitting a manual entry (e.g., "Biryani with extra ghee") hit the backend?
- [ ] **Notification-Capture Flow:** Does receiving a notification trigger a capture event?
- [ ] **Backend Analysis Response:** Does the backend correctly return the structured JSON (`FoodAnalysisResponse`)?
- [ ] **Risk Score Display:** Is the computed risk score displayed in the UI correctly (0.0 to 10.0 scale)?
- [ ] **Nudge Display:** Is a relevant context-aware smart nudge visible?
- [ ] **History Persistence:** Do recent orders save securely and display on the History tab?
- [ ] **Analytics Validation:** Do the heatmap and dashboard summary endpoints return valid JSON?
- [ ] **Fallback Flow:** If the notification capture fails (e.g., due to background limits), can the user still use manual entry?

---

## 🎬 Demo Script

### 1. Main Demo Flow
**Target:** Judges/Stakeholders wanting to see the app's full value proposition.

1.  **Registration/Login:** Launch the mobile app and create a new account or log into a test account.
2.  **Permission Setup:** Present the "Notification Access" onboarding. Explain why this is necessary for frictionless tracking.
3.  **Notification Ingestion (or Manual Entry):** 
    *   *Ideal:* Trigger a real/mocked food delivery notification via emulator/ADB. Wait for the app to capture it.
    *   *Alternative:* Open the app and use the "Manual Entry" feature to log an order (e.g., "Chicken Shawarma Roll at 1 AM").
4.  **Risk Analysis & Smart Nudge:** Show the real-time "Risk Score" card. Read the AI-generated friendly nudge (e.g., "Late-night eating increases caloric impact... try a grilled swap.").
5.  **History:** Navigate to the History tab to show the user's past entries persisted over time.
6.  **Secondary Insights/Analytics:** Navigate to the Profile/Insights tab to show personal analytics (e.g., "2 high-risk meals this week").

### 2. Fallback Demo
**Target:** Scenarios where live notification ingestion cannot be reliably demonstrated (e.g., due to strict emulator policies or network latency).

1.  **Skip Notification Setup:** Clearly state, "In production, the app listens silently, but for this demo, we'll simulate an order manually."
2.  **Manual Entry:** Use the manual form to test extreme cases (e.g., "Double Cheese Burst Pizza" vs "Green Salad").
3.  **Analytics (Seeded Data):** Since real-time geospatial tracking takes time to populate density, switch to the Analytics visualizer connected to the backend's seeded demo data to show how public-health heatmaps function.
4.  **Emphasize MVP Status:** Remind the audience: "The heatmap is populated with seeded anonymized data today, but running live endpoints."
