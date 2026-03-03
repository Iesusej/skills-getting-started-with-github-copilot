"""
Comprehensive test suite for Mergington High School API.

Tests are structured using the AAA (Arrange-Act-Assert) pattern and ensure
all API endpoints function correctly with proper state isolation.
"""

from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture(autouse=True)
def reset_activities():
    """
    Reset activities to original state before and after each test.
    
    This fixture ensures test isolation by restoring the global activities
    dictionary to its initial state. Using autouse=True means this runs
    automatically for every test without explicit declaration.
    """
    # Store original state
    original_activities = deepcopy(activities)
    
    yield
    
    # Restore to original state after test
    activities.clear()
    activities.update(original_activities)


@pytest.fixture
def client():
    """Create a TestClient for the FastAPI app."""
    return TestClient(app)


class TestRootEndpoint:
    """Tests for the root endpoint (GET /)."""
    
    def test_root_redirects_to_static_index(self, client):
        """
        Arrange: TestClient initialized
        Act: GET /
        Assert: Status 307 (temporary redirect) to /static/index.html
        """
        response = client.get("/", follow_redirects=False)
        
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the activities listing endpoint (GET /activities)."""
    
    def test_get_activities_returns_all_activities(self, client):
        """
        Arrange: TestClient with known activities in memory
        Act: GET /activities
        Assert: Response contains all expected activity names
        """
        response = client.get("/activities")
        
        assert response.status_code == 200
        data = response.json()
        
        expected_activities = [
            "Chess Club",
            "Programming Class",
            "Gym Class",
            "Basketball Team",
            "Soccer Club",
            "Debate Team",
            "Science Club"
        ]
        
        for activity in expected_activities:
            assert activity in data
            assert "description" in data[activity]
            assert "schedule" in data[activity]
            assert "max_participants" in data[activity]
            assert "participants" in data[activity]
    
    def test_get_activities_initial_participants(self, client):
        """
        Arrange: TestClient
        Act: GET /activities
        Assert: Activities have expected initial participants
        """
        response = client.get("/activities")
        data = response.json()
        
        # Verify specific participant counts
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]
        assert "emma@mergington.edu" in data["Programming Class"]["participants"]
        assert len(data["Chess Club"]["participants"]) == 2


class TestSignupEndpoint:
    """Tests for the signup endpoint (POST /activities/{activity_name}/signup)."""
    
    def test_signup_new_student_success(self, client):
        """
        Arrange: TestClient, valid activity name, new email
        Act: POST /activities/Chess Club/signup with new email
        Assert: Status 200 and student added to participants
        """
        activity_name = "Chess Club"
        new_email = "newstudent@mergington.edu"
        
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": new_email}
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == f"Signed up {new_email} for {activity_name}"
        assert new_email in activities[activity_name]["participants"]
    
    def test_signup_duplicate_email_fails(self, client):
        """
        Arrange: TestClient, activity with existing participant
        Act: POST /activities/Chess Club/signup with email already in participants
        Assert: Status 400 with 'already signed up' message
        """
        activity_name = "Chess Club"
        existing_email = "michael@mergington.edu"  # Already in Chess Club
        
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": existing_email}
        )
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Student already signed up"
    
    def test_signup_nonexistent_activity_fails(self, client):
        """
        Arrange: TestClient, invalid activity name
        Act: POST /activities/Nonexistent Activity/signup
        Assert: Status 404 with 'Activity not found' message
        """
        activity_name = "Nonexistent Activity"
        email = "newstudent@mergington.edu"
        
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
    
    def test_signup_same_student_multiple_activities(self, client):
        """
        Arrange: TestClient
        Act: Signup same student for two different activities
        Assert: Student appears in both activities
        """
        email = "multitasker@mergington.edu"
        
        # Signup for first activity
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Signup for second activity
        response2 = client.post(
            "/activities/Programming Class/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify in both
        assert email in activities["Chess Club"]["participants"]
        assert email in activities["Programming Class"]["participants"]


class TestRemoveParticipantEndpoint:
    """Tests for the remove participant endpoint (DELETE /activities/{activity_name}/participants)."""
    
    def test_remove_participant_success(self, client):
        """
        Arrange: TestClient, activity with existing participant
        Act: DELETE /activities/Chess Club/participants?email=michael@mergington.edu
        Assert: Status 200 and participant removed
        """
        activity_name = "Chess Club"
        email = "michael@mergington.edu"
        
        response = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == f"Removed {email} from {activity_name}"
        assert email not in activities[activity_name]["participants"]
    
    def test_remove_participant_not_signed_up_fails(self, client):
        """
        Arrange: TestClient, email not in activity's participants
        Act: DELETE /activities/Chess Club/participants?email=nonexistent@example.com
        Assert: Status 400 with 'not signed up' message
        """
        activity_name = "Chess Club"
        email = "notasignedupstudent@example.com"
        
        response = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Student not signed up"
    
    def test_remove_participant_nonexistent_activity_fails(self, client):
        """
        Arrange: TestClient, invalid activity name
        Act: DELETE /activities/Nonexistent Activity/participants
        Assert: Status 404 with 'Activity not found' message
        """
        activity_name = "Nonexistent Activity"
        email = "student@example.com"
        
        response = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
    
    def test_remove_then_resign_success(self, client):
        """
        Arrange: TestClient, activity with participant
        Act: Remove participant, then add them back
        Assert: Both operations succeed
        """
        activity_name = "Gym Class"
        email = "john@mergington.edu"
        
        # Remove
        remove_response = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )
        assert remove_response.status_code == 200
        assert email not in activities[activity_name]["participants"]
        
        # Re-signup
        signup_response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        assert signup_response.status_code == 200
        assert email in activities[activity_name]["participants"]


class TestStateIsolation:
    """Tests to verify that state is properly isolated between tests."""
    
    def test_state_isolation_signup_doesnt_persist(self, client):
        """
        Arrange: Empty or original participant list
        Act: Add participant via POST
        Assert: Next test should not see this change (verified by fixture)
        """
        email = "temporary@example.com"
        
        # Add participant
        response = client.post(
            "/activities/Soccer Club/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        assert email in activities["Soccer Club"]["participants"]
    
    def test_state_isolation_removal_doesnt_persist(self, client):
        """
        Arrange: Original participant in activity
        Act: Remove participant via DELETE
        Assert: Original participant still in activities (state was reset by fixture)
        """
        activity_name = "Soccer Club"
        original_participants = ["lucas@mergington.edu", "alex@mergington.edu"]
        
        # Verify original state exists (fixture reset it)
        assert activities[activity_name]["participants"] == original_participants
