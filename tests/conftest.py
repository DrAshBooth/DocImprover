"""Test configuration for DocImprover."""
import os
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from docx import Document
from doc_improver.app import app as flask_app
from doc_improver.document_processor import DocumentProcessor

@pytest.fixture
def app(tmp_path):
    """Create a test Flask application with temporary upload directory."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(exist_ok=True)
    
    flask_app.config.update({
        "TESTING": True,
        "UPLOAD_FOLDER": str(upload_dir),
        "FILE_CLEANUP_AGE": timedelta(hours=1)
    })
    
    yield flask_app
    
    # Cleanup after tests
    if upload_dir.exists():
        # Walk bottom-up to ensure we delete files before directories
        for root, dirs, files in os.walk(str(upload_dir), topdown=False):
            for name in files:
                os.unlink(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        upload_dir.rmdir()

@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()

@pytest.fixture
def mock_openai(monkeypatch):
    """Mock OpenAI API responses."""
    class MockResponse:
        def __init__(self, content):
            self.content = content
            self.model = "gpt-4"

        @property
        def choices(self):
            return [type('Choice', (), {'message': type('Message', (), {'content': self.content})()})]

    class MockOpenAI:
        def __init__(self, api_key=None, base_url=None):
            self.chat = type('Chat', (), {
                'completions': type('Completions', (), {
                    'create': lambda **kwargs: MockResponse("# Improved Title\n\nThis is the **improved** text.")
                })()
            })()

    monkeypatch.setattr("openai.OpenAI", MockOpenAI)
    return MockOpenAI

@pytest.fixture
def sample_doc():
    """Create a sample Word document for testing."""
    doc = Document()
    doc.add_heading('Test Document', 0)
    doc.add_paragraph('This is a test paragraph.')
    return doc

@pytest.fixture
def temp_docx(tmp_path, sample_doc):
    """Save a sample document to a temporary file."""
    file_path = tmp_path / "test.docx"
    sample_doc.save(file_path)
    return file_path

@pytest.fixture
def old_session_dir(app):
    """Create an old session directory for testing cleanup."""
    session_id = "test_old_session"
    session_dir = Path(app.config['UPLOAD_FOLDER']) / session_id
    session_dir.mkdir(exist_ok=True)
    
    # Create a test file in the directory
    test_file = session_dir / "test.docx"
    test_file.write_text("test content")
    
    # Set old modification time
    old_time = datetime.now() - app.config['FILE_CLEANUP_AGE'] - timedelta(minutes=5)
    os.utime(session_dir, (old_time.timestamp(), old_time.timestamp()))
    
    return session_dir

@pytest.fixture
def recent_session_dir(app):
    """Create a recent session directory that shouldn't be cleaned up."""
    session_id = "test_recent_session"
    session_dir = Path(app.config['UPLOAD_FOLDER']) / session_id
    session_dir.mkdir(exist_ok=True)
    
    # Create a test file in the directory
    test_file = session_dir / "test.docx"
    test_file.write_text("test content")
    
    return session_dir
