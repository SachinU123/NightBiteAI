"""
Simple script to seed some location-based food events into the local database
so the Heatmap tab has data to display.
"""
import sys
import os
from datetime import datetime, timedelta, timezone
from random import choice, randint

# Add the backend directory to sys.path so we can import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.user import User
from app.models.food_event import FoodEvent, RiskScore, FoodClassification
from app.models.analytics import Nudge, UserAggregate, HeatmapAggregate
from app.models.device import Device

def seed_heatmap_data():
    db = SessionLocal()
    
    # Get or create a user
    user = db.query(User).first()
    if not user:
        user = User(
            email="test@nightbite.ai", 
            hashed_password="dummy", 
            full_name="Test User",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    print(f"Using user {user.id}")

    # Dummy locations with some coordinates
    locations = [
        {"pincode": "560034", "lat": 12.9279, "lon": 77.6271}, # Koramangala
        {"pincode": "560038", "lat": 12.9783, "lon": 77.6408}, # Indiranagar
        {"pincode": "560011", "lat": 12.9250, "lon": 77.5938}, # Jayanagar
        {"pincode": "560103", "lat": 12.9259, "lon": 77.6756}, # Bellandur
    ]
    
    # Food combos + risk combos
    food_combos = [
        ("Chicken Biryani & Coke", "high", 8.5, ["high", "critical"]),
        ("Double Cheese Burger", "high", 9.0, ["high", "critical"]),
        ("Paneer Tikka Roll", "moderate", 6.0, ["moderate", "high"]),
        ("Masala Dosa", "low", 3.5, ["low", "moderate"]),
        ("Midnight Chocolate Cake", "critical", 9.8, ["critical"]),
    ]
    
    now = datetime.now(timezone.utc)
    
    events_added = 0
    
    # Generate 15 dummy food events over the last 10 days
    for i in range(15):
        days_ago = randint(0, 10)
        loc = choice(locations)
        food, base_risk_band, score, possible_bands = choice(food_combos)
        final_band = choice(possible_bands)
        
        # Event time at night
        event_time = now - timedelta(days=days_ago)
        event_time = event_time.replace(hour=randint(0, 4), minute=randint(0, 59))
        
        # Create event
        event = FoodEvent(
            user_id=user.id,
            source_type="seed",
            source_app=choice(["Swiggy", "Zomato", "Blinkit"]),
            raw_food_text=food,
            normalized_food_text=food,
            event_timestamp=event_time,
            latitude=loc["lat"],
            longitude=loc["lon"],
            pincode=loc["pincode"],
            is_processed=True
        )
        db.add(event)
        db.flush()
        
        # Create classification
        cls = FoodClassification(
            event_id=event.id,
            food_category="fake_category",
            confidence=0.9,
            parse_quality="complete"
        )
        db.add(cls)
        
        # Create risk score
        rs = RiskScore(
            event_id=event.id,
            base_food_risk=score - 1.0,
            time_multiplier=1.2,
            final_risk_score=score,
            risk_band=final_band
        )
        db.add(rs)
        events_added += 1

    db.commit()
    print(f"Successfully seeded {events_added} localized food events!")
    db.close()

if __name__ == "__main__":
    seed_heatmap_data()
