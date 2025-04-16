"""Test configuration for DocImprover."""
import os
import pytest
from docx import Document
from doc_improver.app import app as flask_app
from doc_improver.document_processor import DocumentProcessor

@pytest.fixture
def app():
    """Create a test Flask application."""
    flask_app.config.update({
        "TESTING": True,
    })
    yield flask_app

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
