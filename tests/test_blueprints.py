"""Tests for the Flask application's blueprint structure."""
import os
import pytest
from flask import session, url_for
from io import BytesIO
import shutil
from PIL import Image
import io

from doc_improver.app import create_app

def create_test_image(width=200, height=200):
    """Create a test image for testing."""
    image = Image.new('RGB', (width, height), color='red')
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

@pytest.fixture
def app(tmp_path):
    """Create a test Flask application with a test configuration."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(exist_ok=True)
    
    # Create a test app with the app factory
    app = create_app()
    
    # Configure the app for testing
    app.config.update({
        "TESTING": True,
        "UPLOAD_FOLDER": str(upload_dir),
        "SECRET_KEY": "test_key",
        "SERVER_NAME": "localhost.localdomain"  # Required for url_for with blueprints
    })
    
    # Create app context
    with app.app_context():
        yield app
    
    # Cleanup after tests
    try:
        if upload_dir.exists():
            shutil.rmtree(upload_dir, ignore_errors=True)
    except Exception:
        pass

@pytest.fixture
def client(app):
    """Create a test client for the app."""
    with app.test_client() as client:
        with app.app_context():
            yield client

def test_main_blueprint(client):
    """Test the main blueprint routes."""
    # Test the index route
    response = client.get('/')
    assert response.status_code == 200
    assert b"DocImprover" in response.data

def test_documents_blueprint_upload_no_file(client):
    """Test upload endpoint with no file."""
    response = client.post('/upload')
    assert response.status_code == 400
    assert b"No file provided" in response.data

def test_documents_blueprint_upload_wrong_filetype(client):
    """Test upload endpoint with wrong file type."""
    data = {
        'file': (BytesIO(b'test content'), 'test.txt')
    }
    response = client.post('/upload', data=data)
    assert response.status_code == 400
    assert b"Please upload a Word document" in response.data

def test_documents_blueprint_download_nonexistent(client):
    """Test download endpoint with nonexistent file."""
    response = client.get('/download/nonexistent-session/nonexistent.docx')
    assert response.status_code == 404
    assert b"File not found" in response.data or b"Not Found" in response.data

def test_media_blueprint_nonexistent_file(client):
    """Test media endpoint with nonexistent file."""
    response = client.get('/media/test-session/nonexistent.png')
    assert response.status_code == 404
    assert b"Not Found" in response.data

def test_media_blueprint_path_traversal(client):
    """Test media endpoint with path traversal attempt."""
    response = client.get('/media/test-session/../config.py')
    assert response.status_code == 404
    assert b"Not Found" in response.data

def test_documents_blueprint_path_traversal(client):
    """Test download endpoint with path traversal attempt."""
    response = client.get('/download/test-session/../config.py')
    assert response.status_code == 404
    assert b"Not Found" in response.data
