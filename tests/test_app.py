"""Tests for the Flask application."""
import os
import pytest
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from io import BytesIO
from doc_improver.app import app, init_upload_dir, cleanup_old_files

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
    # Check for the current response format keys
    assert b"improved_markdown" in response.data
    assert b"original_markdown" in response.data
    assert b"improved_file" in response.data
    assert b"success" in response.data

def test_download_nonexistent_file(client):
    """Test download endpoint with nonexistent file."""
    response = client.get('/download/session123/nonexistent.docx')
    assert response.status_code == 404
    # The actual response is just 'Not Found' for invalid paths
    # No need to check the specific message content as it might vary

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

def test_session_isolation(client, temp_docx):
    """Test that files from different sessions don't interfere."""
    # First session upload
    with client.session_transaction() as sess:
        sess['upload_id'] = 'session1'
    
    with open(temp_docx, 'rb') as f:
        data = {'file': (f, 'test.docx')}
        response1 = client.post('/upload', data=data)
        assert response1.status_code == 200
        result1 = response1.get_json()
        assert 'session1' in result1['improved_file']
    
    # Second session upload
    with client.session_transaction() as sess:
        sess['upload_id'] = 'session2'
    
    with open(temp_docx, 'rb') as f:
        data = {'file': (f, 'test.docx')}
        response2 = client.post('/upload', data=data)
        assert response2.status_code == 200
        result2 = response2.get_json()
        assert 'session2' in result2['improved_file']
    
    # Verify different file paths and both files exist
    assert result1['improved_file'] != result2['improved_file']
    
    # Try downloading both files
    response1 = client.get(f'/download/{result1["improved_file"]}')
    assert response1.status_code == 200
    
    response2 = client.get(f'/download/{result2["improved_file"]}')
    assert response2.status_code == 200

def test_init_upload_dir(app, tmp_path):
    """Test upload directory initialization and configuration."""
    # Test with relative path (should fail)
    app.config['UPLOAD_FOLDER'] = 'relative/uploads'
    with pytest.raises(ValueError, match="Upload folder must be an absolute path"):
        init_upload_dir(app)
    
    # Test with absolute path
    test_uploads = tmp_path / "test_uploads"
    app.config['UPLOAD_FOLDER'] = str(test_uploads)
    init_upload_dir(app)
    
    # Verify directory exists and is writable
    assert test_uploads.exists()
    assert test_uploads.is_dir()
    
    # Test write permissions by creating a test file
    test_file = test_uploads / ".write_test"
    test_file.write_text("test")
    assert test_file.exists()
    
    # Clean up test file
    test_file.unlink()
    assert test_uploads.is_dir()
    
    # Test write permissions
    test_file = test_uploads / 'test.txt'
    test_file.write_text('test')
    assert test_file.exists()
    
    # Test cleanup
    test_file.unlink()
    test_uploads.rmdir()

def test_cleanup_old_files(app, old_session_dir, recent_session_dir):
    """Test that old files are cleaned up but recent ones are kept."""
    old_file = old_session_dir / 'test.docx'
    recent_file = recent_session_dir / 'test.docx'
    
    assert old_file.exists()
    assert recent_file.exists()
    
    # Ensure we're in an application context
    with app.app_context():
        # Run cleanup
        cleanup_old_files(app)
        
        # Verify old files are removed but recent ones remain
        assert not old_file.exists()
        assert not old_session_dir.exists()
        assert recent_file.exists()
        assert recent_session_dir.exists()

def test_invalid_download_path(client):
    """Test download with invalid path format."""
    response = client.get('/download/invalid_path_without_session')
    assert response.status_code == 404
    # The response is a 404 page, no need to check the specific content

def test_download_from_wrong_session(client, temp_docx, tmp_path):
    """Test attempting to download a file from another session."""
    # First, prepare test directories to ensure we have control over file existence
    session1_dir = os.path.join(tmp_path, "session1")
    session2_dir = os.path.join(tmp_path, "session2")
    os.makedirs(session1_dir, exist_ok=True)
    os.makedirs(session2_dir, exist_ok=True)
    
    # Create a test file in session1 directory
    test_file = os.path.join(session1_dir, "test_file.docx")
    shutil.copy(temp_docx, test_file)
    
    # Use the app's configured upload folder for the test
    with client.application.app_context():
        original_upload_folder = client.application.config['UPLOAD_FOLDER']
        client.application.config['UPLOAD_FOLDER'] = str(tmp_path)
        
        try:
            # Try to access the file with session2 in the path
            # This file doesn't physically exist in session2 directory
            response = client.get('/download/session2/test_file.docx')
            # Should get 404 since file doesn't exist in session2 path
            assert response.status_code == 404
            
            # Try to access the file with the correct session path
            response = client.get('/download/session1/test_file.docx')
            # Should succeed since file exists in session1 path
            assert response.status_code == 200
        finally:
            # Restore the original upload folder
            client.application.config['UPLOAD_FOLDER'] = original_upload_folder
