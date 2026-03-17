from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database import SessionLocal, Base, engine
from models import Trip, Preference, Recommendation, Vote, DestinationRecommendation
from schema import RecommendationResponse
import data_crud
import llm
import prompt
import response_parser
import random
import string
from typing import List, Optional
from datetime import datetime, date
from pathlib import Path
from enum import Enum
import uuid
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

Base.metadata.create_all(bind=engine)

# ── Enums & Pydantic models ───────────────────────────────
class BudgetLevel(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"

class TripCreate(BaseModel):
    trip_name: str
    organizer_name: str

class PreferenceSubmit(BaseModel):
    participant_name: str
    budget: BudgetLevel
    date_from: date
    date_to: date
    interests: List[str]

    @validator('participant_name')
    def validate_participant_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Participant name is required')
        return v.strip()

    @validator('interests')
    def validate_interests(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one interest must be selected')
        return v

    @validator('date_to')
    def validate_date_range(cls, v, values):
        if 'date_from' in values and v < values['date_from']:
            raise ValueError('End date must be after or equal to start date')
        return v

class VoteSubmit(BaseModel):
    participant_name: str
    recommendation_id: str

# ── DB helpers ────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

def generate_join_code(db: Session) -> str:
    for _ in range(100):
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not db.query(Trip).filter(Trip.join_code == code).first():
            return code
    raise Exception("Unable to generate unique join code")


# ── Routes ────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/create-trip")
async def create_trip(trip: TripCreate, db: Session = Depends(get_db)):
    join_code = generate_join_code(db)
    db_trip = Trip(
        name=trip.trip_name,
        organiser_name=trip.organizer_name,
        join_code=join_code,
        status="collecting"
    )
    db.add(db_trip)
    db.commit()
    db.refresh(db_trip)
    return {"trip_name": trip.trip_name, "organizer": trip.organizer_name,
            "join_code": join_code, "created_at": str(db_trip.created_at)}

# API Specification Compliant Endpoints
@app.post("/trips")
async def create_trip_api(trip: TripCreate, db: Session = Depends(get_db)):
    """POST /trips - Create a new trip. Returns trip object with join-code."""
    join_code = generate_join_code(db)
    db_trip = Trip(
        name=trip.trip_name,
        organiser_name=trip.organizer_name,
        join_code=join_code,
        status="collecting"
    )
    db.add(db_trip)
    db.commit()
    db.refresh(db_trip)
    return {
        "id": str(db_trip.id),
        "trip_name": trip.trip_name, 
        "organizer": trip.organizer_name,
        "join_code": join_code, 
        "status": db_trip.status,
        "created_at": str(db_trip.created_at)
    }

@app.get("/trip/{join_code}")
async def get_trip(join_code: str, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.join_code == join_code).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return {"id": str(trip.id), "trip_name": trip.name,
            "organizer": trip.organiser_name, "join_code": trip.join_code, "status": trip.status}

@app.get("/trips/{join_code}")
async def get_trip_by_join_code_api(join_code: str, db: Session = Depends(get_db)):
    """GET /trips/{join_code} - Get trip details and current status."""
    trip = db.query(Trip).filter(Trip.join_code == join_code).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return {
        "id": str(trip.id), 
        "trip_name": trip.name,
        "organizer": trip.organiser_name, 
        "join_code": trip.join_code, 
        "status": trip.status,
        "created_at": str(trip.created_at)
    }

@app.get("/trips/{trip_id}/preferences")
async def get_trip_preferences(trip_id: str, db: Session = Depends(get_db)):
    """GET /trips/{id}/preferences - List all preferences for a trip (organiser view)."""
    try:
        trip_uuid = uuid.UUID(trip_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid trip ID format")
    
    trip = db.query(Trip).filter(Trip.id == trip_uuid).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    prefs = db.query(Preference).filter(Preference.trip_id == trip_uuid).all()
    
    return {
        "trip_id": trip_id,
        "preferences": [
            {
                "id": str(p.id),
                "participant_name": p.participant_name, 
                "budget": p.budget,
                "date_from": str(p.date_from), 
                "date_to": str(p.date_to),
                "interests": p.interests or [],
                "submitted_at": str(p.submitted_at) if hasattr(p, 'submitted_at') and p.submitted_at else None
            }
            for p in prefs
        ]
    }

@app.get("/trip-data/{join_code}")
async def get_trip_data(join_code: str, db: Session = Depends(get_db)):
    """Full trip data including preferences, recommendations, votes."""
    trip = db.query(Trip).filter(Trip.join_code == join_code).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    prefs = db.query(Preference).filter(Preference.trip_id == trip.id).all()
    recs  = db.query(Recommendation).filter(Recommendation.trip_id == trip.id).all()
    votes = db.query(Vote).filter(Vote.trip_id == trip.id).all()

    return {
        "id": str(trip.id),
        "name": trip.name,
        "organiser_name": trip.organiser_name,
        "join_code": trip.join_code,
        "status": trip.status,
        "preferences": [
            {"participant_name": p.participant_name, "budget": p.budget,
             "date_from": str(p.date_from), "date_to": str(p.date_to),
             "interests": p.interests or []}
            for p in prefs
        ],
        "recommendations": [
            {"id": str(r.id), "destination_name": r.destination_name,
             "rationale": r.rationale, "is_winner": r.is_winner}
            for r in recs
        ],
        "votes": [
            {"id": str(v.id), "participant_name": v.participant_name,
             "recommendation_id": str(v.recommendation_id),
             "created_at": str(v.created_at) if hasattr(v, 'created_at') and v.created_at else ""}
            for v in votes
        ],
    }

@app.get("/dashboard/{join_code}", response_class=HTMLResponse)
async def dashboard_page(join_code: str, request: Request, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.join_code == join_code).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return templates.TemplateResponse("trip.html", {"request": request, "join_code": join_code})

# Legacy preferences page → redirect to dashboard
@app.get("/preferences/{join_code}", response_class=HTMLResponse)
async def preferences_page(join_code: str, request: Request):
    return RedirectResponse(url=f"/dashboard/{join_code}", status_code=302)

@app.post("/submit-preferences/{join_code}")
async def submit_preferences(join_code: str, preference: PreferenceSubmit, db: Session = Depends(get_db)):
    try:
        trip = db.query(Trip).filter(Trip.join_code == join_code).first()
        if not trip:
            raise HTTPException(status_code=404, detail="Trip not found")

        existing = db.query(Preference).filter(
            Preference.trip_id == trip.id,
            Preference.participant_name == preference.participant_name
        ).first()
        if existing:
            raise HTTPException(status_code=400,
                detail=f"'{preference.participant_name}' already submitted preferences for this trip")

        db_pref = Preference(
            trip_id=trip.id,
            participant_name=preference.participant_name,
            budget=preference.budget.value,
            date_from=preference.date_from,
            date_to=preference.date_to,
            interests=preference.interests
        )
        db.add(db_pref)
        db.commit()
        return {"message": "Preferences submitted successfully", "success": True}

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Participant already submitted preferences")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trips/{trip_id}/preferences")
async def submit_trip_preferences_api(trip_id: str, preference: PreferenceSubmit, db: Session = Depends(get_db)):
    """POST /trips/{id}/preferences - Submit participant preferences."""
    try:
        trip_uuid = uuid.UUID(trip_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid trip ID format")
    
    try:
        trip = db.query(Trip).filter(Trip.id == trip_uuid).first()
        if not trip:
            raise HTTPException(status_code=404, detail="Trip not found")

        existing = db.query(Preference).filter(
            Preference.trip_id == trip_uuid,
            Preference.participant_name == preference.participant_name
        ).first()
        if existing:
            raise HTTPException(status_code=400,
                detail=f"'{preference.participant_name}' already submitted preferences for this trip")

        db_pref = Preference(
            trip_id=trip_uuid,
            participant_name=preference.participant_name,
            budget=preference.budget.value,
            date_from=preference.date_from,
            date_to=preference.date_to,
            interests=preference.interests
        )
        db.add(db_pref)
        db.commit()
        db.refresh(db_pref)
        
        return {
            "id": str(db_pref.id),
            "trip_id": trip_id,
            "participant_name": db_pref.participant_name,
            "budget": db_pref.budget,
            "date_from": str(db_pref.date_from),
            "date_to": str(db_pref.date_to),
            "interests": db_pref.interests,
            "message": "Preferences submitted successfully"
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Participant already submitted preferences")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate/{join_code}")
async def generate_recommendations(join_code: str, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.join_code == join_code).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.status != "collecting":
        raise HTTPException(status_code=400, detail="Trip is not in collecting phase")

    prefs = db.query(Preference).filter(Preference.trip_id == trip.id).all()
    if not prefs:
        raise HTTPException(status_code=400, detail="Need at least one preference")

    # Update trip status to generating
    trip.status = "generating"
    db.commit()

    try:
        # First attempt: Generate AI recommendations
        system_msg = prompt.build_system_messages(prefs)
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": "Suggest exactly 3 travel destinations."}
        ]

        # Call LLM for first attempt
        raw_response = await llm.call_ollama(messages)
        destinations, success = response_parser.parse_llm_response(raw_response)

        # If first attempt failed, retry with explicit JSON reminder
        if not success:
            logger.warning(f"First AI attempt failed for trip {join_code}, retrying with JSON reminder")

            # Add explicit JSON reminder to the prompt
            retry_messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": "Suggest exactly 3 travel destinations. IMPORTANT: Respond with ONLY a valid JSON array containing exactly 3 objects, each with 'name' and 'rationale' keys. Example format: [{\"name\": \"Paris, France\", \"rationale\": \"Perfect for culture lovers\"}, {\"name\": \"Tokyo, Japan\", \"rationale\": \"Amazing food scene\"}, {\"name\": \"Bali, Indonesia\", \"rationale\": \"Great for relaxation\"}]"}
            ]

            # Second attempt
            raw_response = await llm.call_ollama(retry_messages)
            destinations, success = response_parser.parse_llm_response(raw_response)

            # If second attempt also failed, return HTTP 502
            if not success:
                logger.error(f"Both AI attempts failed for trip {join_code}")
                # Rollback trip status
                trip.status = "collecting"
                db.commit()

                raise HTTPException(
                    status_code=502,
                    detail="The AI service is having trouble generating recommendations right now. Please try again in a few minutes, or contact support if the problem persists."
                )

        # Save AI recommendations
        data_crud.save_recommendations(db, trip.id, destinations)

        logger.info(f"Generated AI recommendations for trip {join_code}")

        # Update trip status to voting
        trip.status = "voting"
        db.commit()

        return {"message": "AI recommendations generated successfully", "count": len(destinations)}

    except HTTPException:
        # Re-raise HTTP exceptions (like 502)
        raise
    except Exception as e:
        # Rollback trip status for any other errors
        trip.status = "collecting"
        db.commit()

        logger.error(f"Unexpected error during AI generation for trip {join_code}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while generating recommendations. Please try again. Error: {str(e)}"
        )


@app.post("/vote/{join_code}")
async def cast_vote(join_code: str, vote: VoteSubmit, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.join_code == join_code).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.status != "voting":
        raise HTTPException(status_code=400, detail="Voting is not open")

    existing = db.query(Vote).filter(
        Vote.trip_id == trip.id, Vote.participant_name == vote.participant_name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already voted on this trip")

    try:
        rec_id = uuid.UUID(vote.recommendation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid recommendation id")

    rec = db.query(Recommendation).filter(
        Recommendation.id == rec_id, Recommendation.trip_id == trip.id
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    db_vote = Vote(trip_id=trip.id, recommendation_id=rec_id,
                   participant_name=vote.participant_name)
    db.add(db_vote)
    db.commit()
    return {"message": "Vote cast", "success": True}

@app.post("/close-voting/{join_code}")
async def close_voting(join_code: str, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.join_code == join_code).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.status != "voting":
        raise HTTPException(status_code=400, detail="Trip is not in voting phase")

    recs  = db.query(Recommendation).filter(Recommendation.trip_id == trip.id).all()
    votes = db.query(Vote).filter(Vote.trip_id == trip.id).all()

    # Determine winner
    vote_counts = {str(r.id): 0 for r in recs}
    for v in votes:
        key = str(v.recommendation_id)
        if key in vote_counts:
            vote_counts[key] += 1

    winner_id = max(vote_counts, key=vote_counts.get) if vote_counts else None

    for rec in recs:
        rec.is_winner = (str(rec.id) == winner_id)

    trip.status = "closed"
    db.commit()
    return {"message": "Voting closed", "winner_id": winner_id}

# API Specification Compliant Endpoints - Additional
@app.post("/trips/{trip_id}/recommendations")
async def generate_trip_recommendations_api(trip_id: str, db: Session = Depends(get_db)):
    """POST /trips/{id}/recommendations - Trigger LLM generation. Returns 3 recommendations."""
    try:
        trip_uuid = uuid.UUID(trip_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid trip ID format")
    
    trip = db.query(Trip).filter(Trip.id == trip_uuid).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.status != "collecting":
        raise HTTPException(status_code=400, detail="Trip is not in collecting phase")

    prefs = db.query(Preference).filter(Preference.trip_id == trip_uuid).all()
    if not prefs:
        raise HTTPException(status_code=400, detail="Need at least one preference")

    # Update trip status to generating
    trip.status = "generating"
    db.commit()

    try:
        # Generate AI recommendations using existing logic
        system_msg = prompt.build_system_messages(prefs)
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": "Suggest exactly 3 travel destinations."}
        ]
        
        raw_response = await llm.call_ollama(messages)
        destinations, success = response_parser.parse_llm_response(raw_response)
        
        if not success:
            # Retry with explicit JSON reminder
            retry_messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": "Suggest exactly 3 travel destinations. IMPORTANT: Respond with ONLY a valid JSON array containing exactly 3 objects, each with 'name' and 'rationale' keys."}
            ]
            raw_response = await llm.call_ollama(retry_messages)
            destinations, success = response_parser.parse_llm_response(raw_response)
            
            if not success:
                trip.status = "collecting"
                db.commit()
                raise HTTPException(status_code=502, detail="AI service is having trouble generating recommendations")
        
        # Save recommendations
        saved_recs = data_crud.save_recommendations(db, trip_uuid, destinations)
        
        # Update trip status to voting
        trip.status = "voting"
        db.commit()
        
        return {
            "trip_id": trip_id,
            "recommendations": [
                {
                    "id": str(rec.id),
                    "destination_name": rec.destination_name,
                    "rationale": rec.rationale,
                    "is_winner": rec.is_winner
                }
                for rec in saved_recs
            ],
            "count": len(saved_recs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        trip.status = "collecting"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trips/{trip_id}/recommendations")
async def get_trip_recommendations_api(trip_id: str, db: Session = Depends(get_db)):
    """GET /trips/{id}/recommendations - Get existing recommendations."""
    try:
        trip_uuid = uuid.UUID(trip_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid trip ID format")
    
    trip = db.query(Trip).filter(Trip.id == trip_uuid).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    recs = db.query(Recommendation).filter(Recommendation.trip_id == trip_uuid).all()
    
    return {
        "trip_id": trip_id,
        "recommendations": [
            {
                "id": str(r.id),
                "destination_name": r.destination_name,
                "rationale": r.rationale,
                "is_winner": r.is_winner,
                "created_at": str(r.created_at) if hasattr(r, 'created_at') and r.created_at else None
            }
            for r in recs
        ]
    }

@app.post("/trips/{trip_id}/votes")
async def cast_trip_vote_api(trip_id: str, vote: VoteSubmit, db: Session = Depends(get_db)):
    """POST /trips/{id}/votes - Cast a vote for a recommendation."""
    try:
        trip_uuid = uuid.UUID(trip_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid trip ID format")
    
    trip = db.query(Trip).filter(Trip.id == trip_uuid).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.status != "voting":
        raise HTTPException(status_code=400, detail="Voting is not open")

    existing = db.query(Vote).filter(
        Vote.trip_id == trip_uuid, Vote.participant_name == vote.participant_name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already voted on this trip")

    try:
        rec_id = uuid.UUID(vote.recommendation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid recommendation id")

    rec = db.query(Recommendation).filter(
        Recommendation.id == rec_id, Recommendation.trip_id == trip_uuid
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    db_vote = Vote(trip_id=trip_uuid, recommendation_id=rec_id,
                   participant_name=vote.participant_name)
    db.add(db_vote)
    db.commit()
    db.refresh(db_vote)
    
    return {
        "id": str(db_vote.id),
        "trip_id": trip_id,
        "recommendation_id": vote.recommendation_id,
        "participant_name": vote.participant_name,
        "message": "Vote cast successfully"
    }

@app.get("/trips/{trip_id}/votes")
async def get_trip_votes_api(trip_id: str, db: Session = Depends(get_db)):
    """GET /trips/{id}/votes - Get vote counts per recommendation."""
    try:
        trip_uuid = uuid.UUID(trip_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid trip ID format")
    
    trip = db.query(Trip).filter(Trip.id == trip_uuid).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    votes = db.query(Vote).filter(Vote.trip_id == trip_uuid).all()
    recs = db.query(Recommendation).filter(Recommendation.trip_id == trip_uuid).all()
    
    # Count votes per recommendation
    vote_counts = {}
    for rec in recs:
        rec_votes = [v for v in votes if str(v.recommendation_id) == str(rec.id)]
        vote_counts[str(rec.id)] = {
            "recommendation_id": str(rec.id),
            "destination_name": rec.destination_name,
            "vote_count": len(rec_votes),
            "voters": [v.participant_name for v in rec_votes]
        }
    
    return {
        "trip_id": trip_id,
        "total_votes": len(votes),
        "vote_counts": list(vote_counts.values())
    }

@app.post("/trips/{trip_id}/close")
async def close_trip_voting_api(trip_id: str, db: Session = Depends(get_db)):
    """POST /trips/{id}/close - Close voting and compute winner."""
    try:
        trip_uuid = uuid.UUID(trip_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid trip ID format")
    
    trip = db.query(Trip).filter(Trip.id == trip_uuid).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.status != "voting":
        raise HTTPException(status_code=400, detail="Trip is not in voting phase")

    recs = db.query(Recommendation).filter(Recommendation.trip_id == trip_uuid).all()
    votes = db.query(Vote).filter(Vote.trip_id == trip_uuid).all()

    # Determine winner
    vote_counts = {str(r.id): 0 for r in recs}
    for v in votes:
        key = str(v.recommendation_id)
        if key in vote_counts:
            vote_counts[key] += 1

    winner_id = max(vote_counts, key=vote_counts.get) if vote_counts else None
    winner_rec = None

    for rec in recs:
        is_winner = (str(rec.id) == winner_id)
        rec.is_winner = is_winner
        if is_winner:
            winner_rec = rec

    trip.status = "closed"
    db.commit()
    
    return {
        "trip_id": trip_id,
        "status": "closed",
        "winner": {
            "id": str(winner_rec.id),
            "destination_name": winner_rec.destination_name,
            "rationale": winner_rec.rationale,
            "vote_count": vote_counts.get(winner_id, 0)
        } if winner_rec else None,
        "total_votes": len(votes),
        "message": "Voting closed successfully"
    }

@app.get("/trips/{trip_id}/result")
async def get_trip_result_api(trip_id: str, db: Session = Depends(get_db)):
    """GET /trips/{id}/result - Get the winning destination and vote summary."""
    try:
        trip_uuid = uuid.UUID(trip_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid trip ID format")
    
    trip = db.query(Trip).filter(Trip.id == trip_uuid).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.status != "closed":
        raise HTTPException(status_code=400, detail="Voting is not closed yet")
    
    recs = db.query(Recommendation).filter(Recommendation.trip_id == trip_uuid).all()
    votes = db.query(Vote).filter(Vote.trip_id == trip_uuid).all()
    
    # Find winner
    winner = next((r for r in recs if r.is_winner), None)
    
    # Vote summary
    vote_summary = []
    for rec in recs:
        rec_votes = [v for v in votes if str(v.recommendation_id) == str(rec.id)]
        vote_summary.append({
            "recommendation_id": str(rec.id),
            "destination_name": rec.destination_name,
            "vote_count": len(rec_votes),
            "percentage": round((len(rec_votes) / len(votes)) * 100, 1) if votes else 0,
            "is_winner": rec.is_winner
        })
    
    # Sort by vote count descending
    vote_summary.sort(key=lambda x: x["vote_count"], reverse=True)
    
    return {
        "trip_id": trip_id,
        "status": trip.status,
        "winner": {
            "id": str(winner.id),
            "destination_name": winner.destination_name,
            "rationale": winner.rationale,
            "vote_count": len([v for v in votes if str(v.recommendation_id) == str(winner.id)])
        } if winner else None,
        "vote_summary": vote_summary,
        "total_votes": len(votes),
        "total_participants": len(set(v.participant_name for v in votes))
    }

# Legacy confirmation page (unused but kept for backwards compat)
        # Parse response
    destinations, success = response_parser.parse_llm_response(raw_response)
        
    if not success:
            raise HTTPException(status_code=502, detail="Failed to parse AI response")
    return RedirectResponse(url="/", status_code=302)

# Optional AI-powered recommendation endpoint
@app.post("/ai-recommendations/{join_code}", response_model=RecommendationResponse)
async def get_ai_recommendations(join_code: str, db: Session = Depends(get_db)):
    """Generate AI-powered recommendations for a trip."""
    trip = db.query(Trip).filter(Trip.join_code == join_code).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    prefs = data_crud.get_trip_preferences(db, trip.id)
    if not prefs:
        raise HTTPException(status_code=400, detail="No preferences found for this trip")
    
    try:
        # Build prompt from preferences
        system_msg = prompt.build_system_messages(prefs)
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": "Suggest exactly 3 travel destinations."}
        ]
        
        # Call Ollama
        raw_response = await llm.call_ollama(messages)
        
        # Parse response
        destinations = response_parser.parse_llm_response(raw_response)
        
        return RecommendationResponse(destinations=destinations)
        
    except Exception as e:
        logger.error(f"AI recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")