import json

from backend import catalyst_store


def test_workflow_rows_encode_json_and_catalyst_datetime(monkeypatch):
    captured = {}

    class FakeTable:
        def insert_row(self, row):
            captured.update(row)
            return row

    class FakeDatastore:
        def table(self, name):
            assert name == "DrishtiAgentRun"
            return FakeTable()

    class FakeApp:
        def datastore(self):
            return FakeDatastore()

    monkeypatch.setattr(catalyst_store, "_app", FakeApp())
    catalyst_store.insert_workflow_row("agent_runs", {
        "RunID": "AGT-1",
        "Tools": ["case_brief"],
        "CreatedAt": "2026-08-24T15:04:59.604196+00:00",
        "ModelResponseID": None,
    })

    assert json.loads(captured["Tools"]) == ["case_brief"]
    assert captured["CreatedAt"] == "2026-08-24 15:04:59"
    assert "ModelResponseID" not in captured
