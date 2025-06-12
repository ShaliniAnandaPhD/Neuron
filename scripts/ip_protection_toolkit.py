# scripts/ip_protection_toolkit.py
"""
Neuron Framework IP Protection Toolkit
Comprehensive tools for intellectual property protection and compliance management

This toolkit provides command-line utilities for:
- License compliance checking
- Copyright header management
- Security scanning
- Innovation analysis
- Trademark monitoring
- Automated reporting

Usage:
    python scripts/ip_protection_toolkit.py [command] [options]

Commands:
    scan-licenses      - Scan for license compatibility issues
    add-copyright      - Add copyright headers to files
    check-security     - Run security vulnerability scan
    analyze-innovation - Analyze code for patentable innovations
    check-trademarks   - Check trademark usage compliance
    generate-report    - Generate comprehensive IP report
    setup-git-hooks    - Install git hooks for IP protection

Author: Neuron Framework IP Protection Team
License: MIT License
"""

import argparse
import os
import sys
import json
import re
import subprocess
import glob
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import hashlib
import tempfile
import shutil

class Colors:
    """ANSI color codes for terminal output"""
    BOLD = '\033[1m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

class IPProtectionToolkit:
    """Main IP Protection Toolkit class"""
    
    def __init__(self):
        self.project_root = self._find_project_root()
        self.config = self._load_config()
        self.report_data = {}
    
    def _find_project_root(self) -> str:
        """Find the project root directory"""
        current = os.path.abspath('.')
        while current != '/':
            if os.path.exists(os.path.join(current, '.git')) or os.path.exists(os.path.join(current, 'setup.py')):
                return current
            current = os.path.dirname(current)
        return os.path.abspath('.')
    
    def _load_config(self) -> Dict[str, Any]:
        """Load IP protection configuration"""
        config_path = os.path.join(self.project_root, '.ip_protection_config.json')
        
        default_config = {
            "copyright_holder": "Neuron Development Team",
            "license_type": "MIT",
            "excluded_directories": [".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build"],
            "file_extensions": [".py", ".js", ".ts", ".jsx", ".tsx", ".md", ".yml", ".yaml"],
            "allowed_licenses": ["MIT", "BSD", "Apache-2.0", "ISC", "Unlicense"],
            "prohibited_licenses": ["GPL", "LGPL", "AGPL", "MPL"],
            "trademark_terms": ["Neuron Framework", "NeuroCircuit", "NeuroPilot"],
            "innovation_keywords": [
                "algorithm", "method", "process", "system", "technique",
                "neural", "agent", "coordination", "fault tolerance",
                "memory management", "circuit breaker", "adaptive"
            ]
        }
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                print(f"{Colors.YELLOW}Warning: Could not load config file: {e}{Colors.RESET}")
        
        return default_config
    
    def _print_header(self, title: str):
        """Print a formatted header"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{title.center(60)}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    
    def _print_success(self, message: str):
        """Print success message"""
        print(f"{Colors.GREEN}✅ {message}{Colors.RESET}")
    
    def _print_warning(self, message: str):
        """Print warning message"""
        print(f"{Colors.YELLOW}⚠️ {message}{Colors.RESET}")
    
    def _print_error(self, message: str):
        """Print error message"""
        print(f"{Colors.RED}❌ {message}{Colors.RESET}")
    
    def _print_info(self, message: str):
        """Print info message"""
        print(f"{Colors.BLUE}ℹ️ {message}{Colors.RESET}")
    
    def _get_file_hash(self, filepath: str) -> str:
        """Get MD5 hash of file for change detection"""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def _should_skip_directory(self, directory: str) -> bool:
        """Check if directory should be skipped"""
        dir_name = os.path.basename(directory)
        return (dir_name.startswith('.') or 
                dir_name in self.config['excluded_directories'])
    
    def _should_process_file(self, filepath: str) -> bool:
        """Check if file should be processed"""
        _, ext = os.path.splitext(filepath)
        return ext.lower() in self.config['file_extensions']
    
    def _get_copyright_header(self, file_extension: str) -> str:
        """Get copyright header for file type"""
        year = datetime.now().year
        holder = self.config['copyright_holder']
        license_type = self.config['license_type']
        
        headers = {
            '.py': f'''#!/usr/bin/env python3
"""
Neuron Framework - Advanced Neural Agent Architecture

Copyright (c) {year} {holder}
Author: Neuron Framework Contributors
License: {license_type} License

This file is part of the Neuron Framework, an advanced neural agent
architecture for building sophisticated AI systems with fault tolerance,
memory management, and agent coordination capabilities.

For more information, see: https://github.com/your-org/neuron-framework
"""

''',
            '.js': f'''/*
* Neuron Framework - Advanced Neural Agent Architecture
* 
* Copyright (c) {year} {holder}
* Author: Neuron Framework Contributors
* License: {license_type} License
* 
* This file is part of the Neuron Framework.
* For more information, see: https://github.com/your-org/neuron-framework
*/

''',
            '.md': f'''<!--
Neuron Framework Documentation

Copyright (c) {year} {holder}
License: {license_type} License

Part of the Neuron Framework project.
-->

''',
            '.yml': f'''# Neuron Framework Configuration
# 
# Copyright (c) {year} {holder}
# License: {license_type} License
# 
# Part of the Neuron Framework project.

''',
        }
        
        return headers.get(file_extension, headers['.py'])
    
    def scan_licenses(self, fix_issues: bool = False) -> Dict[str, Any]:
        """Scan for license compatibility issues"""
        self._print_header("LICENSE COMPATIBILITY SCAN")
        
        results = {
            'compatible_licenses': [],
            'incompatible_licenses': [],
            'unknown_licenses': [],
            'total_dependencies': 0,
            'issues_found': 0
        }
        
        # Try to get dependency information
        try:
            # For Python projects
            result = subprocess.run(['pip', 'freeze'], capture_output=True, text=True)
            if result.returncode == 0:
                dependencies = result.stdout.strip().split('\n')
                results['total_dependencies'] = len(dependencies)
                
                self._print_info(f"Found {len(dependencies)} Python dependencies")
                
                # Try to get license information
                try:
                    license_result = subprocess.run(['pip-licenses', '--format=json'], 
                                                 capture_output=True, text=True)
                    if license_result.returncode == 0:
                        licenses = json.loads(license_result.stdout)
                        
                        for pkg in licenses:
                            license_name = pkg.get('License', 'Unknown')
                            pkg_name = pkg.get('Name', 'Unknown')
                            
                            if any(prohibited in license_name for prohibited in self.config['prohibited_licenses']):
                                results['incompatible_licenses'].append(f"{pkg_name}: {license_name}")
                                results['issues_found'] += 1
                            elif any(allowed in license_name for allowed in self.config['allowed_licenses']):
                                results['compatible_licenses'].append(f"{pkg_name}: {license_name}")
                            else:
                                results['unknown_licenses'].append(f"{pkg_name}: {license_name}")
                                
                except subprocess.CalledProcessError:
                    self._print_warning("pip-licenses not available. Install with: pip install pip-licenses")
                    
        except subprocess.CalledProcessError:
            self._print_warning("Could not get dependency information")
        
        # Report results
        if results['issues_found'] > 0:
            self._print_error(f"Found {results['issues_found']} license compatibility issues")
            for issue in results['incompatible_licenses']:
                print(f"  - {issue}")
        else:
            self._print_success("No license compatibility issues found")
        
        if results['unknown_licenses']:
            self._print_warning(f"Found {len(results['unknown_licenses'])} dependencies with unknown licenses")
            for unknown in results['unknown_licenses']:
                print(f"  - {unknown}")
        
        return results
    
    def add_copyright_headers(self, dry_run: bool = False) -> Dict[str, Any]:
        """Add copyright headers to files missing them"""
        self._print_header("COPYRIGHT HEADER MANAGEMENT")
        
        results = {
            'files_processed': 0,
            'files_updated': 0,
            'files_skipped': 0,
            'errors': []
        }
        
        for root, dirs, files in os.walk(self.project_root):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not self._should_skip_directory(os.path.join(root, d))]
            
            for file in files:
                filepath = os.path.join(root, file)
                
                if not self._should_process_file(filepath):
                    continue
                
                results['files_processed'] += 1
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check if file already has copyright header
                    if 'Copyright' in content[:1000] or 'Neuron Framework' in content[:1000]:
                        results['files_skipped'] += 1
                        continue
                    
                    if not dry_run:
                        # Add copyright header
                        _, ext = os.path.splitext(filepath)
                        header = self._get_copyright_header(ext)
                        
                        # For Python files, preserve shebang
                        if ext == '.py' and content.startswith('#!'):
                            lines = content.split('\n')
                            shebang = lines[0] + '\n'
                            rest = '\n'.join(lines[1:])
                            new_content = shebang + header + rest
                        else:
                            new_content = header + content
                        
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        results['files_updated'] += 1
                        self._print_success(f"Added header to {os.path.relpath(filepath)}")
                    else:
                        results['files_updated'] += 1
                        print(f"  Would add header to: {os.path.relpath(filepath)}")
                        
                except Exception as e:
                    error_msg = f"Error processing {filepath}: {e}"
                    results['errors'].append(error_msg)
                    self._print_error(error_msg)
        
        # Summary
        if dry_run:
            self._print_info(f"DRY RUN: Would update {results['files_updated']} files")
        else:
            self._print_success(f"Updated {results['files_updated']} files with copyright headers")
        
        self._print_info(f"Processed {results['files_processed']} files, skipped {results['files_skipped']}")
        
        if results['errors']:
            self._print_warning(f"Encountered {len(results['errors'])} errors")
        
        return results
    
    def check_security(self) -> Dict[str, Any]:
        """Run security vulnerability scan"""
        self._print_header("SECURITY VULNERABILITY SCAN")
        
        results = {
            'vulnerabilities': [],
            'security_issues': [],
            'total_issues': 0
        }
        
        # Check for known vulnerabilities in dependencies
        try:
            self._print_info("Checking for known vulnerabilities...")
            result = subprocess.run(['safety', 'check', '--json'], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0 and result.stdout:
                try:
                    safety_data = json.loads(result.stdout)
                    results['vulnerabilities'] = safety_data
                    results['total_issues'] += len(safety_data)
                    
                    self._print_error(f"Found {len(safety_data)} security vulnerabilities")
                    for vuln in safety_data[:5]:  # Show first 5
                        pkg = vuln.get('package', 'Unknown')
                        advisory = vuln.get('advisory', 'No details')[:100]
                        print(f"  - {pkg}: {advisory}")
                        
                except json.JSONDecodeError:
                    self._print_warning("Could not parse safety check results")
            else:
                self._print_success("No known vulnerabilities found in dependencies")
                
        except FileNotFoundError:
            self._print_warning("Safety not installed. Install with: pip install safety")
        
        # Static analysis for security issues
        try:
            self._print_info("Running static security analysis...")
            result = subprocess.run(['bandit', '-r', self.project_root, '-f', 'json'], 
                                  capture_output=True, text=True)
            
            if result.stdout:
                try:
                    bandit_data = json.loads(result.stdout)
                    issues = bandit_data.get('results', [])
                    results['security_issues'] = issues
                    results['total_issues'] += len(issues)
                    
                    if issues:
                        self._print_warning(f"Found {len(issues)} potential security issues")
                        for issue in issues[:3]:  # Show first 3
                            filename = issue.get('filename', 'Unknown')
                            test_name = issue.get('test_name', 'Unknown')
                            print(f"  - {os.path.relpath(filename)}: {test_name}")
                    else:
                        self._print_success("No security issues found in static analysis")
                        
                except json.JSONDecodeError:
                    self._print_warning("Could not parse bandit results")
                    
        except FileNotFoundError:
            self._print_warning("Bandit not installed. Install with: pip install bandit")
        
        # Scan for potential secrets
        self._print_info("Scanning for potential secrets...")
        secrets_found = self._scan_for_secrets()
        results['secrets'] = secrets_found
        results['total_issues'] += len(secrets_found)
        
        if secrets_found:
            self._print_warning(f"Found {len(secrets_found)} potential secrets")
            for secret in secrets_found[:3]:
                print(f"  - {secret['file']}:{secret['line']} ({secret['type']})")
        else:
            self._print_success("No potential secrets found")
        
        return results
    
    def _scan_for_secrets(self) -> List[Dict[str, Any]]:
        """Scan for potential secrets in files"""
        secrets_patterns = {
            'API Key': r'api[_-]?key["\']?\s*[:=]\s*["\']?[a-zA-Z0-9]{20,}',
            'Password': r'password["\']?\s*[:=]\s*["\'][^"\']{8,}',
            'Secret': r'secret["\']?\s*[:=]\s*["\'][^"\']{10,}',
            'Token': r'token["\']?\s*[:=]\s*["\'][a-zA-Z0-9]{20,}',
            'Private Key': r'-----BEGIN [A-Z ]+PRIVATE KEY-----'
        }
        
        findings = []
        
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not self._should_skip_directory(os.path.join(root, d))]
            
            for file in files:
                if file.endswith(('.py', '.js', '.md')):
                    filepath = os.path.join(root, file)
                    results['total_files'] += 1
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        # Look for class definitions, function definitions, and algorithms
                        patterns = [
                            (r'class\s+(\w+).*?:', 'Class Definition'),
                            (r'def\s+(\w+).*?:', 'Function Definition'),
                            (r'algorithm[:\s]+([^\n]+)', 'Algorithm Description'),
                            (r'patent[:\s]+([^\n]+)', 'Patent Reference'),
                            (r'innovation[:\s]+([^\n]+)', 'Innovation Description'),
                            (r'novel[:\s]+([^\n]+)', 'Novel Approach'),
                        ]
                        
                        for pattern, pattern_type in patterns:
                            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                            for match in matches:
                                context = content[max(0, match.start()-200):match.end()+200]
                                
                                # Check if context contains innovation keywords
                                keyword_matches = []
                                for keyword in innovation_keywords:
                                    if keyword.lower() in context.lower():
                                        keyword_matches.append(keyword)
                                
                                if keyword_matches:
                                    innovation = {
                                        'file': os.path.relpath(filepath),
                                        'type': pattern_type,
                                        'match': match.group(1) if match.groups() else match.group(0),
                                        'keywords': keyword_matches[:5],
                                        'context': context.strip()[:300] + '...' if len(context) > 300 else context.strip()
                                    }
                                    
                                    results['innovations'].append(innovation)
                                    
                                    if pattern_type == 'Class Definition':
                                        results['classes'].append(innovation)
                                    elif pattern_type == 'Function Definition':
                                        results['functions'].append(innovation)
                                    elif 'Algorithm' in pattern_type:
                                        results['algorithms'].append(innovation)
                    except Exception:
                        continue
        
        # Report results
        self._print_info(f"Analyzed {results['total_files']} files")
        self._print_info(f"Found {len(results['innovations'])} potential innovations")
        self._print_info(f"  - Classes: {len(results['classes'])}")
        self._print_info(f"  - Functions: {len(results['functions'])}")
        self._print_info(f"  - Algorithms: {len(results['algorithms'])}")
        
        if results['innovations']:
            self._print_warning("Consider reviewing innovations with IP attorney")
            
            # Show top innovations
            print(f"\n{Colors.BOLD}Top Innovations:{Colors.RESET}")
            for innovation in results['innovations'][:5]:
                print(f"  - {innovation['file']}: {innovation['match']} ({innovation['type']})")
                print(f"    Keywords: {', '.join(innovation['keywords'])}")
        
        return results
    
    def check_trademarks(self) -> Dict[str, Any]:
        """Check trademark usage compliance"""
        self._print_header("TRADEMARK USAGE ANALYSIS")
        
        results = {
            'trademark_terms': {},
            'total_usage': 0,
            'files_checked': 0,
            'recommendations': []
        }
        
        trademark_terms = self.config['trademark_terms']
        
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not self._should_skip_directory(os.path.join(root, d))]
            
            for file in files:
                if file.endswith(('.py', '.js', '.md', '.txt', '.rst')):
                    filepath = os.path.join(root, file)
                    results['files_checked'] += 1
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        for term in trademark_terms:
                            pattern = re.escape(term)
                            matches = list(re.finditer(pattern, content, re.IGNORECASE))
                            
                            if matches:
                                if term not in results['trademark_terms']:
                                    results['trademark_terms'][term] = {
                                        'total_uses': 0,
                                        'with_symbol': 0,
                                        'files': set()
                                    }
                                
                                for match in matches:
                                    results['trademark_terms'][term]['total_uses'] += 1
                                    results['trademark_terms'][term]['files'].add(os.path.relpath(filepath))
                                    results['total_usage'] += 1
                                    
                                    # Check for trademark symbols
                                    surrounding = content[match.start():match.end()+5]
                                    if '™' in surrounding or '®' in surrounding:
                                        results['trademark_terms'][term]['with_symbol'] += 1
                    except Exception:
                        continue
        
        # Convert sets to lists for JSON serialization
        for term_data in results['trademark_terms'].values():
            term_data['files'] = list(term_data['files'])
        
        # Generate recommendations
        for term, data in results['trademark_terms'].items():
            if data['total_uses'] > 5 and data['with_symbol'] == 0:
                results['recommendations'].append(f"Consider adding ™ symbol to '{term}' (used {data['total_uses']} times)")
            elif data['total_uses'] > 10 and (data['with_symbol'] / data['total_uses']) < 0.5:
                results['recommendations'].append(f"Inconsistent trademark symbol use for '{term}'")
        
        # Report results
        self._print_info(f"Checked {results['files_checked']} files")
        self._print_info(f"Found {results['total_usage']} trademark term usages")
        
        for term, data in results['trademark_terms'].items():
            symbol_pct = (data['with_symbol'] / data['total_uses']) * 100 if data['total_uses'] > 0 else 0
            print(f"  - {term}: {data['total_uses']} uses, {data['with_symbol']} with symbols ({symbol_pct:.1f}%)")
        
        if results['recommendations']:
            self._print_warning("Trademark usage recommendations:")
            for rec in results['recommendations']:
                print(f"  - {rec}")
        else:
            self._print_success("Trademark usage appears consistent")
        
        return results
    
    def generate_report(self, output_format: str = 'markdown') -> str:
        """Generate comprehensive IP protection report"""
        self._print_header("GENERATING COMPREHENSIVE IP REPORT")
        
        # Collect all data
        license_results = self.scan_licenses()
        security_results = self.check_security()
        innovation_results = self.analyze_innovations()
        trademark_results = self.check_trademarks()
        
        report_data = {
            'generated_at': datetime.now().isoformat(),
            'project_root': self.project_root,
            'license_compliance': license_results,
            'security_analysis': security_results,
            'innovation_analysis': innovation_results,
            'trademark_analysis': trademark_results
        }
        
        # Calculate overall status
        issues_count = (
            license_results.get('issues_found', 0) +
            security_results.get('total_issues', 0) +
            len(trademark_results.get('recommendations', []))
        )
        
        overall_status = 'COMPLIANT' if issues_count == 0 else 'NEEDS_ATTENTION'
        report_data['overall_status'] = overall_status
        report_data['total_issues'] = issues_count
        
        if output_format.lower() == 'json':
            output_file = 'ip_protection_report.json'
            with open(output_file, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
        else:
            output_file = 'IP_PROTECTION_REPORT.md'
            self._generate_markdown_report(report_data, output_file)
        
        self._print_success(f"Generated report: {output_file}")
        self._print_info(f"Overall status: {overall_status}")
        self._print_info(f"Total issues: {issues_count}")
        
        return output_file
    
    def _generate_markdown_report(self, data: Dict[str, Any], output_file: str):
        """Generate markdown format report"""
        with open(output_file, 'w') as f:
            f.write(f"""# 🛡️ IP Protection Report

**Generated:** {data['generated_at']}  
**Project:** {os.path.basename(data['project_root'])}  
**Overall Status:** {"🟢 " + data['overall_status'] if data['overall_status'] == 'COMPLIANT' else '🟡 ' + data['overall_status']}  
**Total Issues:** {data['total_issues']}

## 📊 Executive Summary

This comprehensive report analyzes intellectual property protection measures
for the project. The analysis covers license compliance, security vulnerabilities,
innovation identification, and trademark usage.

## 📋 License Compliance

**Status:** {"✅ COMPLIANT" if data['license_compliance']['issues_found'] == 0 else f"⚠️ {data['license_compliance']['issues_found']} ISSUES"}

- **Total Dependencies:** {data['license_compliance']['total_dependencies']}
- **Compatible Licenses:** {len(data['license_compliance']['compatible_licenses'])}
- **Incompatible Licenses:** {len(data['license_compliance']['incompatible_licenses'])}
- **Unknown Licenses:** {len(data['license_compliance']['unknown_licenses'])}

""")
            
            if data['license_compliance']['incompatible_licenses']:
                f.write("### ⚠️ License Issues\n\n")
                for issue in data['license_compliance']['incompatible_licenses']:
                    f.write(f"- {issue}\n")
                f.write("\n")
            
            f.write(f"""## 🔒 Security Analysis

**Status:** {"✅ SECURE" if data['security_analysis']['total_issues'] == 0 else f"⚠️ {data['security_analysis']['total_issues']} ISSUES"}

- **Vulnerabilities:** {len(data['security_analysis']['vulnerabilities'])}
- **Security Issues:** {len(data['security_analysis']['security_issues'])}
- **Potential Secrets:** {len(data['security_analysis'].get('secrets', []))}

""")
            
            if data['security_analysis']['total_issues'] > 0:
                f.write("### 🚨 Security Concerns\n\n")
                for vuln in data['security_analysis']['vulnerabilities'][:3]:
                    f.write(f"- **Vulnerability:** {vuln.get('package', 'Unknown')} - {vuln.get('advisory', 'No details')[:100]}\n")
                f.write("\n")
            
            f.write(f"""## 🔬 Innovation Analysis

**Status:** 📊 ANALYZED

- **Files Analyzed:** {data['innovation_analysis']['total_files']}
- **Potential Innovations:** {len(data['innovation_analysis']['innovations'])}
- **Classes Found:** {len(data['innovation_analysis']['classes'])}
- **Functions Found:** {len(data['innovation_analysis']['functions'])}
- **Algorithms Found:** {len(data['innovation_analysis']['algorithms'])}

""")
            
            if data['innovation_analysis']['innovations']:
                f.write("### 💡 Key Innovations\n\n")
                for innovation in data['innovation_analysis']['innovations'][:5]:
                    f.write(f"- **{innovation['match']}** ({innovation['type']}) in `{innovation['file']}`\n")
                    f.write(f"  - Keywords: {', '.join(innovation['keywords'])}\n")
                f.write("\n")
            
            f.write(f"""## 🏷️ Trademark Analysis

**Status:** {"✅ CONSISTENT" if len(data['trademark_analysis']['recommendations']) == 0 else f"⚠️ {len(data['trademark_analysis']['recommendations'])} RECOMMENDATIONS"}

- **Files Checked:** {data['trademark_analysis']['files_checked']}
- **Total Term Usage:** {data['trademark_analysis']['total_usage']}
- **Trademark Terms:** {len(data['trademark_analysis']['trademark_terms'])}

""")
            
            for term, term_data in data['trademark_analysis']['trademark_terms'].items():
                symbol_pct = (term_data['with_symbol'] / term_data['total_uses']) * 100 if term_data['total_uses'] > 0 else 0
                f.write(f"- **{term}:** {term_data['total_uses']} uses, {symbol_pct:.1f}% with symbols\n")
            
            if data['trademark_analysis']['recommendations']:
                f.write("\n### 💭 Recommendations\n\n")
                for rec in data['trademark_analysis']['recommendations']:
                    f.write(f"- {rec}\n")
            
            f.write(f"""

## 🎯 Action Items

### Immediate Actions
""")
            
            if data['overall_status'] == 'NEEDS_ATTENTION':
                f.write("""
1. 🚨 **Address compliance issues** identified in this report
2. 📝 **Review license compatibility** for flagged dependencies
3. 🔒 **Fix security vulnerabilities** and remove potential secrets
4. ⚖️ **Consult legal team** on IP protection strategy
""")
            else:
                f.write("""
1. ✅ **Continue current practices** - compliance status is good
2. 📊 **Monitor for changes** with regular IP audits
3. 📚 **Keep documentation updated** as project evolves
4. 🔍 **Review new dependencies** for license compatibility
""")
            
            f.write(f"""
### Long-term Strategy

1. **Patent Protection** - Review innovation analysis for patentable inventions
2. **Trademark Registration** - Consider registering key trademark terms
3. **Automated Monitoring** - Implement continuous IP compliance checking
4. **Team Training** - Educate team on IP best practices

## 📞 Contact Information

For IP-related questions:
- **Legal Team:** legal@neuron-framework.org
- **Maintainers:** maintainers@neuron-framework.org

---
*Report generated by Neuron Framework IP Protection Toolkit*
""")
    
    def setup_git_hooks(self) -> bool:
        """Setup git hooks for IP protection"""
        self._print_header("SETTING UP GIT HOOKS")
        
        hooks_dir = os.path.join(self.project_root, '.git', 'hooks')
        
        if not os.path.exists(hooks_dir):
            self._print_error("Not a git repository or .git/hooks directory not found")
            return False
        
        # Pre-commit hook
        pre_commit_hook = os.path.join(hooks_dir, 'pre-commit')
        pre_commit_content = f'''#!/bin/bash
# Neuron Framework IP Protection Pre-commit Hook

echo "🛡️ Running IP protection checks..."

# Run copyright header check
python {os.path.abspath(__file__)} add-copyright --dry-run

# Check for potential secrets
if grep -r "password\|secret\|key" --include="*.py" --include="*.js" --include="*.yml" .; then
    echo "⚠️ Potential secrets detected. Please review before committing."
fi

# Run license compatibility check
python {os.path.abspath(__file__)} scan-licenses

echo "✅ IP protection checks completed"
'''
        
        with open(pre_commit_hook, 'w') as f:
            f.write(pre_commit_content)
        
        os.chmod(pre_commit_hook, 0o755)
        self._print_success("Created pre-commit hook")
        
        # Pre-push hook
        pre_push_hook = os.path.join(hooks_dir, 'pre-push')
        pre_push_content = f'''#!/bin/bash
# Neuron Framework IP Protection Pre-push Hook

echo "🛡️ Running comprehensive IP check before push..."

# Generate IP report
python {os.path.abspath(__file__)} generate-report

echo "📋 IP protection report generated"
echo "✅ Pre-push IP checks completed"
'''
        
        with open(pre_push_hook, 'w') as f:
            f.write(pre_push_content)
        
        os.chmod(pre_push_hook, 0o755)
        self._print_success("Created pre-push hook")
        
        self._print_success("Git hooks setup completed")
        return True

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Neuron Framework IP Protection Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ip_protection_toolkit.py scan-licenses
  python ip_protection_toolkit.py add-copyright --dry-run
  python ip_protection_toolkit.py generate-report --format json
  python ip_protection_toolkit.py setup-git-hooks
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scan licenses command
    scan_parser = subparsers.add_parser('scan-licenses', help='Scan for license compatibility issues')
    scan_parser.add_argument('--fix', action='store_true', help='Attempt to fix issues automatically')
    
    # Add copyright command
    copyright_parser = subparsers.add_parser('add-copyright', help='Add copyright headers to files')
    copyright_parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    
    # Check security command
    security_parser = subparsers.add_parser('check-security', help='Run security vulnerability scan')
    
    # Analyze innovation command
    innovation_parser = subparsers.add_parser('analyze-innovation', help='Analyze code for patentable innovations')
    
    # Check trademarks command
    trademark_parser = subparsers.add_parser('check-trademarks', help='Check trademark usage compliance')
    
    # Generate report command
    report_parser = subparsers.add_parser('generate-report', help='Generate comprehensive IP report')
    report_parser.add_argument('--format', choices=['markdown', 'json'], default='markdown', help='Output format')
    
    # Setup git hooks command
    hooks_parser = subparsers.add_parser('setup-git-hooks', help='Install git hooks for IP protection')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize toolkit
    toolkit = IPProtectionToolkit()
    
    try:
        if args.command == 'scan-licenses':
            toolkit.scan_licenses(fix_issues=args.fix)
        
        elif args.command == 'add-copyright':
            toolkit.add_copyright_headers(dry_run=args.dry_run)
        
        elif args.command == 'check-security':
            toolkit.check_security()
        
        elif args.command == 'analyze-innovation':
            toolkit.analyze_innovations()
        
        elif args.command == 'check-trademarks':
            toolkit.check_trademarks()
        
        elif args.command == 'generate-report':
            toolkit.generate_report(output_format=args.format)
        
        elif args.command == 'setup-git-hooks':
            toolkit.setup_git_hooks()
        
        else:
            print(f"Unknown command: {args.command}")
            parser.print_help()
    
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Operation cancelled by user{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.RESET}")
        sys.exit(1)

if __name__ == '__main__':
    main().join(root, d))]
            
            for file in files:
                if file.endswith(('.py', '.js', '.yml', '.yaml', '.json', '.env')):
                    filepath = os.path.join(root, file)
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        for secret_type, pattern in secrets_patterns.items():
                            matches = re.finditer(pattern, content, re.IGNORECASE)
                            for match in matches:
                                # Skip obvious false positives
                                matched_text = match.group(0)
                                if any(fp in matched_text.lower() for fp in ['example', 'placeholder', 'your_', 'xxx', '123']):
                                    continue
                                
                                findings.append({
                                    'file': os.path.relpath(filepath),
                                    'type': secret_type,
                                    'line': content[:match.start()].count('\n') + 1,
                                    'preview': matched_text[:50] + '...' if len(matched_text) > 50 else matched_text
                                })
                    except Exception:
                        continue
        
        return findings
    
    def analyze_innovations(self) -> Dict[str, Any]:
        """Analyze code for potentially patentable innovations"""
        self._print_header("INNOVATION ANALYSIS")
        
        results = {
            'total_files': 0,
            'innovations': [],
            'classes': [],
            'functions': [],
            'algorithms': []
        }
        
        innovation_keywords = self.config['innovation_keywords']
        
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not self._should_skip_directory(os.path
