"""Flask application for DocImprover.

This module implements a Flask web application that processes and improves documents
using OpenAI's API. It handles file uploads, document conversion, and serving media files.
"""
# Standard library imports
import os
import atexit
import logging
from datetime import datetime, timedelta
from pathlib import Path
import shutil

# Third-party imports
from flask import Flask

# Configure logger to output to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_app(test_config=None):
    """Create and configure the Flask application.
    
    Args:
        test_config: Configuration dictionary for testing (optional)
        
    Returns:
        Flask: The configured Flask application
    """
    # Initialize Flask app
    app = Flask(__name__)

    # Load configuration if it exists, otherwise use defaults for testing
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'application.cfg')
    if os.path.exists(config_path):
        app.config.from_pyfile(config_path)
    else:
        # Default configuration for testing
        app.config['UPLOAD_FOLDER'] = os.path.join(Path(__file__).resolve().parent, 'uploads')
        app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max upload
        app.config['SESSION_MAX_AGE'] = 24 * 60 * 60  # 24 hours
        app.config['ALLOWED_EXTENSIONS'] = {'docx'}
    
    # Apply test config if provided
    if test_config is not None:
        app.config.update(test_config)
    
    # Set a secret key for session management if not provided in test_config
    if 'SECRET_KEY' not in app.config:
        app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'development-secret-key')

    # Ensure the secret key is properly set on the app instance
    app.secret_key = app.config['SECRET_KEY']

    # Configure upload folder as an absolute path
    base_dir = Path(__file__).resolve().parent
    app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'uploads')
    app.config['FILE_CLEANUP_AGE'] = timedelta(hours=1)  # Clean files older than 1 hour
    
    # Ensure upload directory exists
    init_upload_dir(app)
    
    # Register clean up function
    atexit.register(cleanup_old_files, app=app)
    
    # Schedule periodic cleanup
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=cleanup_old_files, args=[app], trigger='interval', hours=1)
        scheduler.start()
    except ImportError:
        logger.warning("APScheduler not installed. Periodic cleanup disabled.")
    
    # Register blueprints
    from .routes.main import main_bp
    from .routes.documents import documents_bp
    from .routes.media import media_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(media_bp)
    
    return app


def init_upload_dir(app):
    """Initialize the upload directory.
    
    Creates the upload directory if it doesn't exist and verifies it's an absolute path.
    
    Args:
        app: Flask application object
        
    Returns:
        str: Path to the upload directory
        
    Raises:
        ValueError: If the upload folder is not an absolute path
    """
    upload_dir = app.config['UPLOAD_FOLDER']
    if not os.path.isabs(upload_dir):
        raise ValueError("Upload folder must be an absolute path")
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    return upload_dir


def cleanup_old_files(app):
    """Clean up files older than the configured maximum age.
    
    Removes session directories that are older than the max age defined in app.config.
    
    Args:
        app: Flask application object
    """    
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
                        logger.info(f"Removed old directory: {item_path}")
            except (OSError, FileNotFoundError):
                continue  # Skip if directory was already removed
    except Exception as e:
        logger.error(f"Error during file cleanup: {e}")


# Create the Flask application instance
app = create_app()

# Explicitly set the secret key again to ensure it's available
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'development-secret-key-explicit')
print(f"App secret key set: {bool(app.secret_key)}")

if __name__ == '__main__':
    app.run(debug=True)
