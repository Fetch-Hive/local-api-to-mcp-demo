from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.seed import DEMO_ISSUE_TITLE

VIDEO_ISSUE = {
    "title": DEMO_ISSUE_TITLE,
    "description": "Leave checkout open for 30 minutes, then submit payment",
    "priority": "high",
    "status": "open",
}


@pytest.fixture
def client(tmp_path: Path):
    database_url = f"sqlite:///{tmp_path / 'issues.db'}"
    application = create_app(database_url)
    with TestClient(application) as test_client:
        yield test_client


def test_seeded_issue_listing(client: TestClient):
    response = client.get("/api/issues")
    assert response.status_code == 200
    issues = response.json()
    assert [issue["title"] for issue in issues] == [
        "Fix incorrect dashboard totals",
        "Review onboarding email copy",
        "Add CSV export",
    ]
    by_title = {issue["title"]: issue for issue in issues}
    assert by_title["Add CSV export"]["priority"] == "medium"
    assert by_title["Add CSV export"]["status"] == "open"
    assert by_title["Review onboarding email copy"]["priority"] == "low"
    assert by_title["Review onboarding email copy"]["status"] == "in_progress"
    assert by_title["Fix incorrect dashboard totals"]["priority"] == "high"
    assert by_title["Fix incorrect dashboard totals"]["status"] == "resolved"
    assert VIDEO_ISSUE["title"] not in by_title
    created = [issue["created_at"] for issue in issues]
    assert created == sorted(created, reverse=True)


def test_create_issue(client: TestClient):
    response = client.post("/api/issues", json=VIDEO_ISSUE)
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == VIDEO_ISSUE["title"]
    assert body["description"] == VIDEO_ISSUE["description"]
    assert body["priority"] == "high"
    assert body["status"] == "open"
    assert isinstance(body["id"], int)
    assert body["created_at"].endswith("Z")
    assert body["updated_at"] == body["created_at"]

    listing = client.get("/api/issues")
    assert listing.status_code == 200
    assert listing.json()[0]["id"] == body["id"]


def test_create_issue_defaults(client: TestClient):
    response = client.post("/api/issues", json={"title": "  Defaults  "})
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Defaults"
    assert body["description"] is None
    assert body["priority"] == "medium"
    assert body["status"] == "open"


def test_get_issue(client: TestClient):
    created = client.post("/api/issues", json=VIDEO_ISSUE).json()
    response = client.get(f"/api/issues/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_partial_update(client: TestClient):
    created = client.post("/api/issues", json=VIDEO_ISSUE).json()
    response = client.patch(
        f"/api/issues/{created['id']}",
        json={"status": "in_progress"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["title"] == created["title"]
    assert body["description"] == created["description"]
    assert body["priority"] == created["priority"]
    assert body["created_at"] == created["created_at"]
    assert body["updated_at"] > created["updated_at"]

    unchanged = client.patch(f"/api/issues/{created['id']}", json={})
    assert unchanged.status_code == 200
    assert unchanged.json()["updated_at"] == body["updated_at"]
    assert unchanged.json()["status"] == "in_progress"


def test_clear_description(client: TestClient):
    created = client.post("/api/issues", json=VIDEO_ISSUE).json()
    response = client.patch(
        f"/api/issues/{created['id']}",
        json={"description": None},
    )
    assert response.status_code == 200
    assert response.json()["description"] is None
    assert response.json()["title"] == created["title"]


def test_delete_issue(client: TestClient):
    created = client.post("/api/issues", json={"title": "Temporary"}).json()
    response = client.delete(f"/api/issues/{created['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/api/issues/{created['id']}").status_code == 404
    titles = [issue["title"] for issue in client.get("/api/issues").json()]
    assert "Temporary" not in titles


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": ""},
        {"title": "   "},
        {"title": "Ok", "priority": "urgent"},
        {"title": "Ok", "status": "closed"},
        {"title": "Ok", "owner": "someone"},
    ],
)
def test_create_validation_errors(client: TestClient, payload: dict):
    response = client.post("/api/issues", json=payload)
    assert response.status_code == 422


def test_update_validation_error(client: TestClient):
    created = client.post("/api/issues", json={"title": "Keep me"}).json()
    response = client.patch(
        f"/api/issues/{created['id']}",
        json={"priority": "urgent"},
    )
    assert response.status_code == 422
    assert client.get(f"/api/issues/{created['id']}").json()["priority"] == "medium"


def test_missing_issue(client: TestClient):
    missing = client.get("/api/issues/99999")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "No issue exists with this id."}
    assert client.patch("/api/issues/99999", json={"title": "Nope"}).status_code == 404
    assert client.delete("/api/issues/99999").status_code == 404


def test_homepage_and_static_files(client: TestClient):
    page = client.get("/")
    assert page.status_code == 200
    assert "text/html" in page.headers["content-type"]
    html = page.text
    assert "Local Issue Tracker" in html
    assert "Demo API" in html
    assert "Running locally on 127.0.0.1:8000" in html
    assert 'href="/docs"' in html
    assert 'href="/openapi.json"' in html
    assert page.headers["cache-control"] == "no-store"

    stylesheet = client.get("/static/styles.css")
    script = client.get("/static/app.js")
    assert stylesheet.status_code == 200
    assert "is-new" in stylesheet.text
    assert script.status_code == 200
    assert "const POLL_INTERVAL_MS = 2000;" in script.text
    assert "is-new" in script.text


def test_docs_and_openapi_document(client: TestClient):
    docs = client.get("/docs")
    assert docs.status_code == 200
    assert "text/html" in docs.headers["content-type"]

    response = client.get("/openapi.json")
    assert response.status_code == 200
    document = response.json()
    assert document["openapi"].startswith("3.")
    assert document["info"]["title"] == "Local Issue Tracker"
    assert document["servers"][0]["url"] == "http://127.0.0.1:8000"

    operations = {}
    for path, methods in document["paths"].items():
        for method, operation in methods.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            operations[(method, path)] = operation["operationId"]
    assert operations == {
        ("get", "/api/issues"): "list_issues",
        ("post", "/api/issues"): "create_issue",
        ("get", "/api/issues/{issue_id}"): "get_issue",
        ("patch", "/api/issues/{issue_id}"): "update_issue",
        ("delete", "/api/issues/{issue_id}"): "delete_issue",
    }

    delete_response = document["paths"]["/api/issues/{issue_id}"]["delete"]["responses"]["204"]
    assert "content" not in delete_response

    missing = _fields_missing_descriptions(document)
    assert missing == []


def _fields_missing_descriptions(document: dict) -> list[str]:
    components = document.get("components", {}).get("schemas", {})
    missing: list[str] = []
    for name, schema in components.items():
        if isinstance(schema, dict) and schema.get("type") == "object" and not schema.get("description"):
            missing.append(f"schema {name}")
        missing.extend(_property_gaps(schema, f"{name}", components))
    for path, methods in document["paths"].items():
        for method, operation in methods.items():
            if not isinstance(operation, dict):
                continue
            for param in operation.get("parameters", []):
                label = f"{method.upper()} {path} parameter {param.get('name')}"
                if not param.get("description"):
                    missing.append(label)
    return missing


def _property_gaps(node: object, path: str, components: dict) -> list[str]:
    if not isinstance(node, dict):
        return []
    missing: list[str] = []
    properties = node.get("properties")
    if isinstance(properties, dict):
        for name, details in properties.items():
            if not _has_description(details, components):
                missing.append(f"{path}.{name}")
            missing.extend(_property_gaps(details, f"{path}.{name}", components))
    for key in ("items", "additionalProperties"):
        if isinstance(node.get(key), dict):
            missing.extend(_property_gaps(node[key], f"{path}.{key}", components))
    for key in ("allOf", "anyOf", "oneOf"):
        for index, child in enumerate(node.get(key, [])):
            missing.extend(_property_gaps(child, f"{path}.{key}[{index}]", components))
    return missing


def _has_description(details: object, components: dict) -> bool:
    if not isinstance(details, dict):
        return False
    if details.get("description"):
        return True
    for key in ("allOf", "anyOf", "oneOf"):
        for child in details.get(key, []):
            if _has_description(child, components):
                return True
    ref = details.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
        target = components.get(ref.rsplit("/", 1)[-1], {})
        if isinstance(target, dict) and target.get("description"):
            return True
    return False
