"""Flask web application for document improvement."""
from flask import Flask, request, jsonify, render_template, send_file, session
from docx import Document
import tempfile
import os
import logging
import atexit
from datetime import datetime, timedelta
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename
from .document_processor import DocumentProcessor
from .config import get_settings
from .logging_config import setup_logging

# Set up logging
logger = setup_logging()

app = Flask(__name__)

# Ensure uploads directory is relative to the application directory
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['FILE_CLEANUP_AGE'] = timedelta(hours=1)  # Clean files older than 1 hour
app.secret_key = os.urandom(24)  # For session management

# Create uploads directory if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], mode=0o755)
def init_upload_dir():
    """Initialize the upload directory with proper permissions.
    
    Returns:
        bool: True if initialization was successful.
        
    Raises:
        ValueError: If upload folder path is not absolute
        OSError: If directory cannot be created or is not writable
    """
    upload_dir = Path(app.config['UPLOAD_FOLDER'])
    
    # Ensure upload path is absolute
    if not upload_dir.is_absolute():
        logger.error("Upload folder must be an absolute path")
        raise ValueError("Upload folder must be an absolute path")
    
    try:
        # Create directory if it doesn't exist
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Test if directory is writable
        test_file = upload_dir / '.test_write'
        test_file.write_text('test')
        test_file.unlink()
        
        logger.info(f"Upload directory initialized successfully at: {upload_dir}")
        return True
        
    except OSError as e:
        logger.error(f"Failed to initialize upload directory: {e}")
        raise OSError(f"Upload directory is not writable: {e}")
    except Exception as e:
        logger.error(f"Unexpected error initializing upload directory: {e}")
        raise
            


# Initialize upload directory
if not init_upload_dir():
    logger.error("Application startup failed: Could not initialize upload directory")
    raise RuntimeError("Could not initialize upload directory. Check permissions and path.")

def cleanup_old_files():
    """Remove files older than FILE_CLEANUP_AGE from the uploads directory."""
    current_time = datetime.now()
    cleanup_age = app.config['FILE_CLEANUP_AGE']
    uploads_dir = Path(app.config['UPLOAD_FOLDER'])
    
    try:
        # Iterate through session directories
        for session_dir in uploads_dir.iterdir():
            if not session_dir.is_dir():
                continue
                
            try:
                # Check if directory is old enough to clean
                dir_modified = datetime.fromtimestamp(session_dir.stat().st_mtime)
                if current_time - dir_modified > cleanup_age:
                    # Remove all files in directory
                    for file_path in session_dir.iterdir():
                        try:
                            file_path.unlink()
                            logging.info(f"Removed old file: {file_path}")
                        except OSError as e:
                            logging.error(f"Error removing file {file_path}: {e}")
                    
                    # Remove the directory itself
                    session_dir.rmdir()
                    logging.info(f"Removed session directory: {session_dir}")
            except OSError as e:
                logging.error(f"Error processing directory {session_dir}: {e}")
    except Exception as e:
        logging.error(f"Error during file cleanup: {e}")

# Register cleanup function to run on application shutdown
atexit.register(cleanup_old_files)

# Schedule periodic cleanup
@app.before_request
def before_request():
    """Run cleanup before processing requests."""
    cleanup_old_files()

# Initialize document processor
doc_processor = DocumentProcessor()

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and document improvement."""
    # Verify upload directory is available
    if not os.path.exists(app.config['UPLOAD_FOLDER']) or not os.access(app.config['UPLOAD_FOLDER'], os.W_OK):
        logger.error("Upload directory is not accessible")
        if not init_upload_dir():
            return jsonify({"error": "Server configuration error"}), 500
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if not file.filename.endswith('.docx'):
        return jsonify({"error": "Please upload a Word document (.docx)"}), 400

    try:
        # Generate unique identifier for this upload session
        if 'upload_id' not in session:
            session['upload_id'] = str(uuid.uuid4())
        
        # Create session-specific directory
        session_dir = Path(app.config['UPLOAD_FOLDER']) / session['upload_id']
        session_dir.mkdir(exist_ok=True)
        
        # Save uploaded file with secure filename
        filename = secure_filename(file.filename)
        filepath = session_dir / filename
        file.save(str(filepath))

        # Process document
        doc = Document(filepath)
        result = doc_processor.improve_document(doc)
        if "error" in result:
            return jsonify(result), 400

        # Create improved document with formatting
        improved_doc = Document()
        
        # Split content into lines and process markdown
        lines = result['improvements'].split('\n')
        current_list = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Handle headings
            if line.startswith('# '):
                improved_doc.add_heading(line[2:], level=1)
            elif line.startswith('## '):
                improved_doc.add_heading(line[3:], level=2)
            
            # Handle bullet points
            elif line.startswith('* ') or line.startswith('- '):
                if current_list is None:
                    current_list = improved_doc.add_paragraph()
                list_item = current_list.add_run('• ' + line[2:])
                current_list.add_run('\n')
            
            # Handle regular paragraphs
            else:
                current_list = None
                p = improved_doc.add_paragraph()
                
                # Process bold and italic formatting
                parts = line.split('**')
                is_bold = False
                
                for part in parts:
                    italic_parts = part.split('*')
                    is_italic = False
                    
                    for italic_part in italic_parts:
                        run = p.add_run(italic_part)
                        run.italic = is_italic
                        run.bold = is_bold
                        is_italic = not is_italic
                    
                    is_bold = not is_bold
        
        # Save improved document with secure filename in session directory
        base_name = secure_filename(filename)
        improved_filename = f"improved_{base_name}"
        improved_path = session_dir / improved_filename
        improved_doc.save(str(improved_path))
        logger.info(f"Saved improved document to: {improved_path}")

        # Add session and file info to result
        result['improved_file'] = f"{session['upload_id']}/{improved_filename}"
        logger.info(f"Generated download path: {result['improved_file']}")
        
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        return jsonify({"error": f"Error processing document: {str(e)}"}), 400

@app.route('/download/<path:filepath>')
def download_file(filepath):
    """Download the improved document.
    
    Args:
        filepath: Format should be 'session_id/filename'
    """
    # Log the request details
    logger.info(f"Download requested for file: {filepath}")
    logger.info(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    
    try:
        # Split into session_id and filename
        parts = filepath.split('/')
        if len(parts) != 2:
            logger.error(f"Invalid file path format: {filepath}")
            return jsonify({"error": "Invalid file path"}), 400
            
        session_id, filename = parts
        logger.info(f"Session ID: {session_id}, Filename: {filename}")
        
        # Get the full path to the file
        filepath = Path(app.config['UPLOAD_FOLDER']) / session_id / secure_filename(filename)
        logger.info(f"Looking for file at: {filepath}")
        
        # Check if file exists
        if not os.path.exists(filepath):
            logger.error(f"File not found at path: {filepath}")
            return jsonify({"error": "File not found"}), 404
            
        # Verify file is readable
        if not os.access(filepath, os.R_OK):
            logger.error(f"File not readable: {filepath}")
            return jsonify({"error": "File not accessible"}), 403
            
        # Send the file
        logger.info(f"Sending file: {filepath}")
        response = send_file(
            filepath,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name=filename
        )
        
        # Schedule file for deletion after sending
        @response.call_on_close
        def cleanup_after_download():
            try:
                os.remove(filepath)
                logging.info(f"Removed file after download: {filename}")
            except OSError as e:
                logging.error(f"Error removing file {filename} after download: {e}")
        
        return response
        
    except Exception as e:
        logging.error(f"Error downloading file: {e}")
        return jsonify({"error": "Error downloading file"}), 400

if __name__ == '__main__':
    app.run(debug=True)
