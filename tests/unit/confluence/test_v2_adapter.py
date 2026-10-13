"""Unit tests for ConfluenceV2Adapter class."""

from unittest.mock import MagicMock, Mock

import pytest
import requests
from requests.exceptions import HTTPError

from mcp_atlassian.confluence.v2_adapter import ConfluenceV2Adapter


class TestConfluenceV2Adapter:
    """Test cases for ConfluenceV2Adapter."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock session."""
        return MagicMock(spec=requests.Session)

    @pytest.fixture
    def v2_adapter(self, mock_session):
        """Create a ConfluenceV2Adapter instance."""
        return ConfluenceV2Adapter(
            session=mock_session, base_url="https://example.atlassian.net/wiki"
        )

    def test_get_page_success(self, v2_adapter, mock_session):
        """Test successful page retrieval."""
        # Mock the v2 API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123456",
            "status": "current",
            "title": "Test Page",
            "spaceId": "789",
            "version": {"number": 5},
            "body": {
                "storage": {"value": "<p>Test content</p>", "representation": "storage"}
            },
            "_links": {"webui": "/pages/viewpage.action?pageId=123456"},
        }
        mock_session.get.return_value = mock_response

        # Mock space key lookup
        space_response = Mock()
        space_response.status_code = 200
        space_response.json.return_value = {"key": "TEST"}
        mock_session.get.side_effect = [mock_response, space_response]

        # Call the method
        result = v2_adapter.get_page("123456")

        # Verify the API call
        assert mock_session.get.call_count == 2
        mock_session.get.assert_any_call(
            "https://example.atlassian.net/wiki/api/v2/pages/123456",
            params={"body-format": "storage"},
        )

        # Verify the response format
        assert result["id"] == "123456"
        assert result["type"] == "page"
        assert result["title"] == "Test Page"
        assert result["space"]["key"] == "TEST"
        assert result["space"]["id"] == "789"
        assert result["version"]["number"] == 5
        assert result["body"]["storage"]["value"] == "<p>Test content</p>"
        assert result["body"]["storage"]["representation"] == "storage"

    def test_update_page_uses_expected_version(self, v2_adapter, mock_session):
        """The guarded update must PUT expected_version + 1 without a re-fetch."""
        response = Mock()
        response.json.return_value = {"id": "123", "title": "Title"}
        mock_session.put.return_value = response
        v2_adapter.update_page("123", "Title", "<p>new</p>", expected_version=7)
        payload = mock_session.put.call_args.kwargs["json"]
        assert payload["version"]["number"] == 8
        mock_session.get.assert_not_called()

    def test_get_page_not_found(self, v2_adapter, mock_session):
        """Test page retrieval when page doesn't exist."""
        # Mock a 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Page not found"
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
        mock_session.get.return_value = mock_response

        # Call the method and expect an exception
        with pytest.raises(ValueError, match="Failed to get page '999999'"):
            v2_adapter.get_page("999999")

    def test_get_page_with_minimal_response(self, v2_adapter, mock_session):
        """Test page retrieval with minimal v2 response."""
        # Mock the v2 API response without optional fields
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123456",
            "status": "current",
            "title": "Minimal Page",
        }
        mock_session.get.return_value = mock_response

        # Call the method
        result = v2_adapter.get_page("123456")

        # Verify the response handles missing fields gracefully
        assert result["id"] == "123456"
        assert result["type"] == "page"
        assert result["title"] == "Minimal Page"
        assert result["space"]["key"] == "unknown"  # Fallback when no spaceId
        assert result["version"]["number"] == 1  # Default version

    def test_get_page_network_error(self, v2_adapter, mock_session):
        """Test page retrieval with network error."""
        # Mock a network error
        mock_session.get.side_effect = requests.RequestException("Network error")

        # Call the method and expect an exception
        with pytest.raises(ValueError, match="Failed to get page '123456'"):
            v2_adapter.get_page("123456")

    def test_get_page_with_expand_parameter(self, v2_adapter, mock_session):
        """Test that expand parameter is accepted but not used."""
        # Mock the v2 API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123456",
            "status": "current",
            "title": "Test Page",
        }
        mock_session.get.return_value = mock_response

        # Call with expand parameter
        result = v2_adapter.get_page("123456", expand="body.storage,version")

        # Verify the API call doesn't include expand in params
        mock_session.get.assert_called_once_with(
            "https://example.atlassian.net/wiki/api/v2/pages/123456",
            params={"body-format": "storage"},
        )

        # Verify we still get a result
        assert result["id"] == "123456"

    @pytest.mark.parametrize(
        "method,call_kwargs,expected_path",
        [
            (
                "get_page_views",
                {"page_id": "123"},
                "/rest/api/analytics/content/123/views",
            ),
            (
                "get_page_attachments",
                {"page_id": "123"},
                "/api/v2/pages/123/attachments",
            ),
            (
                "get_attachment_by_id",
                {"attachment_id": "att-1"},
                "/api/v2/attachments/att-1",
            ),
            (
                "delete_attachment",
                {"attachment_id": "att-1"},
                "/api/v2/attachments/att-1",
            ),
        ],
        ids=["analytics", "page_attachments", "get_attachment", "delete_attachment"],
    )
    def test_no_double_wiki_prefix(
        self, v2_adapter, mock_session, method, call_kwargs, expected_path
    ):
        """Regression: URLs must not duplicate /wiki (issue #962)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"count": 0, "results": []}
        mock_session.get.return_value = mock_response
        mock_session.delete.return_value = mock_response

        getattr(v2_adapter, method)(**call_kwargs)

        # Grab the URL from whichever HTTP method was called
        if method == "delete_attachment":
            url = mock_session.delete.call_args[0][0]
        else:
            url = mock_session.get.call_args[0][0]

        assert "/wiki/wiki/" not in url, f"Double /wiki in URL: {url}"
        assert url.endswith(expected_path), f"Expected {expected_path}, got {url}"


class TestConfluenceV2AdapterComments:
    """Tests for v2 adapter comment operations."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock session."""
        return MagicMock(spec=requests.Session)

    @pytest.fixture
    def v2_adapter(self, mock_session):
        """Create a ConfluenceV2Adapter instance."""
        return ConfluenceV2Adapter(
            session=mock_session, base_url="https://example.atlassian.net/wiki"
        )

    def test_create_footer_comment_both_params_raises(self, v2_adapter):
        """T11a: Passing both page_id and parent_comment_id raises ValueError."""
        with pytest.raises(ValueError, match="mutually exclusive"):
            v2_adapter.create_footer_comment(
                page_id="12345",
                parent_comment_id="67890",
                body="<p>Test</p>",
            )

    def test_create_footer_comment_neither_param_raises(self, v2_adapter):
        """T11b: Passing neither page_id nor parent_comment_id raises ValueError."""
        with pytest.raises(ValueError, match="Either"):
            v2_adapter.create_footer_comment(body="<p>Test</p>")

    def test_create_footer_comment_reply(self, v2_adapter, mock_session):
        """T12: Create reply with parentCommentId sends correct POST payload."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "222333444",
            "status": "current",
            "title": "Re: Comment",
            "parentCommentId": "456789123",
            "pageId": "12345",
            "body": {
                "storage": {
                    "value": "<p>Reply content</p>",
                    "representation": "storage",
                },
            },
            "version": {"number": 1},
            "_links": {},
        }
        mock_session.post.return_value = mock_response

        result = v2_adapter.create_footer_comment(
            parent_comment_id="456789123",
            body="<p>Reply content</p>",
        )

        # Verify POST was called with correct URL and payload
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert call_args[0][0] == (
            "https://example.atlassian.net/wiki/api/v2/footer-comments"
        )
        payload = call_args[1]["json"]
        assert payload["parentCommentId"] == "456789123"
        assert "pageId" not in payload

        # Verify the result is in v1-compatible format with body.view
        assert result["id"] == "222333444"
        assert result["body"]["view"]["value"] == "<p>Reply content</p>"
        assert result["extensions"]["location"] == "footer"

    def test_create_footer_comment_top_level(self, v2_adapter, mock_session):
        """Create top-level comment with pageId sends correct payload."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "333444555",
            "status": "current",
            "title": "New Comment",
            "pageId": "12345",
            "body": {
                "storage": {
                    "value": "<p>Top-level comment</p>",
                    "representation": "storage",
                },
            },
            "version": {"number": 1},
            "_links": {},
        }
        mock_session.post.return_value = mock_response

        result = v2_adapter.create_footer_comment(
            page_id="12345",
            body="<p>Top-level comment</p>",
        )

        # Verify payload
        call_args = mock_session.post.call_args
        payload = call_args[1]["json"]
        assert payload["pageId"] == "12345"
        assert "parentCommentId" not in payload
        assert result["id"] == "333444555"


class TestContentProperties:
    @pytest.fixture
    def session(self):
        return MagicMock(spec=requests.Session)

    @pytest.fixture
    def adapter(self, session):
        return ConfluenceV2Adapter(session, "https://example.atlassian.net/wiki")

    def response(self, data):
        response = Mock()
        response.json.return_value = data
        return response

    def test_lookup_pagination_filters_key_and_never_follows_remote_url(
        self, adapter, session
    ):
        session.get.side_effect = [
            self.response(
                {
                    "results": [{"key": "other", "id": "9"}],
                    "_links": {"next": "https://untrusted.example/?cursor=next"},
                }
            ),
            self.response({"results": [{"key": "width", "id": "42", "value": "max"}]}),
        ]
        assert adapter._get_property("123", "width") == {
            "key": "width",
            "id": "42",
            "value": "max",
        }
        assert session.get.call_args.args == (
            "https://example.atlassian.net/wiki/api/v2/pages/123/properties",
        )
        assert session.get.call_args.kwargs["params"] == {
            "key": "width",
            "limit": "100",
            "cursor": "next",
        }

    @pytest.mark.parametrize("value", ["max", None])
    def test_update_delete_use_id(self, adapter, session, value):
        session.get.return_value = self.response(
            {
                "results": [
                    {"key": "width", "id": "42", "version": {"number": 7}},
                ]
            }
        )
        assert adapter._set_page_property("123", "width", value) is True
        url = "https://example.atlassian.net/wiki/api/v2/pages/123/properties/42"
        if value is None:
            session.delete.assert_called_once_with(url)
        else:
            session.put.assert_called_once_with(
                url,
                json={
                    "key": "width",
                    "value": "max",
                    "version": {"number": 8},
                },
            )
        session.post.assert_not_called()

    @pytest.mark.parametrize("value", ["max", None])
    def test_missing_property_create_or_noop(self, adapter, session, value):
        session.get.return_value = self.response({"results": []})
        assert adapter._set_page_property("123", "width", value) is True
        session.put.assert_not_called()
        session.delete.assert_not_called()
        if value is None:
            session.post.assert_not_called()
        else:
            session.post.assert_called_once_with(
                "https://example.atlassian.net/wiki/api/v2/pages/123/properties",
                json={"key": "width", "value": "max"},
            )

    @pytest.mark.parametrize(
        "failure", ["http", "version", "duplicate", "pagination", "malformed"]
    )
    def test_uncertain_lookup_never_creates_or_deletes(self, adapter, session, failure):
        if failure == "http":
            session.get.side_effect = requests.ConnectionError()
        else:
            data = {"results": [{"key": "width", "id": "42"}]}
            if failure == "duplicate":
                data["results"] *= 2
            elif failure == "pagination":
                data["_links"] = {"next": "?cursor=same"}
            elif failure == "malformed":
                data = {}
            session.get.return_value = self.response(data)
        assert adapter._set_page_property("123", "width", "max") is False
        assert adapter._set_page_property("123", "width", None) is False
        session.put.assert_not_called()
        session.post.assert_not_called()
        session.delete.assert_not_called()

    def test_write_error_does_not_fall_back_to_create(self, adapter, session):
        session.get.return_value = self.response(
            {
                "results": [
                    {"key": "width", "id": "42", "version": {"number": 7}},
                ]
            }
        )
        session.put.return_value.raise_for_status.side_effect = HTTPError()
        assert adapter._set_page_property("123", "width", "max") is False
        session.post.assert_not_called()

    def test_emoji_uses_shared_safe_id_updates(self, adapter, session):
        session.get.side_effect = [
            self.response(
                {
                    "results": [
                        {
                            "key": "emoji-title-published",
                            "id": "41",
                            "version": {"number": 2},
                        }
                    ]
                }
            ),
            self.response(
                {
                    "results": [
                        {
                            "key": "emoji-title-draft",
                            "id": "42",
                            "version": {"number": 4},
                        }
                    ]
                }
            ),
        ]
        assert adapter.set_page_emoji("123", "😀") is True
        calls = session.put.call_args_list
        assert calls[0].args[0].endswith("/properties/41")
        assert calls[0].kwargs["json"]["version"] == {"number": 3}
        assert calls[1].args[0].endswith("/properties/42")
        assert calls[1].kwargs["json"]["version"] == {"number": 5}
