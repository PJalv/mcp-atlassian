"""Unit tests for the PagesMixin class."""

from unittest.mock import MagicMock, patch

import pytest

from mcp_atlassian.confluence.pages import PagesMixin
from mcp_atlassian.confluence.utils import extract_emoji_from_property
from mcp_atlassian.models.confluence import ConfluencePage


class TestPagesMixin:
    """Tests for the PagesMixin class."""

    @pytest.fixture
    def pages_mixin(self, confluence_client):
        """Create a PagesMixin instance for testing."""
        # PagesMixin inherits from ConfluenceClient, so we need to create it properly
        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceClient.__init__"
        ) as mock_init:
            mock_init.return_value = None
            mixin = PagesMixin()
            # Copy the necessary attributes from our mocked client
            mixin.confluence = confluence_client.confluence
            mixin.config = confluence_client.config
            mixin.preprocessor = confluence_client.preprocessor
            return mixin

    def test_get_page_content(self, pages_mixin):
        """Test getting page content by ID."""
        # Arrange
        page_id = "987654321"
        pages_mixin.config.url = "https://example.atlassian.net/wiki"

        # Act
        result = pages_mixin.get_page_content(page_id, convert_to_markdown=True)

        # Assert
        pages_mixin.confluence.get_page_by_id.assert_called_once_with(
            page_id=page_id, expand="body.storage,version,space,children.attachment"
        )

        # Verify result structure
        assert isinstance(result, ConfluencePage)
        assert result.id == "987654321"
        assert result.title == "Example Meeting Notes"

        # Test space information
        assert result.space is not None
        assert result.space.key == "PROJ"

        # Use direct attributes instead of backward compatibility
        assert result.content == "Processed Markdown"
        assert result.id == page_id
        assert result.title == "Example Meeting Notes"
        assert result.space.key == "PROJ"
        assert result.url is not None

        # Test version information
        assert result.version is not None
        assert result.version.number == 1

        # Test attachments
        assert result.attachments is not None
        assert len(result.attachments) == 2
        assert result.attachments[0].id is not None
        assert result.attachments[1].id is not None

    def test_get_page_ancestors(self, pages_mixin):
        """Test getting page ancestors (parent pages)."""
        # Arrange
        page_id = "987654321"
        pages_mixin.config.url = "https://example.atlassian.net/wiki"

        # Mock the ancestors API response
        ancestors_data = [
            {
                "id": "123456789",
                "title": "Parent Page",
                "type": "page",
                "status": "current",
                "space": {"key": "PROJ", "name": "Project Space"},
            },
            {
                "id": "111222333",
                "title": "Grandparent Page",
                "type": "page",
                "status": "current",
                "space": {"key": "PROJ", "name": "Project Space"},
            },
        ]
        pages_mixin.confluence.get_page_ancestors.return_value = ancestors_data

        # Act
        result = pages_mixin.get_page_ancestors(page_id)

        # Assert
        pages_mixin.confluence.get_page_ancestors.assert_called_once_with(page_id)

        # Verify result structure
        assert isinstance(result, list)
        assert len(result) == 2

        # Test first ancestor (parent)
        assert isinstance(result[0], ConfluencePage)
        assert result[0].id == "123456789"
        assert result[0].title == "Parent Page"
        assert result[0].space.key == "PROJ"

        # Test second ancestor (grandparent)
        assert isinstance(result[1], ConfluencePage)
        assert result[1].id == "111222333"
        assert result[1].title == "Grandparent Page"

    def test_get_page_ancestors_empty(self, pages_mixin):
        """Test getting ancestors when there are none (top-level page)."""
        # Arrange
        page_id = "987654321"
        pages_mixin.confluence.get_page_ancestors.return_value = []

        # Act
        result = pages_mixin.get_page_ancestors(page_id)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_page_ancestors_error(self, pages_mixin):
        """Test error handling when getting ancestors."""
        # Arrange
        page_id = "987654321"
        pages_mixin.confluence.get_page_ancestors.side_effect = Exception("API Error")

        # Act
        result = pages_mixin.get_page_ancestors(page_id)

        # Assert - should return empty list on error, not raise exception
        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_page_content_html(self, pages_mixin):
        """Test getting page content in HTML format."""
        pages_mixin.config.url = "https://example.atlassian.net/wiki"

        # Mock the preprocessor to return HTML
        pages_mixin.preprocessor.process_html_content.return_value = (
            "<p>Processed HTML</p>",
            "Processed Markdown",
        )

        # Act
        result = pages_mixin.get_page_content("987654321", convert_to_markdown=False)

        # Assert HTML processing was used
        assert result.content == "<p>Processed HTML</p>"

    def test_get_page_by_title_success(self, pages_mixin):
        """Test getting a page by title when it exists."""
        # Setup
        space_key = "DEMO"
        title = "Example Page"

        # Mock getting the page by title
        pages_mixin.confluence.get_page_by_title.return_value = {
            "id": "987654321",
            "title": title,
            "space": {"key": space_key},
            "body": {"storage": {"value": "<p>Example content</p>"}},
            "version": {"number": 1},
        }

        # Mock the HTML processing
        pages_mixin.preprocessor.process_html_content.return_value = (
            "<p>Processed HTML</p>",
            "Processed Markdown",
        )

        # Call the method
        result = pages_mixin.get_page_by_title(space_key, title)

        # Verify API calls
        pages_mixin.confluence.get_page_by_title.assert_called_once_with(
            space=space_key, title=title, expand="body.storage,version"
        )

        # Verify result
        assert result.id == "987654321"
        assert result.title == title
        assert result.content == "Processed Markdown"

    def test_get_page_by_title_space_not_found(self, pages_mixin):
        """Test getting a page when the space doesn't exist."""
        # Arrange - API returns None when space doesn't exist
        pages_mixin.confluence.get_page_by_title.return_value = None

        # Act
        result = pages_mixin.get_page_by_title("NONEXISTENT", "Page Title")

        # Assert
        assert result is None
        pages_mixin.confluence.get_page_by_title.assert_called_once_with(
            space="NONEXISTENT", title="Page Title", expand="body.storage,version"
        )

    def test_get_page_by_title_page_not_found(self, pages_mixin):
        """Test getting a page that doesn't exist."""
        # Arrange
        pages_mixin.confluence.get_page_by_title.return_value = None

        # Act
        result = pages_mixin.get_page_by_title("PROJ", "Nonexistent Page")

        # Assert
        assert result is None
        pages_mixin.confluence.get_page_by_title.assert_called_once_with(
            space="PROJ", title="Nonexistent Page", expand="body.storage,version"
        )

    def test_get_page_by_title_error_handling(self, pages_mixin):
        """Test error handling in get_page_by_title."""
        # Arrange
        pages_mixin.confluence.get_page_by_title.side_effect = KeyError("Missing key")

        # Act
        result = pages_mixin.get_page_by_title("PROJ", "Page Title")

        # Assert
        assert result is None

    def test_get_space_pages(self, pages_mixin):
        """Test getting all pages from a space."""
        # Arrange
        space_key = "PROJ"
        pages_mixin.config.url = "https://example.atlassian.net/wiki"

        # Act
        results = pages_mixin.get_space_pages(
            space_key, start=0, limit=10, convert_to_markdown=True
        )

        # Assert
        pages_mixin.confluence.get_all_pages_from_space.assert_called_once_with(
            space=space_key, start=0, limit=10, expand="body.storage"
        )

        # Verify results
        assert len(results) == 2  # Mock has 2 pages

        # Verify each result is a ConfluencePage
        for result in results:
            assert isinstance(result, ConfluencePage)
            assert result.content == "Processed Markdown"
            assert result.space is not None
            assert result.space.key == "PROJ"

        # Verify individual pages
        assert results[0].id == "123456789"  # First page ID from mock
        assert results[0].title == "Sample Research Paper Title"

        # Verify the second page
        assert results[1].id == "987654321"  # Second page ID from mock
        assert results[1].title == "Example Meeting Notes"

    def test_create_page_success(self, pages_mixin):
        """Test creating a new page."""
        # Arrange
        space_key = "PROJ"
        title = "New Test Page"
        body = "<p>Test content</p>"
        parent_id = "987654321"

        # Mock get_page_content to return a ConfluencePage
        with patch.object(
            pages_mixin,
            "get_page_content",
            return_value=ConfluencePage(
                id="123456789",
                title=title,
                content="Page content",
                space={"key": space_key, "name": "Project"},
            ),
        ):
            # Act - specify is_markdown=False since we're directly providing storage format
            result = pages_mixin.create_page(
                space_key, title, body, parent_id, is_markdown=False
            )

            # Assert
            pages_mixin.confluence.create_page.assert_called_once_with(
                space=space_key,
                title=title,
                body=body,
                parent_id=parent_id,
                representation="storage",
            )

            # Verify result is a ConfluencePage
            assert isinstance(result, ConfluencePage)
            assert result.id == "123456789"
            assert result.title == title
            assert result.content == "Page content"

    def test_create_page_error(self, pages_mixin):
        """Test error handling when creating a page."""
        # Arrange
        pages_mixin.confluence.create_page.side_effect = Exception("API Error")

        # Act/Assert
        with pytest.raises(Exception, match="API Error"):
            pages_mixin.create_page("PROJ", "Test Page", "<p>Content</p>")

    def test_create_page_with_wiki_format(self, pages_mixin):
        """Test creating a new page with wiki markup format."""
        # Arrange
        space_key = "PROJ"
        title = "Wiki Format Test Page"
        wiki_body = "h1. This is a heading\n\n* Item 1\n* Item 2"

        # Mock get_page_content to return a ConfluencePage
        with patch.object(
            pages_mixin,
            "get_page_content",
            return_value=ConfluencePage(
                id="wiki123",
                title=title,
                content="Wiki page content",
                space={"key": space_key, "name": "Project"},
            ),
        ):
            # Act - use wiki format
            result = pages_mixin.create_page(
                space_key,
                title,
                wiki_body,
                is_markdown=False,
                content_representation="wiki",
            )

            # Assert
            pages_mixin.confluence.create_page.assert_called_once_with(
                space=space_key,
                title=title,
                body=wiki_body,  # Should be passed as-is
                parent_id=None,
                representation="wiki",  # Should use wiki representation
            )

            # Verify no markdown conversion happened
            pages_mixin.preprocessor.markdown_to_confluence_storage.assert_not_called()

            # Verify result is a ConfluencePage
            assert isinstance(result, ConfluencePage)
            assert result.id == "wiki123"

    def test_update_page_success(self, pages_mixin):
        """Test updating an existing page."""
        # Arrange
        page_id = "987654321"
        title = "Updated Page"
        body = "<p>Updated content</p>"
        is_minor_edit = True
        version_comment = "Updated test"

        # Mock get_page_content to return a document
        mock_document = ConfluencePage(
            id=page_id,
            title=title,
            content="Updated content",
            space={"key": "PROJ", "name": "Project"},
            version={"number": 1},  # Add version information
        )
        pages_mixin.confluence.get_page_by_id.return_value = {"version": {"number": 1}}
        with patch.object(pages_mixin, "get_page_content", return_value=mock_document):
            # Act - specify is_markdown=False since we're directly providing storage format
            result = pages_mixin.update_page(
                page_id,
                title,
                body,
                is_minor_edit=is_minor_edit,
                version_comment=version_comment,
                is_markdown=False,
            )

            # Assert
            # Verify update_page was called with the correct arguments
            # We now include type='page' and always_update=True parameters
            pages_mixin.confluence.put.assert_called_once_with(
                f"rest/api/content/{page_id}",
                data={
                    "id": page_id,
                    "type": "page",
                    "title": title,
                    "body": {"storage": {"value": body, "representation": "storage"}},
                    "version": {
                        "number": 2,
                        "minorEdit": True,
                        "message": version_comment,
                    },
                },
                params={"status": "current"},
            )

    def test_update_preserves_title_and_width(self, pages_mixin):
        """An omitted title and width must not be reset by the v1 PUT."""
        pages_mixin.confluence.get_page_by_id.return_value = {
            "title": "Original title",
            "version": {"number": 4},
            "body": {"storage": {"value": "<p>old</p>"}},
        }
        with patch.object(pages_mixin, "get_page_content"):
            pages_mixin.update_page("123", None, "<p>new</p>", is_markdown=False)
        payload = pages_mixin.confluence.put.call_args.kwargs["data"]
        assert payload["title"] == "Original title"
        assert payload["version"]["number"] == 5
        assert "metadata" not in payload

    def test_explicit_max_width(self, pages_mixin):
        pages_mixin.confluence.get_page_by_id.return_value = {"version": {"number": 1}}
        with (
            patch.object(pages_mixin, "get_page_content"),
            patch.object(pages_mixin, "_set_page_width") as set_width,
        ):
            pages_mixin.update_page(
                "123",
                "Title",
                "<p>body</p>",
                is_markdown=False,
                page_width="max",
            )
        set_width.assert_called_once_with("123", "max")

    def test_exact_edit_requires_matching_version(self, pages_mixin):
        """A stale edit does not send a write request."""
        pages_mixin.confluence.get_page_by_id.return_value = {
            "title": "Original",
            "version": {"number": 6},
            "body": {"storage": {"value": "<p>old</p>"}},
        }
        with pytest.raises(Exception, match="version mismatch"):
            pages_mixin.update_page(
                "123",
                None,
                None,
                old_text="old",
                new_text="new",
                expected_version=5,
            )
        pages_mixin.confluence.put.assert_not_called()

    def test_exact_edit_updates_storage_once(self, pages_mixin):
        """Small edits do not reconvert storage through Markdown."""
        pages_mixin.confluence.get_page_by_id.return_value = {
            "title": "Original",
            "version": {"number": 6},
            "body": {"storage": {"value": "<p>old</p>"}},
        }
        with patch.object(pages_mixin, "get_page_content"):
            pages_mixin.update_page(
                "123",
                None,
                None,
                old_text="old",
                new_text="new",
                expected_version=6,
            )
        payload = pages_mixin.confluence.put.call_args.kwargs["data"]
        assert payload["body"]["storage"]["value"] == "<p>new</p>"
        assert payload["version"]["number"] == 7
        assert payload["title"] == "Original"
        assert "metadata" not in payload
        pages_mixin.preprocessor.markdown_to_confluence_storage.assert_not_called()

    def test_exact_edit_rejects_missing_version(self, pages_mixin):
        with pytest.raises(Exception, match="requires old_text"):
            pages_mixin.update_page("123", None, None, old_text="old", new_text="new")
        pages_mixin.confluence.put.assert_not_called()

    def test_exact_edit_rejects_ambiguous_match(self, pages_mixin):
        pages_mixin.confluence.get_page_by_id.return_value = {
            "title": "Original",
            "version": {"number": 6},
            "body": {"storage": {"value": "old old"}},
        }
        with pytest.raises(Exception, match="occur once"):
            pages_mixin.update_page(
                "123",
                None,
                None,
                old_text="old",
                new_text="new",
                expected_version=6,
            )
        pages_mixin.confluence.put.assert_not_called()

    def test_update_page_error(self, pages_mixin):
        """Test error handling when updating a page."""
        # Arrange
        pages_mixin.confluence.get_page_by_id.return_value = {"version": {"number": 1}}
        pages_mixin.confluence.put.side_effect = Exception("API Error")

        # Act/Assert
        with pytest.raises(Exception, match="Failed to update page"):
            pages_mixin.update_page("987654321", "Test Page", "<p>Content</p>")

    def test_update_page_with_wiki_format(self, pages_mixin):
        """Test updating a page with wiki markup format."""
        # Arrange
        page_id = "wiki987"
        title = "Updated Wiki Page"
        wiki_body = "h1. Updated Heading\n\n||Header 1||Header 2||\n|Cell 1|Cell 2|"
        version_comment = "Wiki format update"

        # Mock get_page_content to return a document
        mock_document = ConfluencePage(
            id=page_id,
            title=title,
            content="Updated wiki content",
            space={"key": "PROJ", "name": "Project"},
            version={"number": 2},
        )
        pages_mixin.confluence.get_page_by_id.return_value = {"version": {"number": 1}}
        with patch.object(pages_mixin, "get_page_content", return_value=mock_document):
            # Act - use wiki format
            result = pages_mixin.update_page(
                page_id,
                title,
                wiki_body,
                version_comment=version_comment,
                is_markdown=False,
                content_representation="wiki",
            )

            # Assert
            payload = pages_mixin.confluence.put.call_args.kwargs["data"]
            assert payload["body"]["wiki"]["value"] == wiki_body
            assert payload["version"] == {
                "number": 2,
                "minorEdit": False,
                "message": version_comment,
            }
            assert "metadata" not in payload

            # Verify no markdown conversion happened
            pages_mixin.preprocessor.markdown_to_confluence_storage.assert_not_called()

            # Verify result is a ConfluencePage
            assert isinstance(result, ConfluencePage)
            assert result.id == page_id

    def test_delete_page_success(self, pages_mixin):
        """Test successfully deleting a page."""
        # Arrange
        page_id = "987654321"
        pages_mixin.confluence.remove_page.return_value = True

        # Act
        result = pages_mixin.delete_page(page_id)

        # Assert
        pages_mixin.confluence.remove_page.assert_called_once_with(page_id=page_id)
        assert result is True

    def test_delete_page_error(self, pages_mixin):
        """Test error handling when deleting a page."""
        # Arrange
        page_id = "987654321"
        pages_mixin.confluence.remove_page.side_effect = Exception("API Error")

        # Act/Assert
        with pytest.raises(Exception, match="Failed to delete page"):
            pages_mixin.delete_page(page_id)

    def test_get_page_children_success(self, pages_mixin):
        """Test successfully getting child pages and folders."""
        # Arrange
        parent_id = "123456"
        pages_mixin.config.url = "https://example.atlassian.net/wiki"

        # Mock the response from get_page_child_by_type for pages
        child_pages_data = {
            "results": [
                {
                    "id": "789012",
                    "title": "Child Page 1",
                    "type": "page",
                    "space": {"key": "DEMO"},
                    "version": {"number": 1},
                },
                {
                    "id": "345678",
                    "title": "Child Page 2",
                    "type": "page",
                    "space": {"key": "DEMO"},
                    "version": {"number": 3},
                },
            ]
        }
        # Mock the response for folders
        child_folders_data = {
            "results": [
                {
                    "id": "111222",
                    "title": "Child Folder 1",
                    "type": "folder",
                    "space": {"key": "DEMO"},
                    "version": {"number": 1},
                },
            ]
        }

        # Mock to return pages first, then folders
        pages_mixin.confluence.get_page_child_by_type.side_effect = [
            child_pages_data,
            child_folders_data,
        ]

        # Act
        results = pages_mixin.get_page_children(
            page_id=parent_id, limit=10, expand="version"
        )

        # Assert - should be called twice (once for pages, once for folders)
        assert pages_mixin.confluence.get_page_child_by_type.call_count == 2

        # Verify the results include both pages and folders
        assert len(results) == 3
        assert isinstance(results[0], ConfluencePage)
        assert results[0].id == "789012"
        assert results[0].title == "Child Page 1"
        assert results[1].id == "345678"
        assert results[1].title == "Child Page 2"
        assert results[2].id == "111222"
        assert results[2].title == "Child Folder 1"

    def test_get_page_children_without_folders(self, pages_mixin):
        """Test getting child pages only (without folders)."""
        # Arrange
        parent_id = "123456"
        pages_mixin.config.url = "https://example.atlassian.net/wiki"

        # Mock the response from get_page_child_by_type
        child_pages_data = {
            "results": [
                {
                    "id": "789012",
                    "title": "Child Page 1",
                    "space": {"key": "DEMO"},
                    "version": {"number": 1},
                },
            ]
        }
        pages_mixin.confluence.get_page_child_by_type.return_value = child_pages_data

        # Act
        results = pages_mixin.get_page_children(
            page_id=parent_id, limit=10, expand="version", include_folders=False
        )

        # Assert - should only be called once (for pages only)
        pages_mixin.confluence.get_page_child_by_type.assert_called_once_with(
            page_id=parent_id, type="page", start=0, limit=10, expand="version"
        )

        # Verify the results
        assert len(results) == 1
        assert results[0].id == "789012"

    def test_get_page_children_with_content(self, pages_mixin):
        """Test getting child pages with content."""
        # Arrange
        parent_id = "123456"
        pages_mixin.config.url = "https://example.atlassian.net/wiki"

        # Mock the response with body content
        child_pages_data = {
            "results": [
                {
                    "id": "789012",
                    "title": "Child Page With Content",
                    "space": {"key": "DEMO"},
                    "version": {"number": 1},
                    "body": {"storage": {"value": "<p>This is some content</p>"}},
                }
            ]
        }
        # Mock empty folders response
        child_folders_data = {"results": []}

        pages_mixin.confluence.get_page_child_by_type.side_effect = [
            child_pages_data,
            child_folders_data,
        ]

        # Mock the preprocessor
        pages_mixin.preprocessor.process_html_content.return_value = (
            "<p>Processed HTML</p>",
            "Processed Markdown",
        )

        # Act
        results = pages_mixin.get_page_children(
            page_id=parent_id, expand="body.storage", convert_to_markdown=True
        )

        # Assert
        assert len(results) == 1
        assert results[0].content == "Processed Markdown"
        pages_mixin.preprocessor.process_html_content.assert_called_once_with(
            "<p>This is some content</p>",
            space_key="DEMO",
            confluence_client=pages_mixin.confluence,
            content_id="789012",
        )

    def test_get_page_children_empty(self, pages_mixin):
        """Test getting child pages when there are none."""
        # Arrange
        parent_id = "123456"

        # Mock empty response for both pages and folders
        pages_mixin.confluence.get_page_child_by_type.return_value = {"results": []}

        # Act
        results = pages_mixin.get_page_children(page_id=parent_id)

        # Assert
        assert len(results) == 0

    def test_get_page_children_error(self, pages_mixin):
        """Test error handling when getting child pages."""
        # Arrange
        parent_id = "123456"

        # Mock an exception on the first call (pages)
        pages_mixin.confluence.get_page_child_by_type.side_effect = Exception(
            "API Error"
        )

        # Act
        results = pages_mixin.get_page_children(page_id=parent_id)

        # Assert - should return empty list on error, not raise exception
        assert len(results) == 0

    def test_get_page_children_folder_error_graceful(self, pages_mixin):
        """Test that folder fetch errors don't fail the whole operation."""
        # Arrange
        parent_id = "123456"
        pages_mixin.config.url = "https://example.atlassian.net/wiki"

        # Mock pages success, folders failure
        child_pages_data = {
            "results": [
                {
                    "id": "789012",
                    "title": "Child Page 1",
                    "space": {"key": "DEMO"},
                    "version": {"number": 1},
                },
            ]
        }
        pages_mixin.confluence.get_page_child_by_type.side_effect = [
            child_pages_data,
            Exception("Folder API not supported"),
        ]

        # Act
        results = pages_mixin.get_page_children(page_id=parent_id)

        # Assert - should still return pages even if folder fetch fails
        assert len(results) == 1
        assert results[0].id == "789012"

    def test_get_page_success(self, pages_mixin):
        """Test successful page retrieval."""
        # Setup
        page_id = "12345"
        page_data = {
            "id": page_id,
            "title": "Test Page",
            "body": {"storage": {"value": "<p>Test content</p>"}},
            "version": {"number": 1},
            "space": {"key": "TEST", "name": "Test Space"},
        }
        pages_mixin.confluence.get_page_by_id.return_value = page_data

        # Mock the preprocessor
        pages_mixin.preprocessor.process_html_content.return_value = (
            "<p>Processed HTML</p>",
            "Processed content",
        )

        # Call the method
        result = pages_mixin.get_page_content(page_id)

        # Verify the API call
        pages_mixin.confluence.get_page_by_id.assert_called_once_with(
            page_id=page_id, expand="body.storage,version,space,children.attachment"
        )

        # Verify the result
        assert result.id == page_id
        assert result.title == "Test Page"
        assert result.content == "Processed content"
        assert (
            result.version.number == 1
        )  # Compare version number instead of the whole object
        assert result.space.key == "TEST"
        assert result.space.name == "Test Space"

    def test_create_page_with_markdown(self, pages_mixin):
        """Test creating a new page with markdown content."""
        # Arrange
        space_key = "PROJ"
        title = "New Test Page"
        markdown_body = "# Test Heading\n\nThis is *markdown* content."
        parent_id = "987654321"
        storage_format = (
            "<h1>Test Heading</h1><p>This is <em>markdown</em> content.</p>"
        )

        # Mock the markdown conversion
        pages_mixin.preprocessor.markdown_to_confluence_storage.return_value = (
            storage_format
        )

        # Mock get_page_content to return a ConfluencePage
        with patch.object(
            pages_mixin,
            "get_page_content",
            return_value=ConfluencePage(
                id="123456789",
                title=title,
                content="Converted content",
                space={"key": space_key, "name": "Project"},
            ),
        ):
            # Act
            result = pages_mixin.create_page(
                space_key=space_key,
                title=title,
                body=markdown_body,
                parent_id=parent_id,
                is_markdown=True,
            )

            # Assert
            # Verify markdown was converted
            pages_mixin.preprocessor.markdown_to_confluence_storage.assert_called_once_with(
                markdown_body, enable_heading_anchors=False
            )

            # Verify create_page was called with the converted content
            pages_mixin.confluence.create_page.assert_called_once_with(
                space=space_key,
                title=title,
                body=storage_format,
                parent_id=parent_id,
                representation="storage",
            )

            # Verify result
            assert isinstance(result, ConfluencePage)
            assert result.id == "123456789"
            assert result.title == title

    def test_create_page_with_storage_format(self, pages_mixin):
        """Test creating a page with pre-converted storage format content."""
        # Arrange
        space_key = "PROJ"
        title = "New Test Page"
        storage_body = "<p>Already in storage format</p>"

        # Mock get_page_content
        with patch.object(
            pages_mixin,
            "get_page_content",
            return_value=ConfluencePage(id="123456789", title=title),
        ):
            # Act
            result = pages_mixin.create_page(
                space_key=space_key, title=title, body=storage_body, is_markdown=False
            )

            # Assert
            # Verify conversion was not called
            pages_mixin.preprocessor.markdown_to_confluence_storage.assert_not_called()

            # Verify create_page was called with the original content
            pages_mixin.confluence.create_page.assert_called_once_with(
                space=space_key,
                title=title,
                body=storage_body,
                parent_id=None,
                representation="storage",
            )

    def test_update_page_with_markdown(self, pages_mixin):
        """Test updating a page with markdown content."""
        # Arrange
        page_id = "987654321"
        title = "Updated Page"
        markdown_body = "# Updated Content\n\nThis is *updated* content."
        storage_format = (
            "<h1>Updated Content</h1><p>This is <em>updated</em> content.</p>"
        )

        # Mock the markdown conversion
        pages_mixin.preprocessor.markdown_to_confluence_storage.return_value = (
            storage_format
        )

        # Mock get_page_content
        pages_mixin.confluence.get_page_by_id.return_value = {"version": {"number": 1}}
        with patch.object(
            pages_mixin,
            "get_page_content",
            return_value=ConfluencePage(
                id=page_id,
                title=title,
                content="Updated content",
                space={"key": "PROJ", "name": "Project"},
            ),
        ):
            # Act
            result = pages_mixin.update_page(
                page_id=page_id,
                title=title,
                body=markdown_body,
                is_minor_edit=True,
                version_comment="Updated test",
                is_markdown=True,
            )

            # Assert
            # Verify markdown was converted
            pages_mixin.preprocessor.markdown_to_confluence_storage.assert_called_once_with(
                markdown_body, enable_heading_anchors=False
            )

            # Verify update_page was called with the converted content
            payload = pages_mixin.confluence.put.call_args.kwargs["data"]
            assert payload["body"]["storage"]["value"] == storage_format
            assert payload["version"] == {
                "number": 2,
                "minorEdit": True,
                "message": "Updated test",
            }

    def test_update_page_with_parent_id(self, pages_mixin):
        """Test updating a page and changing its parent."""
        # Arrange
        page_id = "987654321"
        title = "Updated Page"
        body = "<p>Updated content</p>"
        parent_id = "123456789"
        is_minor_edit = False
        version_comment = "Parent changed"

        # Mock get_page_content to return a document
        mock_document = ConfluencePage(
            id=page_id,
            title=title,
            content="Updated content",
            space={"key": "PROJ", "name": "Project"},
            version={"number": 2},
        )
        pages_mixin.confluence.get_page_by_id.return_value = {"version": {"number": 1}}
        with patch.object(pages_mixin, "get_page_content", return_value=mock_document):
            # Act
            result = pages_mixin.update_page(
                page_id=page_id,
                title=title,
                body=body,
                is_minor_edit=is_minor_edit,
                version_comment=version_comment,
                is_markdown=False,
                parent_id=parent_id,
            )

            # Assert
            payload = pages_mixin.confluence.put.call_args.kwargs["data"]
            assert payload["ancestors"] == [{"type": "page", "id": parent_id}]
            assert payload["version"] == {
                "number": 2,
                "minorEdit": False,
                "message": version_comment,
            }
            assert "metadata" not in payload
            assert result.id == page_id
            assert result.title == title
            assert result.version.number == 2

    def test_non_oauth_still_uses_v1_api(self, pages_mixin):
        """Test that non-OAuth authentication still uses v1 API."""
        # This test ensures backward compatibility for API token/basic auth
        # Arrange
        space_key = "PROJ"
        title = "New V1 Test Page"
        body = "<p>Test content for V1</p>"

        # Mock get_page_content to return a ConfluencePage
        with patch.object(
            pages_mixin,
            "get_page_content",
            return_value=ConfluencePage(
                id="v1_123456789",
                title=title,
                content="V1 page content",
                space={"key": space_key, "name": "Project"},
            ),
        ):
            # Act
            result = pages_mixin.create_page(space_key, title, body, is_markdown=False)

            # Assert that v1 API was used
            pages_mixin.confluence.create_page.assert_called_once_with(
                space=space_key,
                title=title,
                body=body,
                parent_id=None,
                representation="storage",
            )

            # Verify result is a ConfluencePage
            assert isinstance(result, ConfluencePage)
            assert result.id == "v1_123456789"
            assert result.title == title

    @pytest.mark.parametrize(
        "body",
        [None, {"storage": None}, {"storage": {"value": None}}],
        ids=["body=None", "storage=None", "value=None"],
    )
    def test_get_page_content_missing_body_regression(self, pages_mixin, body):
        """Regression test for #760: handle missing body.storage.value."""
        pages_mixin.confluence.get_page_by_id.return_value = {
            "id": "123456",
            "title": "Test",
            "space": {"key": "TEST"},
            "body": body,
            "version": {"number": 1},
        }
        pages_mixin.config.url = "https://example.atlassian.net/wiki"
        result = pages_mixin.get_page_content("123456")
        assert isinstance(result, ConfluencePage)
        assert result.id == "123456"

    def test_get_page_by_title_missing_body_regression(self, pages_mixin):
        """Regression test for #760: get_page_by_title handles None body."""
        pages_mixin.confluence.get_page_by_title.return_value = {
            "id": "123456",
            "title": "Test",
            "space": {"key": "TEST"},
            "body": None,
            "version": {"number": 1},
        }
        pages_mixin.config.url = "https://example.atlassian.net/wiki"
        result = pages_mixin.get_page_by_title("TEST", "Test")
        assert isinstance(result, ConfluencePage)

    def test_get_space_pages_missing_body_regression(self, pages_mixin):
        """Regression test for #760: get_space_pages handles None body."""
        pages_mixin.confluence.get_all_pages_from_space.return_value = [
            {
                "id": "1",
                "title": "A",
                "space": {"key": "T"},
                "body": None,
                "version": {"number": 1},
            },
            {
                "id": "2",
                "title": "B",
                "space": {"key": "T"},
                "body": {"storage": None},
                "version": {"number": 1},
            },
        ]
        pages_mixin.config.url = "https://example.atlassian.net/wiki"
        results = pages_mixin.get_space_pages("T")
        assert len(results) == 2

    def test_get_page_history_success_v1(self, pages_mixin):
        """Test successfully retrieving a historical page version using v1 API with markdown."""
        # Arrange
        page_id = "987654321"
        version = 2
        pages_mixin.config.url = "https://example.atlassian.net/wiki"

        # Mock the v1 API response for historical page
        historical_page_data = {
            "id": page_id,
            "title": "Historical Meeting Notes",
            "space": {"key": "PROJ", "name": "Project Space"},
            "version": {"number": version},
            "body": {
                "storage": {
                    "value": "<h2>Historical Content</h2><p>This is historical content</p>"
                }
            },
            "children": {"attachment": {"results": []}},
        }
        pages_mixin.confluence.get_page_by_id.return_value = historical_page_data

        # Mock the preprocessor
        pages_mixin.preprocessor.process_html_content.return_value = (
            "<h2>Historical Content</h2><p>This is historical content</p>",
            "## Historical Content\n\nThis is historical content",
        )

        # Mock emoji to return None
        pages_mixin.confluence.get_page_properties.return_value = {"results": []}

        # Act
        result = pages_mixin.get_page_history(
            page_id, version, convert_to_markdown=True
        )

        # Assert - verify v1 API was called with correct parameters
        pages_mixin.confluence.get_page_by_id.assert_called_once_with(
            page_id=page_id,
            status="historical",
            version=version,
            expand="body.storage,version,space,children.attachment",
        )

        # Verify result is a ConfluencePage
        assert isinstance(result, ConfluencePage)
        assert result.id == page_id
        assert result.title == "Historical Meeting Notes"
        assert result.version.number == version
        assert result.content == "## Historical Content\n\nThis is historical content"
        assert result.space.key == "PROJ"

    def test_get_page_history_html_v1(self, pages_mixin):
        """Test retrieving historical version with HTML format (convert_to_markdown=False)."""
        # Arrange
        page_id = "987654321"
        version = 3
        pages_mixin.config.url = "https://example.atlassian.net/wiki"

        historical_page_data = {
            "id": page_id,
            "title": "HTML Historical Page",
            "space": {"key": "PROJ"},
            "version": {"number": version},
            "body": {"storage": {"value": "<p>HTML content</p>"}},
            "children": {"attachment": {"results": []}},
        }
        pages_mixin.confluence.get_page_by_id.return_value = historical_page_data

        pages_mixin.preprocessor.process_html_content.return_value = (
            "<p>Processed HTML content</p>",
            "Processed markdown",
        )
        pages_mixin.confluence.get_page_properties.return_value = {"results": []}

        # Act
        result = pages_mixin.get_page_history(
            page_id, version, convert_to_markdown=False
        )

        # Assert - HTML should be used instead of markdown
        assert isinstance(result, ConfluencePage)
        assert result.content == "<p>Processed HTML content</p>"
        assert result.version.number == version

    def test_get_page_history_with_attachments_v1(self, pages_mixin):
        """Test that attachments are included in historical version."""
        # Arrange
        page_id = "987654321"
        version = 2
        pages_mixin.config.url = "https://example.atlassian.net/wiki"

        historical_page_data = {
            "id": page_id,
            "title": "Page with Attachments",
            "space": {"key": "PROJ"},
            "version": {"number": version},
            "body": {"storage": {"value": "<p>Content</p>"}},
            "children": {
                "attachment": {
                    "results": [
                        {
                            "id": "att123",
                            "title": "document.pdf",
                            "extensions": {"mediaType": "application/pdf"},
                        }
                    ]
                }
            },
        }
        pages_mixin.confluence.get_page_by_id.return_value = historical_page_data

        pages_mixin.preprocessor.process_html_content.return_value = (
            "<p>Content</p>",
            "Content",
        )
        pages_mixin.confluence.get_page_properties.return_value = {"results": []}

        # Act
        result = pages_mixin.get_page_history(page_id, version)

        # Assert
        assert isinstance(result, ConfluencePage)
        assert result.attachments is not None
        assert len(result.attachments) == 1
        assert result.attachments[0].id == "att123"
        assert result.attachments[0].title == "document.pdf"

    def test_get_page_history_missing_body_v1(self, pages_mixin):
        """Regression test for #760: handle missing body.storage.value gracefully."""
        # Arrange
        page_id = "987654321"
        version = 1
        pages_mixin.config.url = "https://example.atlassian.net/wiki"

        # Mock historical page with missing body
        historical_page_data = {
            "id": page_id,
            "title": "Page Without Body",
            "space": {"key": "PROJ"},
            "version": {"number": version},
            "body": None,  # Missing body
            "children": {"attachment": {"results": []}},
        }
        pages_mixin.confluence.get_page_by_id.return_value = historical_page_data

        # Mock preprocessor to return empty strings for missing body
        pages_mixin.preprocessor.process_html_content.return_value = ("", "")
        pages_mixin.confluence.get_page_properties.return_value = {"results": []}

        # Act - should not raise exception
        result = pages_mixin.get_page_history(page_id, version)

        # Assert - empty content should be handled gracefully
        assert isinstance(result, ConfluencePage)
        assert result.id == page_id
        assert result.content == ""

    def test_get_page_history_auth_error_v1(self, pages_mixin):
        """Test that authentication errors raise MCPAtlassianAuthenticationError."""
        # Arrange
        page_id = "987654321"
        version = 1

        from requests.exceptions import HTTPError

        from mcp_atlassian.exceptions import MCPAtlassianAuthenticationError

        # Create a mock HTTP error response with 401
        mock_response = MagicMock()
        mock_response.status_code = 401
        http_error = HTTPError()
        http_error.response = mock_response

        pages_mixin.confluence.get_page_by_id.side_effect = http_error

        # Act/Assert
        with pytest.raises(
            MCPAtlassianAuthenticationError,
            match="Authentication failed for Confluence API",
        ):
            pages_mixin.get_page_history(page_id, version)

    def test_get_page_history_http_error_v1(self, pages_mixin):
        """Test that non-auth HTTP errors are propagated."""
        # Arrange
        page_id = "987654321"
        version = 1

        from requests.exceptions import HTTPError

        # Create a mock HTTP error response with 500
        mock_response = MagicMock()
        mock_response.status_code = 500
        http_error = HTTPError("Internal Server Error")
        http_error.response = mock_response

        pages_mixin.confluence.get_page_by_id.side_effect = http_error

        # Act/Assert - should propagate the HTTPError
        with pytest.raises(HTTPError, match="Internal Server Error"):
            pages_mixin.get_page_history(page_id, version)

    def test_get_page_history_includes_emoji_v1(self, pages_mixin):
        """Test that emoji is fetched and included in historical version result."""
        # Arrange
        page_id = "987654321"
        version = 1
        pages_mixin.config.url = "https://example.atlassian.net/wiki"

        historical_page_data = {
            "id": page_id,
            "title": "Page with Emoji",
            "space": {"key": "PROJ"},
            "version": {"number": version},
            "body": {"storage": {"value": "<p>Content with emoji</p>"}},
            "children": {"attachment": {"results": []}},
        }
        pages_mixin.confluence.get_page_by_id.return_value = historical_page_data

        # Mock preprocessor
        pages_mixin.preprocessor.process_html_content.return_value = (
            "<p>Content with emoji</p>",
            "Content with emoji",
        )

        # Mock emoji properties
        pages_mixin.confluence.get_page_properties.return_value = {
            "results": [
                {
                    "key": "emoji-title-published",
                    "value": {"fallback": "📖"},
                },
            ]
        }

        # Act
        result = pages_mixin.get_page_history(page_id, version)

        # Assert - emoji should be included
        assert isinstance(result, ConfluencePage)
        assert result.emoji == "📖"
        assert result.version.number == version


class TestPagesOAuthMixin:
    """Tests for PagesMixin with OAuth authentication."""

    @pytest.fixture
    def oauth_pages_mixin(self, oauth_confluence_client):
        """Create a PagesMixin instance for OAuth testing."""
        # PagesMixin inherits from ConfluenceClient, so we need to create it properly
        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceClient.__init__"
        ) as mock_init:
            mock_init.return_value = None
            mixin = PagesMixin()
            # Copy the necessary attributes from our mocked client
            mixin.confluence = oauth_confluence_client.confluence
            mixin.config = oauth_confluence_client.config
            mixin.preprocessor = oauth_confluence_client.preprocessor
            return mixin

    def test_create_page_oauth_uses_v2_api(self, oauth_pages_mixin):
        """Test that OAuth authentication uses v2 API for creating pages."""
        # Arrange
        space_key = "PROJ"
        title = "New OAuth Test Page"
        body = "<p>Test content for OAuth</p>"
        parent_id = "987654321"

        # Mock the v2 adapter
        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceV2Adapter"
        ) as mock_v2_adapter_class:
            mock_v2_adapter = MagicMock()
            mock_v2_adapter_class.return_value = mock_v2_adapter
            mock_v2_adapter.create_page.return_value = {
                "id": "oauth_123456789",
                "title": title,
            }

            # Mock get_page_content to return a ConfluencePage
            with patch.object(
                oauth_pages_mixin,
                "get_page_content",
                return_value=ConfluencePage(
                    id="oauth_123456789",
                    title=title,
                    content="OAuth page content",
                    space={"key": space_key, "name": "Project"},
                ),
            ):
                # Act - specify is_markdown=False since we're directly providing storage format
                result = oauth_pages_mixin.create_page(
                    space_key, title, body, parent_id, is_markdown=False
                )

                # Assert that v2 API was used instead of v1
                mock_v2_adapter.create_page.assert_called_once_with(
                    space_key=space_key,
                    title=title,
                    body=body,
                    parent_id=parent_id,
                    representation="storage",
                )

                # Verify v1 API was NOT called
                oauth_pages_mixin.confluence.create_page.assert_not_called()

                # Verify result is a ConfluencePage
                assert isinstance(result, ConfluencePage)
                assert result.id == "oauth_123456789"

    def test_create_page_oauth_with_wiki_format(self, oauth_pages_mixin):
        """Test that OAuth authentication uses v2 API for creating pages with wiki format."""
        # Arrange
        space_key = "PROJ"
        title = "OAuth Wiki Test Page"
        wiki_body = "h1. OAuth Wiki Test\n\n* Item 1\n* Item 2"

        # Mock the v2 adapter
        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceV2Adapter"
        ) as mock_v2_adapter_class:
            mock_v2_adapter = MagicMock()
            mock_v2_adapter_class.return_value = mock_v2_adapter
            mock_v2_adapter.create_page.return_value = {
                "id": "oauth_wiki_123",
                "title": title,
            }

            # Mock get_page_content to return a ConfluencePage
            with patch.object(
                oauth_pages_mixin,
                "get_page_content",
                return_value=ConfluencePage(
                    id="oauth_wiki_123",
                    title=title,
                    content="OAuth wiki page content",
                    space={"key": space_key, "name": "Project"},
                ),
            ):
                # Act - use wiki format
                result = oauth_pages_mixin.create_page(
                    space_key,
                    title,
                    wiki_body,
                    is_markdown=False,
                    content_representation="wiki",
                )

                # Assert that v2 API was used with wiki representation
                mock_v2_adapter.create_page.assert_called_once_with(
                    space_key=space_key,
                    title=title,
                    body=wiki_body,
                    parent_id=None,
                    representation="wiki",
                )

                # Verify v1 API was NOT called
                oauth_pages_mixin.confluence.create_page.assert_not_called()

                # Verify no markdown conversion happened
                oauth_pages_mixin.preprocessor.markdown_to_confluence_storage.assert_not_called()

                # Verify result is a ConfluencePage
                assert isinstance(result, ConfluencePage)
                assert result.id == "oauth_wiki_123"
                assert result.title == title

    def test_update_page_oauth_uses_v2_api(self, oauth_pages_mixin):
        """Test that OAuth authentication uses v2 API for updating pages."""
        # Arrange
        page_id = "oauth_987654321"
        title = "Updated OAuth Test Page"
        body = "<p>Updated test content for OAuth</p>"
        version_comment = "OAuth update test"

        # Mock the v2 adapter
        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceV2Adapter"
        ) as mock_v2_adapter_class:
            mock_v2_adapter = MagicMock()
            mock_v2_adapter_class.return_value = mock_v2_adapter
            mock_v2_adapter.update_page.return_value = {
                "id": page_id,
                "title": title,
            }

            # Mock get_page_content to return a ConfluencePage
            with patch.object(
                oauth_pages_mixin,
                "get_page_content",
                return_value=ConfluencePage(
                    id=page_id,
                    title=title,
                    content="Updated OAuth page content",
                    version={"number": 2},
                ),
            ):
                # Act - specify is_markdown=False since we're directly providing storage format
                result = oauth_pages_mixin.update_page(
                    page_id,
                    title,
                    body,
                    is_markdown=False,
                    version_comment=version_comment,
                )

                # Assert that v2 API was used instead of v1
                mock_v2_adapter.update_page.assert_called_once_with(
                    page_id=page_id,
                    title=title,
                    body=body,
                    representation="storage",
                    version_comment=version_comment,
                    expected_version=None,
                )

                # Verify v1 API was NOT called
                oauth_pages_mixin.confluence.update_page.assert_not_called()

                # Verify result is a ConfluencePage
                assert isinstance(result, ConfluencePage)
                assert result.id == page_id
                assert result.title == title

    def test_get_page_content_oauth_uses_v2_api(self, oauth_pages_mixin):
        """Test that OAuth authentication uses v2 API for getting page content."""
        # Arrange
        page_id = "oauth_get_123"

        # Mock the v2 adapter
        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceV2Adapter"
        ) as mock_v2_adapter_class:
            mock_v2_adapter = MagicMock()
            mock_v2_adapter_class.return_value = mock_v2_adapter

            # Mock v2 API response
            mock_v2_adapter.get_page.return_value = {
                "id": page_id,
                "title": "OAuth Test Page",
                "body": {"storage": {"value": "<p>OAuth page content</p>"}},
                "space": {"key": "PROJ", "name": "Project"},
                "version": {"number": 3},
            }

            # Mock get_page_emoji
            mock_v2_adapter.get_page_emoji.return_value = None

            # Mock the preprocessor
            oauth_pages_mixin.preprocessor.process_html_content.return_value = (
                "<p>Processed HTML</p>",
                "Processed OAuth content",
            )

            # Act
            result = oauth_pages_mixin.get_page_content(
                page_id, convert_to_markdown=True
            )

            # Assert that v2 API was used instead of v1
            mock_v2_adapter.get_page.assert_called_once_with(
                page_id=page_id, expand="body.storage,version,space,children.attachment"
            )

            # Verify v1 API was NOT called
            oauth_pages_mixin.confluence.get_page_by_id.assert_not_called()

            # Verify the preprocessor was called
            oauth_pages_mixin.preprocessor.process_html_content.assert_called_once_with(
                "<p>OAuth page content</p>",
                space_key="PROJ",
                confluence_client=oauth_pages_mixin.confluence,
                content_id=page_id,
                attachments=[],
            )

            # Verify result is a ConfluencePage with correct data
            assert isinstance(result, ConfluencePage)
            assert result.id == page_id
            assert result.title == "OAuth Test Page"
            assert result.content == "Processed OAuth content"
            assert result.space.key == "PROJ"
            assert result.version.number == 3

    def test_delete_page_oauth_uses_v2_api(self, oauth_pages_mixin):
        """Test that OAuth authentication uses v2 API for deleting pages."""
        # Arrange
        page_id = "oauth_delete_123"

        # Mock the v2 adapter
        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceV2Adapter"
        ) as mock_v2_adapter_class:
            mock_v2_adapter = MagicMock()
            mock_v2_adapter_class.return_value = mock_v2_adapter
            mock_v2_adapter.delete_page.return_value = True

            # Act
            result = oauth_pages_mixin.delete_page(page_id)

            # Assert that v2 API was used instead of v1
            mock_v2_adapter.delete_page.assert_called_once_with(page_id=page_id)

            # Verify v1 API was NOT called
            oauth_pages_mixin.confluence.remove_page.assert_not_called()

            # Verify result
            assert result is True

    def test_get_page_history_oauth_uses_v2_api(self, oauth_pages_mixin):
        """Test that OAuth authentication uses v2 API for getting page history."""
        # Arrange
        page_id = "oauth_history_123"
        version = 2

        # Mock the v2 adapter
        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceV2Adapter"
        ) as mock_v2_adapter_class:
            mock_v2_adapter = MagicMock()
            mock_v2_adapter_class.return_value = mock_v2_adapter

            # Mock v2 API response for historical page
            mock_v2_adapter.get_page_by_version.return_value = {
                "id": page_id,
                "title": "OAuth Historical Page",
                "space": {"key": "OAUTH", "name": "OAuth Space"},
                "version": {"number": version},
                "body": {
                    "storage": {"value": "<h2>OAuth Historical</h2><p>Content</p>"}
                },
                "children": {"attachment": {"results": []}},
            }

            # Mock emoji
            mock_v2_adapter.get_page_emoji.return_value = None

            # Mock preprocessor
            oauth_pages_mixin.preprocessor.process_html_content.return_value = (
                "<h2>OAuth Historical</h2><p>Content</p>",
                "## OAuth Historical\n\nContent",
            )

            # Act
            result = oauth_pages_mixin.get_page_history(
                page_id, version, convert_to_markdown=True
            )

            # Assert that v2 API was used instead of v1
            mock_v2_adapter.get_page_by_version.assert_called_once_with(
                page_id=page_id,
                version=version,
                expand="body.storage,version,space,children.attachment",
            )

            # Verify v1 API was NOT called
            oauth_pages_mixin.confluence.get_page_by_id.assert_not_called()

            # Verify result
            assert isinstance(result, ConfluencePage)
            assert result.id == page_id
            assert result.title == "OAuth Historical Page"
            assert result.version.number == version
            assert result.content == "## OAuth Historical\n\nContent"
            assert result.space.key == "OAUTH"

    def test_get_page_history_oauth_success(self, oauth_pages_mixin):
        """Test successfully retrieving historical version with OAuth."""
        # Arrange
        page_id = "oauth_hist_456"
        version = 3

        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceV2Adapter"
        ) as mock_v2_adapter_class:
            mock_v2_adapter = MagicMock()
            mock_v2_adapter_class.return_value = mock_v2_adapter

            mock_v2_adapter.get_page_by_version.return_value = {
                "id": page_id,
                "title": "OAuth Page Version 3",
                "space": {"key": "PROJ", "name": "Project"},
                "version": {"number": version},
                "body": {"storage": {"value": "<p>Version 3 content</p>"}},
                "children": {"attachment": {"results": []}},
            }

            mock_v2_adapter.get_page_emoji.return_value = None
            oauth_pages_mixin.preprocessor.process_html_content.return_value = (
                "<p>Version 3 content</p>",
                "Version 3 content",
            )

            # Act
            result = oauth_pages_mixin.get_page_history(page_id, version)

            # Assert
            assert isinstance(result, ConfluencePage)
            assert result.id == page_id
            assert result.version.number == version
            assert result.content == "Version 3 content"
            assert result.space.key == "PROJ"

    def test_get_page_history_oauth_html(self, oauth_pages_mixin):
        """Test retrieving historical version with HTML format using OAuth."""
        # Arrange
        page_id = "oauth_html_789"
        version = 1

        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceV2Adapter"
        ) as mock_v2_adapter_class:
            mock_v2_adapter = MagicMock()
            mock_v2_adapter_class.return_value = mock_v2_adapter

            mock_v2_adapter.get_page_by_version.return_value = {
                "id": page_id,
                "title": "OAuth HTML Version",
                "space": {"key": "PROJ"},
                "version": {"number": version},
                "body": {"storage": {"value": "<h1>HTML</h1>"}},
                "children": {"attachment": {"results": []}},
            }

            mock_v2_adapter.get_page_emoji.return_value = None
            oauth_pages_mixin.preprocessor.process_html_content.return_value = (
                "<h1>Processed HTML</h1>",
                "Processed markdown",
            )

            # Act - get HTML instead of markdown
            result = oauth_pages_mixin.get_page_history(
                page_id, version, convert_to_markdown=False
            )

            # Assert - should return HTML
            assert isinstance(result, ConfluencePage)
            assert result.content == "<h1>Processed HTML</h1>"
            assert result.version.number == version

    def test_get_page_history_oauth_missing_body(self, oauth_pages_mixin):
        """Test handling missing body with v2 API."""
        # Arrange
        page_id = "oauth_no_body_123"
        version = 1

        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceV2Adapter"
        ) as mock_v2_adapter_class:
            mock_v2_adapter = MagicMock()
            mock_v2_adapter_class.return_value = mock_v2_adapter

            # Mock historical page with missing body
            mock_v2_adapter.get_page_by_version.return_value = {
                "id": page_id,
                "title": "OAuth No Body",
                "space": {"key": "PROJ"},
                "version": {"number": version},
                "body": None,
                "children": {"attachment": {"results": []}},
            }

            mock_v2_adapter.get_page_emoji.return_value = None
            # Mock preprocessor to return empty strings for missing body
            oauth_pages_mixin.preprocessor.process_html_content.return_value = ("", "")

            # Act - should not raise exception
            result = oauth_pages_mixin.get_page_history(page_id, version)

            # Assert - empty content should be handled gracefully
            assert isinstance(result, ConfluencePage)
            assert result.id == page_id
            assert result.content == ""

    def test_get_page_history_includes_emoji_oauth(self, oauth_pages_mixin):
        """Test that emoji is fetched and included in historical version with OAuth."""
        # Arrange
        page_id = "oauth_emoji_hist_123"
        version = 2

        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceV2Adapter"
        ) as mock_v2_adapter_class:
            mock_v2_adapter = MagicMock()
            mock_v2_adapter_class.return_value = mock_v2_adapter

            mock_v2_adapter.get_page_by_version.return_value = {
                "id": page_id,
                "title": "OAuth Emoji History",
                "space": {"key": "PROJ", "name": "Project"},
                "version": {"number": version},
                "body": {"storage": {"value": "<p>Content</p>"}},
                "children": {"attachment": {"results": []}},
            }

            # Mock emoji
            mock_v2_adapter.get_page_emoji.return_value = "🔥"

            oauth_pages_mixin.preprocessor.process_html_content.return_value = (
                "<p>Content</p>",
                "Content",
            )

            # Act
            result = oauth_pages_mixin.get_page_history(page_id, version)

            # Assert - emoji should be included
            assert isinstance(result, ConfluencePage)
            assert result.emoji == "🔥"
            assert result.version.number == version


class TestPageEmoji:
    """Tests for page title emoji functionality."""

    @pytest.fixture
    def pages_mixin(self, confluence_client):
        """Create a PagesMixin instance for testing."""
        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceClient.__init__"
        ) as mock_init:
            mock_init.return_value = None
            mixin = PagesMixin()
            mixin.confluence = confluence_client.confluence
            mixin.config = confluence_client.config
            mixin.preprocessor = confluence_client.preprocessor
            return mixin

    def test_extract_emoji_from_property_with_fallback(self, pages_mixin):
        """Test extracting emoji from property with fallback attribute."""
        value = {"id": "1f4dd", "shortName": ":memo:", "fallback": "📝"}
        result = extract_emoji_from_property(value)
        assert result == "📝"

    def test_extract_emoji_from_property_with_shortname(self, pages_mixin):
        """Test extracting emoji from property with shortName when no fallback."""
        value = {"id": "1f4dd", "shortName": ":memo:"}
        result = extract_emoji_from_property(value)
        assert result == ":memo:"

    def test_extract_emoji_from_property_with_id(self, pages_mixin):
        """Test extracting emoji from property using hex id conversion."""
        value = {"id": "1f4dd"}  # Memo emoji code point
        result = extract_emoji_from_property(value)
        assert result == "📝"

    def test_extract_emoji_from_property_string(self, pages_mixin):
        """Test extracting emoji from string property value."""
        result = extract_emoji_from_property("🚀")
        assert result == "🚀"

    def test_extract_emoji_from_property_none(self, pages_mixin):
        """Test extracting emoji from None value."""
        result = extract_emoji_from_property(None)
        assert result is None

    def test_extract_emoji_from_property_empty_dict(self, pages_mixin):
        """Test extracting emoji from empty dict."""
        result = extract_emoji_from_property({})
        assert result is None

    def test_get_page_emoji_v1_api(self, pages_mixin):
        """Test getting page emoji via v1 API (non-OAuth)."""
        # Mock the properties API response
        pages_mixin.confluence.get_page_properties.return_value = {
            "results": [
                {
                    "key": "emoji-title-published",
                    "value": {"id": "1f680", "shortName": ":rocket:", "fallback": "🚀"},
                },
            ]
        }

        result = pages_mixin._get_page_emoji("123456")
        assert result == "🚀"
        pages_mixin.confluence.get_page_properties.assert_called_once_with("123456")

    def test_get_page_emoji_draft_fallback(self, pages_mixin):
        """Test getting page emoji from draft when published not available."""
        pages_mixin.confluence.get_page_properties.return_value = {
            "results": [
                {
                    "key": "emoji-title-draft",
                    "value": {"fallback": "📋"},
                },
            ]
        }

        result = pages_mixin._get_page_emoji("123456")
        assert result == "📋"

    def test_get_page_emoji_no_emoji(self, pages_mixin):
        """Test getting page emoji when none is set."""
        pages_mixin.confluence.get_page_properties.return_value = {
            "results": [
                {"key": "some-other-property", "value": "something"},
            ]
        }

        result = pages_mixin._get_page_emoji("123456")
        assert result is None

    def test_get_page_emoji_empty_properties(self, pages_mixin):
        """Test getting page emoji with empty properties."""
        pages_mixin.confluence.get_page_properties.return_value = {"results": []}

        result = pages_mixin._get_page_emoji("123456")
        assert result is None

    def test_get_page_emoji_api_error(self, pages_mixin):
        """Test that API errors return None gracefully."""
        pages_mixin.confluence.get_page_properties.side_effect = Exception("API Error")

        result = pages_mixin._get_page_emoji("123456")
        assert result is None

    def test_get_page_content_includes_emoji(self, pages_mixin):
        """Test that get_page_content includes emoji in result."""
        page_id = "987654321"
        pages_mixin.config.url = "https://example.atlassian.net/wiki"

        # Mock the emoji properties
        pages_mixin.confluence.get_page_properties.return_value = {
            "results": [
                {
                    "key": "emoji-title-published",
                    "value": {"fallback": "📖"},
                },
            ]
        }

        result = pages_mixin.get_page_content(page_id, convert_to_markdown=True)

        assert isinstance(result, ConfluencePage)
        assert result.emoji == "📖"

    def test_get_page_by_title_includes_emoji(self, pages_mixin):
        """Test that get_page_by_title includes emoji in result."""
        space_key = "DEMO"
        title = "Example Page"

        pages_mixin.confluence.get_page_by_title.return_value = {
            "id": "987654321",
            "title": title,
            "space": {"key": space_key},
            "body": {"storage": {"value": "<p>Example content</p>"}},
            "version": {"number": 1},
        }

        pages_mixin.preprocessor.process_html_content.return_value = (
            "<p>Processed HTML</p>",
            "Processed Markdown",
        )

        # Mock the emoji properties
        pages_mixin.confluence.get_page_properties.return_value = {
            "results": [
                {
                    "key": "emoji-title-published",
                    "value": {"fallback": "✨"},
                },
            ]
        }

        result = pages_mixin.get_page_by_title(space_key, title)

        assert result is not None
        assert result.emoji == "✨"

    def test_set_page_emoji_success(self, pages_mixin):
        """Test successfully setting a page emoji."""
        page_id = "set_emoji_123"

        # Mock set_page_property for creating new property
        pages_mixin.confluence.get_page_properties.return_value = {"results": []}
        pages_mixin.confluence.set_page_property.return_value = {
            "key": "emoji-title-published"
        }

        result = pages_mixin._set_page_emoji(page_id, "🚀")

        assert result is True
        # Emoji 🚀 has Unicode code point U+1F680 - Confluence expects just the hex string
        # Both published and draft properties should be set
        assert pages_mixin.confluence.set_page_property.call_count == 2
        pages_mixin.confluence.set_page_property.assert_any_call(
            page_id,
            {"key": "emoji-title-published", "value": "1f680"},
        )
        pages_mixin.confluence.set_page_property.assert_any_call(
            page_id,
            {"key": "emoji-title-draft", "value": "1f680"},
        )

    def test_set_page_emoji_update_existing(self, pages_mixin):
        """Test updating an existing page emoji."""
        page_id = "update_emoji_123"

        # The v1 API doesn't need to fetch existing properties - it just sets the value
        pages_mixin.confluence.set_page_property.return_value = {
            "key": "emoji-title-published"
        }

        result = pages_mixin._set_page_emoji(page_id, "🎉")

        assert result is True
        # Emoji 🎉 has Unicode code point U+1F389 - Confluence expects just the hex string
        # Both published and draft properties should be set
        assert pages_mixin.confluence.set_page_property.call_count == 2
        pages_mixin.confluence.set_page_property.assert_any_call(
            page_id,
            {"key": "emoji-title-published", "value": "1f389"},
        )
        pages_mixin.confluence.set_page_property.assert_any_call(
            page_id,
            {"key": "emoji-title-draft", "value": "1f389"},
        )

    def test_set_page_emoji_remove(self, pages_mixin):
        """Test removing a page emoji by setting to None."""
        page_id = "remove_emoji_123"

        # Mock existing emoji property
        pages_mixin.confluence.get_page_properties.return_value = {
            "results": [
                {
                    "key": "emoji-title-published",
                    "value": {"fallback": "📝"},
                    "version": {"number": 1},
                }
            ]
        }
        pages_mixin.confluence.delete_page_property.return_value = True

        result = pages_mixin._set_page_emoji(page_id, None)

        assert result is True
        # Both published and draft properties should be deleted
        assert pages_mixin.confluence.delete_page_property.call_count == 2
        pages_mixin.confluence.delete_page_property.assert_any_call(
            page_id, "emoji-title-published"
        )
        pages_mixin.confluence.delete_page_property.assert_any_call(
            page_id, "emoji-title-draft"
        )

    def test_set_page_emoji_remove_nonexistent(self, pages_mixin):
        """Test removing emoji when none exists still succeeds."""
        page_id = "no_emoji_123"

        # Mock delete returning an error (property doesn't exist)
        pages_mixin.confluence.delete_page_property.side_effect = Exception(
            "Property not found"
        )

        result = pages_mixin._set_page_emoji(page_id, None)

        # Should succeed even if property doesn't exist (exception caught)
        assert result is True
        # Both published and draft properties should be attempted to delete
        assert pages_mixin.confluence.delete_page_property.call_count == 2
        pages_mixin.confluence.delete_page_property.assert_any_call(
            page_id, "emoji-title-published"
        )
        pages_mixin.confluence.delete_page_property.assert_any_call(
            page_id, "emoji-title-draft"
        )

    def test_set_page_emoji_failure(self, pages_mixin):
        """Test handling failure when setting emoji."""
        page_id = "fail_emoji_123"

        pages_mixin.confluence.get_page_properties.return_value = {"results": []}
        pages_mixin.confluence.set_page_property.side_effect = Exception("API error")

        result = pages_mixin._set_page_emoji(page_id, "💥")

        assert result is False


class TestPageEmojiOAuth:
    """Tests for page emoji with OAuth authentication."""

    @pytest.fixture
    def oauth_pages_mixin(self, oauth_confluence_client):
        """Create a PagesMixin instance for OAuth testing."""
        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceClient.__init__"
        ) as mock_init:
            mock_init.return_value = None
            mixin = PagesMixin()
            mixin.confluence = oauth_confluence_client.confluence
            mixin.config = oauth_confluence_client.config
            mixin.preprocessor = oauth_confluence_client.preprocessor
            return mixin

    def test_get_page_emoji_oauth_uses_v2_api(self, oauth_pages_mixin):
        """Test that OAuth authentication uses v2 API for getting page emoji."""
        page_id = "oauth_emoji_123"

        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceV2Adapter"
        ) as mock_v2_adapter_class:
            mock_v2_adapter = MagicMock()
            mock_v2_adapter_class.return_value = mock_v2_adapter
            mock_v2_adapter.get_page_emoji.return_value = "🎉"

            result = oauth_pages_mixin._get_page_emoji(page_id)

            mock_v2_adapter.get_page_emoji.assert_called_once_with(page_id)
            assert result == "🎉"

    def test_get_page_content_oauth_includes_emoji(self, oauth_pages_mixin):
        """Test that OAuth get_page_content includes emoji in result."""
        page_id = "oauth_get_123"

        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceV2Adapter"
        ) as mock_v2_adapter_class:
            mock_v2_adapter = MagicMock()
            mock_v2_adapter_class.return_value = mock_v2_adapter

            mock_v2_adapter.get_page.return_value = {
                "id": page_id,
                "title": "OAuth Test Page",
                "body": {"storage": {"value": "<p>OAuth page content</p>"}},
                "space": {"key": "PROJ", "name": "Project"},
                "version": {"number": 3},
            }
            mock_v2_adapter.get_page_emoji.return_value = "🔥"

            oauth_pages_mixin.preprocessor.process_html_content.return_value = (
                "<p>Processed HTML</p>",
                "Processed OAuth content",
            )

            result = oauth_pages_mixin.get_page_content(
                page_id, convert_to_markdown=True
            )

            assert isinstance(result, ConfluencePage)
            assert result.emoji == "🔥"

    def test_set_page_emoji_oauth_uses_v2_api(self, oauth_pages_mixin):
        """Test that OAuth authentication uses v2 API for setting page emoji."""
        page_id = "oauth_set_emoji_123"

        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceV2Adapter"
        ) as mock_v2_adapter_class:
            mock_v2_adapter = MagicMock()
            mock_v2_adapter_class.return_value = mock_v2_adapter
            mock_v2_adapter.set_page_emoji.return_value = True

            result = oauth_pages_mixin._set_page_emoji(page_id, "🚀")

            mock_v2_adapter.set_page_emoji.assert_called_once_with(page_id, "🚀")
            assert result is True

    def test_set_page_emoji_oauth_remove(self, oauth_pages_mixin):
        """Test that OAuth can remove emoji by setting to None."""
        page_id = "oauth_remove_emoji_123"

        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceV2Adapter"
        ) as mock_v2_adapter_class:
            mock_v2_adapter = MagicMock()
            mock_v2_adapter_class.return_value = mock_v2_adapter
            mock_v2_adapter.set_page_emoji.return_value = True

            result = oauth_pages_mixin._set_page_emoji(page_id, None)

            mock_v2_adapter.set_page_emoji.assert_called_once_with(page_id, None)
            assert result is True


class TestMovePage:
    """Tests for the move_page method."""

    @pytest.fixture
    def pages_mixin(self, confluence_client):
        """Create a PagesMixin instance for testing."""
        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceClient.__init__"
        ) as mock_init:
            mock_init.return_value = None
            mixin = PagesMixin()
            mixin.confluence = confluence_client.confluence
            mixin.config = confluence_client.config
            mixin.preprocessor = confluence_client.preprocessor
            return mixin

    def test_move_page_to_new_parent_same_space(self, pages_mixin):
        """Test moving a page to a new parent within the same space."""
        page_id = "111"
        target_parent_id = "222"

        # Mock get_page_by_id to return target page with space info
        pages_mixin.confluence.get_page_by_id.return_value = {
            "id": target_parent_id,
            "title": "Target Parent",
            "space": {"key": "PROJ", "name": "Project"},
            "version": {"number": 1},
            "body": {"storage": {"value": "<p>Parent content</p>"}},
        }

        # Mock move_page
        pages_mixin.confluence.move_page.return_value = {"status": "ok"}

        # Mock get_page_content for the re-fetch after move
        mock_moved_page = ConfluencePage(
            id=page_id,
            title="Moved Page",
            content="Moved content",
            space={"key": "PROJ", "name": "Project"},
            version={"number": 2},
        )
        with patch.object(
            pages_mixin, "get_page_content", return_value=mock_moved_page
        ):
            result = pages_mixin.move_page(
                page_id=page_id, target_parent_id=target_parent_id
            )

        # Verify move_page was called with the correct space_key from the target
        pages_mixin.confluence.move_page.assert_called_once_with(
            "PROJ", page_id, target_id=target_parent_id, position="append"
        )
        assert isinstance(result, ConfluencePage)
        assert result.id == page_id

    def test_move_page_to_different_space_root(self, pages_mixin):
        """Test moving a page to the root of a different space."""
        page_id = "111"
        target_space_key = "NEWSPACE"

        # Mock move_page
        pages_mixin.confluence.move_page.return_value = {"status": "ok"}

        # Mock get_page_content for the re-fetch after move
        mock_moved_page = ConfluencePage(
            id=page_id,
            title="Moved Page",
            content="Moved content",
            space={"key": target_space_key, "name": "New Space"},
            version={"number": 2},
        )
        with patch.object(
            pages_mixin, "get_page_content", return_value=mock_moved_page
        ):
            result = pages_mixin.move_page(
                page_id=page_id, target_space_key=target_space_key
            )

        # Verify move_page was called with target_space_key and no target_id
        pages_mixin.confluence.move_page.assert_called_once_with(
            target_space_key, page_id, target_id=None, position="append"
        )
        assert isinstance(result, ConfluencePage)
        assert result.space.key == target_space_key

    def test_move_page_with_both_parent_and_space(self, pages_mixin):
        """Test moving a page with both target_parent_id and target_space_key."""
        page_id = "111"
        target_parent_id = "333"
        target_space_key = "OTHERSPACE"

        # Mock move_page
        pages_mixin.confluence.move_page.return_value = {"status": "ok"}

        # Mock get_page_content for the re-fetch after move
        mock_moved_page = ConfluencePage(
            id=page_id,
            title="Cross-Space Moved",
            content="Moved content",
            space={"key": target_space_key, "name": "Other Space"},
            version={"number": 2},
        )
        with patch.object(
            pages_mixin, "get_page_content", return_value=mock_moved_page
        ):
            result = pages_mixin.move_page(
                page_id=page_id,
                target_parent_id=target_parent_id,
                target_space_key=target_space_key,
            )

        # When both are given, use target_space_key directly (no need to look up)
        pages_mixin.confluence.move_page.assert_called_once_with(
            target_space_key, page_id, target_id=target_parent_id, position="append"
        )
        assert isinstance(result, ConfluencePage)
        assert result.space.key == target_space_key

    def test_move_page_validation_error_neither_provided(self, pages_mixin):
        """Test that ValueError is raised when neither target is provided."""
        with pytest.raises(ValueError, match="At least one of"):
            pages_mixin.move_page(page_id="111")

    def test_move_page_with_above_position(self, pages_mixin):
        """Test moving a page with 'above' position (sibling ordering)."""
        page_id = "111"
        target_parent_id = "222"

        pages_mixin.confluence.get_page_by_id.return_value = {
            "id": target_parent_id,
            "title": "Target Parent",
            "space": {"key": "PROJ", "name": "Project"},
            "version": {"number": 1},
            "body": {"storage": {"value": "<p>content</p>"}},
        }
        pages_mixin.confluence.move_page.return_value = {"status": "ok"}

        mock_moved_page = ConfluencePage(
            id=page_id,
            title="Moved Above Page",
            content="Content",
            space={"key": "PROJ", "name": "Project"},
            version={"number": 2},
        )
        with patch.object(
            pages_mixin, "get_page_content", return_value=mock_moved_page
        ):
            result = pages_mixin.move_page(
                page_id=page_id,
                target_parent_id=target_parent_id,
                position="above",
            )

        pages_mixin.confluence.move_page.assert_called_once_with(
            "PROJ", page_id, target_id=target_parent_id, position="above"
        )
        assert isinstance(result, ConfluencePage)

    def test_move_page_api_error(self, pages_mixin):
        """Test that API errors are propagated correctly."""
        page_id = "111"
        target_space_key = "BADSPACE"

        pages_mixin.confluence.move_page.side_effect = Exception(
            "API error: space not found"
        )

        with pytest.raises(Exception, match="Failed to move page"):
            pages_mixin.move_page(page_id=page_id, target_space_key=target_space_key)

    def test_move_page_uses_v2_adapter_for_oauth(self, pages_mixin):
        """Test that move_page uses v2 adapter for OAuth authentication."""
        page_id = "111"
        target_parent_id = "222"

        mock_v2_adapter = MagicMock()
        mock_v2_adapter.move_page.return_value = None

        mock_moved_page = ConfluencePage(
            id=page_id,
            title="OAuth Moved Page",
            content="Content",
            space={"key": "PROJ", "name": "Project"},
            version={"number": 2},
        )

        with (
            patch.object(
                type(pages_mixin),
                "_v2_adapter",
                new_callable=lambda: property(lambda self: mock_v2_adapter),
            ),
            patch.object(pages_mixin, "get_page_content", return_value=mock_moved_page),
        ):
            result = pages_mixin.move_page(
                page_id=page_id,
                target_parent_id=target_parent_id,
            )

        # v2 adapter should be called instead of confluence.move_page
        mock_v2_adapter.move_page.assert_called_once_with(
            page_id=page_id,
            position="append",
            target_id=target_parent_id,
        )
        pages_mixin.confluence.move_page.assert_not_called()
        assert isinstance(result, ConfluencePage)


class TestGetPageVersionDiff:
    """Tests for the get_page_version_diff method."""

    @pytest.fixture
    def pages_mixin(self, confluence_client):
        """Create a PagesMixin instance for testing."""
        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceClient.__init__"
        ) as mock_init:
            mock_init.return_value = None
            mixin = PagesMixin()
            mixin.confluence = confluence_client.confluence
            mixin.config = confluence_client.config
            mixin.preprocessor = confluence_client.preprocessor
            return mixin

    def _make_page(self, content: str, title: str = "Test Page") -> ConfluencePage:
        """Create a ConfluencePage with given content."""
        return ConfluencePage(
            id="12345",
            title=title,
            content=content,
        )

    def test_diff_shows_additions_and_removals(self, pages_mixin):
        """Test that diff output contains expected additions and removals."""
        old_content = "Line 1\nLine 2\nLine 3"
        new_content = "Line 1\nLine 2 modified\nLine 3\nLine 4"

        pages_mixin.get_page_history = MagicMock(
            side_effect=lambda page_id, version, convert_to_markdown=True: (
                self._make_page(old_content)
                if version == 1
                else self._make_page(new_content)
            )
        )

        result = pages_mixin.get_page_version_diff(
            page_id="12345", from_version=1, to_version=2
        )

        assert result["page_id"] == "12345"
        assert result["title"] == "Test Page"
        assert result["from_version"] == 1
        assert result["to_version"] == 2
        diff = result["diff"]
        assert "-Line 2" in diff
        assert "+Line 2 modified" in diff
        assert "+Line 4" in diff

    def test_diff_identical_content(self, pages_mixin):
        """Test that identical content produces empty diff."""
        content = "Same content\nOn multiple lines"

        pages_mixin.get_page_history = MagicMock(return_value=self._make_page(content))

        result = pages_mixin.get_page_version_diff(
            page_id="12345", from_version=1, to_version=2
        )

        assert result["page_id"] == "12345"
        assert result["from_version"] == 1
        assert result["to_version"] == 2
        assert result["diff"] == ""

    def test_versions_passed_correctly(self, pages_mixin):
        """Test that from_version and to_version are passed to get_page_history."""
        content = "Some content"
        pages_mixin.get_page_history = MagicMock(return_value=self._make_page(content))

        pages_mixin.get_page_version_diff(page_id="99999", from_version=3, to_version=7)

        calls = pages_mixin.get_page_history.call_args_list
        assert len(calls) == 2
        assert calls[0].kwargs["page_id"] == "99999"
        assert calls[0].kwargs["version"] == 3
        assert calls[1].kwargs["page_id"] == "99999"
        assert calls[1].kwargs["version"] == 7

    def test_diff_complete_replacement(self, pages_mixin):
        """Test diff when content is completely different."""
        old_content = "Old line 1\nOld line 2"
        new_content = "New line 1\nNew line 2"

        pages_mixin.get_page_history = MagicMock(
            side_effect=lambda page_id, version, convert_to_markdown=True: (
                self._make_page(old_content)
                if version == 1
                else self._make_page(new_content)
            )
        )

        result = pages_mixin.get_page_version_diff(
            page_id="12345", from_version=1, to_version=2
        )

        diff = result["diff"]
        assert "-Old line 1" in diff
        assert "-Old line 2" in diff
        assert "+New line 1" in diff
        assert "+New line 2" in diff


class TestPageWidth:
    """Tests for page layout width functionality."""

    @pytest.fixture
    def pages_mixin(self, confluence_client):
        """Create a PagesMixin instance for testing."""
        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceClient.__init__"
        ) as mock_init:
            mock_init.return_value = None
            mixin = PagesMixin()
            mixin.confluence = confluence_client.confluence
            mixin.config = confluence_client.config
            mixin.preprocessor = confluence_client.preprocessor
            return mixin

    @pytest.mark.parametrize(
        "raw,label",
        [
            ("default", "narrow"),
            ("full-width", "wide"),
            ("max", "max"),
        ],
    )
    def test_width_mapping_published_precedence(self, pages_mixin, raw, label):
        from mcp_atlassian.confluence.v2_adapter import ConfluenceV2Adapter

        with patch.object(
            ConfluenceV2Adapter,
            "_get_property",
            side_effect=[
                {"value": raw},
                {"value": "max" if raw != "max" else "default"},
            ],
        ):
            state = pages_mixin._read_width_state("123")
        assert state["page_width"] == raw
        assert state["published"] == {"state": "known", "raw": raw, "label": label}
        assert state["conflict"] is True
        assert state["rendered_verified"] is False

    @pytest.mark.parametrize(
        "published,draft,expected",
        [
            (None, None, None),
            (None, {"value": {"value": "max"}}, "max"),
            ({"value": "future-width"}, {"value": "max"}, None),
        ],
    )
    def test_missing_unknown_width(self, pages_mixin, published, draft, expected):
        from mcp_atlassian.confluence.v2_adapter import ConfluenceV2Adapter

        with patch.object(
            ConfluenceV2Adapter, "_get_property", side_effect=[published, draft]
        ):
            state = pages_mixin._read_width_state("123")
        assert state["page_width"] == expected
        assert state["published"]["state"] == (
            "missing" if published is None else "unknown"
        )
        assert state["published"]["raw"] == (
            None if published is None else "future-width"
        )

    def test_property_read_failure_not_missing(self, pages_mixin):
        from requests import ConnectionError

        from mcp_atlassian.confluence.v2_adapter import ConfluenceV2Adapter

        with patch.object(
            ConfluenceV2Adapter,
            "_get_property",
            side_effect=[
                ConnectionError(),
                {"value": "max"},
            ],
        ):
            state = pages_mixin._read_width_state("123")
        assert state["published"]["state"] == "read_failed"
        assert state["draft"]["state"] == "known"
        assert state["page_width"] is None
        assert state["conflict"] is None

    @pytest.mark.parametrize(
        "width,raw",
        [
            ("narrow", "default"),
            ("wide", "full-width"),
            ("max", "max"),
            ("default", "default"),
            ("full-width", "full-width"),
        ],
    )
    def test_width_only_preserves_body_draft(self, pages_mixin, width, raw):
        from mcp_atlassian.confluence.v2_adapter import ConfluenceV2Adapter

        with (
            patch.object(
                ConfluenceV2Adapter, "_set_page_property", return_value=True
            ) as write,
            patch.object(
                ConfluenceV2Adapter,
                "_get_property",
                side_effect=[
                    {"value": raw},
                    {"value": "max"},
                ],
            ),
        ):
            result = pages_mixin.set_page_width("123", width)
        write.assert_called_once_with("123", "content-appearance-published", raw)
        assert result["success"] is True
        assert result["readback_verified"] == {"published": True}
        assert result["rendered_verified"] is False
        pages_mixin.confluence.put.assert_not_called()
        pages_mixin.confluence.update_page.assert_not_called()

    def test_draft_only_scope(self, pages_mixin):
        from mcp_atlassian.confluence.v2_adapter import ConfluenceV2Adapter

        with (
            patch.object(
                ConfluenceV2Adapter, "_set_page_property", return_value=True
            ) as write,
            patch.object(
                ConfluenceV2Adapter,
                "_get_property",
                side_effect=[
                    {"value": "default"},
                    {"value": "max"},
                ],
            ),
        ):
            result = pages_mixin.set_page_width("123", "max", scope="draft")
        write.assert_called_once_with("123", "content-appearance-draft", "max")
        assert result["success"] is True
        assert result["readback_verified"] == {"draft": True}
        assert result["layout"]["page_width"] == "default"

    def test_invalid_scope_never_writes(self, pages_mixin):
        from mcp_atlassian.confluence.v2_adapter import ConfluenceV2Adapter

        with patch.object(ConfluenceV2Adapter, "_set_page_property") as write:
            with pytest.raises(ValueError, match="scope must"):
                pages_mixin.set_page_width("123", "max", scope="invalid")
        write.assert_not_called()

    def test_partial_write_report(self, pages_mixin):
        from mcp_atlassian.confluence.v2_adapter import ConfluenceV2Adapter

        with (
            patch.object(
                ConfluenceV2Adapter, "_set_page_property", side_effect=[True, False]
            ),
            patch.object(
                ConfluenceV2Adapter,
                "_get_property",
                side_effect=[
                    {"value": "max"},
                    {"value": "default"},
                ],
            ),
        ):
            result = pages_mixin.set_page_width("123", "max", scope="both")
        assert result["success"] is False
        assert result["partial_write"] is True
        assert result["writes"] == {"published": True, "draft": False}
        assert result["readback_verified"] == {"published": True, "draft": False}

    def test_readback_failure_report(self, pages_mixin):
        from requests import ConnectionError

        from mcp_atlassian.confluence.v2_adapter import ConfluenceV2Adapter

        with (
            patch.object(ConfluenceV2Adapter, "_set_page_property", return_value=True),
            patch.object(
                ConfluenceV2Adapter, "_get_property", side_effect=ConnectionError()
            ),
        ):
            result = pages_mixin.set_page_width("123", "max")
        assert result["success"] is False
        assert result["writes"] == {"published": True}
        assert result["readback_verified"] == {"published": False}
        assert result["layout"]["published"]["state"] == "read_failed"

    @pytest.mark.parametrize("operation", ["create", "update", "width"])
    def test_invalid_width_before_mutation(self, pages_mixin, operation):
        with pytest.raises(Exception, match="page_width must"):
            if operation == "create":
                pages_mixin.create_page("TEST", "Title", "body", page_width="invalid")
            elif operation == "update":
                pages_mixin.update_page("123", "Title", "body", page_width="invalid")
            else:
                pages_mixin.set_page_width("123", "invalid")
        pages_mixin.confluence.create_page.assert_not_called()
        pages_mixin.confluence.put.assert_not_called()
        pages_mixin.preprocessor.markdown_to_confluence_storage.assert_not_called()

    def test_server_width_unsupported(self, pages_mixin):
        pages_mixin.config.url = "https://confluence.example.com"
        assert (
            pages_mixin._read_width_state("123")["published"]["state"] == "unsupported"
        )
        with pytest.raises(ValueError, match="only on Cloud"):
            pages_mixin.set_page_width("123", "wide")

    @pytest.mark.parametrize("operation", ["create", "update"])
    def test_content_write_width_failure(self, pages_mixin, operation):
        pages_mixin.confluence.create_page.return_value = {"id": "123"}
        pages_mixin.confluence.get_page_by_id.return_value = {"version": {"number": 1}}
        with patch.object(pages_mixin, "_set_page_width", return_value=False):
            with pytest.raises(
                Exception, match="content was .*width write/readback failed"
            ):
                if operation == "create":
                    pages_mixin.create_page("TEST", "Title", "body", page_width="wide")
                else:
                    pages_mixin.update_page("123", "Title", "body", page_width="wide")

    def test_layout_read_fetches_both_formats(self, pages_mixin):
        from mcp_atlassian.confluence.v2_adapter import ConfluenceV2Adapter

        storage = MagicMock()
        storage.json.return_value = {"body": {"storage": {"value": "<p>plain</p>"}}}
        adf = MagicMock()
        adf.json.return_value = {
            "body": {
                "atlas_doc_format": {
                    "value": '{"type":"doc","content":[{"type":"paragraph"}]}'
                }
            }
        }
        pages_mixin.confluence._session.get.side_effect = [storage, adf]
        with patch.object(ConfluenceV2Adapter, "_get_property", return_value=None):
            result = pages_mixin.get_page_layout("123")
        assert result["published"]["state"] == "missing"
        for representation in ("storage", "atlas_doc_format"):
            evidence = result["content"][representation]
            assert evidence["state"] == "read"
            assert evidence["evidence"][0]["alignment_state"] == "unspecified"
        assert [
            call.kwargs["params"]
            for call in pages_mixin.confluence._session.get.call_args_list
        ] == [
            {"body-format": "storage"},
            {"body-format": "atlas_doc_format"},
        ]

    def test_layout_body_failure_is_independent(self, pages_mixin):
        from requests import ConnectionError

        from mcp_atlassian.confluence.v2_adapter import ConfluenceV2Adapter

        missing = MagicMock()
        missing.json.return_value = {"body": {}}
        pages_mixin.confluence._session.get.side_effect = [ConnectionError(), missing]
        with patch.object(
            ConfluenceV2Adapter, "_get_property", return_value={"value": "max"}
        ):
            result = pages_mixin.get_page_layout("123")
        assert result["page_width"] == "max"
        assert result["content"]["storage"] == {"state": "read_failed"}
        assert result["content"]["atlas_doc_format"] == {"state": "missing"}

    def test_layout_auth_error_uses_decorator(self, pages_mixin):
        from requests import Response
        from requests.exceptions import HTTPError

        from mcp_atlassian.confluence.v2_adapter import ConfluenceV2Adapter
        from mcp_atlassian.exceptions import MCPAtlassianAuthenticationError

        response = Response()
        response.status_code = 403
        with patch.object(
            ConfluenceV2Adapter,
            "_get_property",
            side_effect=HTTPError(response=response),
        ):
            with pytest.raises(MCPAtlassianAuthenticationError):
                pages_mixin.get_page_layout("123")

    def test_get_page_content_includes_width(self, pages_mixin):
        """Test that get_page_content includes page width."""
        page_id = "page_with_width_123"

        with (
            patch.object(pages_mixin.confluence, "get_page_by_id") as mock_get,
            patch.object(pages_mixin, "_get_page_emoji") as mock_emoji,
            patch.object(pages_mixin, "_read_width_state") as mock_width,
            patch.object(
                pages_mixin.preprocessor, "process_html_content"
            ) as mock_process,
        ):
            mock_get.return_value = {
                "id": page_id,
                "title": "Test Page",
                "body": {"storage": {"value": "<p>Content</p>"}},
                "version": {"number": 1},
                "space": {"key": "TEST"},
            }
            mock_emoji.return_value = "\U0001f4c4"
            mock_width.return_value = {
                "page_width": "full-width",
                "rendered_verified": False,
            }
            mock_process.return_value = ("<p>Content</p>", "Content")

            page = pages_mixin.get_page_content(page_id)

            mock_width.assert_called_once_with(page_id)
            assert page.page_width == "full-width"


class TestPageHierarchy:
    """Tests for page hierarchy and navigation methods."""

    @pytest.fixture
    def pages_mixin(self, confluence_client):
        """Create a PagesMixin instance for testing."""
        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceClient.__init__"
        ) as mock_init:
            mock_init.return_value = None
            mixin = PagesMixin()
            mixin.confluence = confluence_client.confluence
            mixin.config = confluence_client.config
            mixin.preprocessor = confluence_client.preprocessor
            return mixin

    @staticmethod
    def _raw_response(pages: list[dict], next_link: str | None = None) -> dict:
        """Build a mock get_all_pages_from_space_raw response."""
        resp: dict = {"results": pages}
        if next_link:
            resp["_links"] = {"next": next_link}
        return resp

    def test_get_space_page_tree_empty(self, pages_mixin):
        """Test get_space_page_tree with no pages."""
        pages_mixin.confluence.get_all_pages_from_space_raw = MagicMock(
            return_value=self._raw_response([])
        )

        result = pages_mixin.get_space_page_tree("EMPTY")

        assert isinstance(result, dict)
        assert result["space_key"] == "EMPTY"
        assert result["total_pages"] == 0
        assert result["has_more"] is False
        assert result["pages"] == []

    def test_get_space_page_tree_single_root(self, pages_mixin):
        """Test get_space_page_tree with single root page."""
        mock_page = {
            "id": "123",
            "title": "Root Page",
            "ancestors": [],
            "extensions": {"position": 0},
        }
        pages_mixin.confluence.get_all_pages_from_space_raw = MagicMock(
            return_value=self._raw_response([mock_page])
        )

        result = pages_mixin.get_space_page_tree("TEST")

        assert result["space_key"] == "TEST"
        assert result["total_pages"] == 1
        assert result["has_more"] is False
        assert len(result["pages"]) == 1
        page = result["pages"][0]
        assert page["id"] == "123"
        assert page["title"] == "Root Page"
        assert page["parent_id"] is None
        assert page["depth"] == 0
        assert page["position"] == 0

    def test_get_space_page_tree_with_children(self, pages_mixin):
        """Test get_space_page_tree returns parent_id and depth correctly."""
        mock_pages = [
            {
                "id": "123",
                "title": "Parent Page",
                "ancestors": [],
                "extensions": {"position": 0},
            },
            {
                "id": "456",
                "title": "Child Page",
                "ancestors": [{"id": "123"}],
                "extensions": {"position": 0},
            },
        ]
        pages_mixin.confluence.get_all_pages_from_space_raw = MagicMock(
            return_value=self._raw_response(mock_pages)
        )

        result = pages_mixin.get_space_page_tree("TEST")

        assert result["total_pages"] == 2
        pages = result["pages"]

        parent = next(p for p in pages if p["id"] == "123")
        child = next(p for p in pages if p["id"] == "456")

        assert parent["parent_id"] is None
        assert parent["depth"] == 0
        assert child["parent_id"] == "123"
        assert child["depth"] == 1

        parent_idx = pages.index(parent)
        child_idx = pages.index(child)
        assert parent_idx < child_idx

    def test_get_space_page_tree_sorting(self, pages_mixin):
        """Test that pages are sorted by depth then position."""
        mock_pages = [
            {
                "id": "789",
                "title": "Third Page",
                "ancestors": [],
                "extensions": {"position": 2},
            },
            {
                "id": "123",
                "title": "First Page",
                "ancestors": [],
                "extensions": {"position": 0},
            },
            {
                "id": "456",
                "title": "Second Page",
                "ancestors": [],
                "extensions": {"position": 1},
            },
        ]
        pages_mixin.confluence.get_all_pages_from_space_raw = MagicMock(
            return_value=self._raw_response(mock_pages)
        )

        result = pages_mixin.get_space_page_tree("TEST")

        pages = result["pages"]
        assert pages[0]["id"] == "123"  # position 0
        assert pages[1]["id"] == "456"  # position 1
        assert pages[2]["id"] == "789"  # position 2

    def test_get_space_page_tree_sorting_mixed_position_types(self, pages_mixin):
        """Test sorting handles string, int, and missing positions safely."""
        mock_pages = [
            {
                "id": "c",
                "title": "Third",
                "ancestors": [],
                "extensions": {"position": None},
            },
            {
                "id": "b",
                "title": None,
                "ancestors": [],
                "extensions": {"position": "1"},
            },
            {
                "id": "a",
                "title": "First",
                "ancestors": [],
                "extensions": {"position": 0},
            },
        ]
        pages_mixin.confluence.get_all_pages_from_space_raw = MagicMock(
            return_value=self._raw_response(mock_pages)
        )

        result = pages_mixin.get_space_page_tree("TEST")

        pages = result["pages"]
        assert [page["id"] for page in pages] == ["a", "b", "c"]

    def test_pagination_multiple_batches(self, pages_mixin):
        """Test that pagination fetches across multiple API batches."""
        batch1 = [
            {
                "id": str(i),
                "title": f"Page {i}",
                "ancestors": [],
                "extensions": {"position": i},
            }
            for i in range(3)
        ]
        batch2 = [
            {
                "id": str(i),
                "title": f"Page {i}",
                "ancestors": [],
                "extensions": {"position": i},
            }
            for i in range(3, 5)
        ]
        pages_mixin.confluence.get_all_pages_from_space_raw = MagicMock(
            side_effect=[
                self._raw_response(batch1, next_link="/rest/api/content?start=3"),
                self._raw_response(batch2),  # no next link = last batch
            ]
        )

        result = pages_mixin.get_space_page_tree("TEST", limit=500)

        assert result["total_pages"] == 5
        assert result["has_more"] is False
        assert pages_mixin.confluence.get_all_pages_from_space_raw.call_count == 2

        # Verify correct start offsets were passed to each batch
        calls = pages_mixin.confluence.get_all_pages_from_space_raw.call_args_list
        assert calls[0].kwargs["start"] == 0
        assert calls[1].kwargs["start"] == 3

    def test_pagination_respects_limit_ceiling(self, pages_mixin):
        """Test has_more=True when limit reached but more pages exist."""
        # 3 pages in batch, limit=3, and next_link exists
        batch = [
            {
                "id": str(i),
                "title": f"Page {i}",
                "ancestors": [],
                "extensions": {"position": i},
            }
            for i in range(3)
        ]
        pages_mixin.confluence.get_all_pages_from_space_raw = MagicMock(
            return_value=self._raw_response(
                batch, next_link="/rest/api/content?start=3"
            )
        )

        result = pages_mixin.get_space_page_tree("TEST", limit=3)

        assert result["total_pages"] == 3
        assert result["has_more"] is True
        assert result["next_start"] == 3

    def test_pagination_exhausted_before_limit(self, pages_mixin):
        """Test has_more=False when all pages fetched before hitting limit."""
        batch = [
            {
                "id": "1",
                "title": "Only Page",
                "ancestors": [],
                "extensions": {"position": 0},
            }
        ]
        pages_mixin.confluence.get_all_pages_from_space_raw = MagicMock(
            return_value=self._raw_response(batch)  # no next link
        )

        result = pages_mixin.get_space_page_tree("TEST", limit=500)

        assert result["total_pages"] == 1
        assert result["has_more"] is False
        assert "next_start" not in result

    def test_pagination_stops_on_empty_batch(self, pages_mixin):
        """Test that pagination terminates when API returns empty results."""
        batch1 = [
            {
                "id": "1",
                "title": "Page 1",
                "ancestors": [],
                "extensions": {"position": 0},
            }
        ]
        pages_mixin.confluence.get_all_pages_from_space_raw = MagicMock(
            side_effect=[
                self._raw_response(batch1, next_link="/rest/api/content?start=1"),
                self._raw_response([]),  # empty batch
            ]
        )

        result = pages_mixin.get_space_page_tree("TEST", limit=500)

        assert result["total_pages"] == 1
        assert result["has_more"] is False

    def test_pagination_api_cap_smaller_than_limit(self, pages_mixin):
        """Test correct pagination when API caps below requested limit.

        Simulates Confluence's ~200 result server-side cap: even though
        we request more, each batch returns at most the cap amount.
        """
        # Simulate: limit=500, API caps at 3 per batch, space has 7 pages
        batches = [
            [
                {
                    "id": str(i),
                    "title": f"Page {i}",
                    "ancestors": [],
                    "extensions": {"position": i},
                }
                for i in range(0, 3)
            ],
            [
                {
                    "id": str(i),
                    "title": f"Page {i}",
                    "ancestors": [],
                    "extensions": {"position": i},
                }
                for i in range(3, 6)
            ],
            [
                {
                    "id": "6",
                    "title": "Page 6",
                    "ancestors": [],
                    "extensions": {"position": 6},
                }
            ],
        ]
        pages_mixin.confluence.get_all_pages_from_space_raw = MagicMock(
            side_effect=[
                self._raw_response(batches[0], next_link="/rest/api/content?start=3"),
                self._raw_response(batches[1], next_link="/rest/api/content?start=6"),
                self._raw_response(batches[2]),  # last batch, no next
            ]
        )

        result = pages_mixin.get_space_page_tree("TEST", limit=500)

        assert result["total_pages"] == 7
        assert result["has_more"] is False
        assert pages_mixin.confluence.get_all_pages_from_space_raw.call_count == 3

    def test_pagination_missing_links_treated_as_last_page(self, pages_mixin):
        """Test that missing _links in response is treated as no more pages."""
        batch = [
            {
                "id": "1",
                "title": "Page 1",
                "ancestors": [],
                "extensions": {"position": 0},
            }
        ]
        # Response has no _links key at all
        pages_mixin.confluence.get_all_pages_from_space_raw = MagicMock(
            return_value={"results": batch}
        )

        result = pages_mixin.get_space_page_tree("TEST", limit=500)

        assert result["total_pages"] == 1
        assert result["has_more"] is False

    def test_expand_uses_ancestors_only(self, pages_mixin):
        """Test that the API call uses only 'ancestors' expand parameter."""
        pages_mixin.confluence.get_all_pages_from_space_raw = MagicMock(
            return_value=self._raw_response([])
        )

        pages_mixin.get_space_page_tree("TEST")

        call_kwargs = pages_mixin.confluence.get_all_pages_from_space_raw.call_args
        assert call_kwargs.kwargs.get("expand") == "ancestors"

    def test_pagination_limit_one(self, pages_mixin):
        """Test degenerate limit=1 boundary case."""
        batch = [
            {
                "id": "1",
                "title": "Page 1",
                "ancestors": [],
                "extensions": {"position": 0},
            }
        ]
        pages_mixin.confluence.get_all_pages_from_space_raw = MagicMock(
            return_value=self._raw_response(
                batch, next_link="/rest/api/content?start=1"
            )
        )

        result = pages_mixin.get_space_page_tree("TEST", limit=1)

        assert result["total_pages"] == 1
        assert result["has_more"] is True
        assert result["next_start"] == 1
        # Should request exactly 1 page
        call_kwargs = pages_mixin.confluence.get_all_pages_from_space_raw.call_args
        assert call_kwargs.kwargs["limit"] == 1

    def test_pagination_links_without_next_key(self, pages_mixin):
        """Test response where _links exists but next is absent."""
        batch = [
            {
                "id": "1",
                "title": "Page 1",
                "ancestors": [],
                "extensions": {"position": 0},
            }
        ]
        # _links present with 'self' but no 'next'
        pages_mixin.confluence.get_all_pages_from_space_raw = MagicMock(
            return_value={
                "results": batch,
                "_links": {"self": "/rest/api/content?spaceKey=TEST"},
            }
        )

        result = pages_mixin.get_space_page_tree("TEST", limit=500)

        assert result["total_pages"] == 1
        assert result["has_more"] is False


class TestLayoutEvidence:
    def test_storage_alignment_and_unspecified_images(self):
        from mcp_atlassian.confluence.layout import inspect_storage

        result = inspect_storage(
            '<h2 style="text-align: center">private text</h2><p>plain</p>'
            '<ac:image ac:align="end" ac:width="300"><ri:attachment '
            'ri:filename="private.png" /></ac:image><img width="200" src="private" />'
            '<ac:layout-section ac:type="two_equal"><ac:layout-cell>'
            '<table><tr><td colspan="2"><p style="text-align: right">x</p>'
            "</td></tr></table></ac:layout-cell></ac:layout-section>"
        )
        rows = result["evidence"]
        assert rows[0]["alignment"] == {"text-align": "center"}
        assert rows[1]["alignment_state"] == "unspecified"
        assert rows[1]["alignment"] == {}
        assert rows[2]["alignment"] == {"ac:align": "end"}
        assert rows[2]["size"] == {"ac:width": "300"}
        assert rows[3]["alignment_state"] == "unspecified"
        assert rows[3]["size"] == {"width": "200"}
        assert rows[4]["structure"] == {"ac:type": "two_equal"}
        assert rows[-2]["structure"] == {"colspan": "2"}
        assert rows[-1]["alignment"] == {"text-align": "right"}
        assert "private" not in str(result)
        assert inspect_storage("<p>x</p><p>y</p>", limit=1)["truncated"] is True

    @pytest.mark.parametrize("align", ["start", "center", "end"])
    def test_adf_alignment_marks_nested_tables_and_images(self, align):
        from mcp_atlassian.confluence.layout import inspect_adf

        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "marks": [
                        {"type": "alignment", "attrs": {"align": align}},
                    ],
                },
                {
                    "type": "table",
                    "content": [
                        {
                            "type": "tableRow",
                            "content": [
                                {
                                    "type": "tableCell",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "marks": [
                                                {
                                                    "type": "alignment",
                                                    "attrs": {"align": "end"},
                                                },
                                            ],
                                        },
                                        {"type": "paragraph"},
                                    ],
                                },
                            ],
                        }
                    ],
                },
                {
                    "type": "mediaSingle",
                    "attrs": {"layout": "align-start", "width": 50},
                    "content": [
                        {
                            "type": "media",
                            "attrs": {
                                "id": "private-media",
                                "width": 300,
                                "height": 200,
                            },
                        }
                    ],
                },
            ],
        }
        result = inspect_adf(adf)
        rows = result["evidence"]
        assert rows[0]["alignment"] == {"mark": align}
        assert rows[4]["alignment"] == {"mark": "end"}
        assert rows[4]["path"] == "doc/content/1/content/0/content/0/content/0"
        assert rows[5]["alignment_state"] == "unspecified"
        assert rows[6]["alignment"] == {"layout": "align-start"}
        assert rows[6]["size"] == {"width": 50}
        assert rows[7]["alignment_state"] == "unspecified"
        assert rows[7]["size"] == {"width": 300, "height": 200}
        assert "private-media" not in str(result)
        assert inspect_adf(adf, limit=1)["truncated"] is True


@pytest.mark.parametrize(
    "value",
    [
        "not-json",
        [],
        {"type": "doc", "content": [None]},
        {"type": "paragraph", "marks": [None]},
        {"type": "paragraph", "marks": [{"type": "alignment", "attrs": None}]},
    ],
)
def test_malformed_adf_is_rejected(value):
    from mcp_atlassian.confluence.layout import inspect_adf

    with pytest.raises(ValueError):
        inspect_adf(value)
