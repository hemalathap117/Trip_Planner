from pydantic import BaseModel
from typing import List, Optional
from datetime import date 

class TripCreate(BaseModel):
    trip_name: str
    organizer_name: str

class TripResponse(BaseModel):
    id: str
    trip_name: str
    organizer_name: str
    join_code: str
    status: str

    class Config:
        from_attributes = True

class PreferenceRequest(BaseModel):
    participant_name: str
    budget: str
    date_from: date
    date_to: date
    interests: List[str]

class DestinationRecommendation(BaseModel):
    name: str
    rationale: str

class RecommendationResponse(BaseModel):
    destinations: List[DestinationRecommendation]
    request_id: Optional[int] = None
