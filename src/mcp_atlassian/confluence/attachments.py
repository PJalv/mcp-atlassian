"""Attachment operations for Confluence API."""

import logging
import os
from pathlib import Path
from typing import Any

from ..models.confluence.common import ConfluenceAttachment

logger = logging.getLogger("mcp-atlassian")

class AttachmentsMixin:
    """Mixin for Confluence attachment operations."""
    confluence: Any  # The Confluence client/session
    config: Any      # The config object

    def download_attachment(self, url: str, target_path: str) -> bool:
        """
        Download a Confluence attachment to the specified path.

        Args:
            url: The URL of the attachment to download
            target_path: The path where the attachment should be saved

        Returns:
            True if successful, False otherwise
        """
        if not url:
            logger.error("No URL provided for attachment download")
            return False

        try:
            if not os.path.isabs(target_path):
                target_path = os.path.abspath(target_path)

            logger.info(f"Downloading attachment from {url} to {target_path}")
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            # Use the Confluence session to download the file
            response = self.confluence._session.get(url, stream=True)
            response.raise_for_status()

            with open(target_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            if os.path.exists(target_path):
                file_size = os.path.getsize(target_path)
                logger.info(
                    f"Successfully downloaded attachment to {target_path} (size: {file_size} bytes)"
                )
                return True
            else:
                logger.error(f"File was not created at {target_path}")
                return False
        except Exception as e:
            logger.error(f"Error downloading attachment: {str(e)}")
            return False

    def download_page_attachments(self, page_id: str, target_dir: str) -> dict[str, Any]:
        """
        Download all attachments for a Confluence page.

        Args:
            page_id: The Confluence page ID
            target_dir: The directory where attachments should be saved

        Returns:
            A dictionary with download results
        """
        if not os.path.isabs(target_dir):
            target_dir = os.path.abspath(target_dir)
        logger.info(f"Downloading attachments for page {page_id} to directory: {target_dir}")
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)

        # Get the page with attachments expanded
        page = self.confluence.get_page_by_id(
            page_id=page_id, expand="children.attachment"
        )
        attachments_data = (
            page.get("children", {}).get("attachment", {}).get("results", [])
        )
        if not attachments_data:
            return {
                "success": True,
                "message": f"No attachments found for page {page_id}",
                "downloaded": [],
                "failed": [],
            }
        attachments = [ConfluenceAttachment.from_api_response(a) for a in attachments_data]
        downloaded = []
        failed = []
        for attachment in attachments:
            # Use the model's method to get the full download URL
            url = attachment.get_download_url(self.config.url)
            if not url:
                logger.warning(f"No download URL for attachment {getattr(attachment, 'title', None)}")
                failed.append({"filename": getattr(attachment, "title", None), "error": "No URL available"})
                continue
            safe_filename = Path(getattr(attachment, "title", "attachment")).name
            file_path = target_path / safe_filename
            success = self.download_attachment(url, str(file_path))
            if success:
                downloaded.append({
                    "filename": safe_filename,
                    "path": str(file_path),
                    "size": getattr(attachment, "file_size", None),
                })
            else:
                failed.append({"filename": safe_filename, "error": "Download failed"})
        return {
            "success": True,
            "page_id": page_id,
            "total": len(attachments),
            "downloaded": downloaded,
            "failed": failed,
        }
