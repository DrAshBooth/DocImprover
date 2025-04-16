"""Flask web application for document improvement."""
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from docx import Document
import tempfile
import os
from .document_processor import DocumentProcessor
from .config import get_settings
from .logging_config import setup_logging

# Set up logging
logger = setup_logging()

app = Flask(__name__)

# Initialize document processor
doc_processor = DocumentProcessor()

# HTML template
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DocImprover - AI-Powered Document Improvement</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        .diff-highlight {
            transition: background-color 0.3s;
        }
        .diff-highlight:hover {
            background-color: #f0f9ff;
        }
        /* Markdown styles */
        #improvements h1 {
            font-size: 1.875rem;
            font-weight: 700;
            margin-bottom: 1rem;
            color: #1a56db;
        }
        #improvements h2 {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.875rem;
            color: #2563eb;
        }
        #improvements p {
            margin-bottom: 1rem;
            line-height: 1.625;
        }
        #improvements ul {
            list-style-type: disc;
            margin-left: 1.5rem;
            margin-bottom: 1rem;
        }
        #improvements li {
            margin-bottom: 0.5rem;
        }
        #improvements strong {
            font-weight: 600;
            color: #1e40af;
        }
        #improvements em {
            font-style: italic;
            color: #3b82f6;
        }
    </style>
</head>
<body class="bg-gray-100 min-h-screen py-8">
    <div class="container mx-auto px-4">
        <h1 class="text-3xl font-bold text-center mb-8">DocImprover</h1>
        
        <!-- Upload Section -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-8">
            <form id="uploadForm" class="space-y-4">
                <label for="file" class="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-500 transition-all duration-200 group">
                    <div class="flex flex-col items-center justify-center space-y-2 transition-all duration-200 transform group-hover:scale-105">
                        <svg class="w-10 h-10 text-gray-400 mb-2 transition-colors duration-200 group-hover:text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                        </svg>
                        <span class="text-gray-600 transition-colors duration-200 group-hover:text-blue-600">Drop your document here or click to browse</span>
                        <span class="text-sm text-gray-400 transition-colors duration-200 group-hover:text-blue-400">.docx files only</span>
                    </div>
                    <input type="file" id="file" class="hidden" accept=".docx">
                </label>
                
                <div id="fileInfo" class="text-gray-600 text-sm hidden">
                    Selected file: <span id="fileName"></span>
                </div>
                
                <button id="uploadButton" type="submit" class="w-full bg-blue-500 text-white py-2 px-4 rounded-lg hover:bg-blue-600 transition-colors duration-200 hidden">
                    Upload and Improve
                </button>
            </form>
            
            <div id="message" class="hidden"></div>
        </div>
        
        <!-- Results Section -->
        <div id="results" class="bg-white rounded-lg shadow-md p-6 hidden">
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div class="p-4 rounded-lg border border-gray-200 diff-highlight">
                    <h2 class="text-xl font-semibold mb-4 text-gray-700">Original Text</h2>
                    <div id="originalText" class="prose max-w-none text-gray-600 whitespace-pre-wrap"></div>
                </div>
                <div class="p-4 rounded-lg border border-gray-200 diff-highlight bg-blue-50">
                    <h2 class="text-xl font-semibold mb-4 text-blue-700">Improved Version</h2>
                    <div id="improvements" class="prose max-w-none text-gray-800 mb-4"></div>
                    <div id="downloadContainer" class="hidden">
                        <a id="downloadLink" href="#" class="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors duration-200">
                            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                            </svg>
                            Download Improved Document
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const fileInput = document.getElementById('file');
        const fileInfo = document.getElementById('fileInfo');
        const fileName = document.getElementById('fileName');
        const uploadButton = document.getElementById('uploadButton');
        const message = document.getElementById('message');
        const results = document.getElementById('results');
        const originalText = document.getElementById('originalText');
        const improvements = document.getElementById('improvements');
        const downloadContainer = document.getElementById('downloadContainer');
        const downloadLink = document.getElementById('downloadLink');
        const dropZone = document.querySelector('label[for="file"]');

        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
            document.body.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        // Handle drop zone highlighting
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, unhighlight, false);
        });

        function highlight(e) {
            dropZone.classList.add('border-blue-500', 'bg-blue-50', 'scale-105');
            dropZone.querySelector('svg').classList.add('text-blue-500');
            dropZone.querySelector('span').classList.add('text-blue-600');
        }

        function unhighlight(e) {
            dropZone.classList.remove('border-blue-500', 'bg-blue-50', 'scale-105');
            dropZone.querySelector('svg').classList.remove('text-blue-500');
            dropZone.querySelector('span').classList.remove('text-blue-600');
        }

        // Handle dropped files
        dropZone.addEventListener('drop', handleDrop, false);

        function handleDrop(e) {
            const dt = e.dataTransfer;
            const file = dt.files[0];
            
            if (file && file.name.toLowerCase().endsWith('.docx')) {
                fileInput.files = dt.files;
                fileName.textContent = file.name;
                fileInfo.classList.remove('hidden');
                uploadButton.classList.remove('hidden');
            } else {
                message.textContent = 'Please upload a Word document (.docx)';
                message.classList.remove('hidden', 'bg-blue-100', 'text-blue-700', 'bg-green-100', 'text-green-700');
                message.classList.add('bg-red-100', 'text-red-700', 'p-4', 'rounded-lg', 'mb-4');
            }
        }

        // Handle file selection through input
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                fileName.textContent = file.name;
                fileInfo.classList.remove('hidden');
                uploadButton.classList.remove('hidden');
                message.classList.add('hidden');
            }
        });

        // Handle form submission
        document.getElementById('uploadForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Show loading state
            uploadButton.disabled = true;
            uploadButton.innerHTML = '<span class="animate-pulse">Processing...</span>';
            message.textContent = 'Uploading and processing document...';
            message.classList.remove('hidden', 'bg-red-100', 'text-red-700');
            message.classList.add('bg-blue-100', 'text-blue-700', 'p-4', 'rounded-lg', 'mb-4');

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    // Hide any previous messages
                    message.classList.add('hidden');

                    // Display results
                    originalText.textContent = data.original_text;
                    improvements.innerHTML = marked.parse(data.improvements);
                    results.classList.remove('hidden');
                    
                    // Set up download link
                    downloadLink.href = `/download/${data.improved_file}`;
                    downloadContainer.classList.remove('hidden');
                    
                    // Scroll to results
                    results.scrollIntoView({ behavior: 'smooth' });
                    
                    // Reset form for next upload
                    fileInput.value = '';
                    fileInfo.classList.add('hidden');
                } else {
                    message.textContent = data.error || 'An error occurred';
                    message.classList.remove('bg-blue-100', 'text-blue-700', 'bg-green-100', 'text-green-700');
                    message.classList.add('bg-red-100', 'text-red-700');
                }
            } catch (error) {
                console.error('Error:', error);
                message.textContent = 'An error occurred while processing the document';
                message.classList.remove('bg-blue-100', 'text-blue-700', 'bg-green-100', 'text-green-700');
                message.classList.add('bg-red-100', 'text-red-700');
            } finally {
                // Reset button state
                uploadButton.disabled = false;
                uploadButton.innerHTML = 'Upload and Improve';
                uploadButton.classList.add('hidden');
            }
        }); 

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults (e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, unhighlight, false);
        });

        function highlight(e) {
            dropZone.classList.add('border-primary');
        }

        function unhighlight(e) {
            dropZone.classList.remove('border-primary');
        }

        dropZone.addEventListener('drop', handleDrop, false);

        function handleDrop(e) {
            const dt = e.dataTransfer;
            const file = dt.files[0];

            fileInput.files = dt.files;
            if (file) {
                fileName.textContent = file.name;
                fileInfo.classList.remove('hidden');
                uploadButton.classList.remove('hidden');
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and process document."""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if not file.filename.endswith('.docx'):
        return jsonify({"error": "Please upload a Word document (.docx)"}), 400

    try:
        # Save uploaded file to temp directory
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
            file.save(temp_file.name)
            doc = Document(temp_file.name)

            # Process document
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
            
            # Save improved document
            improved_filename = f"improved_{file.filename}"
            improved_path = os.path.join(tempfile.gettempdir(), improved_filename)
            improved_doc.save(improved_path)

            # Add file path to result
            result['improved_file'] = improved_filename
            
            return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        return jsonify({"error": f"Error processing document: {str(e)}"}), 400

@app.route('/download/<filename>')
def download_file(filename):
    """Download the improved document."""
    try:
        return send_from_directory(
            tempfile.gettempdir(),
            filename,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({"error": f"Error downloading file: {str(e)}"}), 400

if __name__ == '__main__':
    app.run(debug=True)
