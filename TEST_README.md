# AI Trip Planner - Test Suite

Comprehensive pytest suite covering all API endpoints with happy path and error cases.

## Test Coverage

### Trip Management Tests
- ✅ Create trip (happy path)
- ✅ Create trip via API endpoint
- ✅ Get trip by join code
- ✅ Get trip not found (404)

### Preference Tests
- ✅ Submit valid preference
- ✅ Duplicate preference (400)
- ✅ Invalid trip (404)
- ✅ Invalid date range (422)
- ✅ Empty interests (422)
- ✅ Get all preferences

### AI Recommendation Tests
- ✅ Generate without preferences (400)
- ✅ Generate with wrong status (400)
- ✅ Get recommendations

### Voting Tests
- ✅ Cast valid vote
- ✅ Duplicate vote (409 Conflict) ⭐
- ✅ Invalid recommendation (404)
- ✅ Vote with wrong status (400)
- ✅ Get vote counts

### Close Voting Tests
- ✅ Close voting successfully
- ✅ Close with wrong status (400)
- ✅ Tie-breaking by first vote ⭐

### Result Tests
- ✅ Get result after closed
- ✅ Get result before closed

### UI Tests
- ✅ Dashboard page loads
- ✅ Dashboard invalid trip (404)
- ✅ Home page loads

## Running Tests

### Local Environment

1. Install test dependencies:
```bash
pip install -r requirements.txt
```

2. Run all tests:
```bash
pytest test_api.py -v
```

3. Run specific test class:
```bash
pytest test_api.py::TestVoting -v
```

4. Run with coverage:
```bash
pytest test_api.py --cov=main --cov-report=html
```

### Docker Environment

1. Build and start services:
```bash
docker-compose up -d --build
```

2. Run tests inside container:
```bash
docker-compose exec app pytest test_api.py -v
```

## Test Database

Tests use an in-memory SQLite database (`test.db`) that is:
- Created fresh for each test function
- Automatically cleaned up after each test
- Isolated from production PostgreSQL database

## Key Test Features

### Fixtures
- `client`: Fresh test client with clean database
- `sample_trip`: Pre-created trip for testing
- `trip_with_preferences`: Trip with 3 participant preferences
- `trip_with_recommendations`: Trip with mock recommendations in voting phase

### HTTP Status Codes Tested
- 200: Success
- 400: Bad Request (validation errors, wrong status)
- 404: Not Found (invalid IDs, non-existent resources)
- 409: Conflict (duplicate votes) ⭐
- 422: Unprocessable Entity (Pydantic validation errors)

### Special Test Cases

#### Duplicate Vote Returns 409
```python
def test_cast_duplicate_vote(self, client, trip_with_recommendations):
    # First vote succeeds
    response1 = client.post(f"/vote/{join_code}", json=vote_data)
    assert response1.status_code == 200
    
    # Duplicate vote returns 409 Conflict
    response2 = client.post(f"/vote/{join_code}", json=vote_data)
    assert response2.status_code == 409
```

#### Tie-Breaking by First Vote
```python
def test_close_voting_tie_breaking(self, client, trip_with_recommendations):
    # Create tie: both get 1 vote
    # First vote cast wins the tie
    client.post(f"/vote/{join_code}", json={
        "participant_name": "Alice",
        "recommendation_id": rec_ids[0]  # This one wins (first vote)
    })
    client.post(f"/vote/{join_code}", json={
        "participant_name": "Bob",
        "recommendation_id": rec_ids[1]
    })
    
    response = client.post(f"/close-voting/{join_code}")
    assert response.json()["winner_id"] == rec_ids[0]  # First vote wins
```

## Test Output Example

```
test_api.py::TestTripCreation::test_create_trip_success PASSED
test_api.py::TestTripCreation::test_get_trip_not_found PASSED
test_api.py::TestPreferences::test_submit_preference_success PASSED
test_api.py::TestPreferences::test_submit_duplicate_preference PASSED
test_api.py::TestVoting::test_cast_vote_success PASSED
test_api.py::TestVoting::test_cast_duplicate_vote PASSED
test_api.py::TestCloseVoting::test_close_voting_tie_breaking PASSED

======================== 25 passed in 2.34s ========================
```

## Notes

- LLM integration tests are limited since they require actual Ollama service
- Tests focus on API logic, validation, and database constraints
- Mock recommendations are used for voting tests to avoid LLM dependency
- All tests are independent and can run in any order
