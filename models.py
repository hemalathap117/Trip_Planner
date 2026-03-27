from sqlalchemy import Column, String, Boolean, Date, Text, ARRAY, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from database import Base
from pydantic import BaseModel
import uuid
import datetime

class Trip(Base):
    __tablename__ = "trips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), nullable=False)  # Trip display name
    organiser_name = Column(String(80))
    join_code = Column(String(6), unique=True, nullable=False)  # Alphanumeric join code
    status = Column(String(20), default="collecting")  # collecting | generating | voting | closed
    created_at = Column(TIMESTAMP, server_default="now()")


class Preference(Base):
    __tablename__ = "preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"))
    participant_name = Column(String(80))
    budget = Column(String(10))  # low | medium | high
    date_from = Column(Date)
    date_to = Column(Date)
    interests = Column(ARRAY(Text))  # PostgreSQL array
    submitted_at = Column(TIMESTAMP, server_default="now()")  # Added missing column
    
    # One response per participant per trip
    __table_args__ = (
        UniqueConstraint('trip_id', 'participant_name', name='unique_trip_participant'),
    )


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"))
    destination_name = Column(String(120))
    rationale = Column(Text)  # LLM-generated explanation
    is_winner = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default="now()")


class Vote(Base):
    __tablename__ = "votes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"))
    recommendation_id = Column(UUID(as_uuid=True), ForeignKey("recommendations.id"))
    participant_name = Column(String(80))
    created_at = Column(TIMESTAMP, server_default="now()")

    # One vote per participant per trip
    __table_args__ = (
        UniqueConstraint('trip_id', 'participant_name', name='unique_trip_vote'),
    )


# Pydantic models for API responses (separate from SQLAlchemy models)
class DestinationRecommendation(BaseModel):
    name: str
    rationale: str