# DocImprover

A web application that uses GPT-4 to improve your documents. Upload a Word document and get suggestions for improving grammar, style, clarity, and professional tone.

## Setup

1. Install dependencies:
   ```bash
   poetry install
   ```

2. Create a `.env` file in the project root with your OpenAI API key:
   ```
   OPENAI_API_KEY=your-api-key-here
   ```

## Running the Application

1. Start the Flask server:
   ```bash
   poetry run python -m doc_improver.app
   ```

2. Open your browser to http://localhost:5000

3. Upload a Word document and get AI-powered suggestions for improvement!

## Features

- Upload Word documents (.docx)
- Get AI-powered suggestions for:
  - Grammar and style
  - Clarity and conciseness
  - Structure and organization
  - Professional tone
- Modern, responsive UI with drag-and-drop support
- Markdown formatting for easy-to-read suggestions