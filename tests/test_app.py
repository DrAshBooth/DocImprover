"""Tests for the Flask application."""
import os
import pytest
from io import BytesIO
from doc_improver.app import app

def test_index_page(client):
    """Test the index page loads correctly."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"DocImprover" in response.data
    assert b"Drop your document here" in response.data

def test_upload_no_file(client):
    """Test upload endpoint with no file."""
    response = client.post('/upload')
    assert response.status_code == 400
    assert b"No file provided" in response.data

def test_upload_wrong_file_type(client):
    """Test upload endpoint with wrong file type."""
    data = {
        'file': (BytesIO(b'test content'), 'test.txt')
    }
    response = client.post('/upload', data=data)
    assert response.status_code == 400
    assert b"Please upload a Word document" in response.data

def test_upload_valid_file(client, temp_docx, mock_openai):
    """Test upload endpoint with valid file."""
    with open(temp_docx, 'rb') as f:
        data = {
            'file': (f, 'test.docx')
        }
        response = client.post('/upload', data=data)
    
    assert response.status_code == 200
    assert b"improvements" in response.data
    assert b"original_text" in response.data
    assert b"improved_file" in response.data

def test_download_nonexistent_file(client):
    """Test download endpoint with nonexistent file."""
    response = client.get('/download/nonexistent.docx')
    assert response.status_code == 400
    assert b"Error downloading file" in response.data

def test_download_valid_file(client, temp_docx):
    """Test download endpoint with valid file."""
    # First upload a file
    with open(temp_docx, 'rb') as f:
        data = {
            'file': (f, 'test.docx')
        }
        response = client.post('/upload', data=data)
        assert response.status_code == 200
        result = response.get_json()
        
    # Then try to download it
    response = client.get(f'/download/{result["improved_file"]}')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    assert 'attachment' in response.headers['Content-Disposition']
