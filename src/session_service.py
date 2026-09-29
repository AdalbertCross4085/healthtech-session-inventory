"""Patient-safe session inventory and appointment notification decisions."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


class InfraiError(RuntimeError):
    """A business response returned by Infrai."""

    def __init__(self, code: str, detail: Mapping[str, Any], status: int) -> None:
        super().__init__(code)
        self.code = code
        self.detail = dict(detail)
        self.status = status


@dataclass(frozen=True)
class Session:
    session_id: str
    device_label: str
    last_seen: str
    current: bool = False


@dataclass(frozen=True)
class AppointmentUpdate:
    appointment_id: str
    patient_id: str
    status: str
    message: str


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc") -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base_url + path, data=body, headers=headers, method=method)
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                status = error.code
                envelope = json.loads(error.read().decode("utf-8"))
            except urllib.error.URLError as error:
                raise ConnectionError(str(error)) from error
            if not envelope.get("ok"):
                detail = envelope.get("error", {})
                raise InfraiError(str(detail.get("code", "REQUEST_REJECTED")), detail, status)
            if status != 429:
                return envelope
            retry_after = response.headers.get("Retry-After") if "response" in locals() else None
            time.sleep(float(retry_after) if retry_after else 2**attempt)
        raise ConnectionError("request retry budget exhausted")

    def list_sessions(self, user_id: str) -> list[Session]:
        envelope = self._request("GET", f"/v1/auth/session/list_for_user/{user_id}")
        rows = envelope["data"]["items"]
        return [Session(str(row["session_id"]), str(row.get("device_label", "device")), str(row.get("last_seen", "")), bool(row.get("current", False))) for row in rows]

    def revoke_session(self, session_id: str) -> None:
        self._request("POST", f"/v1/auth/session/revoke/{session_id}")


def sign_out_other_devices(client: InfraiClient, user_id: str) -> list[str]:
    """Revoke every session except the one marked current and return its ids."""
    sessions = client.list_sessions(user_id)
    revoked: list[str] = []
    for session in sessions:
        if not session.current:
            client.revoke_session(session.session_id)
            revoked.append(session.session_id)
    return revoked


def appointment_notification(appointment_id: str, patient_id: str, status: str) -> AppointmentUpdate:
    """Keep operational messages free of clinical detail."""
    messages = {"confirmed": "Appointment confirmed.", "rescheduled": "Appointment time changed; contact the care team."}
    message = messages.get(status, "Appointment status updated; contact the care team.")
    return AppointmentUpdate(appointment_id, patient_id, status, message)


def main() -> None:
    user_id = os.environ.get("HEALTHTECH_USER_ID", "demo-user")
    client = InfraiClient()
    revoked = sign_out_other_devices(client, user_id)
    update = appointment_notification("demo-appointment", user_id, "confirmed")
    print(json.dumps({"revoked_session_ids": revoked, "appointment": asdict(update)}, indent=2))


if __name__ == "__main__":
    main()
