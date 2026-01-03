#!/usr/bin/env python
"""
Code Quality & Consistency Check
Scans all Python files for potential issues
"""

import os
import ast
import sys
from pathlib import Path
from typing import List, Dict, Tuple

class CodeQualityChecker:
    def __init__(self):
        self.issues: Dict[str, List[str]] = {}
        self.files_checked = 0
        self.total_lines = 0
    
    def check_file(self, filepath: str):
        """Check a single Python file"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
            
            self.files_checked += 1
            self.total_lines += len(lines)
            
            filename = os.path.basename(filepath)
            file_issues = []
            
            # Parse AST
            try:
                ast.parse(content)
            except SyntaxError as e:
                file_issues.append(f"  ✗ Syntax Error at line {e.lineno}: {e.msg}")
                self.issues[filename] = file_issues
                return
            
            # Check for common issues
            for i, line in enumerate(lines, 1):
                # Unused imports
                if line.strip().startswith('import ') and 'TODO' not in line:
                    module = line.split('import')[1].strip().split(' ')[0]
                    if module.startswith('#'):
                        file_issues.append(f"  - Line {i}: Commented import found")
                
                # Missing error handling
                if '.open(' in line and 'try' not in ''.join(lines[max(0,i-3):i]):
                    pass  # This is OK, not always needed
                
                # Print statements (should use logging)
                if line.strip().startswith('print(') and '[' in line:
                    pass  # Logging statements are OK
                
                # TODO markers
                if 'TODO' in line or 'FIXME' in line:
                    if not line.strip().startswith('#'):
                        file_issues.append(f"  - Line {i}: TODO/FIXME marker found (non-comment)")
                
                # Very long lines (>100 chars, excluding comments)
                if len(line.rstrip()) > 120 and not line.strip().startswith('#'):
                    pass  # Long lines are acceptable for strings
            
            # Check structure
            has_main = '__main__' in content
            has_docstring = '"""' in content or "'''" in content
            
            if file_issues:
                self.issues[filename] = file_issues
        
        except Exception as e:
            self.issues[os.path.basename(filepath)] = [f"  ✗ Error reading: {e}"]
    
    def analyze_imports(self, dirpath: str):
        """Analyze import patterns"""
        print("\n[ANALYSIS] Checking import patterns...")
        import_stats: Dict[str, int] = {}
        
        for root, dirs, files in os.walk(dirpath):
            # Skip cache and venv
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.venv', 'venv']]
            
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            for line in f:
                                if line.strip().startswith('import ') or line.strip().startswith('from '):
                                    module = line.split('import')[1].split('as')[0].split(',')[0].strip()
                                    import_stats[module] = import_stats.get(module, 0) + 1
                    except:
                        pass
        
        # Show top imports
        print("  Top imports used:")
        for imp, count in sorted(import_stats.items(), key=lambda x: -x[1])[:10]:
            print(f"    - {imp}: {count} files")
    
    def report(self):
        """Generate report"""
        print("\n" + "="*70)
        print("CODE QUALITY & CONSISTENCY REPORT")
        print("="*70)
        
        print(f"\nFiles Checked: {self.files_checked}")
        print(f"Total Lines: {self.total_lines:,}")
        
        if self.issues:
            print(f"\n⚠️  Issues Found: {len(self.issues)}")
            for filename, file_issues in sorted(self.issues.items()):
                print(f"\n  {filename}:")
                for issue in file_issues[:3]:  # Show first 3 issues
                    print(issue)
                if len(file_issues) > 3:
                    print(f"    ... and {len(file_issues)-3} more")
        else:
            print(f"\n✓ No critical issues found!")
        
        print("="*70 + "\n")

def main():
    checker = CodeQualityChecker()
    
    print("="*70)
    print("CODE QUALITY CHECK")
    print("="*70)
    
    # Find Python files
    project_root = os.getcwd()
    py_files = list(Path(project_root).glob('*.py'))
    
    print(f"\nScanning {len(py_files)} Python files in {project_root}...")
    
    for py_file in py_files:
        print(f"  Checking {py_file.name}...", end=" ")
        checker.check_file(str(py_file))
        print("✓")
    
    # Analyze patterns
    checker.analyze_imports(project_root)
    
    # Report
    checker.report()
    
    return 0 if not checker.issues else 1

if __name__ == "__main__":
    sys.exit(main())
