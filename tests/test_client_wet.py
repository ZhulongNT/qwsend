import os
import pytest

from qwsend import WebhookClient


pytestmark = pytest.mark.wet


@pytest.mark.skipif(not os.getenv("QWSEND_WEBHOOK_KEY"), reason="no webhook key configured")
def test_live_send_text():
    key = os.environ["QWSEND_WEBHOOK_KEY"]
    client = WebhookClient(key)
    try:
        data = client.send_text("qwsend wet test")
        assert data["errmsg"] == "ok"
    finally:
        client.close()
