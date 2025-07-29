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
        Find the main proposal document (PDF only).
        """
        if not proposal_dir.exists():
            self.logger.error(f"Proposal directory not found: {proposal_dir}")
            return None

        # Look for PDF files only
        pdf_patterns = [
            "main_proposal.pdf",
            "*proposal*.pdf",
            "*main*.pdf",
            "*submission*.pdf",
            "submission*.pdf"
        ]

        for pattern in pdf_patterns:
            matches = list(proposal_dir.rglob(pattern))
            if matches:
                self.logger.info(f"Found main proposal: {matches[0]}")
                return matches[0]

        self.logger.error(f"No main proposal found in {proposal_dir}")
        return None
    
    def find_supporting_docs(self, supporting_dir: Path) -> List[Path]:
        """Find supporting documents (PDF, TXT, MD, CSV only)."""
        if not supporting_dir.exists():
            self.logger.warning(f"Supporting docs directory not found: {supporting_dir}")
            return []

        # Find all supported files (including sub-folders)
        supported_extensions = ['.pdf', '.txt', '.md', '.csv']
        all_files = []
        
        for ext in supported_extensions:
            all_files.extend(list(supporting_dir.rglob(f"*{ext}")))

        self.logger.info(f"Found {len(all_files)} supporting documents")
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
        
        # Also check supporting_docs subdirectory if it exists
        supporting_docs_dir = solicitation_dir / "supporting_docs"
        if supporting_docs_dir.exists():
            csv_files.extend(list(supporting_docs_dir.rglob("*.csv")))
            md_files.extend(list(supporting_docs_dir.rglob("*.md")))
            pdf_files.extend(list(supporting_docs_dir.rglob("*.pdf")))
        
        self.logger.info(f"Found solicitation documents: {len(csv_files)} CSV, {len(md_files)} MD, {len(pdf_files)} PDF")
        
        return {
            "csv": csv_files,
            "md": md_files,
            "pdf": pdf_files
        }
    
    def validate_file_structure(self, proposal_dir: Path, supporting_dir: Path, solicitation_dir: Path) -> Dict[str, Any]:
        """Validate the file structure and return validation results."""
        validation = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # Check proposal directory
        if not proposal_dir.exists():
            validation["errors"].append(f"Proposal directory not found: {proposal_dir}")
            validation["valid"] = False
        else:
            main_proposal = self.find_main_proposal(proposal_dir)
            if not main_proposal:
                validation["errors"].append(f"No main proposal PDF found in {proposal_dir}")
                validation["valid"] = False
            else:
                validation["warnings"].append(f"Found main proposal: {main_proposal.name}")

        # Check supporting documents directory
        if supporting_dir.exists():
            supporting_docs = self.find_supporting_docs(supporting_dir)
            if supporting_docs:
                validation["warnings"].append(f"Found {len(supporting_docs)} supporting documents")
            else:
                validation["warnings"].append("No supporting documents found")
        else:
            validation["warnings"].append(f"Supporting docs directory not found: {supporting_dir}")

        # Check solicitation directory
        if solicitation_dir.exists():
            solicitation_files = self.find_solicitation_docs(solicitation_dir)
            total_solicitation = len(solicitation_files["csv"]) + len(solicitation_files["md"]) + len(solicitation_files["pdf"])
            if total_solicitation > 0:
                validation["warnings"].append(f"Found {total_solicitation} solicitation documents")
            else:
                validation["warnings"].append("No solicitation documents found")
        else:
            validation["warnings"].append(f"Solicitation directory not found: {solicitation_dir}")

        return validation
    
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