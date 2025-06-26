"""Media routes for the DocImprover application."""

import os
import logging
from typing import Union, Tuple, Any

from flask import Blueprint, send_file, current_app as app

# Configure logger
logger = logging.getLogger(__name__)

# Create a blueprint for media routes
media_bp = Blueprint('media', __name__)


@media_bp.route('/media/<session_id>/<path:filepath>')
def serve_media(session_id: str, filepath: str) -> Union[Any, Tuple[str, int]]:
    """Serve media files stored in the user's session directory.
    
    This endpoint provides access to media files (primarily images) that were extracted
    from uploaded DOCX documents and are referenced in the rendered Markdown content.
    Security measures prevent directory traversal attacks.
    
    Args:
        session_id: The unique session identifier
        filepath: The relative path to the media file
        
    Returns:
        Union[Any, Tuple[str, int]]: The file content or an error with status code
    """
    try:
        # Security check: ensure path is not attempting to traverse directories
        if '..' in filepath or filepath.startswith('/'):
            logger.warning(f"Rejected suspicious media path: {filepath}")
            return "Not Found", 404
            
        session_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        media_path = os.path.join(session_dir, 'media', filepath)
        
        if not os.path.exists(media_path) or not os.path.isfile(media_path):
            logger.warning(f"Media file not found: {media_path}")
            return "Not Found", 404
            
        return send_file(media_path)
    except Exception as e:
        logger.error(f"Error serving media: {e}")
        return "Error serving media", 500
