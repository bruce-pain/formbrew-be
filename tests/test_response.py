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
def other_auth_headers(second_user):
    return {"Authorization": f"Bearer {second_user['access_token']}"}


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
                "required": True,
            },
        ],
    }


@pytest.fixture
def created_form(client, auth_headers, sample_form_data):
    response = client.post("/api/v1/forms", json=sample_form_data, headers=auth_headers)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


@pytest.fixture
def published_form(client, auth_headers, sample_form_data):
    response = client.post("/api/v1/forms", json=sample_form_data, headers=auth_headers)
    assert response.status_code == status.HTTP_201_CREATED
    form_id = response.json()["data"]["id"]
    response = client.patch(
        f"/api/v1/forms/{form_id}",
        json={"is_published": True},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    return response.json()


@pytest.fixture
def sample_response_data():
    return {
        "answers": [
            {
                "question_id": "q1",
                "answer_type": "text",
                "value": "John Doe",
            },
            {
                "question_id": "q2",
                "answer_type": "select",
                "selected_option": "Option A",
            },
        ],
    }


@pytest.fixture
def created_response(client, published_form, sample_response_data):
    form_id = published_form["data"]["id"]
    response = client.post(
        f"/api/v1/forms/{form_id}/responses", json=sample_response_data
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


class TestSubmitResponse:
    def test_submit_response_success(
        self, client, published_form, sample_response_data
    ):
        form_id = published_form["data"]["id"]
        response = client.post(
            f"/api/v1/forms/{form_id}/responses", json=sample_response_data
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["message"] == "Response submitted successfully"
        assert data["data"]["form_id"] == form_id
        assert len(data["data"]["answers"]) == 2

    def test_submit_response_form_not_published(
        self, client, created_form, sample_response_data
    ):
        form_id = created_form["data"]["id"]
        response = client.post(
            f"/api/v1/forms/{form_id}/responses", json=sample_response_data
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found or not published" in response.json()["message"].lower()

    def test_submit_response_form_not_found(self, client, sample_response_data):
        response = client.post(
            "/api/v1/forms/nonexistent-id/responses", json=sample_response_data
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_submit_response_missing_answers(self, client, published_form):
        form_id = published_form["data"]["id"]
        response = client.post(f"/api/v1/forms/{form_id}/responses", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_submit_response_text_missing_answer(self, client, published_form):
        form_id = published_form["data"]["id"]
        payload = {
            "answers": [
                {"question_id": "q1", "answer_type": "text", "value": None}
            ],
        }
        response = client.post(f"/api/v1/forms/{form_id}/responses", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_submit_response_select_missing_answer(self, client, published_form):
        form_id = published_form["data"]["id"]
        payload = {
            "answers": [
                {
                    "question_id": "q2",
                    "answer_type": "select",
                    "selected_option": None,
                }
            ],
        }
        response = client.post(f"/api/v1/forms/{form_id}/responses", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_submit_response_text_answer_rejects_extra_field(
        self, client, published_form
    ):
        form_id = published_form["data"]["id"]
        payload = {
            "answers": [
                {
                    "question_id": "q1",
                    "answer_type": "text",
                    "value": "foo",
                    "selected_option": "bar",
                }
            ],
        }
        response = client.post(f"/api/v1/forms/{form_id}/responses", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_submit_response_select_answer_rejects_extra_field(
        self, client, published_form
    ):
        form_id = published_form["data"]["id"]
        payload = {
            "answers": [
                {
                    "question_id": "q2",
                    "answer_type": "select",
                    "selected_option": "Option A",
                    "value": "foo",
                }
            ],
        }
        response = client.post(f"/api/v1/forms/{form_id}/responses", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_submit_response_unknown_question(self, client, published_form):
        form_id = published_form["data"]["id"]
        payload = {
            "answers": [
                {"question_id": "q3", "answer_type": "text", "value": "foo"}
            ],
        }
        response = client.post(f"/api/v1/forms/{form_id}/responses", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_submit_response_wrong_answer_type(self, client, published_form):
        form_id = published_form["data"]["id"]
        payload = {
            "answers": [
                {
                    "question_id": "q1",
                    "answer_type": "select",
                    "selected_option": "Option A",
                }
            ],
        }
        response = client.post(f"/api/v1/forms/{form_id}/responses", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_submit_response_invalid_select_option(self, client, published_form):
        form_id = published_form["data"]["id"]
        payload = {
            "answers": [
                {
                    "question_id": "q2",
                    "answer_type": "select",
                    "selected_option": "Option C",
                }
            ],
        }
        response = client.post(f"/api/v1/forms/{form_id}/responses", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_submit_response_missing_required_question(self, client, published_form):
        form_id = published_form["data"]["id"]
        payload = {
            "answers": [
                {
                    "question_id": "q2",
                    "answer_type": "select",
                    "selected_option": "Option A",
                }
            ],
        }
        response = client.post(f"/api/v1/forms/{form_id}/responses", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_submit_response_checkbox_success(self, client, auth_headers):
        form_data = {
            "title": "Checkbox Form",
            "description": "Form with a checkbox question",
            "questions": [
                {
                    "id": "cq1",
                    "text": "Pick topics",
                    "answer_type": "checkbox",
                    "options": ["A", "B", "C"],
                    "required": False,
                }
            ],
        }
        response = client.post("/api/v1/forms", json=form_data, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        form_id = response.json()["data"]["id"]
        response = client.patch(
            f"/api/v1/forms/{form_id}",
            json={"is_published": True},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        payload = {
            "answers": [
                {
                    "question_id": "cq1",
                    "answer_type": "checkbox",
                    "selected_options": ["A", "C"],
                }
            ],
        }
        response = client.post(f"/api/v1/forms/{form_id}/responses", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["data"]["answers"][0]["selected_options"] == ["A", "C"]

    def test_submit_response_checkbox_empty_not_required(self, client, auth_headers):
        form_data = {
            "title": "Checkbox Form",
            "description": "Form with a checkbox question",
            "questions": [
                {
                    "id": "cq1",
                    "text": "Pick topics",
                    "answer_type": "checkbox",
                    "options": ["A", "B", "C"],
                    "required": False,
                }
            ],
        }
        response = client.post("/api/v1/forms", json=form_data, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        form_id = response.json()["data"]["id"]
        response = client.patch(
            f"/api/v1/forms/{form_id}",
            json={"is_published": True},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        payload = {
            "answers": [
                {
                    "question_id": "cq1",
                    "answer_type": "checkbox",
                    "selected_options": None,
                }
            ],
        }
        response = client.post(f"/api/v1/forms/{form_id}/responses", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["data"]["answers"][0]["selected_options"] is None

    def test_submit_response_invalid_checkbox_option(self, client, auth_headers):
        form_data = {
            "title": "Checkbox Form",
            "description": "Form with a checkbox question",
            "questions": [
                {
                    "id": "cq1",
                    "text": "Pick topics",
                    "answer_type": "checkbox",
                    "options": ["A", "B", "C"],
                    "required": False,
                }
            ],
        }
        response = client.post("/api/v1/forms", json=form_data, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        form_id = response.json()["data"]["id"]
        response = client.patch(
            f"/api/v1/forms/{form_id}",
            json={"is_published": True},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        payload = {
            "answers": [
                {
                    "question_id": "cq1",
                    "answer_type": "checkbox",
                    "selected_options": ["A", "ZZZ"],
                }
            ],
        }
        response = client.post(f"/api/v1/forms/{form_id}/responses", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_submit_response_non_required_question_empty_answer(
        self, client, auth_headers
    ):
        form_data = {
            "title": "Optional Questions Form",
            "description": "Form with optional questions",
            "questions": [
                {
                    "id": "oq1",
                    "text": "Optional text",
                    "answer_type": "text",
                    "required": False,
                },
                {
                    "id": "oq2",
                    "text": "Optional select",
                    "answer_type": "select",
                    "options": ["X", "Y"],
                    "required": False,
                },
            ],
        }
        response = client.post("/api/v1/forms", json=form_data, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        form_id = response.json()["data"]["id"]

        response = client.patch(
            f"/api/v1/forms/{form_id}",
            json={"is_published": True},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        payload = {
            "answers": [
                {"question_id": "oq1", "answer_type": "text", "value": None},
                {
                    "question_id": "oq2",
                    "answer_type": "select",
                    "selected_option": None,
                },
            ],
        }
        response = client.post(f"/api/v1/forms/{form_id}/responses", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["data"]["answers"][0]["value"] is None
        assert data["data"]["answers"][1]["selected_option"] is None


class TestListResponses:
    def test_list_responses_success(self, client, auth_headers, created_response):
        form_id = created_response["data"]["form_id"]
        response = client.get(
            f"/api/v1/forms/{form_id}/responses", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Responses retrieved successfully"
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == created_response["data"]["id"]

    def test_list_responses_empty(self, client, auth_headers, published_form):
        form_id = published_form["data"]["id"]
        response = client.get(
            f"/api/v1/forms/{form_id}/responses", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"] == []

    def test_list_responses_unauthorized(self, client, published_form):
        form_id = published_form["data"]["id"]
        response = client.get(f"/api/v1/forms/{form_id}/responses")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_responses_other_user(
        self, client, other_auth_headers, created_response
    ):
        form_id = created_response["data"]["form_id"]
        response = client.get(
            f"/api/v1/forms/{form_id}/responses", headers=other_auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_responses_form_not_found(self, client, auth_headers):
        response = client.get(
            "/api/v1/forms/nonexistent-id/responses", headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGetResponse:
    def test_get_response_success(self, client, auth_headers, created_response):
        form_id = created_response["data"]["form_id"]
        response_id = created_response["data"]["id"]
        response = client.get(
            f"/api/v1/forms/{form_id}/responses/{response_id}",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Response retrieved successfully"
        assert data["data"]["id"] == response_id
        assert data["data"]["form_id"] == form_id
        assert len(data["data"]["answers"]) == 2

    def test_get_response_unauthorized(self, client, created_response):
        form_id = created_response["data"]["form_id"]
        response_id = created_response["data"]["id"]
        response = client.get(f"/api/v1/forms/{form_id}/responses/{response_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_response_other_user(
        self, client, other_auth_headers, created_response
    ):
        form_id = created_response["data"]["form_id"]
        response_id = created_response["data"]["id"]
        response = client.get(
            f"/api/v1/forms/{form_id}/responses/{response_id}",
            headers=other_auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_response_not_found(self, client, auth_headers, published_form):
        form_id = published_form["data"]["id"]
        response = client.get(
            f"/api/v1/forms/{form_id}/responses/nonexistent-id",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_response_invalid_form(self, client, auth_headers, created_response):
        response_id = created_response["data"]["id"]
        response = client.get(
            f"/api/v1/forms/nonexistent-id/responses/{response_id}",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
