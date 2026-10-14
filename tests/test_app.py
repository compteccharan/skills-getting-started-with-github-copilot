from copy import deepcopy

import httpx
import pytest

from src import app as app_module


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    original_activities = deepcopy(app_module.activities)
    transport = httpx.ASGITransport(app=app_module.app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        follow_redirects=False,
    ) as test_client:
        yield test_client

    app_module.activities.clear()
    app_module.activities.update(original_activities)


@pytest.mark.anyio
async def test_root_redirects_to_static_index(client):
    # Arrange
    expected_location = "/static/index.html"

    # Act
    response = await client.get("/")

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == expected_location


@pytest.mark.anyio
async def test_get_activities_returns_activity_catalog(client):
    # Arrange
    expected_activity = "Chess Club"

    # Act
    response = await client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert expected_activity in response.json()
    assert "participants" in response.json()[expected_activity]


@pytest.mark.anyio
async def test_signup_adds_participant(client):
    # Arrange
    activity = "Basketball Team"
    email = "student@mergington.edu"

    # Act
    response = await client.post(
        f"/activities/{activity}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "message": f"Signed up {email} for {activity}"
    }
    assert email in app_module.activities[activity]["participants"]


@pytest.mark.anyio
async def test_signup_rejects_duplicate_participant(client):
    # Arrange
    activity = "Chess Club"
    email = app_module.activities[activity]["participants"][0]

    # Act
    response = await client.post(
        f"/activities/{activity}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"


@pytest.mark.anyio
async def test_signup_rejects_unknown_activity(client):
    # Arrange
    activity = "Unknown Club"

    # Act
    response = await client.post(
        f"/activities/{activity}/signup",
        params={"email": "student@mergington.edu"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


@pytest.mark.anyio
async def test_unregister_removes_participant(client):
    # Arrange
    activity = "Chess Club"
    email = app_module.activities[activity]["participants"][0]

    # Act
    response = await client.request(
        "DELETE",
        f"/activities/{activity}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "message": f"Unregistered {email} from {activity}"
    }
    assert email not in app_module.activities[activity]["participants"]


@pytest.mark.anyio
async def test_unregister_rejects_unknown_activity(client):
    # Arrange
    activity = "Unknown Club"

    # Act
    response = await client.request(
        "DELETE",
        f"/activities/{activity}/signup",
        params={"email": "student@mergington.edu"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


@pytest.mark.anyio
async def test_unregister_rejects_missing_participant(client):
    # Arrange
    activity = "Basketball Team"
    email = "student@mergington.edu"

    # Act
    response = await client.request(
        "DELETE",
        f"/activities/{activity}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"
