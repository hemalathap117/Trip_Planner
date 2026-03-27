"""
Comprehensive pytest suite for AI Trip Planner API
Tests all endpoints with happy path and error cases
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date, datetime
import uuid

from main import app, get_db
from database import Base
from models import Trip, Preference, Recommendation, Vote

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def client():
    """Create test database and client for each test"""
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def sample_trip(client):
    """Create a sample trip for testing"""
    response = client.post("/create-trip", json={
        "trip_name": "Summer Vacation",
        "organizer_name": "Alice"
    })
    assert response.status_code == 200
    return response.json()

@pytest.fixture
def trip_with_preferences(client, sample_trip):
    """Create a trip with 3 preferences"""
    join_code = sample_trip["join_code"]
    
    participants = [
        {"participant_name": "Alice", "budget": "medium", "interests": ["beaches", "culture"]},
        {"participant_name": "Bob", "budget": "high", "interests": ["adventure", "food"]},
        {"participant_name": "Charlie", "budget": "low", "interests": ["nature", "culture"]}
    ]
    
    for p in participants:
        response = client.post(f"/submit-preferences/{join_code}", json={
            **p,
            "date_from": "2026-07-01",
            "date_to": "2026-07-15"
        })
        assert response.status_code == 200
    
    return sample_trip


# ==================== TRIP CREATION TESTS ====================

class TestTripCreation:
    def test_create_trip_success(self, client):
        """Happy path: Create a new trip"""
        response = client.post("/create-trip", json={
            "trip_name": "Beach Holiday",
            "organizer_name": "John"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["trip_name"] == "Beach Holiday"
        assert data["organizer"] == "John"
        assert "join_code" in data
        assert len(data["join_code"]) == 6

    def test_create_trip_api_endpoint(self, client):
        """Happy path: Create trip via API endpoint"""
        response = client.post("/trips", json={
            "trip_name": "Mountain Trek",
            "organizer_name": "Jane"
        })
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == "collecting"

    def test_get_trip_by_join_code(self, client, sample_trip):
        """Happy path: Retrieve trip by join code"""
        join_code = sample_trip["join_code"]
        response = client.get(f"/trip/{join_code}")
        assert response.status_code == 200
        data = response.json()
        assert data["join_code"] == join_code
        assert data["trip_name"] == "Summer Vacation"

    def test_get_trip_not_found(self, client):
        """Error case: Trip with invalid join code"""
        response = client.get("/trip/INVALID")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# ==================== PREFERENCE TESTS ====================

class TestPreferences:
    def test_submit_preference_success(self, client, sample_trip):
        """Happy path: Submit valid preference"""
        join_code = sample_trip["join_code"]
        response = client.post(f"/submit-preferences/{join_code}", json={
            "participant_name": "Alice",
            "budget": "medium",
            "date_from": "2026-06-01",
            "date_to": "2026-06-15",
            "interests": ["beaches", "culture", "food"]
        })
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_submit_duplicate_preference(self, client, sample_trip):
        """Error case: Duplicate preference from same participant"""
        join_code = sample_trip["join_code"]
        pref_data = {
            "participant_name": "Alice",
            "budget": "medium",
            "date_from": "2026-06-01",
            "date_to": "2026-06-15",
            "interests": ["beaches"]
        }
        
        # First submission
        response1 = client.post(f"/submit-preferences/{join_code}", json=pref_data)
        assert response1.status_code == 200
        
        # Duplicate submission
        response2 = client.post(f"/submit-preferences/{join_code}", json=pref_data)
        assert response2.status_code == 400
        assert "already submitted" in response2.json()["detail"].lower()

    def test_submit_preference_invalid_trip(self, client):
        """Error case: Submit preference to non-existent trip"""
        response = client.post("/submit-preferences/INVALID", json={
            "participant_name": "Alice",
            "budget": "medium",
            "date_from": "2026-06-01",
            "date_to": "2026-06-15",
            "interests": ["beaches"]
        })
        assert response.status_code == 404

    def test_submit_preference_invalid_date_range(self, client, sample_trip):
        """Error case: End date before start date"""
        join_code = sample_trip["join_code"]
        response = client.post(f"/submit-preferences/{join_code}", json={
            "participant_name": "Alice",
            "budget": "medium",
            "date_from": "2026-06-15",
            "date_to": "2026-06-01",  # Before start date
            "interests": ["beaches"]
        })
        assert response.status_code == 422  # Validation error

    def test_submit_preference_empty_interests(self, client, sample_trip):
        """Error case: No interests selected"""
        join_code = sample_trip["join_code"]
        response = client.post(f"/submit-preferences/{join_code}", json={
            "participant_name": "Alice",
            "budget": "medium",
            "date_from": "2026-06-01",
            "date_to": "2026-06-15",
            "interests": []
        })
        assert response.status_code == 422  # Validation error

    def test_get_trip_preferences(self, client, trip_with_preferences):
        """Happy path: Get all preferences for a trip"""
        trip_id = trip_with_preferences["join_code"]
        
        # Get trip data
        response = client.get(f"/trip-data/{trip_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["preferences"]) == 3
        assert all("participant_name" in p for p in data["preferences"])


# ==================== AI RECOMMENDATION TESTS ====================

class TestRecommendations:
    def test_generate_recommendations_no_preferences(self, client, sample_trip):
        """Error case: Generate recommendations without preferences"""
        join_code = sample_trip["join_code"]
        response = client.post(f"/generate/{join_code}")
        assert response.status_code == 400
        assert "at least one preference" in response.json()["detail"].lower()

    def test_generate_recommendations_wrong_status(self, client, trip_with_preferences):
        """Error case: Generate when not in collecting phase"""
        join_code = trip_with_preferences["join_code"]
        
        # First generation (should succeed)
        # Note: This will fail in test without mocking LLM, but tests the status check
        response = client.post(f"/generate/{join_code}")
        # Status will be 'generating' or error, but not 'collecting'
        
        # Try again (should fail due to status)
        response2 = client.post(f"/generate/{join_code}")
        assert response2.status_code == 400

    def test_get_recommendations(self, client):
        """Happy path: Get recommendations for a trip"""
        # Create trip with preferences
        trip_response = client.post("/create-trip", json={
            "trip_name": "Test Trip",
            "organizer_name": "Tester"
        })
        join_code = trip_response.json()["join_code"]
        
        # Add preference
        client.post(f"/submit-preferences/{join_code}", json={
            "participant_name": "Alice",
            "budget": "medium",
            "date_from": "2026-06-01",
            "date_to": "2026-06-15",
            "interests": ["beaches"]
        })
        
        # Get trip data (recommendations will be empty until generated)
        response = client.get(f"/trip-data/{join_code}")
        assert response.status_code == 200
        assert "recommendations" in response.json()


# ==================== VOTING TESTS ====================

class TestVoting:
    @pytest.fixture
    def trip_with_recommendations(self, client, trip_with_preferences):
        """Create a trip with mock recommendations"""
        db = next(override_get_db())
        trip = db.query(Trip).filter(Trip.join_code == trip_with_preferences["join_code"]).first()
        
        # Manually create recommendations (bypassing LLM)
        recommendations = [
            Recommendation(trip_id=trip.id, destination_name="Paris", rationale="Great culture"),
            Recommendation(trip_id=trip.id, destination_name="Tokyo", rationale="Amazing food"),
            Recommendation(trip_id=trip.id, destination_name="Bali", rationale="Beautiful beaches")
        ]
        for rec in recommendations:
            db.add(rec)
        
        # Update trip status to voting
        trip.status = "voting"
        db.commit()
        
        # Get recommendation IDs
        recs = db.query(Recommendation).filter(Recommendation.trip_id == trip.id).all()
        trip_with_preferences["recommendation_ids"] = [str(r.id) for r in recs]
        
        db.close()
        return trip_with_preferences

    def test_cast_vote_success(self, client, trip_with_recommendations):
        """Happy path: Cast a valid vote"""
        join_code = trip_with_recommendations["join_code"]
        rec_id = trip_with_recommendations["recommendation_ids"][0]
        
        response = client.post(f"/vote/{join_code}", json={
            "participant_name": "Alice",
            "recommendation_id": rec_id
        })
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_cast_duplicate_vote(self, client, trip_with_recommendations):
        """Error case: Participant votes twice - should return HTTP 409"""
        join_code = trip_with_recommendations["join_code"]
        rec_id = trip_with_recommendations["recommendation_ids"][0]
        
        vote_data = {
            "participant_name": "Alice",
            "recommendation_id": rec_id
        }
        
        # First vote
        response1 = client.post(f"/vote/{join_code}", json=vote_data)
        assert response1.status_code == 200
        
        # Duplicate vote - should return 409 Conflict
        response2 = client.post(f"/vote/{join_code}", json=vote_data)
        assert response2.status_code == 409
        assert "already voted" in response2.json()["detail"].lower()

    def test_vote_invalid_recommendation(self, client, trip_with_recommendations):
        """Error case: Vote for non-existent recommendation"""
        join_code = trip_with_recommendations["join_code"]
        fake_uuid = str(uuid.uuid4())
        
        response = client.post(f"/vote/{join_code}", json={
            "participant_name": "Alice",
            "recommendation_id": fake_uuid
        })
        assert response.status_code == 404

    def test_vote_wrong_status(self, client, sample_trip):
        """Error case: Vote when not in voting phase"""
        join_code = sample_trip["join_code"]
        
        response = client.post(f"/vote/{join_code}", json={
            "participant_name": "Alice",
            "recommendation_id": str(uuid.uuid4())
        })
        assert response.status_code == 400
        assert "not open" in response.json()["detail"].lower()

    def test_get_vote_counts(self, client, trip_with_recommendations):
        """Happy path: Get vote counts"""
        join_code = trip_with_recommendations["join_code"]
        rec_ids = trip_with_recommendations["recommendation_ids"]
        
        # Cast some votes
        client.post(f"/vote/{join_code}", json={
            "participant_name": "Alice",
            "recommendation_id": rec_ids[0]
        })
        client.post(f"/vote/{join_code}", json={
            "participant_name": "Bob",
            "recommendation_id": rec_ids[0]
        })
        client.post(f"/vote/{join_code}", json={
            "participant_name": "Charlie",
            "recommendation_id": rec_ids[1]
        })
        
        # Get trip data with votes
        response = client.get(f"/trip-data/{join_code}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["votes"]) == 3


# ==================== CLOSE VOTING TESTS ====================

class TestCloseVoting:
    def test_close_voting_success(self, client, trip_with_recommendations):
        """Happy path: Close voting and determine winner"""
        join_code = trip_with_recommendations["join_code"]
        rec_ids = trip_with_recommendations["recommendation_ids"]
        
        # Cast votes (rec_ids[0] gets 2 votes, should win)
        client.post(f"/vote/{join_code}", json={
            "participant_name": "Alice",
            "recommendation_id": rec_ids[0]
        })
        client.post(f"/vote/{join_code}", json={
            "participant_name": "Bob",
            "recommendation_id": rec_ids[0]
        })
        client.post(f"/vote/{join_code}", json={
            "participant_name": "Charlie",
            "recommendation_id": rec_ids[1]
        })
        
        # Close voting
        response = client.post(f"/close-voting/{join_code}")
        assert response.status_code == 200
        assert "winner_id" in response.json()
        assert response.json()["winner_id"] == rec_ids[0]

    def test_close_voting_wrong_status(self, client, sample_trip):
        """Error case: Close voting when not in voting phase"""
        join_code = sample_trip["join_code"]
        
        response = client.post(f"/close-voting/{join_code}")
        assert response.status_code == 400
        assert "not in voting phase" in response.json()["detail"].lower()

    def test_close_voting_tie_breaking(self, client, trip_with_recommendations):
        """Happy path: Tie broken by first vote timestamp"""
        join_code = trip_with_recommendations["join_code"]
        rec_ids = trip_with_recommendations["recommendation_ids"]
        
        # Create a tie: rec_ids[0] and rec_ids[1] both get 1 vote
        # rec_ids[0] gets first vote (should win tie)
        client.post(f"/vote/{join_code}", json={
            "participant_name": "Alice",
            "recommendation_id": rec_ids[0]
        })
        client.post(f"/vote/{join_code}", json={
            "participant_name": "Bob",
            "recommendation_id": rec_ids[1]
        })
        
        # Close voting
        response = client.post(f"/close-voting/{join_code}")
        assert response.status_code == 200
        # Winner should be rec_ids[0] (first vote)
        assert response.json()["winner_id"] == rec_ids[0]


# ==================== RESULT TESTS ====================

class TestResults:
    def test_get_result_success(self, client, trip_with_recommendations):
        """Happy path: Get result after voting closed"""
        join_code = trip_with_recommendations["join_code"]
        rec_ids = trip_with_recommendations["recommendation_ids"]
        
        # Cast votes and close
        client.post(f"/vote/{join_code}", json={
            "participant_name": "Alice",
            "recommendation_id": rec_ids[0]
        })
        client.post(f"/close-voting/{join_code}")
        
        # Get trip data (should show winner)
        response = client.get(f"/trip-data/{join_code}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "closed"
        
        # Check recommendations for winner
        winner = next((r for r in data["recommendations"] if r["is_winner"]), None)
        assert winner is not None

    def test_get_result_not_closed(self, client, trip_with_recommendations):
        """Error case: Get result before voting closed"""
        join_code = trip_with_recommendations["join_code"]
        
        # Try to get result (voting not closed yet)
        response = client.get(f"/trip-data/{join_code}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "voting"  # Not closed yet


# ==================== DASHBOARD TESTS ====================

class TestDashboard:
    def test_dashboard_page_loads(self, client, sample_trip):
        """Happy path: Dashboard page loads"""
        join_code = sample_trip["join_code"]
        response = client.get(f"/dashboard/{join_code}")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_dashboard_invalid_trip(self, client):
        """Error case: Dashboard for non-existent trip"""
        response = client.get("/dashboard/INVALID")
        assert response.status_code == 404


# ==================== HOME PAGE TESTS ====================

class TestHomePage:
    def test_home_page_loads(self, client):
        """Happy path: Home page loads"""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
