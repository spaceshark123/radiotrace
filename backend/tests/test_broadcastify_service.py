from unittest.mock import MagicMock, patch

import pytest
import requests

from app.services.broadcastify_service import BroadcastifyError, BroadcastifyGuestClient


CONSOLE_HTML = """
<script>
var sessionKey = 'live-session-key';
var pos = 1700000000;
</script>
"""


def _json_response(payload: dict, status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    response.content = b"audio-bytes"
    response.text = CONSOLE_HTML
    return response


def test_get_clips_uses_session_and_skips_historical_on_first_poll():
    client = BroadcastifyGuestClient()
    console = _json_response({})
    primed = _json_response(
        {
            "lastPos": 1700000100,
            "calls": [{"filename": "old-call", "hash": "h", "systemId": 1}],
        }
    )
    live = _json_response(
        {
            "lastPos": 1700000200,
            "calls": [{"filename": "new-call", "hash": "n", "systemId": 1, "enc": "mp3"}],
        }
    )
    client.session.get = MagicMock(return_value=console)
    client.session.post = MagicMock(side_effect=[primed, live])

    with patch("app.services.broadcastify_service.requests.post") as naked_post:
        first = client.get_clips()
        assert first["calls"] == []
        assert client.last_current_time == 1700000100
        second = client.get_clips()

    naked_post.assert_not_called()
    assert second["calls"][0]["filename"] == "new-call"
    assert client.last_current_time == 1700000200
    assert client.session.post.call_count == 2
    assert client.session.post.call_args_list[0].kwargs["data"]["doInit"] == "1"
    assert client.session.post.call_args_list[1].kwargs["data"]["doInit"] == "0"
    assert client.session.post.call_args_list[1].kwargs["data"]["pos"] == "1700000100"


def test_get_clips_resets_session_after_request_error():
    client = BroadcastifyGuestClient()
    client.initialized = True
    client.last_current_time = 99
    client.playlist_uuid = "uuid"
    client.groups = "g"
    client.session_key = "sk"
    client.session.post = MagicMock(side_effect=requests.Timeout("slow"))

    with pytest.raises(BroadcastifyError):
        client.get_clips()

    assert client.initialized is False
