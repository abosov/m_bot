import os

import pytest

def test_token_format():
    token = os.getenv("MASTER_BOT_TOKEN")
    if not token:
        pytest.skip("MASTER_BOT_TOKEN not set; skipping token format smoke test.")
    assert ":" in token
