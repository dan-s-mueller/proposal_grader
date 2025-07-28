"""
File discovery module for finding proposal and supporting documents.
Handles pattern matching and file validation with support for multiple formats.
"""

import logging
import fnmatch
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional


class FileDiscovery:
    """Handles discovery and validation of proposal files."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def find_main_proposal(self, proposal_dir: Path) -> Optional[Path]:
        """
        Find the main proposal document (DOCX or PDF).
        Prioritizes DOCX files as specified in USER_GUIDE.md.
        """
        if not proposal_dir.exists():
            self.logger.error(f"Proposal directory not found: {proposal_dir}")
            return None
        
        # Look for DOCX files first (preferred)
        docx_patterns = [
            "main_proposal.docx",
            "*proposal*.docx",
            "*main*.docx",
            "*submission*.docx",  # Added for submission files
            "*.docx"  # Fallback to any DOCX file
        ]
        
        for pattern in docx_patterns:
            matches = list(proposal_dir.rglob(pattern))
            if matches:
                self.logger.info(f"Found main proposal: {matches[0]}")
                return matches[0]
        
        # Fallback to PDF patterns
        pdf_patterns = [
            "main_proposal.pdf",
            "*proposal*.pdf",
            "*main*.pdf",
            "*submission*.pdf",  # Added for submission files
            "submission*.pdf"
        ]
        
        for pattern in pdf_patterns:
            matches = list(proposal_dir.rglob(pattern))
            if matches:
                self.logger.info(f"Found main proposal (PDF): {matches[0]}")
                return matches[0]
        
        self.logger.error(f"No main proposal found in {proposal_dir}")
        return None
    
    def find_supporting_docs(self, supporting_dir: Path) -> List[Path]:
        """
        Find supporting documents in the supporting_docs directory.
        Supports PDF and DOCX files.
        """
        if not supporting_dir.exists():
            self.logger.warning(f"Supporting docs directory not found: {supporting_dir}")
            return []
        
        # Find all PDF and DOCX files in supporting_docs (including sub-folders)
        pdf_files = list(supporting_dir.rglob("*.pdf"))
        docx_files = list(supporting_dir.rglob("*.docx"))
        
        all_files = pdf_files + docx_files
        
        self.logger.info(f"Found {len(all_files)} supporting documents ({len(pdf_files)} PDF, {len(docx_files)} DOCX)")
        for doc_file in all_files:
            self.logger.debug(f"Supporting doc: {doc_file.name}")
        
        return all_files
    
    def find_solicitation_docs(self, solicitation_dir: Path) -> Dict[str, List[Path]]:
        """
        Find solicitation documents in various formats (CSV, MD, PDF).
        Returns organized by file type.
        """
        if not solicitation_dir.exists():
            self.logger.warning(f"Solicitation directory not found: {solicitation_dir}")
            return {"csv": [], "md": [], "pdf": []}
        
        # Find files by type (including sub-folders)
        csv_files = list(solicitation_dir.rglob("*.csv"))
        md_files = list(solicitation_dir.rglob("*.md"))
        pdf_files = list(solicitation_dir.rglob("*.pdf"))
        
        self.logger.info(f"Found solicitation documents: {len(csv_files)} CSV, {len(md_files)} MD, {len(pdf_files)} PDF")
        
        return {
            "csv": csv_files,
            "md": md_files,
            "pdf": pdf_files
        }
    
    def validate_file_structure(self, proposal_dir: Path, supporting_dir: Path, solicitation_dir: Path = None) -> Dict[str, Any]:
        """
        Validate the file structure and return status.
        """
        validation_result = {
            "main_proposal_found": False,
            "main_proposal_path": None,
            "supporting_docs_found": 0,
            "supporting_docs_paths": [],
            "solicitation_docs_found": {"csv": 0, "md": 0, "pdf": 0},
            "solicitation_docs_paths": {"csv": [], "md": [], "pdf": []},
            "errors": [],
            "warnings": []
        }
        
        # Check main proposal
        main_proposal = self.find_main_proposal(proposal_dir)
        if main_proposal:
            validation_result["main_proposal_found"] = True
            validation_result["main_proposal_path"] = str(main_proposal)
        else:
            validation_result["errors"].append("Main proposal not found")
        
        # Check supporting docs
        supporting_docs = self.find_supporting_docs(supporting_dir)
        validation_result["supporting_docs_found"] = len(supporting_docs)
        validation_result["supporting_docs_paths"] = [str(doc) for doc in supporting_docs]
        
        if len(supporting_docs) == 0:
            validation_result["warnings"].append("No supporting documents found")
        
        # Check solicitation docs if directory provided
        if solicitation_dir:
            solicitation_docs = self.find_solicitation_docs(solicitation_dir)
            validation_result["solicitation_docs_found"] = {
                "csv": len(solicitation_docs["csv"]),
                "md": len(solicitation_docs["md"]),
                "pdf": len(solicitation_docs["pdf"])
            }
            validation_result["solicitation_docs_paths"] = {
                "csv": [str(f) for f in solicitation_docs["csv"]],
                "md": [str(f) for f in solicitation_docs["md"]],
                "pdf": [str(f) for f in solicitation_docs["pdf"]]
            }
            
            total_solicitation_docs = sum(validation_result["solicitation_docs_found"].values())
            if total_solicitation_docs == 0:
                validation_result["warnings"].append("No solicitation documents found")
        
        return validation_result
    
    def find_files_by_patterns(self, root: Path, patterns: List[str]) -> List[Path]:
        """
        Find files matching patterns in a directory tree.
        """
        found = []
        for pattern in patterns:
            for file_path in root.rglob("*"):
                if file_path.is_file() and fnmatch.fnmatch(file_path.name.lower(), pattern.lower()):
                    found.append(file_path)
        return found 