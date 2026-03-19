from models import Preference
from typing import List

def build_system_messages(prefs: List[Preference]) -> str:
    """Build system prompt for LLM based on group preferences."""
    
    if not prefs:
        return "You are a travel advisor. Suggest 3 diverse travel destinations with rationales."
    
    # Aggregate budget preferences
    budget_counts = {"low": 0, "medium": 0, "high": 0}
    for pref in prefs:
        if pref.budget in budget_counts:
            budget_counts[pref.budget] += 1
    
    # Find most common budget
    most_common_budget = max(budget_counts, key=budget_counts.get)
    
    # Aggregate interests
    interest_counts = {}
    for pref in prefs:
        if pref.interests:
            for interest in pref.interests:
                interest_counts[interest] = interest_counts.get(interest, 0) + 1
    
    # Sort interests by popularity
    sorted_interests = sorted(interest_counts.items(), key=lambda x: x[1], reverse=True)
    interests_str = ", ".join([f"{interest} ({count} votes)" for interest, count in sorted_interests[:5]])
    
    # Get date range (use first preference as example)
    date_info = ""
    if prefs[0].date_from and prefs[0].date_to:
        date_info = f"- Travel dates: {prefs[0].date_from} to {prefs[0].date_to}"
    
    prompt = f"""You are a travel advisor. A group of {len(prefs)} people is planning a trip together.
Their aggregated preferences are:
- Budget: most people prefer {most_common_budget}
{date_info}
- Interests: {interests_str}

Suggest exactly 3 travel destinations that suit this group's preferences.
Consider their budget level, interests, and group size when making recommendations.

IMPORTANT: You must respond with ONLY a valid JSON array. No other text before or after.
Use this EXACT format:
[
  {{"name": "Paris, France", "rationale": "Perfect for culture and food lovers with medium budget"}},
  {{"name": "Bali, Indonesia", "rationale": "Great beaches and affordable luxury"}},
  {{"name": "Barcelona, Spain", "rationale": "Combines beach, culture, and amazing cuisine"}}
]

Now provide your 3 destination recommendations in the same JSON array format:"""

    return prompt