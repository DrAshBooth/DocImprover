"""Tests for the DocumentProcessor class."""
import pytest
import re
from docx import Document
from docx.shared import Inches
from doc_improver.document_processor import DocumentProcessor
import os
import io
from PIL import Image
import zipfile
from docx.opc.constants import RELATIONSHIP_TYPE as RT
import shutil
from pathlib import Path

def create_test_image(size=(300, 300), color=(255, 0, 0), large_file=False):
    """Create a test image with specified size and color."""
    image = Image.new('RGB', size, color)
    
    if large_file:
        # Create a pattern that doesn't compress well
        pixels = image.load()
        for i in range(size[0]):
            for j in range(size[1]):
                pixels[i, j] = (i % 256, j % 256, (i + j) % 256)
    
    img_byte_arr = io.BytesIO()
    # Use BMP format for large files as it's uncompressed
    format_type = 'BMP' if large_file else 'PNG'
    image.save(img_byte_arr, format=format_type)
    img_byte_arr.seek(0)
    return img_byte_arr

def create_test_doc_with_image():
    """Create a test document with an embedded image."""
    doc = Document()  # Create empty document
    doc.add_paragraph("Test document with image")
    img_stream = create_test_image()
    doc.add_picture(img_stream)
    return doc

def verify_image_in_document(doc_path):
    """Verify that images in the document are properly embedded and accessible."""
    try:
        # Check if the file exists and is a valid zip (docx) file
        if not os.path.exists(doc_path) or not zipfile.is_zipfile(doc_path):
            return False, "Document doesn't exist or is not a valid Office document"

        doc = Document(doc_path)
        
        # Get all image relationships
        image_rels = []
        for rel in doc.part.rels.values():
            if rel.reltype == RT.IMAGE:
                image_rels.append(rel)

        if not image_rels:
            return False, "No images found in document relationships"

        # Verify each image is accessible and valid
        for rel in image_rels:
            # Check if the image part exists
            if not rel.target_part:
                return False, f"Image part missing for relationship {rel.rId}"
            
            # Check if the image data is valid
            image_bytes = rel.target_part.blob
            if not image_bytes:
                return False, f"Image data is empty for relationship {rel.rId}"
            
            # Verify the image data is valid by trying to open it
            try:
                img = Image.open(io.BytesIO(image_bytes))
                img.verify()
            except Exception as e:
                return False, f"Invalid image data for relationship {rel.rId}: {str(e)}"

        return True, "All images are valid and properly embedded"
    except Exception as e:
        return False, f"Error verifying document: {str(e)}"

@pytest.fixture
def processor():
    """Create a DocumentProcessor instance."""
    return DocumentProcessor()

@pytest.fixture
def test_doc_with_image(tmp_path):
    """Create a test document with an image in a temporary directory."""
    doc = create_test_doc_with_image()
    doc_path = tmp_path / "test_with_image.docx"
    doc.save(str(doc_path))
    return str(doc_path)

def test_document_processor_initialization():
    """Test DocumentProcessor initialization."""
    processor = DocumentProcessor()
    assert processor.model == "gpt-4"  # Default model
    assert processor._temp_dir is None
    assert processor._image_map == {}

def test_temp_dir_management():
    """Test temporary directory creation and cleanup."""
    processor = DocumentProcessor()
    temp_dir = processor._create_temp_dir()
    assert os.path.exists(temp_dir)
    processor._cleanup_temp_dir()
    assert not os.path.exists(temp_dir)

def test_image_embedding(processor, test_doc_with_image, tmp_path, monkeypatch):
    """Test that images are properly embedded in the improved document."""
    # Mock OpenAI response
    class MockResponse:
        def __init__(self):
            self.choices = [type('Choice', (), {'message': type('Message', (), {'content': '[IMAGE:placeholder]'})()})]

    class MockOpenAI:
        def __init__(self, **kwargs):
            pass
        
        @property
        def chat(self):
            return self
            
        def completions(self):
            return self
            
        def create(self, **kwargs):
            # Extract the image ID from the input text
            input_text = kwargs.get('messages', [{}])[1].get('content', '')
            image_id = re.search(r'\[IMAGE:([a-f0-9-]+)\]', input_text).group(1)
            # Return the same image ID in the response
            return type('Response', (), {'choices': [
                type('Choice', (), {'message': type('Message', (), {'content': f'Test document with image\n\n[IMAGE:{image_id}]'})()})
            ]})()

    monkeypatch.setattr("openai.OpenAI", MockOpenAI)
    
    # Process the document
    doc = Document(test_doc_with_image)
    result = processor.improve_document(doc)
    
    assert result["success"] is True, "Document processing failed"
    
    # Save the improved document
    output_path = tmp_path / "improved_doc.docx"
    result["formatted_doc"].save(str(output_path))
    
    # Verify the image in the improved document
    is_valid, message = verify_image_in_document(str(output_path))
    assert is_valid, f"Image verification failed: {message}"
    
    # Additional checks for image relationships
    doc = Document(str(output_path))
    
    # Check that image relationships exist
    image_rels = [rel for rel in doc.part.rels.values() if rel.reltype == RT.IMAGE]
    assert len(image_rels) > 0, "No image relationships found in the document"
    
    # Check that image parts are accessible
    for rel in image_rels:
        assert rel.target_part is not None, "Image part is missing"
        assert len(rel.target_part.blob) > 0, "Image data is empty"
        
        # Verify image data is valid
        img_stream = io.BytesIO(rel.target_part.blob)
        img = Image.open(img_stream)
        assert img.size[0] > 0 and img.size[1] > 0, "Invalid image dimensions"

def test_large_image_handling(processor, tmp_path, monkeypatch):
    """Test handling of large images."""
    # Mock OpenAI response
    class MockResponse:
        def __init__(self):
            self.choices = [type('Choice', (), {'message': type('Message', (), {
                'content': 'Document Featuring a Large Image\n\n[IMAGE: This image is too large to process]'
            })()})]

    class MockOpenAI:
        def __init__(self, **kwargs):
            pass
        
        @property
        def chat(self):
            return self
            
        def completions(self):
            return self
            
        def create(self, **kwargs):
            # Extract the original text to see if it contains the warning
            input_text = kwargs.get('messages', [{}])[1].get('content', '')
            if '[Image too large to process]' in input_text:
                return MockResponse()
            # If not in input, return the same format as the original text
            return type('Response', (), {'choices': [
                type('Choice', (), {'message': type('Message', (), {'content': input_text})()})
            ]})()

    monkeypatch.setattr("openai.OpenAI", MockOpenAI)
    
    # Create a document with a large image
    doc = Document()
    doc.add_paragraph("Test document with large image")
    
    # Create a large image (>10MB)
    large_size = (3000, 3000)
    img_stream = create_test_image(size=large_size, large_file=True)
    doc.add_picture(img_stream)
    
    # Save and process the document
    doc_path = tmp_path / "large_image.docx"
    doc.save(str(doc_path))
    
    # Process the document
    doc = Document(str(doc_path))
    result = processor.improve_document(doc)
    
    # Verify that the document was processed
    assert result["success"] is True, "Document processing failed"
    
    # Save the improved document
    output_path = tmp_path / "improved_large.docx"
    result["formatted_doc"].save(str(output_path))
    
    # The document should still be valid (even without images)
    doc = Document(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "[IMAGE: This image is too large to process]" in text, "Large image warning not found in document"

def test_image_scaling(processor, tmp_path, monkeypatch):
    """Test that images are properly scaled."""
    # Mock OpenAI response
    class MockResponse:
        def __init__(self):
            self.choices = [type('Choice', (), {'message': type('Message', (), {'content': 'Test document with scaled image'})()})]

    class MockOpenAI:
        def __init__(self, **kwargs):
            pass
        
        @property
        def chat(self):
            return self
            
        def completions(self):
            return self
            
        def create(self, **kwargs):
            return MockResponse()

    monkeypatch.setattr("openai.OpenAI", MockOpenAI)
    
    # Create a document with a large dimension image
    doc = Document()
    doc.add_paragraph("Test document with large dimensions image")
    
    # Create an image with large dimensions but small file size
    large_dims = (2000, 1500)  # Large dimensions
    img_stream = create_test_image(size=large_dims)
    doc.add_picture(img_stream)
    
    # Save and process the document
    doc_path = tmp_path / "large_dims.docx"
    doc.save(str(doc_path))
    
    # Process the document
    doc = Document(str(doc_path))
    result = processor.improve_document(doc)
    
    assert result["success"] is True, "Document processing failed"
    
    # Save the improved document
    output_path = tmp_path / "improved_scaled.docx"
    result["formatted_doc"].save(str(output_path))
    
    # Verify the image was scaled properly
    doc = Document(str(output_path))
    for shape in doc.inline_shapes:
        # Convert to inches (EMU to inches)
        width_inches = shape.width / 914400  # 914400 EMUs per inch
        height_inches = shape.height / 914400
        
        # Check that dimensions are within limits
        assert width_inches <= 6.0, f"Image width {width_inches} exceeds 6 inches"
        assert height_inches <= 8.0, f"Image height {height_inches} exceeds 8 inches"
        
        # Check aspect ratio is maintained (within 1% tolerance)
        original_ratio = 2000 / 1500
        new_ratio = shape.width / shape.height
        assert abs(original_ratio - new_ratio) < 0.01, "Aspect ratio was not maintained"
