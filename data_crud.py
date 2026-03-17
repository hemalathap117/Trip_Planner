from sqlalchemy.orm import Session
from sqlalchemy import select
from models import Trip, Preference, Recommendation, Vote, DestinationRecommendation
from typing import List
import uuid

def save_preferences(db: Session, trip_id: uuid.UUID, preferences_data: dict) -> Preference:
    """Save user preferences to database."""
    db_pref = Preference(
        trip_id=trip_id,
        participant_name=preferences_data["participant_name"],
        budget=preferences_data["budget"],
        date_from=preferences_data["date_from"],
        date_to=preferences_data["date_to"],
        interests=preferences_data["interests"]
    )
    db.add(db_pref)
    db.commit()
    db.refresh(db_pref)
    return db_pref

def save_recommendations(db: Session, trip_id: uuid.UUID, destinations: List[DestinationRecommendation]) -> List[Recommendation]:
    """Save AI-generated recommendations to database."""
    recommendations = []
    
    # Delete existing recommendations for this trip
    db.query(Recommendation).filter(Recommendation.trip_id == trip_id).delete()
    
    for dest in destinations:
        db_rec = Recommendation(
            trip_id=trip_id,
            destination_name=dest.name,
            rationale=dest.rationale,
            is_winner=False
        )
        db.add(db_rec)
        recommendations.append(db_rec)
    
    db.commit()
    
    # Refresh all recommendations to get their IDs
    for rec in recommendations:
        db.refresh(rec)
    
    return recommendations

def get_trip_preferences(db: Session, trip_id: uuid.UUID) -> List[Preference]:
    """Get all preferences for a trip."""
    return db.query(Preference).filter(Preference.trip_id == trip_id).all()

def get_trip_recommendations(db: Session, trip_id: uuid.UUID) -> List[Recommendation]:
    """Get all recommendations for a trip."""
    return db.query(Recommendation).filter(Recommendation.trip_id == trip_id).all()

def get_trip_votes(db: Session, trip_id: uuid.UUID) -> List[Vote]:
    """Get all votes for a trip."""
    return db.query(Vote).filter(Vote.trip_id == trip_id).all()

def save_vote(db: Session, trip_id: uuid.UUID, recommendation_id: uuid.UUID, participant_name: str) -> Vote:
    """Save a vote to database."""
    db_vote = Vote(
        trip_id=trip_id,
        recommendation_id=recommendation_id,
        participant_name=participant_name
    )
    db.add(db_vote)
    db.commit()
    db.refresh(db_vote)
    return db_vote

def update_trip_status(db: Session, trip_id: uuid.UUID, status: str) -> Trip:
    """Update trip status."""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if trip:
        trip.status = status
        db.commit()
        db.refresh(trip)
    return trip

def mark_winner(db: Session, recommendation_id: uuid.UUID) -> Recommendation:
    """Mark a recommendation as winner."""
    # First, unmark all recommendations for this trip
    rec = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if rec:
        # Unmark all recommendations for this trip
        db.query(Recommendation).filter(Recommendation.trip_id == rec.trip_id).update({"is_winner": False})
        
        # Mark the winner
        rec.is_winner = True
        db.commit()
        db.refresh(rec)
    
    return rec