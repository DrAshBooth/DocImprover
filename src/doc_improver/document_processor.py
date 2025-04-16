"""Document processing module for DocImprover."""
from docx import Document
from openai import OpenAI
from .config import get_settings
import logging

logger = logging.getLogger('docimprover')

class DocumentProcessor:
    """Process documents using OpenAI's GPT models."""

    def __init__(self):
        """Initialize the document processor."""
        settings = get_settings()
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url="https://api.openai.com/v1"
        )
        self.model = settings.model_name

    def extract_text(self, doc: Document) -> str:
        """Extract text from a Word document."""
        full_text = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                full_text.append(paragraph.text)
        return "\n".join(full_text)

    def improve_document(self, doc: Document) -> dict:
        """Improve the document using GPT-4."""
        text = self.extract_text(doc)
        
        if not text.strip():
            return {"error": "Document is empty"}

        try:
            import os
            logger.debug("API key loaded from environment")
            logger.debug("OpenAI client initialized")
            logger.debug("Making OpenAI API call...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": (
                        "You are a professional document improver. Your task is to improve the given text "
                        "while maintaining its original meaning. Focus on enhancing:\n"
                        "- Grammar and style\n"
                        "- Clarity and conciseness\n"
                        "- Structure and organization\n"
                        "- Professional tone\n\n"
                        "IMPORTANT: Format your response using markdown syntax:\n"
                        "- Use # for main headings\n"
                        "- Use ## for subheadings\n"
                        "- Use * or - for bullet points\n"
                        "- Use **text** for bold\n"
                        "- Use *text* for italics\n"
                        "- Use proper paragraph spacing\n\n"
                        "Only provide the improved version of the text. Do not include any explanations."
                    )},
                    {"role": "user", "content": text}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            logger.debug(f"OpenAI API response received: {response.model} model used")
            
            return {
                "success": True,
                "improvements": response.choices[0].message.content,
                "original_text": text
            }
            
        except Exception as e:
            return {"error": f"Error processing document: {str(e)}"}
