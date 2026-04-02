import sys
sys.path.insert(0, '.')
from app.services.nlp_service import nlp_service as n

tests = [
    'banana',
    'dosa',
    'butter chicken',
    'pizza',
    'alcohol',
    'ice cream',
    'pepperoni pizza -- cheese burst',
    'fried rice side manchurian',
    'burger',
    'gulab jamun',
    'idli sambhar',
    'chicken biryani',
]

print(f"{'FOOD':<40} {'CATEGORY':<22} {'RISK':>6} {'TAGS'}")
print("-" * 100)
for t in tests:
    r = n.analyze(t)
    print(f"{t!r:<40} {str(r.food_category):<22} {r.base_food_risk:>6.1f}  {r.risk_tags[:3]}")
