from src.session_service import InfraiClient, appointment_notification, sign_out_other_devices


class FakeClient:
    def __init__(self):
        self.revoked = []

    def list_sessions(self, user_id):
        return [
            type("S", (), {"session_id": "phone", "current": True})(),
            type("S", (), {"session_id": "clinic-laptop", "current": False})(),
            type("S", (), {"session_id": "home-tablet", "current": False})(),
        ]

    def revoke_session(self, session_id):
        self.revoked.append(session_id)


def test_sign_out_other_devices_preserves_current_session():
    client = FakeClient()
    assert sign_out_other_devices(client, "patient-42") == ["clinic-laptop", "home-tablet"]
    assert client.revoked == ["clinic-laptop", "home-tablet"]


def test_appointment_notification_avoids_clinical_detail():
    update = appointment_notification("a-1", "p-1", "confirmed")
    assert update.message == "Appointment confirmed."
    assert "diagnosis" not in update.message.lower()


def test_list_sessions_reads_items_from_data(monkeypatch):
    client = InfraiClient(api_key="test-key")
    monkeypatch.setattr(client, "_request", lambda method, path: {"ok": True, "data": {"items": [
        {"session_id": "phone", "device_label": "Phone", "current": True}
    ]}})
    sessions = client.list_sessions("patient-42")
    assert len(sessions) == 1
    assert sessions[0].session_id == "phone"
    assert sessions[0].current is True
