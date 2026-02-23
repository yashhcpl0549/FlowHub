"""
Validation script for Diversity Score Checker
Validates that input files are PDFs
"""
import sys
import json
import os
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate.py <config_json_path>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    # Load config
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print("=" * 50)
    print("VALIDATING INPUT FILES")
    print("=" * 50)
    
    errors = []
    warnings = []
    
    # Check if files exist
    if not config.get('files'):
        errors.append("No input files provided")
    
    pdf_count = 0
    for file_info in config.get('files', []):
        file_path = file_info.get('local_path')
        filename = file_info.get('filename', '')
        
        if not file_path:
            errors.append(f"Missing file path for: {filename}")
            continue
        
        if not os.path.exists(file_path):
            errors.append(f"File not found: {file_path}")
            continue
        
        # Check file extension
        if filename.lower().endswith('.pdf'):
            pdf_count += 1
            print(f"✓ Valid PDF: {filename}")
        else:
            warnings.append(f"Non-PDF file will be skipped: {filename}")
    
    print()
    
    # Report warnings
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  ⚠ {w}")
        print()
    
    # Report errors
    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  ✗ {e}")
        print()
        print("Validation FAILED")
        sys.exit(1)
    
    if pdf_count == 0:
        print("ERROR: No valid PDF files found")
        sys.exit(1)
    
    print(f"Validation PASSED - {pdf_count} PDF file(s) ready for processing")
    sys.exit(0)


if __name__ == "__main__":
    main()
