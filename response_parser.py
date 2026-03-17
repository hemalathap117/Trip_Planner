import json
import re
from typing import List, Tuple
from models import DestinationRecommendation

def extract_json_array(raw: str) -> str:
    """Extract JSON array from LLM response using regex on the first [...] block."""
    # Remove markdown code fences if present
    cleaned = re.sub(r'^```json\n|```$', '', raw.strip(), flags=re.MULTILINE)
    
    # Find the first JSON array using regex
    json_match = re.search(r'\[.*?\]', cleaned, re.DOTALL)
    if json_match:
        return json_match.group()
    
    # If no array found, try to find any JSON-like structure
    json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if json_match:
        # Wrap single object in array
        return f"[{json_match.group()}]"
    
    raise ValueError("No JSON array found in response")

def validate_recommendations(data: List[dict]) -> None:
    """Validate that exactly 3 objects exist, each with name and rationale keys."""
    if not isinstance(data, list):
        raise ValueError("Response is not a list")
    
    if len(data) != 3:
        raise ValueError(f"Expected exactly 3 recommendations, got {len(data)}")
    
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Item {i+1} is not a dictionary: {item}")
        
        if "name" not in item:
            raise ValueError(f"Item {i+1} missing 'name' field: {item}")
        
        if "rationale" not in item:
            raise ValueError(f"Item {i+1} missing 'rationale' field: {item}")
        
        if not isinstance(item["name"], str) or not item["name"].strip():
            raise ValueError(f"Item {i+1} has invalid 'name' field: {item['name']}")
        
        if not isinstance(item["rationale"], str) or not item["rationale"].strip():
            raise ValueError(f"Item {i+1} has invalid 'rationale' field: {item['rationale']}")

def parse_llm_response(raw: str) -> Tuple[List[DestinationRecommendation], bool]:
    """
    Parse LLM response and convert to DestinationRecommendation objects.
    
    Returns:
        Tuple of (recommendations, success_flag)
        - recommendations: List of DestinationRecommendation objects
        - success_flag: True if parsing succeeded, False if retry needed
    """
    try:
        # Extract JSON array from response
        json_str = extract_json_array(raw)
        
        # Parse JSON
        data = json.loads(json_str)
        
        # Validate structure and content
        validate_recommendations(data)
        
        # Convert to DestinationRecommendation objects
        recommendations = []
        for item in data:
            recommendations.append(
                DestinationRecommendation(
                    name=item["name"].strip(),
                    rationale=item["rationale"].strip()
                )
            )
        
        return recommendations, True
        
    except (json.JSONDecodeError, ValueError) as e:
        # Return empty list and failure flag for retry
        return [], False