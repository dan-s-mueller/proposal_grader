#!/usr/bin/env python3
"""
Proposal Grading Pipeline

This script orchestrates the complete proposal grading process:
1. Parse solicitation PDF to extract evaluation criteria
2. Convert criteria to markdown format
3. Convert markdown to JSON rubric
4. Create dummy files for testing
5. Grade the proposal using the generated rubric
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list, description: str) -> bool:
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"COMMAND: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run complete proposal grading pipeline")
    parser.add_argument("--solicitation", default="documents/solicitations/solicitation.pdf", 
                       type=Path, help="Path to solicitation PDF")
    parser.add_argument("--proposal-dir", default="documents/proposal", 
                       type=Path, help="Path to proposal directory")
    parser.add_argument("--openai-key", help="OpenAI API key (or set OPENAI_API_KEY env var)")
    parser.add_argument("--skip-dummy-files", action="store_true", 
                       help="Skip creating dummy files")
    parser.add_argument("--skip-solicitation-parse", action="store_true",
                       help="Skip solicitation parsing (use existing rubrics)")
    parser.add_argument("--output-dir", default="output", type=Path,
                       help="Output directory for results")
    
    args = parser.parse_args()
    
    # Create output directory
    args.output_dir.mkdir(exist_ok=True)
    
    print("🚀 Starting Proposal Grading Pipeline")
    print(f"Solicitation: {args.solicitation}")
    print(f"Proposal Directory: {args.proposal_dir}")
    print(f"Output Directory: {args.output_dir}")
    
    # Step 1: Parse solicitation PDF
    if not args.skip_solicitation_parse:
        if not args.solicitation.exists():
            print(f"❌ Solicitation PDF not found: {args.solicitation}")
            return False
        
        md_rubric_path = args.output_dir / "evaluation_rubric.md"
        success = run_command([
            sys.executable, "solicitation_parser.py",
            str(args.solicitation),
            str(md_rubric_path)
        ], "Parsing solicitation PDF to extract evaluation criteria")
        
        if not success:
            print("❌ Failed to parse solicitation")
            return False
    else:
        print("⏭️  Skipping solicitation parsing")
        md_rubric_path = args.output_dir / "evaluation_rubric.md"
        if not md_rubric_path.exists():
            print(f"❌ Markdown rubric not found: {md_rubric_path}")
            return False
    
    # Step 2: Convert markdown to JSON rubric
    success = run_command([
        sys.executable, "md_to_rubric_json.py",
        str(md_rubric_path),
        "--output-dir", "rubrics",
        "--prompts-dir", "prompts"
    ], "Converting markdown rubric to JSON format")
    
    if not success:
        print("❌ Failed to convert markdown to JSON")
        return False
    
    # Step 3: Create dummy files (if not skipped)
    if not args.skip_dummy_files:
        success = run_command([
            sys.executable, "create_dummy_files.py",
            "--output-dir", str(args.proposal_dir),
            "--overwrite"
        ], "Creating dummy proposal files for testing")
        
        if not success:
            print("❌ Failed to create dummy files")
            return False
    else:
        print("⏭️  Skipping dummy file creation")
    
    # Step 4: List required files
    print(f"\n{'='*60}")
    print("STEP: Listing required files")
    print('='*60)
    
    success = run_command([
        sys.executable, "proposal_grader.py",
        "--list-required"
    ], "Listing required proposal files")
    
    if not success:
        print("❌ Failed to list required files")
        return False
    
    # Step 5: Grade the proposal
    cmd = [
        sys.executable, "proposal_grader.py",
        "--bundle", str(args.proposal_dir),
        "--output", str(args.output_dir / "results.json"),
        "--report", str(args.output_dir / "evaluation_report.md")
    ]
    
    if args.openai_key:
        cmd.extend(["--openai-key", args.openai_key])
    
    success = run_command(cmd, "Grading proposal using generated rubric")
    
    if not success:
        print("❌ Failed to grade proposal")
        return False
    
    # Step 6: Display results
    print(f"\n{'='*60}")
    print("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
    print('='*60)
    
    results_file = args.output_dir / "results.json"
    report_file = args.output_dir / "evaluation_report.md"
    
    if results_file.exists():
        print(f"📊 Results saved to: {results_file}")
    
    if report_file.exists():
        print(f"📋 Detailed report saved to: {report_file}")
    
    print("\n📁 Generated files:")
    print(f"  - {md_rubric_path}")
    print(f"  - rubrics/phase1_technical.json")
    print(f"  - rubrics/phase1_commercial.json")
    print(f"  - prompts/ (various .md files)")
    print(f"  - {results_file}")
    print(f"  - {report_file}")
    
    print("\n✨ Next steps:")
    print("  1. Review the evaluation report")
    print("  2. Check the generated rubrics and prompts")
    print("  3. Replace dummy files with real proposal documents")
    print("  4. Re-run grading with real documents")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 