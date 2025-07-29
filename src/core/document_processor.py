"""
Unified document processor using Marker for PDF processing with LLM enhancement.
Supports PDF, CSV, and MD files with OCR and LLM processing.
"""

import logging
import csv
import json
import os
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from marker.services.openai import OpenAIService


class DocumentProcessor:
    """Unified document processor using Marker for PDF processing."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Load environment variables from .env file
        load_dotenv()
        
        # Initialize Marker converter with OpenAI LLM enhancement
        try:
            # Load configuration
            from ..utils.config_loader import ConfigLoader
            config_loader = ConfigLoader()
            llm_config = config_loader.get_llm_config("document_processing")
            
            # Create config for OpenAIService
            openai_config = {
                "openai_api_key": os.getenv("OPENAI_API_KEY"),
                "openai_model": llm_config.get("model"),
                "openai_base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                "openai_image_format": "png"
            }
            
            # Create OpenAI service for LLM enhancement with proper configuration
            self.openai_service = OpenAIService(config=openai_config)
            self.logger.info("OpenAIService created successfully")
            
            # Initialize Marker converter with LLM service using config
            self.converter = PdfConverter(
                artifact_dict=create_model_dict(),
                llm_service="marker.services.openai.OpenAIService",
                config=openai_config
            )
            self.logger.info("Marker converter initialized successfully with OpenAI LLM")
        except Exception as e:
            self.logger.error(f"Failed to initialize Marker converter: {e}")
            self.converter = None
    
    def _get_processed_document_path(self, original_path: Path, doc_type: str) -> Path:
        """Get the path for a processed document."""
        if doc_type == "proposal":
            processed_dir = original_path.parent / "processed"
        else:  # solicitation
            processed_dir = original_path.parent / "processed"
        
        base_name = original_path.stem
        if doc_type == "supporting":
            return processed_dir / f"supporting_{base_name}_processed.json"
        elif doc_type == "solicitation":
            return processed_dir / f"solicitation_{base_name}_processed.json"
        else:
            return processed_dir / f"{base_name}_processed.json"
    
    def _load_processed_document(self, processed_path: Path) -> Dict[str, Any]:
        """Load a processed document from JSON."""
        try:
            with open(processed_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.logger.info(f"Loaded processed document: {list(data.keys()) if data else 'None'}")
                return data
        except Exception as e:
            self.logger.warning(f"Failed to load processed document {processed_path}: {e}")
            return None
    
    def _is_document_processed(self, original_path: Path, doc_type: str) -> bool:
        """Check if a document has already been processed."""
        processed_path = self._get_processed_document_path(original_path, doc_type)
        return processed_path.exists()
    
    def _process_document_unified(self, file_path: Path, doc_type: str) -> Dict[str, Any]:
        """Unified document processing method for all document types."""
        try:
            self.logger.info(f"Processing {file_path.name} with unified method")
            
            ext = file_path.suffix.lower()
            
            # Handle different file types
            if ext == '.pdf':
                return self._process_pdf_document(file_path, doc_type)
            elif ext == '.csv':
                return self._process_csv_document(file_path, doc_type)
            elif ext == '.md':
                return self._process_md_document(file_path, doc_type)
            else:
                raise ValueError(f"Unsupported file type: {ext}")
                
        except Exception as e:
            self.logger.error(f"Failed to process {file_path}: {e}")
            raise RuntimeError(f"Document processing failed for {file_path.name}: {str(e)}")
    
    def _process_pdf_document(self, file_path: Path, doc_type: str) -> Dict[str, Any]:
        """Process PDF documents using Marker with LLM enhancement."""
        if not self.converter:
            raise RuntimeError("Marker converter not initialized")
        
        # Process PDF with OCR and LLM
        rendered = self.converter(str(file_path))
        md_text, _, images = text_from_rendered(rendered)
        
        # Validate that we got actual content
        if not md_text or md_text.strip() == "":
            raise RuntimeError(f"PDF processing failed for {file_path.name}: extracted text is empty")
        
        return {
            "full_text": md_text,
            "file_path": str(file_path),
            "file_name": file_path.name,
            "format": ".pdf",
            "type": doc_type,
            "processed_with": "marker_pdf_ocr",
            "sections": self._extract_sections_from_markdown(md_text),
            "metadata": {"format": "pdf", "processed_with": "marker_pdf_ocr"},
            "images_count": len(images) if images else 0
        }
    
    def _process_csv_document(self, file_path: Path, doc_type: str) -> Dict[str, Any]:
        """Process CSV documents to readable text format."""
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Convert CSV to readable text format
        text_lines = []
        for i, row in enumerate(rows):
            if i == 0:  # Header row
                text_lines.append(" | ".join(row))
                text_lines.append("-" * len(" | ".join(row)))
            else:
                text_lines.append(" | ".join(row))
        
        csv_text = "\n".join(text_lines)
        
        # Validate that we got actual content
        if not csv_text or csv_text.strip() == "":
            raise RuntimeError(f"CSV processing failed for {file_path.name}: extracted text is empty")
        
        return {
            "full_text": csv_text,
            "file_path": str(file_path),
            "file_name": file_path.name,
            "format": ".csv",
            "type": doc_type,
            "processed_with": "csv_processor",
            "sections": [{"title": "CSV Data", "content": csv_text, "level": 1}],
            "metadata": {"format": "csv", "processed_with": "csv_processor"},
            "images_count": 0
        }
    
    def _process_md_document(self, file_path: Path, doc_type: str) -> Dict[str, Any]:
        """Process Markdown documents."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # Validate that we got actual content
        if not content or content.strip() == "":
            raise RuntimeError(f"Markdown processing failed for {file_path.name}: file is empty")
        
        return {
            "full_text": content,
            "file_path": str(file_path),
            "file_name": file_path.name,
            "format": ".md",
            "type": doc_type,
            "processed_with": "md_processor",
            "sections": [{"title": "Markdown Document", "content": content, "level": 1}],
            "metadata": {"format": "md", "processed_with": "md_processor"},
            "images_count": 0
        }

    
    def _extract_sections_from_markdown(self, markdown_content: str) -> List[Dict[str, Any]]:
        """Extract sections from markdown content."""
        sections = []
        lines = markdown_content.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            if line.startswith('#'):
                # Save previous section if exists
                if current_section:
                    current_section['content'] = '\n'.join(current_content).strip()
                    sections.append(current_section)
                
                # Start new section
                level = len(line) - len(line.lstrip('#'))
                title = line.lstrip('#').strip()
                current_section = {
                    'title': title,
                    'level': level,
                    'content': ''
                }
                current_content = []
            else:
                current_content.append(line)
        
        # Add final section
        if current_section:
            current_section['content'] = '\n'.join(current_content).strip()
            sections.append(current_section)
        
        return sections
    
    def _save_processed_document(self, original_path: Path, processed_data: Dict[str, Any], doc_type: str):
        """Save processed document to JSON file."""
        try:
            processed_dir = original_path.parent / "processed"
            processed_dir.mkdir(exist_ok=True)
            
            base_name = original_path.stem
            if doc_type == "supporting":
                processed_path = processed_dir / f"supporting_{base_name}_processed.json"
            elif doc_type == "solicitation":
                processed_path = processed_dir / f"solicitation_{base_name}_processed.json"
            else:
                processed_path = processed_dir / f"{base_name}_processed.json"
            
            # Create wrapper structure for saved file
            saved_doc = {
                "original_file": str(original_path),
                "processed_at": str(Path.cwd()),
                "format": original_path.suffix,
                "content": processed_data,  # Store the standardized structure under 'content'
                "file_size_bytes": original_path.stat().st_size if original_path.exists() else 0,
                "type": f"{doc_type}_document",
                "processed_with": processed_data.get("processed_with"),
                "images_count": processed_data.get("images_count", 0)
            }
            
            with open(processed_path, "w", encoding="utf-8") as f:
                json.dump(saved_doc, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved processed document to: {processed_path}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save processed document: {e}")
    
    def process_main_proposal(self, proposal_path: Path) -> Dict[str, Any]:
        """Process main proposal document using unified method."""
        self.logger.info(f"Processing main proposal: {proposal_path}")
        
        # Check if already processed
        if self._is_document_processed(proposal_path, "proposal"):
            self.logger.info(f"Using cached processed document: {proposal_path.name}")
            processed_path = self._get_processed_document_path(proposal_path, "proposal")
            processed_data = self._load_processed_document(processed_path)
            if processed_data:
                # Extract the standardized structure from the cached wrapper
                return processed_data["content"]
        
        # Process with unified method
        doc_data = self._process_document_unified(proposal_path, "proposal")
        
        # Save processed document
        self._save_processed_document(proposal_path, doc_data, "proposal")
        
        return doc_data
    
    def process_supporting_docs(self, supporting_dir: Path) -> List[Dict[str, Any]]:
        """Process supporting documents using Marker."""
        if not supporting_dir.exists():
            self.logger.warning(f"Supporting docs directory not found: {supporting_dir}")
            return []

        # Find all supported files (including sub-folders)
        supported_extensions = ['.pdf', '.txt', '.md', '.csv']
        all_files = []
        for ext in supported_extensions:
            all_files.extend(list(supporting_dir.rglob(f"*{ext}")))

        if not all_files:
            self.logger.warning(f"No supporting documents found in {supporting_dir}")
            return []

        self.logger.info(f"Processing {len(all_files)} supporting documents")

        supporting_docs = []
        needs_processing = False

        for file_path in all_files:
            # Check if already processed
            if self._is_document_processed(file_path, "supporting"):
                self.logger.info(f"Using cached processed document: {file_path.name}")
                processed_path = self._get_processed_document_path(file_path, "supporting")
                processed_data = self._load_processed_document(processed_path)
                if processed_data:
                    # Extract the standardized structure from the cached wrapper
                    doc_data = processed_data["content"]
                    supporting_docs.append(doc_data)
                    continue
            
            needs_processing = True
            self.logger.info(f"Processing supporting document: {file_path.name}")
            doc_data = self._process_document_unified(file_path, "supporting")
            supporting_docs.append(doc_data)

        # Save processed supporting documents only if we processed new ones
        if needs_processing:
            self._save_processed_supporting_docs(supporting_docs, supporting_dir)

        return supporting_docs
    
    def _save_processed_supporting_docs(self, supporting_docs: List[Dict[str, Any]], supporting_dir: Path):
        """Save processed supporting documents as individual files."""
        try:
            processed_dir = supporting_dir.parent / "processed"
            processed_dir.mkdir(exist_ok=True)
            
            for doc in supporting_docs:
                # Create individual processed file for each supporting document
                original_path = Path(doc["file_path"])
                base_name = original_path.stem
                processed_path = processed_dir / f"supporting_{base_name}_processed.json"
                
                processed_doc = {
                    "original_file": doc["file_path"],
                    "processed_at": str(Path.cwd()),
                    "format": doc.get("format"),
                    "content": doc,
                    "file_size_bytes": original_path.stat().st_size if original_path.exists() else 0,
                    "type": "supporting_document",
                    "processed_with": doc.get("processed_with"),
                    "images_count": doc.get("images_count", 0)
                }
                
                with open(processed_path, "w", encoding="utf-8") as f:
                    json.dump(processed_doc, f, indent=2, ensure_ascii=False)
                
                self.logger.info(f"Saved processed supporting document to: {processed_path}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save processed supporting documents: {e}")
    
    def process_solicitation_docs(self, solicitation_dir: Path) -> Dict[str, Any]:
        """Process solicitation documents using Marker."""
        if not solicitation_dir.exists():
            raise FileNotFoundError(f"Solicitation directory not found: {solicitation_dir}")

        self.logger.info(f"Processing solicitation documents from: {solicitation_dir}")

        # Import file discovery to find documents
        from .file_discovery import FileDiscovery
        file_discovery = FileDiscovery()
        solicitation_files = file_discovery.find_solicitation_docs(solicitation_dir)

        # Process each file type
        all_docs = []
        needs_processing = False

        # Process all files with Marker
        all_files = solicitation_files["csv"] + solicitation_files["md"] + solicitation_files["pdf"]
        
        for file_path in all_files:
            # Check if already processed
            if self._is_document_processed(file_path, "solicitation"):
                self.logger.info(f"Using cached processed document: {file_path.name}")
                processed_path = self._get_processed_document_path(file_path, "solicitation")
                processed_data = self._load_processed_document(processed_path)
                if processed_data:
                    # Extract the standardized structure from the cached wrapper
                    doc_data = processed_data["content"]
                    all_docs.append(doc_data)
                    continue
            
            needs_processing = True
            self.logger.info(f"Processing solicitation document: {file_path.name}")
            doc_data = self._process_document_unified(file_path, "solicitation")
            all_docs.append(doc_data)

        # Save processed solicitation documents only if we processed new ones
        if needs_processing:
            self._save_processed_solicitation_docs(all_docs, solicitation_dir)

        return {
            "solicitation_documents": all_docs,
            "total_documents": len(all_docs)
        }
    
    def _save_processed_solicitation_docs(self, solicitation_docs: List[Dict[str, Any]], solicitation_dir: Path):
        """Save processed solicitation documents as individual files."""
        try:
            processed_dir = solicitation_dir / "processed"
            processed_dir.mkdir(exist_ok=True)
            
            for doc in solicitation_docs:
                # Create individual processed file for each solicitation document
                original_path = Path(doc["file_path"])
                base_name = original_path.stem
                processed_path = processed_dir / f"solicitation_{base_name}_processed.json"
                
                processed_doc = {
                    "original_file": doc["file_path"],
                    "processed_at": str(Path.cwd()),
                    "format": doc.get("format"),
                    "content": doc,
                    "file_size_bytes": original_path.stat().st_size if original_path.exists() else 0,
                    "type": "solicitation_document",
                    "processed_with": doc.get("processed_with"),
                    "images_count": doc.get("images_count", 0)
                }
                
                with open(processed_path, "w", encoding="utf-8") as f:
                    json.dump(processed_doc, f, indent=2, ensure_ascii=False)
                
                self.logger.info(f"Saved processed solicitation document to: {processed_path}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save processed solicitation documents: {e}") 