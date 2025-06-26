"""Main routes for the DocImprover application."""

from flask import Blueprint, render_template

# Create a blueprint for the main routes
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Render the index page.
    
    Returns:
        Response: The rendered index.html template
    """
    return render_template('index.html')
