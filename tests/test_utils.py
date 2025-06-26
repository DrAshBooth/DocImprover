"""Tests for utility functions in the doc_improver application."""
import os
import pytest
import tempfile
import shutil
from pathlib import Path
import re
from uuid import UUID

from doc_improver.utils.file_helpers import (
    get_session_id, ensure_session_dir, validate_docx_file,
    copy_files_recursively, rewrite_markdown_image_paths
)

def test_get_session_id(app, client):
    """Test that get_session_id returns a valid UUID."""
    # Use the app context for testing
    with app.test_request_context():
        # Call get_session_id directly
        session_id = get_session_id()
        
        # Verify it's a valid UUID
        try:
            UUID(session_id, version=4)
            assert True
        except ValueError:
            assert False, f"Generated session ID {session_id} is not a valid UUID"

def test_ensure_session_dir(app, tmp_path):
    """Test that ensure_session_dir creates and returns a valid directory."""
    # Set up
    session_id = "test-session-id"
    
    # Override app config to use tmp_path
    app.config['UPLOAD_FOLDER'] = str(tmp_path / "uploads")
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    # Test function
    session_dir = ensure_session_dir(session_id)
    
    # Verify
    assert os.path.exists(session_dir)
    assert os.path.isdir(session_dir)
    assert os.path.basename(os.path.dirname(session_dir)) == "uploads"
    assert os.path.basename(session_dir) == session_id

def test_validate_docx_file():
    """Test validation of DOCX files."""
    # Valid DOCX
    class MockValidFile:
        filename = "test.docx"
    
    # Invalid extension
    class MockInvalidExtension:
        filename = "test.txt"
    
    # Empty filename
    class MockEmptyFilename:
        filename = ""
    
    assert validate_docx_file(MockValidFile()) is None
    assert "Please upload a Word document" in validate_docx_file(MockInvalidExtension())
    assert "No file selected" in validate_docx_file(MockEmptyFilename())

def test_copy_files_recursively(tmp_path):
    """Test recursive file copying."""
    # Set up source directory with nested files
    src_dir = tmp_path / "source"
    src_dir.mkdir(exist_ok=True)
    
    # Create source files
    (src_dir / "file1.txt").write_text("Test file 1")
    (src_dir / "file2.txt").write_text("Test file 2")
    
    # Create nested directory with files
    nested_dir = src_dir / "nested"
    nested_dir.mkdir(exist_ok=True)
    (nested_dir / "nested_file.txt").write_text("Nested file")
    
    # Create media directory to test flattening
    media_dir = src_dir / "media"
    media_dir.mkdir(exist_ok=True)
    (media_dir / "media_file.jpg").write_text("Media file content")
    
    # Create nested media directory to test flattening
    nested_media = media_dir / "media"
    nested_media.mkdir(exist_ok=True)
    (nested_media / "double_nested.jpg").write_text("Double nested content")
    
    # Create destination directory
    dest_dir = tmp_path / "destination"
    dest_dir.mkdir(exist_ok=True)
    
    # Test function
    copy_files_recursively(str(src_dir), str(dest_dir))
    
    # Verify files were copied
    assert os.path.exists(dest_dir / "file1.txt")
    assert os.path.exists(dest_dir / "file2.txt")
    assert os.path.exists(dest_dir / "nested" / "nested_file.txt")
    
    # Verify media flattening worked
    assert os.path.exists(dest_dir / "media_file.jpg")
    assert os.path.exists(dest_dir / "double_nested.jpg")
    
    # Verify content was preserved
    assert (dest_dir / "file1.txt").read_text() == "Test file 1"
    assert (dest_dir / "file2.txt").read_text() == "Test file 2"
    assert (dest_dir / "nested" / "nested_file.txt").read_text() == "Nested file"

def test_rewrite_markdown_image_paths():
    """Test rewriting of image paths in Markdown."""
    session_id = "test-session"
    
    # Test standard markdown image syntax
    markdown = "Here's an image: ![Alt text](/absolute/path/to/media/image.png)"
    rewritten = rewrite_markdown_image_paths(markdown, session_id)
    assert f"/media/{session_id}/image.png" in rewritten
    assert "/absolute/path/to/media/image.png" not in rewritten
    
    # Test multiple images
    markdown = (
        "Image 1: ![](media/img1.jpg)\n"
        "Image 2: ![Caption](/var/media/img2.png)\n"
        "Image 3: ![](/tmp/media/img3.jpeg)"
    )
    rewritten = rewrite_markdown_image_paths(markdown, session_id)
    assert f"/media/{session_id}/img1.jpg" in rewritten
    assert f"/media/{session_id}/img2.png" in rewritten
    assert f"/media/{session_id}/img3.jpeg" in rewritten
    
    # Test no images
    markdown = "No images here, just text."
    rewritten = rewrite_markdown_image_paths(markdown, session_id)
    assert rewritten == markdown
    
    # Test with different image formats
    markdown = "Formats: ![](media/a.png) ![](media/b.jpg) ![](media/c.gif) ![](media/d.svg) ![](media/e.webp)"
    rewritten = rewrite_markdown_image_paths(markdown, session_id)
    
    # Check only for the extensions that are actually in the markdown
    assert f"/media/{session_id}/a.png" in rewritten
    assert f"/media/{session_id}/b.jpg" in rewritten
    assert f"/media/{session_id}/c.gif" in rewritten
    assert f"/media/{session_id}/d.svg" in rewritten
    assert f"/media/{session_id}/e.webp" in rewritten
