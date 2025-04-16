"""Tests for the document processor module."""
import pytest
from doc_improver.document_processor import DocumentProcessor

def test_extract_text(sample_doc):
    """Test extracting text from a Word document."""
    processor = DocumentProcessor()
    text = processor.extract_text(sample_doc)
    assert "Test Document" in text
    assert "This is a test paragraph." in text

def test_improve_document_with_content(mock_openai, sample_doc):
    """Test improving a document with content."""
    processor = DocumentProcessor()
    result = processor.improve_document(sample_doc)
    
    assert "error" not in result
    assert "success" in result
    assert result["success"] is True
    assert "improvements" in result
    assert isinstance(result["improvements"], str)
    assert result["improvements"].strip() != ""
    assert "original_text" in result
    assert "Test Document" in result["original_text"]

def test_improve_empty_document(sample_doc):
    """Test improving an empty document."""
    # Create an empty document
    sample_doc._body.clear_content()
    
    processor = DocumentProcessor()
    result = processor.improve_document(sample_doc)
    
    assert "error" in result
    assert result["error"] == "Document is empty"

def test_document_processor_initialization():
    """Test DocumentProcessor initialization."""
    processor = DocumentProcessor()
    assert processor.model == "gpt-4"  # Default model
    assert processor.client is not None
