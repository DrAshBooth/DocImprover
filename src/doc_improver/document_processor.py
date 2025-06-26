"""Document processing module for DocImprover."""
import logging
import os
import re
import pypandoc
import shutil
import tempfile
from openai import OpenAI
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from .config.config import get_settings

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
        self.system_prompt = settings.system_prompt
        self._temp_dir = tempfile.mkdtemp(prefix='docimprover_')
        self._image_map = {}  # Initialize image map

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self._cleanup_temp_dir()

    def _cleanup_temp_dir(self) -> None:
        """Clean up temporary directory."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            except Exception as e:
                logger.error(f"Error cleaning up temporary directory: {e}")
        self._temp_dir = None

    def _docx_to_markdown(self, docx_path: str) -> Tuple[str, Optional[str]]:
        """Convert a .docx file to Markdown, extracting media files."""
        media_path = os.path.join(self._temp_dir, 'media')
        try:
            os.makedirs(media_path, exist_ok=True)

            # Pandoc argument to extract media to the specified folder
            extra_args = [f'--extract-media={media_path}']
            
            markdown_str = pypandoc.convert_file(
                docx_path,
                'gfm+hard_line_breaks',
                format='docx',
                extra_args=extra_args
            )

            # Reset image map for this conversion
            self._image_map = {}

            # Process all extracted media files
            if os.path.exists(media_path):
                # First, handle standard Markdown image syntax
                markdown_str = re.sub(
                    rf'!\\[(.*)\\]\\({re.escape(media_path)}/(.*)\\)',
                    r'![\1](media/\2)',
                    markdown_str
                )
                
                # Convert HTML <img> tags to Markdown format
                img_pattern = r'<img src="([^"]+)"[^>]*>'
                for match in re.finditer(img_pattern, markdown_str):
                    img_path = match.group(1)
                    # Extract filename from path
                    img_filename = os.path.basename(img_path)
                    # Add to image map
                    self._image_map[img_filename] = img_path
                    # Replace with Markdown image syntax
                    markdown_str = markdown_str.replace(
                        match.group(0),
                        f'![{img_filename}](media/{img_filename})'
                    )
                
                logger.info(f"Converted {len(self._image_map)} images to Markdown syntax")
            
            # If no media was extracted, the folder will be empty.
            if os.path.exists(media_path) and not os.listdir(media_path):
                # No need to keep an empty media directory
                shutil.rmtree(media_path)
                media_path = None

            return markdown_str, media_path
        except Exception as e:
            logger.error(f"Error converting .docx to Markdown: {e}")
            raise

    def _markdown_to_docx(self, markdown_str: str, output_path: str, media_path: Optional[str] = None) -> None:
        """Convert Markdown string to a .docx file, re-embedding media from the resource path."""
        try:
            extra_args = []
            
            # If media was extracted, we need to ensure image references are correctly formatted
            # for pandoc to find them and the resource path is set correctly
            if media_path and os.path.exists(media_path):
                # Ensure media folder name is 'media' for consistent references
                media_dir_name = os.path.basename(media_path)
                
                # Make sure media paths in markdown are using 'media/' prefix
                if media_dir_name != 'media':
                    markdown_str = markdown_str.replace(f'{media_dir_name}/', 'media/')
                
                # Get parent directory of media folder to set as resource path
                parent_dir = os.path.dirname(media_path)
                
                # Set resource path to the directory containing media folder
                extra_args.append(f'--resource-path={parent_dir}')
                
                # Also add the temp directory itself as a resource path
                extra_args.append(f'--resource-path={self._temp_dir}')
                
                # Add verbose flag for debugging
                extra_args.append('--verbose')
                
                # Log what we're about to do
                logger.info(f"Converting Markdown to DOCX with media from: {media_path}")
                logger.info(f"Resource paths: {parent_dir}, {self._temp_dir}")
                logger.info(f"Extra args: {extra_args}")
                
                # Verify image references in Markdown string
                img_refs = re.findall(r'!\[.*?\]\((.*?)\)', markdown_str)
                logger.info(f"Found {len(img_refs)} image references in Markdown")
                for ref in img_refs:
                    logger.info(f"Image reference: {ref}")

            # Add additional resource paths for the test environment
            # Create a temporary directory with correct file structure for pandoc
            if media_path and os.path.exists(media_path):
                temp_media_dir = os.path.join(self._temp_dir, 'temp_media_for_pandoc')
                os.makedirs(temp_media_dir, exist_ok=True)
                
                # Copy all images from media_path to a structure pandoc can find
                for img_ref in re.findall(r'!\[.*?\]\((.*?)\)', markdown_str):
                    # Extract image name from path
                    img_name = os.path.basename(img_ref)
                    
                    # For absolute paths in tests, check if it's already a full file path
                    if os.path.exists(img_ref):
                        # If image reference is already a full path to an existing file
                        source_path = img_ref
                        # Use just the filename in the destination path
                        if '/' in img_ref:
                            # Create subdirectory structure if needed
                            subdir = 'media'
                            dest_dir = os.path.join(temp_media_dir, subdir)
                            os.makedirs(dest_dir, exist_ok=True)
                            dest_path = os.path.join(dest_dir, img_name)
                        else:
                            dest_path = os.path.join(temp_media_dir, img_name)
                    else:
                        # Regular case for relative paths
                        source_path = os.path.join(media_path, img_name)
                        
                        # Create proper directory structure matching img_ref
                        if '/' in img_ref:
                            # Create subdirectory structure if img_ref contains paths
                            subdir = os.path.dirname(img_ref)
                            dest_dir = os.path.join(temp_media_dir, subdir)
                            os.makedirs(dest_dir, exist_ok=True)
                            dest_path = os.path.join(temp_media_dir, img_ref)
                        else:
                            dest_path = os.path.join(temp_media_dir, img_name)
                    
                    # Only attempt to copy if source exists and source != dest
                    if os.path.exists(source_path) and source_path != dest_path:
                        # Find the image file in media_path regardless of extension if source doesn't exist exactly
                        if not os.path.exists(source_path) and os.path.exists(media_path):
                            media_files = os.listdir(media_path)
                            for file in media_files:
                                if file.startswith(img_name.split('.')[0]):
                                    alt_source_path = os.path.join(media_path, file)
                                    if os.path.exists(alt_source_path):
                                        source_path = alt_source_path
                                        break
                        
                        # Make sure destination directory exists
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        
                        try:
                            # Avoid SameFileError
                            if os.path.abspath(source_path) != os.path.abspath(dest_path):
                                shutil.copy(source_path, dest_path)
                                logger.info(f"Copied {source_path} to {dest_path} for Pandoc")
                        except Exception as e:
                            logger.warning(f"Failed to copy {source_path} to {dest_path}: {e}")
                
                # Add this directory to resource paths
                extra_args.append(f'--resource-path={temp_media_dir}')
                
                # Also make sure Pandoc can find the original media directory
                extra_args.append(f'--resource-path={media_path}')
                
                # For absolute path tests, add the parent directory as well
                parent_dir = os.path.dirname(media_path)
                extra_args.append(f'--resource-path={parent_dir}')
            
            # Convert markdown to docx
            pypandoc.convert_text(
                markdown_str,
                'docx',
                format='gfm+smart',  # Use smart extension for better typography
                outputfile=output_path,
                extra_args=extra_args
            )
            
            logger.info(f"DOCX file created successfully at: {output_path}")
            
            # Verify file was created
            if not os.path.exists(output_path):
                logger.error("DOCX file was not created despite no exceptions")
            
        except Exception as e:
            logger.error(f"Error converting Markdown to .docx: {e}", exc_info=True)
            raise

    def improve_document(self, doc_path: str) -> Dict[str, Any]:
        """
        Improve a document by converting it to Markdown, processing with an LLM,
        and converting back to .docx.
        """
        try:
            # 1. Convert .docx to Markdown and extract media
            original_markdown, media_path = self._docx_to_markdown(doc_path)

            # Save original markdown to file for testing and compatibility
            markdown_path = os.path.join(self._temp_dir, "original.md")
            with open(markdown_path, 'w', encoding='utf-8') as f:
                f.write(original_markdown)

            # 2. Send Markdown to OpenAI for improvement
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": original_markdown}
                ],
                temperature=0.7,
            )
            improved_markdown = response.choices[0].message.content

            if not improved_markdown:
                return {"error": "Failed to get a response from the LLM."}

            # Save improved markdown to file
            improved_markdown_path = os.path.join(self._temp_dir, "improved.md")
            with open(improved_markdown_path, 'w', encoding='utf-8') as f:
                f.write(improved_markdown)

            # 3. Convert improved Markdown back to .docx, re-embedding media
            output_filename = f"improved_{Path(doc_path).name}"
            output_path = os.path.join(self._temp_dir, output_filename)
            self._markdown_to_docx(improved_markdown, output_path, media_path)

            return {
                "original_markdown": original_markdown,
                "improved_markdown": improved_markdown,
                "improved_docx_path": output_path,
                "media_path": media_path,
                "markdown_path": markdown_path,  # Add original markdown path for test compatibility
                "success": True
            }

        except Exception as e:
            logger.error(f"Error in improve_document workflow: {e}")
            return {"error": str(e)}
