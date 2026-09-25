import pytest
from fastapi import status


@pytest.fixture
def test_user_data():
    return {"email": "test@example.com", "password": "testpassword123"}


@pytest.fixture
def second_user_data():
    return {"email": "other@example.com", "password": "otherpass123"}


@pytest.fixture
def registered_user(client, test_user_data):
    response = client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


@pytest.fixture
def second_user(client, second_user_data):
    response = client.post("/api/v1/auth/register", json=second_user_data)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


@pytest.fixture
def auth_headers(registered_user):
    return {"Authorization": f"Bearer {registered_user['access_token']}"}


@pytest.fixture
def sample_form_data():
    return {
        "title": "Test Form",
        "description": "A test form description",
        "questions": [
            {
                "id": "q1",
                "text": "What is your name?",
                "answer_type": "text",
                "required": True,
            },
            {
                "id": "q2",
                "text": "Select your preference",
                "answer_type": "select",
                "options": ["Option A", "Option B"],
                "required": False,
            },
        ],
    }


@pytest.fixture
def created_form(client, auth_headers, sample_form_data):
    response = client.post("/api/v1/forms", json=sample_form_data, headers=auth_headers)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


class TestCreateForm:
    def test_create_form_success(self, client, auth_headers, sample_form_data):
        response = client.post(
            "/api/v1/forms", json=sample_form_data, headers=auth_headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["message"] == "Form created successfully"
        assert data["data"]["title"] == sample_form_data["title"]
        assert data["data"]["description"] == sample_form_data["description"]
        assert data["data"]["is_published"] is False
        assert len(data["data"]["questions"]) == 2

    def test_create_form_no_questions(self, client, auth_headers):
        payload = {"title": "Minimal Form", "description": "No questions"}
        response = client.post("/api/v1/forms", json=payload, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["data"]["questions"] is None

    def test_create_form_missing_title(self, client, auth_headers):
        payload = {"description": "Missing title"}
        response = client.post("/api/v1/forms", json=payload, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_form_missing_description(self, client, auth_headers):
        payload = {"title": "No description"}
        response = client.post("/api/v1/forms", json=payload, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_form_unauthorized(self, client, sample_form_data):
        response = client.post("/api/v1/forms", json=sample_form_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_form_empty_title(self, client, auth_headers):
        payload = {"title": "", "description": "desc"}
        response = client.post("/api/v1/forms", json=payload, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_form_empty_description(self, client, auth_headers):
        payload = {"title": "Title", "description": ""}
        response = client.post("/api/v1/forms", json=payload, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_form_question_empty_text(self, client, auth_headers):
        payload = {
            "title": "Title",
            "description": "desc",
            "questions": [
                {"id": "q1", "text": "", "answer_type": "text", "required": False}
            ],
        }
        response = client.post("/api/v1/forms", json=payload, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_form_select_type_missing_options(self, client, auth_headers):
        payload = {
            "title": "Title",
            "description": "desc",
            "questions": [
                {
                    "id": "q1",
                    "text": "Pick one",
                    "answer_type": "select",
                    "options": [],
                    "required": False,
                }
            ],
        }
        response = client.post("/api/v1/forms", json=payload, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_form_checkbox_type_missing_options(self, client, auth_headers):
        payload = {
            "title": "Title",
            "description": "desc",
            "questions": [
                {
                    "id": "q1",
                    "text": "Pick several",
                    "answer_type": "checkbox",
                    "options": [],
                    "required": False,
                }
            ],
        }
        response = client.post("/api/v1/forms", json=payload, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_form_text_type_with_options(self, client, auth_headers):
        payload = {
            "title": "Title",
            "description": "desc",
            "questions": [
                {
                    "id": "q1",
                    "text": "Your name",
                    "answer_type": "text",
                    "options": ["A"],
                    "required": False,
                }
            ],
        }
        response = client.post("/api/v1/forms", json=payload, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestListForms:
    def test_list_forms_empty(self, client, auth_headers):
        response = client.get("/api/v1/forms", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"] == []

    def test_list_forms_with_data(self, client, auth_headers, created_form):
        response = client.get("/api/v1/forms", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["title"] == "Test Form"

    def test_list_forms_multiple(self, client, auth_headers):
        client.post(
            "/api/v1/forms",
            json={"title": "Form 1", "description": "First"},
            headers=auth_headers,
        )
        client.post(
            "/api/v1/forms",
            json={"title": "Form 2", "description": "Second"},
            headers=auth_headers,
        )
        response = client.get("/api/v1/forms", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["data"]) == 2

    def test_list_forms_unauthorized(self, client):
        response = client.get("/api/v1/forms")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetForm:
    def test_get_form_success(self, client, auth_headers, created_form):
        form_id = created_form["data"]["id"]
        response = client.get(f"/api/v1/forms/{form_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["title"] == "Test Form"
        assert response.json()["message"] == "Form retrieved successfully"

    def test_get_form_not_found(self, client, auth_headers):
        response = client.get("/api/v1/forms/nonexistent-id", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_form_unauthorized(self, client, created_form):
        form_id = created_form["data"]["id"]
        response = client.get(f"/api/v1/forms/{form_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_form_other_user(self, client, auth_headers, created_form, second_user):
        other_headers = {"Authorization": f"Bearer {second_user['access_token']}"}
        form_id = created_form["data"]["id"]
        response = client.get(f"/api/v1/forms/{form_id}", headers=other_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateForm:
    def test_update_form_success(self, client, auth_headers, created_form):
        form_id = created_form["data"]["id"]
        payload = {
            "title": "Updated Title",
            "description": "Updated description",
        }
        response = client.patch(
            f"/api/v1/forms/{form_id}", json=payload, headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Form updated successfully"
        assert response.json()["data"]["title"] == "Updated Title"
        assert response.json()["data"]["description"] == "Updated description"

    def test_update_form_partial_title(self, client, auth_headers, created_form):
        form_id = created_form["data"]["id"]
        payload = {"title": "Only Title Changed"}
        response = client.patch(
            f"/api/v1/forms/{form_id}", json=payload, headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["title"] == "Only Title Changed"
        assert response.json()["data"]["description"] == "A test form description"

    def test_update_form_no_fields(self, client, auth_headers, created_form):
        form_id = created_form["data"]["id"]
        response = client.patch(
            f"/api/v1/forms/{form_id}", json={}, headers=auth_headers
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_form_not_found(self, client, auth_headers):
        payload = {"title": "Nope"}
        response = client.patch(
            "/api/v1/forms/nonexistent-id", json=payload, headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_form_unauthorized(self, client, created_form):
        form_id = created_form["data"]["id"]
        payload = {"title": "Unauthorized"}
        response = client.patch(f"/api/v1/forms/{form_id}", json=payload)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_form_is_published(self, client, auth_headers, created_form):
        form_id = created_form["data"]["id"]
        assert created_form["data"]["is_published"] is False
        response = client.patch(
            f"/api/v1/forms/{form_id}",
            json={"is_published": True},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["is_published"] is True

    def test_update_form_other_user(
        self, client, auth_headers, created_form, second_user
    ):
        other_headers = {"Authorization": f"Bearer {second_user['access_token']}"}
        form_id = created_form["data"]["id"]
        payload = {"title": "Hacked"}
        response = client.patch(
            f"/api/v1/forms/{form_id}", json=payload, headers=other_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteForm:
    def test_delete_form_success(self, client, auth_headers, created_form):
        form_id = created_form["data"]["id"]
        response = client.delete(f"/api/v1/forms/{form_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_form_not_found(self, client, auth_headers):
        response = client.delete("/api/v1/forms/nonexistent-id", headers=auth_headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_form_unauthorized(self, client, created_form):
        form_id = created_form["data"]["id"]
        response = client.delete(f"/api/v1/forms/{form_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_form_other_user(
        self, client, auth_headers, created_form, second_user
    ):
        other_headers = {"Authorization": f"Bearer {second_user['access_token']}"}
        form_id = created_form["data"]["id"]
        response = client.delete(f"/api/v1/forms/{form_id}", headers=other_headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestGetPublicForm:
    @pytest.fixture
    def published_form(self, client, auth_headers, sample_form_data):
        response = client.post(
            "/api/v1/forms", json=sample_form_data, headers=auth_headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        form_id = response.json()["data"]["id"]
        response = client.patch(
            f"/api/v1/forms/{form_id}",
            json={"is_published": True},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        return form_id

    def test_get_public_form_success(self, client, published_form):
        response = client.get(f"/api/v1/forms/public/{published_form}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Form retrieved successfully"
        assert response.json()["data"]["is_published"] is True

    def test_get_public_form_not_published(self, client, created_form):
        form_id = created_form["data"]["id"]
        response = client.get(f"/api/v1/forms/public/{form_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found or not published" in response.json()["message"].lower()

    def test_get_public_form_not_found(self, client):
        response = client.get("/api/v1/forms/public/nonexistent-id")
        assert response.status_code == status.HTTP_404_NOT_FOUND
