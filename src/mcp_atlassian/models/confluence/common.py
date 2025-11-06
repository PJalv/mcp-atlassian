"""
Common Confluence entity models.
This module provides Pydantic models for common Confluence entities like users
and attachments.
"""

import logging
import warnings
from typing import Any

from ..base import ApiModel
from ..constants import (
    UNASSIGNED,
)

logger = logging.getLogger("mcp-atlassian")


class ConfluenceUser(ApiModel):
    """
    Model representing a Confluence user.
    """

    account_id: str | None = None
    display_name: str = UNASSIGNED
    email: str | None = None
    profile_picture: str | None = None
    is_active: bool = True
    locale: str | None = None

    @property
    def name(self) -> str:
        """
        Alias for display_name to maintain compatibility with tests.

        Deprecated: Use display_name instead.
        """
        warnings.warn(
            "The 'name' property is deprecated. Use 'display_name' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.display_name

    @classmethod
    def from_api_response(cls, data: dict[str, Any], **kwargs: Any) -> "ConfluenceUser":
        """
        Create a ConfluenceUser from a Confluence API response.

        Args:
            data: The user data from the Confluence API

        Returns:
            A ConfluenceUser instance
        """
        if not data:
            return cls()

        profile_pic = None
        if pic_data := data.get("profilePicture"):
            # Use the full path to the profile picture
            profile_pic = pic_data.get("path")

        return cls(
            account_id=data.get("accountId"),
            display_name=data.get("displayName", UNASSIGNED),
            email=data.get("email"),
            profile_picture=profile_pic,
            is_active=data.get("accountStatus") == "active",
            locale=data.get("locale"),
        )

    def to_simplified_dict(self) -> dict[str, Any]:
        """Convert to simplified dictionary for API response."""
        return {
            "display_name": self.display_name,
            "email": self.email,
            "profile_picture": self.profile_picture,
        }


from pydantic import ConfigDict
class ConfluenceAttachment(ApiModel):
    """
    Model representing a Confluence attachment.
    """

    id: str | None = None
    type: str | None = None
    status: str | None = None
    title: str | None = None
    media_type: str | None = None
    file_size: int | None = None
    download_url: str | None = None  # direct download URL (if present)
    relative_path: str | None = None  # relative download path (if present)
    model_config = ConfigDict(extra="allow")

    @classmethod
    def from_api_response(
        cls, data: dict[str, Any], **kwargs: Any
    ) -> "ConfluenceAttachment":
        """
        Create a ConfluenceAttachment from a Confluence API response.

        Args:
            data: The attachment data from the Confluence API

        Returns:
            A ConfluenceAttachment instance
        """
        if not data:
            return cls()

        # Try to extract download URL and relative path
        logger.debug(f"from_api_response: incoming data={data}")
        download_url = None
        relative_path = None
        # Cloud/Server: _links.download is a relative path
        if "_links" in data and "download" in data["_links"]:
            relative_path = data["_links"]["download"]
        # Some APIs may provide an absolute URL
        if "_links" in data and "self" in data["_links"]:
            # Not always a download URL, but keep for reference
            download_url = data["_links"].get("self")
        # Some APIs may provide a direct download link
        if "_expandable" in data and "content" in data["_expandable"]:
            # Not a URL, but keep for future
            pass
        logger.debug(f"from_api_response: extracted download_url={download_url}, relative_path={relative_path}")
        return cls(
            id=data.get("id"),
            type=data.get("type"),
            status=data.get("status"),
            title=data.get("title"),
            media_type=data.get("extensions", {}).get("mediaType"),
            file_size=data.get("extensions", {}).get("fileSize"),
            download_url=download_url,
            relative_path=relative_path,
        )

    def get_download_url(self, base_url: str) -> str | None:
        """
        Get the full download URL for this attachment.
        Args:
            base_url: The base URL of the Confluence instance
        Returns:
            The full download URL, or None if not available
        """
        logger.debug(f"get_download_url: download_url={self.download_url}, relative_path={self.relative_path}, base_url={base_url}")
        if self.relative_path:
            return base_url.rstrip("/") + self.relative_path
        if self.download_url and self.download_url.startswith("http"):
            return self.download_url
        return None

    def to_simplified_dict(self) -> dict[str, Any]:
        """Convert to simplified dictionary for API response."""
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status,
            "title": self.title,
            "media_type": self.media_type,
            "file_size": self.file_size,
            "download_url": self.get_download_url("") if self.download_url or self.relative_path else None,
        }
