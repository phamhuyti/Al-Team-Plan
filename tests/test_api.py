from fastapi.testclient import TestClient

from ai_team.api.app import create_app
from ai_team.config import Settings


def test_health_and_agents(project_root, settings: Settings) -> None:
    app = create_app(project_root, settings)
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    agents = client.get("/agents").json()
    roles = {row["role"] for row in agents}
    assert {"manager", "architect", "coder", "reviewer", "redteam", "researcher"} <= roles

    created = client.post("/tasks", json={"title": "Add authentication"}).json()
    assert created["task_key"].startswith("TASK-")
    fetched = client.get(f"/tasks/{created['task_key']}").json()
    assert fetched["title"] == "Add authentication"
