"""Response export tests (Google Sheets + CSV).

Network boundaries (code exchange, id_token verification, Sheets API)
are mocked with monkeypatch. Everything else runs against the test DB.
"""

from datetime import datetime, timezone

import csv
import io

import pytest
from cryptography.fernet import Fernet
from fastapi import status

from app.core.config import settings
from app.core.limiter import limiter
from app.features.export.models import UserGoogleToken
from app.features.export.service import build_rows, build_spreadsheet_title
from app.features.export.utils import google_oauth, google_sheets
from app.features.export.utils.crypto import decrypt_token
from app.features.export.utils.csv_export import build_csv_filename, rows_to_csv_bytes
from app.features.form.models import Form, FormQuestion
from app.features.response.models import Response, ResponseAnswer


@pytest.fixture(autouse=True)
def export_test_env(monkeypatch):
    """Hermetic Fernet key + fresh rate-limit bucket for every test."""
    monkeypatch.setattr(
        settings,
        "GOOGLE_SHEETS_TOKEN_ENCRYPTION_KEY",
        Fernet.generate_key().decode(),
    )
    limiter.reset()
    yield


@pytest.fixture
def test_user_data():
    return {"email": "export@example.com", "password": "testpassword123"}


@pytest.fixture
def second_user_data():
    return {"email": "export-other@example.com", "password": "otherpass123"}


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
        "title": "Export Form",
        "description": "A form for export tests",
        "questions": [
            {
                "id": "q1",
                "text": "What is your name?",
                "answer_type": "text",
                "answer_select_options": None,
                "answer_select_multiple": None,
                "required": True,
            },
            {
                "id": "q2",
                "text": "Pick colors",
                "answer_type": "select",
                "answer_select_options": ["Red", "Blue"],
                "answer_select_multiple": True,
                "required": False,
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
                "text_answer": "John Doe",
                "select_answer": None,
            },
            {
                "question_id": "q2",
                "answer_type": "select",
                "text_answer": None,
                "select_answer": ["Red", "Blue"],
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


def mock_google_connect(monkeypatch, email="export@gmail.com"):
    monkeypatch.setattr(
        google_oauth,
        "exchange_code",
        lambda code, code_verifier, redirect_uri: {
            "refresh_token": "fake_refresh",
            "access_token": "fake_access",
            "id_token": "fake_id_token",
        },
    )
    monkeypatch.setattr(
        google_oauth,
        "get_id_token_email",
        lambda id_token_string: email,
    )


def connect(client, auth_headers):
    return client.post(
        "/api/v1/export/google/tokens",
        headers=auth_headers,
        json={
            "code": "one-time-code",
            "code_verifier": "a" * 60,
            "redirect_uri": "http://localhost:3000/export/google/callback",
        },
    )


class TestGoogleExportStatus:
    def test_status_not_connected(self, client, auth_headers):
        res = client.get("/api/v1/export/google/status", headers=auth_headers)
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["data"] == {"connected": False, "google_email": None}

    def test_status_unauthorized(self, client):
        res = client.get("/api/v1/export/google/status")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


class TestGoogleConnect:
    def test_connect_stores_encrypted_token(
        self, client, auth_headers, db_session, registered_user, monkeypatch
    ):
        mock_google_connect(monkeypatch)
        res = connect(client, auth_headers)
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["data"] == {
            "connected": True,
            "google_email": "export@gmail.com",
        }

        row = (
            db_session.query(UserGoogleToken)
            .filter(UserGoogleToken.user_id == registered_user["data"]["id"])
            .one()
        )
        assert decrypt_token(row.google_refresh_token) == "fake_refresh"
        assert row.google_email == "export@gmail.com"

    def test_connect_without_refresh_token_400(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(
            google_oauth,
            "exchange_code",
            lambda code, code_verifier, redirect_uri: {
                "refresh_token": "",
                "access_token": "fake_access",
                "id_token": "fake_id_token",
            },
        )
        res = connect(client, auth_headers)
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_connect_exchange_failure_400(self, client, auth_headers, monkeypatch):
        def _boom(code, code_verifier, redirect_uri):
            raise Exception("invalid_grant")

        monkeypatch.setattr(google_oauth, "exchange_code", _boom)
        res = connect(client, auth_headers)
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_connect_without_redirect_uri_422(self, client, auth_headers):
        res = client.post(
            "/api/v1/export/google/tokens",
            headers=auth_headers,
            json={"code": "one-time-code", "code_verifier": "a" * 60},
        )
        assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGoogleExchangeRedirect:
    def test_redirect_uri_forwarded_to_flow(self, monkeypatch):
        seen = {}

        class FakeCredentials:
            refresh_token = "r"
            token = "a"
            id_token = "i"

        class FakeFlow:
            def __init__(self):
                self.redirect_uri = None
                self.credentials = FakeCredentials()

            def fetch_token(self, code, code_verifier):
                seen["code"] = code
                seen["code_verifier"] = code_verifier

        def fake_from_client_config(config, scopes):
            seen["config"] = config
            seen["scopes"] = scopes
            flow = FakeFlow()
            seen["flow"] = flow
            return flow

        monkeypatch.setattr(
            google_oauth.Flow, "from_client_config", fake_from_client_config
        )

        tokens = google_oauth.exchange_code(
            code="c",
            code_verifier="v" * 60,
            redirect_uri="http://localhost:3000/export/google/callback",
        )

        assert tokens == {
            "refresh_token": "r",
            "access_token": "a",
            "id_token": "i",
        }
        assert (
            seen["flow"].redirect_uri == "http://localhost:3000/export/google/callback"
        )
        assert seen["config"]["web"]["redirect_uris"] == [
            "http://localhost:3000/export/google/callback"
        ]
        assert seen["code"] == "c"


def make_form(title="Feedback", questions=None):
    if questions is None:
        questions = [
            FormQuestion(id="q1", text="Name", answer_type="text", required=True),
            FormQuestion(
                id="q2",
                text="Colors",
                answer_type="select",
                answer_select_options=["Red", "Blue"],
                answer_select_multiple=True,
                required=False,
            ),
        ]
    return Form(title=title, description="d", questions=questions, user_id="u1")


def make_response(created_at, answers):
    return Response(answers=answers, form_id="f1", created_at=created_at)


class TestRowSerializer:
    def test_build_rows_happy_path(self):
        form = make_form()
        r_new = make_response(
            datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
            [
                # answers deliberately unordered
                ResponseAnswer(
                    question_id="q2",
                    answer_type="select",
                    select_answer=["Blue", "Red"],
                ),
                ResponseAnswer(
                    question_id="q1",
                    answer_type="text",
                    text_answer="  Ann  ",
                ),
            ],
        )
        r_old = make_response(
            datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            [
                ResponseAnswer(question_id="q1", answer_type="text", text_answer="Bob"),
            ],
        )
        rows = build_rows(form, [r_new, r_old])
        assert rows[0] == ["Submitted At", "Name", "Colors"]
        assert rows[1] == ["2026-01-01 00:00:00 UTC", "Bob", ""]
        assert rows[2] == ["2026-01-02 03:04:05 UTC", "Ann", "Blue, Red"]

    def test_build_rows_edge_cases(self):
        form = make_form()
        # unknown question ignored, missing answer -> "", no responses -> header
        r = make_response(
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            [
                ResponseAnswer(question_id="nope", answer_type="text", text_answer="x"),
                ResponseAnswer(
                    question_id="q2", answer_type="select", select_answer=None
                ),
            ],
        )
        assert build_rows(form, [r]) == [
            ["Submitted At", "Name", "Colors"],
            ["2026-01-01 00:00:00 UTC", "", ""],
        ]
        assert build_rows(form, []) == [["Submitted At", "Name", "Colors"]]

    def test_build_spreadsheet_title(self):
        assert build_spreadsheet_title(make_form("Feedback")) == "Feedback - Responses"
        long_title = build_spreadsheet_title(make_form("x" * 95))
        assert len(long_title) <= 100
        assert long_title.endswith("- Responses")
        edge = build_spreadsheet_title(make_form("y" * 88))
        assert edge == "y" * 88 + " - Responses"
        assert len(edge) == 100


class TestGoogleExportFlow:
    def test_export_requires_ownership(
        self, client, other_auth_headers, created_form, monkeypatch
    ):
        mock_google_connect(monkeypatch)
        form_id = created_form["data"]["id"]
        res = client.post(
            f"/api/v1/export/google/sheets/{form_id}", headers=other_auth_headers
        )
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_export_requires_connection(self, client, auth_headers, created_form):
        form_id = created_form["data"]["id"]
        res = client.post(
            f"/api/v1/export/google/sheets/{form_id}", headers=auth_headers
        )
        assert res.status_code == status.HTTP_409_CONFLICT

    def test_export_success(self, client, auth_headers, created_response, monkeypatch):
        mock_google_connect(monkeypatch)
        assert connect(client, auth_headers).status_code == status.HTTP_200_OK
        monkeypatch.setattr(
            google_sheets,
            "create_spreadsheet_with_rows",
            lambda refresh_token, title, rows: (
                "https://docs.google.com/spreadsheets/d/fake"
            ),
        )
        form_id = created_response["data"]["form_id"]
        res = client.post(
            f"/api/v1/export/google/sheets/{form_id}", headers=auth_headers
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["data"] == {
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/fake"
        }

    def test_export_dead_token_keeps_session(
        self, client, auth_headers, created_response, monkeypatch
    ):
        mock_google_connect(monkeypatch)
        assert connect(client, auth_headers).status_code == status.HTTP_200_OK

        def _dead(refresh_token, title, rows):
            raise Exception("invalid_grant")

        monkeypatch.setattr(google_sheets, "create_spreadsheet_with_rows", _dead)
        form_id = created_response["data"]["form_id"]
        res = client.post(
            f"/api/v1/export/google/sheets/{form_id}", headers=auth_headers
        )
        assert res.status_code == status.HTTP_409_CONFLICT

        # the Formbrew session must survive a Google-side failure (never 401)
        res = client.get(f"/api/v1/forms/{form_id}/responses", headers=auth_headers)
        assert res.status_code == status.HTTP_200_OK

    def test_export_undecryptable_token_reconnects(
        self, client, auth_headers, db_session, registered_user, created_form
    ):
        db_session.add(
            UserGoogleToken(
                user_id=registered_user["data"]["id"],
                google_refresh_token="not-a-fernet-token",
                google_email="export@gmail.com",
            )
        )
        db_session.commit()

        form_id = created_form["data"]["id"]
        res = client.post(
            f"/api/v1/export/google/sheets/{form_id}", headers=auth_headers
        )
        assert res.status_code == status.HTTP_409_CONFLICT

        # the bad row is forgotten — status flips back to disconnected
        res = client.get("/api/v1/export/google/status", headers=auth_headers)
        assert res.json()["data"] == {"connected": False, "google_email": None}


class TestGoogleDisconnect:
    def test_disconnect_lifecycle(self, client, auth_headers, monkeypatch):
        mock_google_connect(monkeypatch)
        assert connect(client, auth_headers).status_code == status.HTTP_200_OK

        res = client.post("/api/v1/export/google/disconnect", headers=auth_headers)
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["message"] == "Google Sheets disconnected"
        assert "data" not in res.json()

        res = client.get("/api/v1/export/google/status", headers=auth_headers)
        assert res.json()["data"] == {"connected": False, "google_email": None}

        res = client.post("/api/v1/export/google/disconnect", headers=auth_headers)
        assert res.status_code == status.HTTP_404_NOT_FOUND


class TestCsvUtils:
    def test_rows_to_csv_bytes_roundtrip(self):
        rows = [
            ["Submitted At", "Name", "Colors"],
            ["2026-01-01 00:00:00 UTC", "Ann, Jr.", "Blue, Red"],
            ["2026-01-02 00:00:00 UTC", 'q"uote', "line\nbreak café"],
        ]
        content = rows_to_csv_bytes(rows)
        assert content.startswith("﻿".encode("utf-8"))  # BOM for Excel
        assert b"\r\n" in content
        parsed = list(csv.reader(io.StringIO(content.decode("utf-8-sig"))))
        assert parsed == rows

    def test_rows_to_csv_bytes_header_only(self):
        content = rows_to_csv_bytes([["Submitted At", "Name"]])
        assert list(csv.reader(io.StringIO(content.decode("utf-8-sig")))) == [
            ["Submitted At", "Name"]
        ]

    def test_build_csv_filename(self):
        assert build_csv_filename("My Form! 2026") == "my-form-2026-responses.csv"
        assert build_csv_filename("   ") == "form-responses.csv"
        assert build_csv_filename("Export Form") == "export-form-responses.csv"
        long_name = build_csv_filename("x" * 100)
        assert long_name.endswith("-responses.csv")
        assert len(long_name) <= len("x" * 50 + "-responses.csv")


class TestCsvDownload:
    def test_csv_download_success(self, client, auth_headers, created_response):
        # no Google connection needed — CSV works connectionless
        form_id = created_response["data"]["form_id"]
        res = client.get(f"/api/v1/export/csv/{form_id}", headers=auth_headers)
        assert res.status_code == status.HTTP_200_OK
        assert res.headers["content-type"].startswith("text/csv")
        assert "attachment" in res.headers["content-disposition"]
        assert "export-form-responses.csv" in res.headers["content-disposition"]
        assert res.content.startswith("﻿".encode("utf-8"))
        parsed = list(csv.reader(io.StringIO(res.content.decode("utf-8-sig"))))
        assert parsed[0] == ["Submitted At", "What is your name?", "Pick colors"]
        assert parsed[1][1] == "John Doe"
        assert parsed[1][2] == "Red, Blue"

    def test_csv_empty_is_header_only(self, client, auth_headers, created_form):
        form_id = created_form["data"]["id"]
        res = client.get(f"/api/v1/export/csv/{form_id}", headers=auth_headers)
        assert res.status_code == status.HTTP_200_OK
        parsed = list(csv.reader(io.StringIO(res.content.decode("utf-8-sig"))))
        assert parsed == [["Submitted At", "What is your name?", "Pick colors"]]

    def test_csv_requires_ownership(self, client, other_auth_headers, created_form):
        form_id = created_form["data"]["id"]
        res = client.get(f"/api/v1/export/csv/{form_id}", headers=other_auth_headers)
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_csv_unauthorized(self, client, created_form):
        form_id = created_form["data"]["id"]
        res = client.get(f"/api/v1/export/csv/{form_id}")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_csv_form_not_found(self, client, auth_headers):
        res = client.get("/api/v1/export/csv/does-not-exist", headers=auth_headers)
        assert res.status_code == status.HTTP_404_NOT_FOUND
