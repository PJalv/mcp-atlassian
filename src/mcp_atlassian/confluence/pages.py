"""Module for Confluence page operations."""

import difflib
import logging
from typing import Any

import requests
from requests.exceptions import HTTPError

from ..models.confluence import ConfluencePage
from ..utils.decorators import handle_auth_errors
from .client import ConfluenceClient
from .layout import (
    inspect_adf,
    inspect_storage,
    layout_state,
    normalize_width,
    width_property,
)
from .utils import emoji_to_hex_id, extract_emoji_from_property
from .v2_adapter import ConfluenceV2Adapter

logger = logging.getLogger("mcp-atlassian")


def _page_tree_sort_position(value: Any) -> int:
    """Normalize Confluence page position values for stable sorting."""
    if value is None:
        return 999999

    if isinstance(value, bool):
        return int(value)

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 999999


def _page_tree_sort_title(value: Any) -> str:
    """Normalize Confluence page titles for stable sorting."""
    if value is None:
        return ""
    return str(value)


class PagesMixin(ConfluenceClient):
    """Mixin for Confluence page operations."""

    @property
    def _v2_adapter(self) -> ConfluenceV2Adapter | None:
        """Get v2 API adapter for OAuth authentication.

        Returns:
            ConfluenceV2Adapter instance if OAuth is configured, None otherwise
        """
        if self.config.auth_type == "oauth" and self.config.is_cloud:
            return ConfluenceV2Adapter(
                session=self.confluence._session, base_url=self.confluence.url
            )
        return None

    @handle_auth_errors("Confluence API")
    def get_page_content(
        self, page_id: str, *, convert_to_markdown: bool = True
    ) -> ConfluencePage:
        """
        Get content of a specific page.

        Args:
            page_id: The ID of the page to retrieve
            convert_to_markdown: When True, returns content in
                markdown format, otherwise returns raw HTML
                (keyword-only)

        Returns:
            ConfluencePage model containing the page content and
            metadata

        Raises:
            MCPAtlassianAuthenticationError: If authentication fails
                with the Confluence API (401/403)
            Exception: If there is an error retrieving the page
        """
        try:
            # Use v2 API for OAuth, v1 API for token/basic auth
            v2_adapter = self._v2_adapter
            if v2_adapter:
                logger.debug(
                    f"Using v2 API for OAuth authentication to get page '{page_id}'"
                )
                page = v2_adapter.get_page(
                    page_id=page_id,
                    expand="body.storage,version,space,children.attachment",
                )
            else:
                logger.debug(
                    "Using v1 API for token/basic"
                    f" authentication to get page '{page_id}'"
                )
                page = self.confluence.get_page_by_id(
                    page_id=page_id,
                    expand="body.storage,version,space,children.attachment",
                )

            # Check if API returned an error string
            if isinstance(page, str):
                error_msg = f"API returned error response: {page[:500]}"
                raise Exception(error_msg)

            space_key = page.get("space", {}).get("key", "")
            try:
                content = page["body"]["storage"]["value"]
            except (KeyError, TypeError) as e:
                logger.warning(
                    f"Page {page.get('id', 'unknown')} missing body.storage.value: {e}"
                )
                content = ""
            page_id_str = str(page.get("id", ""))
            page_attachments = (
                page.get("children", {}).get("attachment", {}).get("results", [])
            )
            processed_html, processed_markdown = self.preprocessor.process_html_content(
                content,
                space_key=space_key,
                confluence_client=self.confluence,
                content_id=page_id_str,
                attachments=page_attachments,
            )

            page_content = processed_markdown if convert_to_markdown else processed_html

            # Fetch page emoji and width from content properties
            emoji = self._get_page_emoji(page_id)
            layout = self._read_width_state(page_id)
            layout["content"] = {
                "storage": inspect_storage(content)
                if isinstance(content, str)
                else {"state": "missing"}
            }
            page_width = layout["page_width"]

            return ConfluencePage.from_api_response(
                page,
                base_url=self.config.url,
                include_body=True,
                content_override=page_content,
                content_format=("storage" if not convert_to_markdown else "markdown"),
                is_cloud=self.config.is_cloud,
                emoji=emoji,
                page_width=page_width,
                layout=layout,
            )
        except HTTPError:
            raise  # let decorator handle auth errors
        except Exception as e:
            logger.error(
                f"Error retrieving page content for page ID {page_id}: {str(e)}"
            )
            raise Exception(f"Error retrieving page content: {str(e)}") from e

    @handle_auth_errors("Confluence API")
    def get_page_ancestors(self, page_id: str) -> list[ConfluencePage]:
        """
        Get ancestors (parent pages) of a specific page.

        Args:
            page_id: The ID of the page to get ancestors for

        Returns:
            List of ConfluencePage models representing the
            ancestors in hierarchical order (immediate parent
            first, root ancestor last)

        Raises:
            MCPAtlassianAuthenticationError: If authentication
                fails with the Confluence API (401/403)
        """
        try:
            ancestors = self.confluence.get_page_ancestors(page_id)

            ancestor_models = []
            for ancestor in ancestors:
                page_model = ConfluencePage.from_api_response(
                    ancestor,
                    base_url=self.config.url,
                    include_body=False,
                )
                ancestor_models.append(page_model)

            return ancestor_models
        except HTTPError:
            raise  # let decorator handle auth errors
        except Exception as e:
            logger.error(f"Error fetching ancestors for page {page_id}: {str(e)}")
            logger.debug("Full exception details:", exc_info=True)
            return []

    def _get_page_emoji(self, page_id: str) -> str | None:
        """Get the page title emoji from content properties.

        The page emoji (icon shown in navigation) is stored as a content property
        with key 'emoji-title-published' or 'emoji-title-draft'.

        Args:
            page_id: The ID of the page

        Returns:
            The emoji character if set, None otherwise
        """
        try:
            # Use v2 API for OAuth authentication
            v2_adapter = self._v2_adapter
            if v2_adapter:
                return v2_adapter.get_page_emoji(page_id)

            # For token/basic auth, use v1 API via atlassian library
            properties = self.confluence.get_page_properties(page_id)
            if not properties:
                return None

            results = properties.get("results", [])
            for prop in results:
                key = prop.get("key", "")
                if key in ("emoji-title-published", "emoji-title-draft"):
                    value = prop.get("value", {})
                    return extract_emoji_from_property(value)

            return None

        except Exception as e:
            logger.debug(f"Error fetching emoji for page {page_id}: {str(e)}")
            return None

    def _set_single_property(
        self, page_id: str, property_key: str, value: str | None
    ) -> bool:
        """Set or remove a single page property via v1 API.

        Uses create (POST) for new properties and update (PUT) for existing ones.
        The v1 API requires a version number when updating existing properties.

        Args:
            page_id: The ID of the page
            property_key: The property key to set
            value: The value to set, or None to delete the property

        Returns:
            True if the operation succeeded, False otherwise
        """
        try:
            if value is None:
                # Delete the property
                try:
                    self.confluence.delete_page_property(page_id, property_key)
                except Exception as e:
                    # Property might not exist, which is fine
                    logger.debug(f"Could not delete property '{property_key}': {e}")
                return True

            # Check if the property already exists (need version for update)
            existing_version = None
            try:
                existing = self.confluence.get_page_property(page_id, property_key)
                if existing and isinstance(existing, dict):
                    existing_version = existing.get("version", {}).get("number")
            except Exception:  # noqa: S110
                # Property doesn't exist yet, that's fine - we'll create it
                pass

            property_data = {
                "key": property_key,
                "value": value,
            }

            if existing_version is not None:
                # Property exists - use PUT (update) with incremented version
                property_data["version"] = {"number": existing_version + 1}
                self.confluence.update_page_property(page_id, property_data)
            else:
                # Property doesn't exist - use POST (create)
                self.confluence.set_page_property(page_id, property_data)

            return True

        except Exception as e:
            logger.warning(
                f"Error setting property '{property_key}' for page {page_id}: {str(e)}"
            )
            return False

    def _set_page_emoji(self, page_id: str, emoji: str | None) -> bool:
        """Set or remove the page title emoji.

        The page emoji (icon shown in navigation) is stored as content properties.
        Both 'emoji-title-published' and 'emoji-title-draft' are set to ensure
        the emoji appears in both view and edit modes.

        Args:
            page_id: The ID of the page
            emoji: The emoji character to set, or None to remove the emoji

        Returns:
            True if the operation succeeded, False otherwise
        """
        try:
            # Use v2 API for OAuth authentication
            v2_adapter = self._v2_adapter
            if v2_adapter:
                return v2_adapter.set_page_emoji(page_id, emoji)

            # For token/basic auth, use v1 API via atlassian library
            # Convert emoji to hex code, or None to delete
            emoji_value = emoji_to_hex_id(emoji) if emoji else None

            # Set both published and draft properties
            published_ok = self._set_single_property(
                page_id, "emoji-title-published", emoji_value
            )
            draft_ok = self._set_single_property(
                page_id, "emoji-title-draft", emoji_value
            )

            if not published_ok:
                logger.warning(
                    f"Failed to set emoji-title-published for page {page_id}"
                )
            if not draft_ok:
                logger.warning(f"Failed to set emoji-title-draft for page {page_id}")

            return published_ok and draft_ok

        except Exception as e:
            logger.warning(f"Error setting emoji for page {page_id}: {str(e)}")
            return False

    def _read_width_state(self, page_id: str) -> dict[str, Any]:
        if not self.config.is_cloud:
            unavailable = {"state": "unsupported", "raw": None, "label": None}
            return layout_state(unavailable.copy(), unavailable.copy())
        adapter = self._v2_adapter or ConfluenceV2Adapter(
            self.confluence._session, self.confluence.url
        )
        states = []
        for scope in ("published", "draft"):
            try:
                states.append(
                    width_property(
                        adapter._get_property(page_id, f"content-appearance-{scope}")
                    )
                )
            except HTTPError as exc:
                if exc.response is not None and exc.response.status_code in (401, 403):
                    raise
                states.append({"state": "read_failed", "raw": None, "label": None})
            except (requests.RequestException, ValueError, TypeError, KeyError):
                states.append({"state": "read_failed", "raw": None, "label": None})
        return layout_state(*states)

    def _get_page_width(self, page_id: str) -> str | None:
        """Read legacy width with published precedence, never infer a default."""
        value = self._read_width_state(page_id)["page_width"]
        return value if isinstance(value, str) else None

    def _set_page_width(self, page_id: str, width: str | None) -> bool:
        """Set published width only, without changing the active draft."""
        result = self.set_page_width(page_id, width or "default")
        return bool(result["success"])

    @handle_auth_errors("Confluence API")
    def set_page_width(
        self, page_id: str, width: str, *, scope: str = "published"
    ) -> dict[str, Any]:
        """Write scoped Cloud width metadata and verify it with REST readback.

        Args:
            page_id: Page whose content must remain unchanged.
            width: narrow/default, wide/full-width, or max.
            scope: published, draft, or both. Default leaves active drafts alone.

        Returns:
            Per-scope write and readback results. This is not visual verification.
        """
        raw = normalize_width(width)
        if scope not in ("published", "draft", "both"):
            raise ValueError("scope must be published, draft, or both")
        if not self.config.is_cloud:
            raise ValueError("Page width properties are supported only on Cloud")
        adapter = self._v2_adapter or ConfluenceV2Adapter(
            self.confluence._session, self.confluence.url
        )
        scopes = ("published", "draft") if scope == "both" else (scope,)
        writes = {
            item: adapter._set_page_property(page_id, f"content-appearance-{item}", raw)
            for item in scopes
        }
        try:
            readback = self._read_width_state(page_id)
        except HTTPError:
            readback = layout_state(
                {"state": "read_failed", "raw": None, "label": None},
                {"state": "read_failed", "raw": None, "label": None},
            )
        verified = {
            item: readback[item]["state"] == "known" and readback[item]["raw"] == raw
            for item in scopes
        }
        success = all(writes.values()) and all(verified.values())
        return {
            "success": success,
            "partial_write": any(writes.values()) and not all(writes.values()),
            "writes": writes,
            "readback_verified": verified,
            "layout": readback,
            "rendered_verified": False,
        }

    @handle_auth_errors("Confluence API")
    def get_page_layout(self, page_id: str) -> dict[str, Any]:
        """Read width metadata and bounded storage/ADF layout evidence.

        Args:
            page_id: Page to inspect through supported REST APIs.

        Returns:
            Independent property/body states without claims about rendered layout.
        """
        result = self._read_width_state(page_id)
        result["content"] = {}
        formats = (
            ("storage", "atlas_doc_format") if self.config.is_cloud else ("storage",)
        )
        for representation in formats:
            try:
                if self.config.is_cloud:
                    response = self.confluence._session.get(
                        f"{self.confluence.url}/api/v2/pages/{page_id}",
                        params={"body-format": representation},
                    )
                    response.raise_for_status()
                    page = response.json()
                else:
                    page = self.confluence.get_page_by_id(
                        page_id, expand="body.storage"
                    )
                value = page.get("body", {}).get(representation, {}).get("value")
                if value is None:
                    evidence = {"state": "missing"}
                else:
                    evidence = (
                        inspect_storage(value)
                        if representation == "storage"
                        else inspect_adf(value)
                    )
            except HTTPError as exc:
                if exc.response is not None and exc.response.status_code in (401, 403):
                    raise
                evidence = {"state": "read_failed"}
            except (requests.RequestException, ValueError, TypeError, KeyError):
                evidence = {"state": "read_failed"}
            result["content"][representation] = evidence
        if not self.config.is_cloud:
            result["content"]["atlas_doc_format"] = {"state": "unsupported"}
        return result

    def get_page_by_title(
        self, space_key: str, title: str, *, convert_to_markdown: bool = True
    ) -> ConfluencePage | None:
        """
        Get a specific page by its title from a Confluence space.

        Args:
            space_key: The key of the space containing the page
            title: The title of the page to retrieve
            convert_to_markdown: When True, returns content in markdown format,
                               otherwise returns raw HTML (keyword-only)

        Returns:
            ConfluencePage model containing the page content and metadata, or None if not found
        """
        try:
            # Directly try to find the page by title
            page = self.confluence.get_page_by_title(
                space=space_key, title=title, expand="body.storage,version"
            )

            if not page:
                logger.warning(
                    f"Page '{title}' not found in space '{space_key}'. "
                    f"The space may be invalid, the page may not exist, or permissions may be insufficient."
                )
                return None

            try:
                content = page["body"]["storage"]["value"]
            except (KeyError, TypeError) as e:
                logger.warning(
                    f"Page {page.get('id', 'unknown')} missing body.storage.value: {e}"
                )
                content = ""
            processed_html, processed_markdown = self.preprocessor.process_html_content(
                content,
                space_key=space_key,
                confluence_client=self.confluence,
                content_id=str(page.get("id", "")),
            )

            # Use the appropriate content format based on the convert_to_markdown flag
            page_content = processed_markdown if convert_to_markdown else processed_html

            # Fetch page emoji and width from content properties
            emoji = self._get_page_emoji(str(page.get("id", "")))
            layout = self._read_width_state(str(page.get("id", "")))
            layout["content"] = {
                "storage": inspect_storage(content)
                if isinstance(content, str)
                else {"state": "missing"}
            }
            page_width = layout["page_width"]

            # Create and return the ConfluencePage model
            return ConfluencePage.from_api_response(
                page,
                base_url=self.config.url,
                include_body=True,
                # Override content with our processed version
                content_override=page_content,
                content_format="storage" if not convert_to_markdown else "markdown",
                is_cloud=self.config.is_cloud,
                emoji=emoji,
                page_width=page_width,
                layout=layout,
            )

        except KeyError as e:
            logger.error(f"Missing key in page data: {str(e)}")
            return None
        except requests.RequestException as e:
            logger.error(f"Network error when fetching page: {str(e)}")
            return None
        except (ValueError, TypeError) as e:
            logger.error(f"Error processing page data: {str(e)}")
            return None
        except Exception as e:  # noqa: BLE001 - Intentional fallback with full logging
            logger.error(f"Unexpected error fetching page: {str(e)}")
            # Log the full traceback at debug level for troubleshooting
            logger.debug("Full exception details:", exc_info=True)
            return None

    def get_space_pages(
        self,
        space_key: str,
        start: int = 0,
        limit: int = 10,
        *,
        convert_to_markdown: bool = True,
    ) -> list[ConfluencePage]:
        """
        Get all pages from a specific space.

        Args:
            space_key: The key of the space to get pages from
            start: The starting index for pagination
            limit: Maximum number of pages to return
            convert_to_markdown: When True, returns content in markdown format,
                               otherwise returns raw HTML (keyword-only)

        Returns:
            List of ConfluencePage models containing page content and metadata
        """
        pages = self.confluence.get_all_pages_from_space(
            space=space_key, start=start, limit=limit, expand="body.storage"
        )

        page_models = []
        for page in pages:
            try:
                content = page["body"]["storage"]["value"]
            except (KeyError, TypeError) as e:
                logger.warning(
                    f"Page {page.get('id', 'unknown')} missing body.storage.value: {e}"
                )
                content = ""
            processed_html, processed_markdown = self.preprocessor.process_html_content(
                content,
                space_key=space_key,
                confluence_client=self.confluence,
                content_id=str(page.get("id", "")),
            )

            # Use the appropriate content format based on the convert_to_markdown flag
            page_content = processed_markdown if convert_to_markdown else processed_html

            # Ensure space information is included
            if "space" not in page:
                page["space"] = {
                    "key": space_key,
                    "name": space_key,  # Use space_key as name if not available
                }

            # Create the ConfluencePage model
            page_model = ConfluencePage.from_api_response(
                page,
                base_url=self.config.url,
                include_body=True,
                # Override content with our processed version
                content_override=page_content,
                content_format="storage" if not convert_to_markdown else "markdown",
                is_cloud=self.config.is_cloud,
            )

            page_models.append(page_model)

        return page_models

    def create_page(
        self,
        space_key: str,
        title: str,
        body: str,
        parent_id: str | None = None,
        *,
        is_markdown: bool = True,
        enable_heading_anchors: bool = False,
        content_representation: str | None = None,
        emoji: str | None = None,
        page_width: str | None = None,
    ) -> ConfluencePage:
        """
        Create a new page in a Confluence space.

        Args:
            space_key: The key of the space to create the page in
            title: The title of the new page
            body: The content of the page (markdown, wiki markup, or storage format)
            parent_id: Optional ID of a parent page
            is_markdown: Whether the body content is in markdown format (default: True, keyword-only)
            enable_heading_anchors: Whether to enable automatic heading anchor generation (default: False, keyword-only)
            content_representation: Content format when is_markdown=False ('wiki' or 'storage', keyword-only)
            emoji: Optional emoji character for the page title icon (keyword-only)
            page_width: Cloud published width. narrow=default, wide=full-width, max=max.

        Returns:
            ConfluencePage model containing the new page's data

        Raises:
            Exception: If there is an error creating the page
        """
        try:
            if page_width is not None:
                page_width = normalize_width(page_width or "default")
                if not self.config.is_cloud:
                    raise ValueError(
                        "Page width properties are supported only on Cloud"
                    )
            # Determine body and representation based on content type
            if is_markdown:
                # Convert markdown to Confluence storage format
                final_body = self.preprocessor.markdown_to_confluence_storage(
                    body, enable_heading_anchors=enable_heading_anchors
                )
                representation = "storage"
            else:
                # Use body as-is with specified representation
                final_body = body
                representation = content_representation or "storage"

            # Use v2 API for OAuth authentication, v1 API for token/basic auth
            v2_adapter = self._v2_adapter
            if v2_adapter:
                logger.debug(
                    f"Using v2 API for OAuth authentication to create page '{title}'"
                )
                result = v2_adapter.create_page(
                    space_key=space_key,
                    title=title,
                    body=final_body,
                    parent_id=parent_id,
                    representation=representation,
                )
            else:
                logger.debug(
                    f"Using v1 API for token/basic authentication to create page '{title}'"
                )
                result = self.confluence.create_page(
                    space=space_key,
                    title=title,
                    body=final_body,
                    parent_id=parent_id,
                    representation=representation,
                )

            # Get the new page content
            page_id = result.get("id")
            if not page_id:
                raise ValueError("Create page response did not contain an ID")

            # Set the page emoji if provided
            if emoji:
                self._set_page_emoji(page_id, emoji)

            # Set the page width if provided
            if page_width is not None and not self._set_page_width(page_id, page_width):
                raise ValueError(
                    "Page content was created, but width write/readback failed. "
                    "Do not retry page creation; inspect layout instead."
                )

            return self.get_page_content(page_id)
        except Exception as e:
            logger.error(
                f"Error creating page '{title}' in space {space_key}: {str(e)}"
            )
            raise Exception(
                f"Failed to create page '{title}' in space {space_key}: {str(e)}"
            ) from e

    def update_page(
        self,
        page_id: str,
        title: str | None,
        body: str | None,
        *,
        expected_version: int | None = None,
        old_text: str | None = None,
        new_text: str | None = None,
        is_minor_edit: bool = False,
        version_comment: str = "",
        is_markdown: bool = True,
        parent_id: str | None = None,
        enable_heading_anchors: bool = False,
        content_representation: str | None = None,
        emoji: str | None = None,
        page_width: str | None = None,
    ) -> ConfluencePage:
        """
        Update an existing page in Confluence.

        Args:
            page_id: The ID of the page to update
            title: New title, or None to keep the current title.
            body: New content, or None when replacing an exact storage string.
            expected_version: Refuse to update unless the page has this version.
            old_text: Exact storage text to replace once (requires expected_version).
            new_text: Replacement storage text (requires old_text).
            is_minor_edit: Whether this is a minor edit (keyword-only)
            version_comment: Optional comment for this version (keyword-only)
            is_markdown: Whether the body content is in markdown format (default: True, keyword-only)
            parent_id: Optional new parent page ID (keyword-only)
            enable_heading_anchors: Whether to enable automatic heading anchor generation (default: False, keyword-only)
            content_representation: Content format when is_markdown=False ('wiki' or 'storage', keyword-only)
            emoji: Optional emoji character for the page title icon (keyword-only). Pass empty string to remove emoji.
            page_width: Cloud published width. narrow=default, wide=full-width,
                max=max. Omit to preserve; empty resets published width to default.

        Returns:
            ConfluencePage model containing the updated page's data

        Raises:
            Exception: If there is an error updating the page
        """
        try:
            if old_text is not None:
                if (
                    body is not None
                    or new_text is None
                    or not old_text
                    or expected_version is None
                ):
                    raise ValueError(
                        "Exact replacement requires old_text, new_text and "
                        "expected_version, and no body"
                    )
            elif body is None or new_text is not None:
                raise ValueError("Provide body or an exact replacement, not both")
            if expected_version is not None and expected_version < 1:
                raise ValueError("expected_version must be positive")
            if page_width is not None:
                page_width = normalize_width(page_width or "default")
                if not self.config.is_cloud:
                    raise ValueError(
                        "Page width properties are supported only on Cloud"
                    )

            v2_adapter = self._v2_adapter
            current = None
            if title is None or expected_version is not None:
                if v2_adapter:
                    current = v2_adapter.get_page(
                        page_id=page_id, expand="body.storage,version,space"
                    )
                else:
                    current = self.confluence.get_page_by_id(
                        page_id=page_id, expand="body.storage,version"
                    )
                if not isinstance(current, dict):
                    raise ValueError(f"Could not read page {page_id}")
                if expected_version is not None:
                    actual_version = current.get("version", {}).get("number")
                    if actual_version != expected_version:
                        raise ValueError(
                            f"Page version mismatch: expected {expected_version}, "
                            f"found {actual_version}"
                        )
                if title is None:
                    title = current["title"]

            if old_text is not None:
                if current is None or new_text is None:
                    raise ValueError("Exact replacement requires current content")
                storage = current["body"]["storage"]["value"]
                if storage.count(old_text) != 1:
                    raise ValueError("Exact text must occur once in storage content")
                body = storage.replace(old_text, new_text, 1)
                is_markdown = False
                content_representation = "storage"

            if body is None or not isinstance(title, str):
                raise ValueError("Page content and title must be strings")
            if is_markdown:
                final_body = self.preprocessor.markdown_to_confluence_storage(
                    body, enable_heading_anchors=enable_heading_anchors
                )
                representation = "storage"
            else:
                final_body = body
                representation = content_representation or "storage"

            logger.debug(f"Updating page {page_id} with title '{title}'")

            # The upstream update helper forces fixed-width metadata. Omit it
            # and let Confluence reject a stale version in the PUT instead.
            if v2_adapter:
                v2_adapter.update_page(
                    page_id=page_id,
                    title=title,
                    body=final_body,
                    representation=representation,
                    version_comment=version_comment,
                    expected_version=expected_version,
                )
            else:
                if current is None:
                    current = self.confluence.get_page_by_id(
                        page_id=page_id, expand="version"
                    )
                version = current["version"]["number"]
                data: dict[str, Any] = {
                    "id": page_id,
                    "type": "page",
                    "title": title,
                    "body": {
                        representation: {
                            "value": final_body,
                            "representation": representation,
                        }
                    },
                    "version": {"number": version + 1, "minorEdit": is_minor_edit},
                }
                if version_comment:
                    data["version"]["message"] = version_comment
                if parent_id:
                    data["ancestors"] = [{"type": "page", "id": parent_id}]
                self.confluence.put(
                    f"rest/api/content/{page_id}",
                    data=data,
                    params={"status": "current"},
                )

            # Set or remove the page emoji if provided
            if emoji is not None:
                # Empty string means remove emoji, otherwise set it
                emoji_to_set = emoji if emoji else None
                self._set_page_emoji(page_id, emoji_to_set)

            # Set or remove the page width if provided
            if page_width is not None:
                if not self._set_page_width(page_id, page_width):
                    raise ValueError(
                        "Page content was updated, but width write/readback failed. "
                        "Inspect layout before retrying."
                    )

            # After update, refresh the page data
            return self.get_page_content(page_id)
        except Exception as e:
            logger.error(f"Error updating page {page_id}: {str(e)}")
            raise Exception(f"Failed to update page {page_id}: {str(e)}") from e

    def get_page_children(
        self,
        page_id: str,
        start: int = 0,
        limit: int = 25,
        expand: str = "version",
        *,
        convert_to_markdown: bool = True,
        include_folders: bool = True,
    ) -> list[ConfluencePage]:
        """
        Get child pages and folders of a specific Confluence page.

        Args:
            page_id: The ID of the parent page
            start: The starting index for pagination
            limit: Maximum number of child items to return
            expand: Fields to expand in the response
            convert_to_markdown: When True, returns content in markdown format,
                               otherwise returns raw HTML (keyword-only)
            include_folders: When True, also returns child folders (keyword-only)

        Returns:
            List of ConfluencePage models containing the child pages and folders
        """
        try:
            # Use the Atlassian Python API's get_page_child_by_type method
            # First, get child pages
            page_results = self.confluence.get_page_child_by_type(
                page_id=page_id, type="page", start=start, limit=limit, expand=expand
            )

            # Handle both pagination modes for pages
            if isinstance(page_results, dict) and "results" in page_results:
                child_items = page_results.get("results", [])
            else:
                child_items = page_results or []

            # Also get child folders if requested
            if include_folders:
                try:
                    folder_results = self.confluence.get_page_child_by_type(
                        page_id=page_id,
                        type="folder",
                        start=start,
                        limit=limit,
                        expand=expand,
                    )

                    # Handle both pagination modes for folders
                    if isinstance(folder_results, dict) and "results" in folder_results:
                        child_folders = folder_results.get("results", [])
                    else:
                        child_folders = folder_results or []

                    # Combine pages and folders
                    child_items = child_items + child_folders
                except Exception as folder_err:
                    # Log but don't fail if folder fetching fails
                    # (e.g., older Confluence versions might not support folders)
                    logger.debug(
                        f"Could not fetch child folders for page {page_id}: {folder_err}"
                    )

            # Process results
            page_models = []
            space_key = ""

            # Get space key from the first result if available
            if child_items and "space" in child_items[0]:
                space_key = child_items[0].get("space", {}).get("key", "")

            # Process each child item (page or folder)
            for item in child_items:
                # Only process content if we have "body" expanded
                content_override = None
                if "body" in item and convert_to_markdown:
                    content = item.get("body", {}).get("storage", {}).get("value", "")
                    if content:
                        _, processed_markdown = self.preprocessor.process_html_content(
                            content,
                            space_key=space_key,
                            confluence_client=self.confluence,
                            content_id=str(item.get("id", "")),
                        )
                        content_override = processed_markdown

                # Create the page model (works for both pages and folders)
                page_model = ConfluencePage.from_api_response(
                    item,
                    base_url=self.config.url,
                    include_body=True,
                    content_override=content_override,
                    content_format="markdown" if convert_to_markdown else "storage",
                )

                page_models.append(page_model)

            return page_models

        except Exception as e:
            logger.error(f"Error fetching child pages for page {page_id}: {str(e)}")
            logger.debug("Full exception details:", exc_info=True)
            return []

    @handle_auth_errors("Confluence API")
    def get_space_page_tree(
        self,
        space_key: str,
        limit: int = 500,
    ) -> dict:
        """Get hierarchical page tree for a space.

        Returns a flat list of pages with parent_id and position attributes,
        allowing the AI to build custom views or filter as needed. This is
        more token-efficient than ASCII art and easier to process.

        Uses manual pagination via get_all_pages_from_space_raw() to reliably
        fetch all pages and detect truncation via _links.next, matching the
        pagination pattern in search.py.

        Args:
            space_key: The key of the space
            limit: Maximum number of pages to fetch (default: 500)

        Returns:
            Dictionary with:
            - space_key: The space key
            - total_pages: Total number of pages in the response
            - has_more: Whether more pages exist beyond the limit
            - pages: List of dicts with id, title, parent_id, position, depth
            - Note: parent_id is None for root pages

        Raises:
            Exception: If there is an error fetching pages
        """
        try:
            # Paginate using the raw API to access _links.next for reliable
            # truncation detection. The higher-level get_all_pages_from_space()
            # has a broken termination condition when limit > server-side cap.
            page_size = 200
            start = 0
            all_pages: list[dict[str, Any]] = []
            next_link: str | None = None

            while len(all_pages) < limit:
                fetch_limit = min(page_size, limit - len(all_pages))
                response = self.confluence.get_all_pages_from_space_raw(
                    space=space_key,
                    start=start,
                    limit=fetch_limit,
                    expand="ancestors",
                )
                batch = response.get("results", [])
                all_pages.extend(batch)

                next_link = response.get("_links", {}).get("next")
                if not batch or not next_link:
                    break
                start += len(batch)

            has_more = len(all_pages) >= limit and bool(next_link)

            if not all_pages:
                return {
                    "space_key": space_key,
                    "total_pages": 0,
                    "has_more": False,
                    "pages": [],
                }

            # Build flat list with parent_id and depth
            result_pages = []

            for page in all_pages:
                page_id = page.get("id")
                title = page.get("title", "Untitled")

                # Position is auto-included via extensions in the v1 API
                position = page.get("extensions", {}).get("position")

                # Determine parent and depth from ancestors
                ancestors = page.get("ancestors", [])
                if ancestors:
                    parent_id = ancestors[-1].get("id")
                    depth = len(ancestors)
                else:
                    parent_id = None
                    depth = 0

                result_pages.append(
                    {
                        "id": page_id,
                        "title": title,
                        "parent_id": parent_id,
                        "position": position,
                        "depth": depth,
                    }
                )

            # Sort by depth first (breadth-first), then by position and title.
            # Confluence may return mixed types for position/title on some instances,
            # so normalize before comparison.
            result_pages.sort(
                key=lambda p: (
                    p["depth"],
                    _page_tree_sort_position(p["position"]),
                    _page_tree_sort_title(p["title"]),
                )
            )

            result: dict[str, Any] = {
                "space_key": space_key,
                "total_pages": len(result_pages),
                "has_more": has_more,
                "pages": result_pages,
            }
            if has_more:
                result["next_start"] = start
            return result

        except HTTPError:
            raise  # let @handle_auth_errors decorator handle auth errors
        except Exception as e:
            logger.error(f"Error fetching page tree for space '{space_key}': {e}")
            raise Exception(f"Failed to fetch page tree: {e}") from e

    def delete_page(self, page_id: str) -> bool:
        """
        Delete a Confluence page by its ID.

        Args:
            page_id: The ID of the page to delete

        Returns:
            Boolean indicating success (True) or failure (False)

        Raises:
            Exception: If there is an error deleting the page
        """
        try:
            logger.debug(f"Deleting page {page_id}")

            # Use v2 API for OAuth authentication, v1 API for token/basic auth
            v2_adapter = self._v2_adapter
            if v2_adapter:
                logger.debug(
                    f"Using v2 API for OAuth authentication to delete page '{page_id}'"
                )
                return v2_adapter.delete_page(page_id=page_id)
            else:
                logger.debug(
                    f"Using v1 API for token/basic authentication to delete page '{page_id}'"
                )
                response = self.confluence.remove_page(page_id=page_id)

                # The Atlassian library's remove_page returns the raw response from
                # the REST API call. For a successful deletion, we should get a
                # response object, but it might be empty (HTTP 204 No Content).
                # For REST DELETE operations, a success typically returns 204 or 200

                # Check if we got a response object
                if isinstance(response, requests.Response):
                    # Check if status code indicates success (2xx)
                    success = 200 <= response.status_code < 300
                    logger.debug(
                        f"Delete page {page_id} returned status code {response.status_code}"
                    )
                    return success
                # If it's not a response object but truthy (like True), consider it a success
                elif response:
                    return True
                # Default to true since no exception was raised
                # This is safer than returning false when we don't know what happened
                return True

        except Exception as e:
            logger.error(f"Error deleting page {page_id}: {str(e)}")
            raise Exception(f"Failed to delete page {page_id}: {str(e)}") from e

    @handle_auth_errors("Confluence API")
    def get_page_history(
        self,
        page_id: str,
        version: int,
        convert_to_markdown: bool = True,
    ) -> ConfluencePage:
        """
        Get the history of a specific page.

        Args:
            page_id: The ID of the page to get history for
            version: The version to get history for
            convert_to_markdown: When True, returns content in
                markdown format

        Returns:
            ConfluencePage model containing the page history

        Raises:
            MCPAtlassianAuthenticationError: If authentication
                fails with the Confluence API (401/403)
            Exception: If there is an error getting page history
        """
        try:
            v2_adapter = self._v2_adapter
            if v2_adapter:
                logger.debug(
                    "Using v2 API for OAuth authentication"
                    " to get page history for"
                    f" '{page_id}' version {version}"
                )
                page = v2_adapter.get_page_by_version(
                    page_id=page_id,
                    version=version,
                    expand="body.storage,version,space,children.attachment",
                )
            else:
                logger.debug(
                    "Using v1 API for token/basic"
                    " authentication to get page history"
                    f" for '{page_id}'"
                )
                page = self.confluence.get_page_by_id(
                    page_id=page_id,
                    status="historical",
                    version=version,
                    expand="body.storage,version,space,children.attachment",
                )

            if isinstance(page, str):
                error_msg = f"API returned error response: {page[:500]}"
                raise Exception(error_msg)

            try:
                content = page["body"]["storage"]["value"]
            except (KeyError, TypeError) as e:
                logger.warning(
                    f"Page {page.get('id', 'unknown')} missing body.storage.value: {e}"
                )
                content = ""

            space_key = page.get("space", {}).get("key", "")
            page_attachments = (
                page.get("children", {}).get("attachment", {}).get("results", [])
            )
            processed_html, processed_markdown = self.preprocessor.process_html_content(
                content,
                space_key=space_key,
                confluence_client=self.confluence,
                content_id=str(page.get("id", "")),
                attachments=page_attachments,
            )

            page_content = processed_markdown if convert_to_markdown else processed_html

            emoji = self._get_page_emoji(page_id)
            return ConfluencePage.from_api_response(
                page,
                base_url=self.config.url,
                include_body=True,
                content_override=page_content,
                content_format=("markdown" if convert_to_markdown else "storage"),
                is_cloud=self.config.is_cloud,
                emoji=emoji,
            )
        except HTTPError:
            raise  # let decorator handle auth errors
        except Exception as e:
            logger.error(f"Error getting page history for page {page_id}: {str(e)}")
            raise Exception(f"Error getting page history: {str(e)}") from e

    @handle_auth_errors("Confluence API")
    def move_page(
        self,
        page_id: str,
        target_parent_id: str | None = None,
        target_space_key: str | None = None,
        position: str = "append",
    ) -> ConfluencePage:
        """Move a page to a new parent or space.

        Args:
            page_id: ID of the page to move.
            target_parent_id: Target parent page ID. If omitted with
                target_space_key, moves page to root of target space.
            target_space_key: Target space key for cross-space moves.
            position: Position relative to target ("append", "above",
                or "below").

        Returns:
            Updated ConfluencePage after move.

        Raises:
            ValueError: If neither target_parent_id nor target_space_key
                is provided.
            MCPAtlassianAuthenticationError: If authentication fails.
        """
        if not target_parent_id and not target_space_key:
            raise ValueError(
                "At least one of target_parent_id or target_space_key must be provided."
            )

        try:
            # Use v2 adapter for OAuth authentication
            v2_adapter = self._v2_adapter
            if v2_adapter:
                logger.debug(
                    f"Using REST API for OAuth authentication to move page '{page_id}'"
                )
                v2_adapter.move_page(
                    page_id=page_id,
                    position=position,
                    target_id=target_parent_id,
                )
            else:
                # Determine space_key for the move_page call
                if target_space_key:
                    space_key = target_space_key
                else:
                    # Look up the target parent's space key
                    target_page = self.confluence.get_page_by_id(target_parent_id)
                    space_key = target_page.get("space", {}).get("key", "")

                self.confluence.move_page(
                    space_key,
                    page_id,
                    target_id=target_parent_id,
                    position=position,
                )

            # Re-fetch the page to return updated state
            return self.get_page_content(page_id)
        except HTTPError:
            raise  # let decorator handle auth errors
        except ValueError:
            raise  # re-raise our own validation error
        except Exception as e:
            logger.error(f"Error moving page {page_id}: {str(e)}")
            raise Exception(f"Failed to move page {page_id}: {str(e)}") from e

    @handle_auth_errors("Confluence API")
    def get_page_version_diff(
        self,
        page_id: str,
        from_version: int,
        to_version: int,
    ) -> dict[str, Any]:
        """Get unified diff between two versions of a page.

        Args:
            page_id: Page ID.
            from_version: Source version number.
            to_version: Target version number.

        Returns:
            Dict with page_id, title, from_version, to_version,
            and diff string.

        Raises:
            MCPAtlassianAuthenticationError: If authentication fails.
        """
        from_page = self.get_page_history(page_id=page_id, version=from_version)
        to_page = self.get_page_history(page_id=page_id, version=to_version)

        from_lines = (from_page.content or "").splitlines()
        to_lines = (to_page.content or "").splitlines()

        diff_lines = difflib.unified_diff(
            from_lines,
            to_lines,
            fromfile=f"v{from_version}",
            tofile=f"v{to_version}",
            lineterm="",
        )
        diff_string = "\n".join(diff_lines)

        return {
            "page_id": page_id,
            "title": to_page.title,
            "from_version": from_version,
            "to_version": to_version,
            "diff": diff_string,
        }
