"""
NightBite AI — Demo Seed Script

Creates realistic anonymized seed data for demo purposes:
- 3 demo users
- Food events with varied risk levels, sources, times
- Covers late-night patterns, delivery app notifications, manual entries
- Pre-populates heatmap geo data

Run: python seed.py
"""
import sys
import os
import json
import random
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from app.models.device import Device
from app.models.food_event import FoodEvent, FoodClassification, RiskScore
from app.models.analytics import Nudge, HeatmapAggregate
from app.services.nlp_service import nlp_service
from app.services.risk_engine import risk_engine, score_to_band
from app.services.nudge_generator import nudge_generator

# ── Sample food entries ───────────────────────────────────────────────────────

DEMO_FOODS = [
    # (food_text, source_type, source_app, hour_offset_days_ago, hour_of_day, pincode)
    ("Butter Chicken Biryani with extra ghee", "notification", "zomato", 0, 1, "400001"),
    ("Double Cheese Burst Pizza", "notification", "swiggy", 0, 23, "400001"),
    ("Grilled Chicken Salad", "manual", None, 1, 22, "400002"),
    ("Chocolate Brownie with ice cream scoop", "notification", "swiggy", 1, 2, "400001"),
    ("Masala Chai", "manual", None, 2, 21, "400003"),
    ("Fried Chicken Wings + Soda", "notification", "zomato", 2, 0, "400002"),
    ("Idli Sambar", "manual", None, 3, 19, "400001"),
    ("Maggi Noodles with extra butter", "manual", None, 3, 1, "400001"),
    ("Paneer Tikka", "notification", "swiggy", 4, 22, "400003"),
    ("Cold Coffee with sugar", "manual", None, 4, 23, "400002"),
    ("Vada Pav", "notification", "zomato", 5, 3, "400001"),
    ("Quinoa Salad with lemon dressing", "manual", None, 5, 20, "400002"),
    ("Chicken Shawarma Roll", "notification", "swiggy", 6, 0, "400003"),
    ("Dahi Vada", "notification", "zomato", 6, 21, "400001"),
    ("Cheesy Loaded Nachos + Pepsi", "manual", None, 7, 1, "400002"),
    ("Tandoori Roti + Dal", "manual", None, 7, 19, "400001"),
    ("Kachori with aloo sabzi", "notification", "swiggy", 8, 23, "400003"),
    ("Green tea", "manual", None, 8, 22, "400002"),
    ("Fried Rice with egg", "notification", "zomato", 9, 0, "400001"),
    ("Gulab Jamun x4", "notification", "swiggy", 9, 2, "400002"),
]

DEMO_NOTIFICATION_TEXTS = {
    "zomato": "Your order from {} has been placed! {} will arrive in 35 mins. Order #ZOM{:06d}",
    "swiggy": "Order Confirmed! {} items from {} are being prepared. Delivery in 40 mins. ₹{}",
}

DEMO_PINCODES = ["400001", "400002", "400003", "400016", "110001", "560001"]


def seed_db():
    db = SessionLocal()

    print("🌱 Seeding NightBite AI demo data...")

    # ── Clear existing seed data ──────────────────────────────────────────────
    try:
        db.query(HeatmapAggregate).delete()
        db.query(Nudge).delete()
        db.query(RiskScore).delete()
        db.query(FoodClassification).delete()
        db.query(FoodEvent).delete()
        db.query(Device).delete()
        db.query(User).filter(User.email.like("demo%@nightbite.ai")).delete()
        db.commit()
        print("  ✓ Cleared old seed data")
    except Exception as e:
        db.rollback()
        print(f"  ⚠ Could not clear old data: {e}")

    # ── Create demo users ─────────────────────────────────────────────────────
    users = []
    demo_accounts = [
        ("Priya Sharma", "demo1@nightbite.ai", "Demo@1234"),
        ("Rahul Verma", "demo2@nightbite.ai", "Demo@1234"),
        ("Admin User", "admin@nightbite.ai", "Admin@1234"),
    ]

    for name, email, pw in demo_accounts:
        user = User(name=name, email=email, password_hash=get_password_hash(pw))
        db.add(user)
        db.flush()
        users.append(user)

        # Register a device
        device = Device(
            user_id=user.id,
            platform="android",
            device_name=f"{name.split()[0]}'s Phone",
            notification_listener_enabled=True,
        )
        db.add(device)

    db.flush()
    print(f"  ✓ Created {len(users)} demo users")

    # ── Seed food events ──────────────────────────────────────────────────────
    event_count = 0
    primary_user = users[0]
    secondary_user = users[1]

    for food_text, source_type, source_app, days_ago, hour, pincode in DEMO_FOODS:
        # Alternate between users
        user = primary_user if event_count % 3 != 2 else secondary_user

        event_dt = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=0)
        event_dt = event_dt.replace(hour=hour, minute=random.randint(0, 59), second=0, microsecond=0)

        raw_notif = None
        if source_type == "notification" and source_app:
            tmpl = DEMO_NOTIFICATION_TEXTS.get(source_app, "{}")
            raw_notif = tmpl.format(
                food_text, random.choice(["Milano", "Spice Garden", "Baba's Kitchen"]),
                random.randint(10000, 99999), random.randint(200, 800)
            )

        event = FoodEvent(
            user_id=user.id,
            source_type=source_type,
            source_app=source_app,
            raw_food_text=food_text,
            raw_notification_text=raw_notif,
            event_timestamp=event_dt,
            pincode=pincode,
            is_processed=False,
        )
        db.add(event)
        db.flush()

        # Run NLP + risk
        nlp_result = nlp_service.analyze(food_text)
        event.normalized_food_text = nlp_result.normalized_text
        event.is_processed = True

        classification = FoodClassification(
            event_id=event.id,
            food_category=nlp_result.food_category,
            risk_tags=json.dumps(nlp_result.risk_tags),
            matched_keywords=json.dumps(nlp_result.matched_keywords),
            confidence=nlp_result.confidence,
            parse_quality=nlp_result.parse_quality,
        )
        db.add(classification)
        db.flush()

        time_mult, time_label = __import__("app.services.risk_engine", fromlist=["get_time_multiplier"]).get_time_multiplier(event_dt)
        final = round(nlp_result.base_food_risk * time_mult, 2)
        final = min(final, 10.0)
        band = score_to_band(final)

        risk_row = RiskScore(
            event_id=event.id,
            base_food_risk=nlp_result.base_food_risk,
            time_multiplier=time_mult,
            behavior_multiplier=1.0,
            final_risk_score=final,
            risk_band=band,
        )
        db.add(risk_row)
        db.flush()

        from app.services.risk_engine import RiskResult
        risk_result = RiskResult(
            base_food_risk=nlp_result.base_food_risk,
            time_multiplier=time_mult,
            behavior_multiplier=1.0,
            final_risk_score=final,
            risk_band=band,
            time_label=time_label,
            behavior_label="normal_behavior",
        )

        nudge_output = nudge_generator.generate(nlp_result, risk_result, "normal_behavior")
        nudge_row = Nudge(
            event_id=event.id,
            user_id=user.id,
            nudge_text=nudge_output.nudge_text,
            healthier_swap=nudge_output.healthier_swap,
            nudge_type=nudge_output.nudge_type,
        )
        db.add(nudge_row)
        event_count += 1

    db.flush()
    print(f"  ✓ Seeded {event_count} food events with analysis")

    # ── Seed heatmap aggregates ───────────────────────────────────────────────
    heatmap_data = [
        ("400001", 19.076090, 72.877426, 120, 7.2, 68),
        ("400002", 19.118040, 72.907750, 85, 5.8, 32),
        ("400003", 19.090050, 72.860120, 54, 6.5, 28),
        ("400016", 19.052060, 72.841500, 200, 8.1, 140),
        ("110001", 28.639700, 77.228000, 310, 7.6, 195),
        ("560001", 12.971600, 77.594600, 175, 6.9, 95),
    ]

    for pincode, lat, lon, count, avg_r, high_risk in heatmap_data:
        density = round(high_risk / max(count, 1), 3)
        intensity = round(avg_r * density, 2)
        row = HeatmapAggregate(
            location_key=f"pin:{pincode}",
            pincode=pincode,
            lat_bin=lat,
            lon_bin=lon,
            time_bucket="2026-03-30 00",
            hour_of_day=0,
            order_count=count,
            avg_risk=avg_r,
            high_risk_count=high_risk,
            high_risk_density=density,
            hotspot_intensity=intensity,
        )
        db.add(row)

    db.commit()
    print(f"  ✓ Seeded {len(heatmap_data)} heatmap cells")
    print("\n✅ Seeding complete!")
    print("\n📋 Demo Credentials:")
    for name, email, pw in demo_accounts:
        print(f"   {name}: {email} / {pw}")


if __name__ == "__main__":
    seed_db()
