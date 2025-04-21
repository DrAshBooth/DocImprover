"""Flask application for DocImprover."""
import os
import uuid
import shutil
import atexit
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, request, send_file, session, jsonify, render_template
from werkzeug.utils import secure_filename
from .document_processor import DocumentProcessor
from docx import Document
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger('docimprover')

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Ensure uploads directory exists
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['FILE_CLEANUP_AGE'] = timedelta(hours=1)  # Clean files older than 1 hour

def init_upload_dir() -> str:
    """Initialize the upload directory."""
    upload_dir = app.config['UPLOAD_FOLDER']
    if not os.path.isabs(upload_dir):
        raise ValueError("Upload folder must be an absolute path")
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    return upload_dir

def cleanup_old_files() -> None:
    """Clean up files older than max_age_hours."""
    upload_dir = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_dir):
        return  # Nothing to clean if directory doesn't exist
        
    max_age_hours = app.config['FILE_CLEANUP_AGE'].total_seconds() / 3600
    try:
        now = datetime.now()
        for item in os.listdir(upload_dir):
            item_path = os.path.join(upload_dir, item)
            try:
                if os.path.isdir(item_path):
                    if (now - datetime.fromtimestamp(os.path.getmtime(item_path))) > timedelta(hours=max_age_hours):
                        shutil.rmtree(item_path, ignore_errors=True)
            except (OSError, FileNotFoundError):
                continue  # Skip if directory was already removed
    except Exception as e:
        logger.error(f"Error during file cleanup: {e}")

def get_session_id() -> str:
    """Get or create a session ID."""
    if 'upload_id' not in session:
        session['upload_id'] = str(uuid.uuid4())
    return session['upload_id']

def ensure_session_dir(session_id: str) -> str:
    """Ensure session directory exists and return its path."""
    session_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
    return session_dir

def validate_docx_file(file) -> Optional[str]:
    """Validate uploaded file. Returns error message if invalid, None if valid."""
    if not file or not file.filename:
        return "No file selected"
    if not file.filename.endswith('.docx'):
        return "Please upload a Word document (.docx)"
    return None

@app.route('/')
def index() -> str:
    """Render the index page."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file() -> tuple[Dict[str, Any], int]:
    """Handle file upload and improvement."""
    # Check if a file was uploaded
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    error = validate_docx_file(file)
    if error:
        return jsonify({"error": error}), 400
    
    try:
        session_id = get_session_id()
        upload_dir = ensure_session_dir(session_id)
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        input_path = os.path.join(upload_dir, filename)
        file.save(input_path)
        
        # Process document using context manager
        with DocumentProcessor() as processor:
            doc = Document(input_path)
            result = processor.improve_document(doc)
            
            if "error" in result:
                return jsonify({"error": result["error"]}), 400
            
            # Save improved document
            output_filename = f"improved_{filename}"
            output_path = os.path.join(upload_dir, output_filename)
            result["formatted_doc"].save(output_path)
            
            # Return response
            improved_file = f"{session_id}/{output_filename}"
            return jsonify({
                "improvements": result["improvements"],
                "original_text": result["original_text"],
                "improved_file": improved_file,
                "success": True
            }), 200
        
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        return jsonify({"error": f"Error processing document: {str(e)}"}), 400

@app.route('/download/<path:filepath>')
def download_file(filepath: str) -> Any:
    """Download an improved document."""
    try:
        # Split into session_id and filename
        parts = filepath.split('/')
        if len(parts) != 2:
            return jsonify({"error": "Invalid file path"}), 400
        
        session_id, filename = parts
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], session_id, secure_filename(filename))
        
        # Check if file exists first
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404
        
        # Store current session ID
        current_session_id = session.get('upload_id')
        
        try:
            # Temporarily set session to match the requested file's session
            session['upload_id'] = session_id
            
            # Send file
            return send_file(file_path, as_attachment=True)
        finally:
            # Restore original session
            if current_session_id:
                session['upload_id'] = current_session_id
        
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return jsonify({"error": f"Error downloading file: {str(e)}"}), 404

# Create uploads directory if it doesn't exist
init_upload_dir()

# Register cleanup function
atexit.register(cleanup_old_files)

if __name__ == '__main__':
    app.run(debug=True)
