import os
import tempfile
import pytest
from mcp_atlassian.confluence.attachments import AttachmentsMixin
from mcp_atlassian.confluence.client import ConfluenceClient

class DummyConfluence:
    def __init__(self, attachments_data=None):
        self.attachments_data = attachments_data or []
        self._session = self
    def get_page_by_id(self, page_id, expand=None):
        return {
            "children": {
                "attachment": {
                    "results": self.attachments_data
                }
            }
        }
    def get(self, url, stream=True):
        class DummyResponse:
            def __init__(self):
                self.status_code = 200
            def raise_for_status(self):
                pass
            def iter_content(self, chunk_size=8192):
                yield b"dummydata"
        return DummyResponse()

class DummyConfig:
    url = "https://example.atlassian.net/wiki"

@pytest.fixture
def dummy_attachment():
    return {
        "id": "123",
        "type": "attachment",
        "status": "current",
        "title": "test.png",
        "extensions": {"mediaType": "image/png", "fileSize": 42},
        "_links": {"download": "/download/attachments/1/test.png"}
    }

def test_download_page_attachments(tmp_path, dummy_attachment):
    import logging
    logging.getLogger("mcp-atlassian").setLevel(logging.DEBUG)

    mixin = AttachmentsMixin()
    mixin.confluence = DummyConfluence([dummy_attachment])
    mixin.config = DummyConfig()
    target_dir = tmp_path / "attachments"
    result = mixin.download_page_attachments(page_id="1", target_dir=str(target_dir))
    assert result["success"] is True
    assert result["total"] == 1
    assert result["downloaded"][0]["filename"] == "test.png"
    assert os.path.exists(os.path.join(target_dir, "test.png"))
