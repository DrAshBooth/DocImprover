# DocImprover

A web application that leverages OpenAI's GPT-4 to enhance and improve your documents. Upload a Word document (.docx) and receive AI-generated suggestions for improving grammar, style, clarity, structure, and professional tone.

## About DocImprover

DocImprover is designed to help professionals, students, and writers improve their document quality with AI assistance. The application processes Microsoft Word documents (.docx), extracts their content, and uses OpenAI's advanced language models to provide suggestions and improvements while preserving the original document structure, including images and formatting.

### Key Features

- **Document Enhancement**: Improve grammar, style, clarity, and professional tone of your writing
- **Image Support**: Full support for embedded images in documents, preserving them in the improved version
- **Markdown Preview**: View side-by-side comparison of your original and improved document with Markdown formatting
- **Download Integration**: Download the improved document as a Word file (.docx) ready for further editing
- **Session Management**: Secure session-based file handling with temporary file cleanup
- **Modern UI**: Clean, responsive interface with drag-and-drop file upload support

## System Requirements

- Python 3.10+
- Poetry package manager
- Pandoc (for document conversion)

## Architecture

DocImprover is built with a modern, modular architecture:

- **Flask Web Framework**: Powers the web interface and API endpoints
- **Blueprints**: Modular route organization for maintainability
- **OpenAI Integration**: Secure connection to OpenAI's GPT models
- **Document Processing Pipeline**: Handles the conversion between formats while preserving document elements
- **Session Management**: Ensures user data isolation and security

## Setup

### 1. Install Dependencies

```bash
poetry install
```

### 2. Install Pandoc

Pandoc is required for document format conversion. Install it according to your operating system:

- **macOS**:
  ```bash
  brew install pandoc
  ```

- **Linux**:
  ```bash
  apt-get install pandoc
  ```

- **Windows**:
  Download from [pandoc.org](https://pandoc.org/installing.html)

### 3. Configure Environment

Create a `.env` file in the project root with your OpenAI API key:
```
OPENAI_API_KEY=your-api-key-here
```

## Running the Application

### Development Mode

1. Start the Flask development server:
   ```bash
   poetry run python -m doc_improver.app
   ```

2. Open your browser to http://localhost:5000

3. Upload a Word document and get AI-powered suggestions for improvement!

### Production Deployment

For production environments, it's recommended to use a WSGI server such as Gunicorn:

```bash
poetry run gunicorn -w 4 "doc_improver.app:create_app()"
```

## How It Works

1. **Document Upload**: User uploads a .docx document through the web interface
2. **Document Processing**:
   - The document is converted to Markdown format using Pandoc
   - Images are extracted and stored in a session-specific media folder
   - The Markdown content is sent to OpenAI's API for enhancement
3. **AI Enhancement**: The AI model improves the document while preserving its structure
4. **Preview**: The user can preview the improvements in the web interface
5. **Download**: The user can download the enhanced document as a .docx file

## Testing

DocImprover includes a comprehensive test suite covering all major functionality:

```bash
poetry run pytest
```

For coverage information:

```bash
poetry run pytest --cov=doc_improver
```

## Project Structure

```
├── src/
│   └── doc_improver/           # Main application package
│       ├── config/             # Application configuration
│       ├── routes/             # API and web routes (Flask blueprints)
│       ├── static/             # Static assets (CSS, JS, etc.)
│       ├── templates/          # HTML templates
│       ├── utils/              # Utility functions
│       ├── app.py              # Flask application factory
│       └── document_processor.py # Core document processing logic
├── tests/                      # Test suite
└── uploads/                    # Temporary storage for uploaded documents
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is proprietary software. All rights reserved.