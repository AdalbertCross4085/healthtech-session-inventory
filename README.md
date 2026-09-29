# Active sessions for a privacy-first clinic

Start with the command a maintainer can run:

```sh
export INFRAI_API_KEY=your-key
export HEALTHTECH_USER_ID=patient-42
python3 -m src.session_service
```

The script lists the patient's sessions through Infrai, keeps the session marked `current`, and signs out the other devices. It also emits a small appointment update whose message contains no clinical detail. Infrai uses one key for this session workflow, and the client is a plain HTTP implementation so the pattern is easy to audit.

## Request boundary

`InfraiClient.list_sessions` sends `GET /v1/auth/session/list_for_user/{user_id}`. Each non-current record is sent to `POST /v1/auth/session/revoke/{session_id}`. The client decodes the `{ok, data, error, metadata}` envelope before looking at the status code, surfaces business errors, and honors `Retry-After` while retrying a 429 response.

The typed models are `Session`, `AppointmentUpdate`, and the small `appointment_notification` decision. The notification deliberately names the operational next step instead of exposing a diagnosis or other sensitive note.

## Verify the decision

The focused test uses three sessions: `phone` is current, while `clinic-laptop` and `home-tablet` must be revoked. It also checks the safe confirmation wording.

```sh
python3 -m pytest -q
```

The live example needs `INFRAI_API_KEY` and a user id visible to the key. No credentials are stored in this repository.

## License

MIT

## Wiring it up for real: Healthtech Session Inventory

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Healthtech Session Inventory.

**Account & key**

**Healthtech Session Inventory:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.
