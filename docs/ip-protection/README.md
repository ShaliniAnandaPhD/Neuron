# 🛡️ Neuron Framework IP Protection Kit

**Comprehensive intellectual property protection and compliance management system**

This IP Protection Kit provides automated tools and workflows to protect the intellectual property of the Neuron Framework project. It includes license compliance checking, copyright management, security scanning, innovation analysis, and trademark monitoring.

## 📋 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [🏗️ Architecture](#️-architecture)
- [🔧 Installation](#-installation)
- [📊 Features](#-features)
- [🎮 Usage](#-usage)
- [⚙️ Configuration](#️-configuration)
- [🤖 Automation](#-automation)
- [📚 Documentation](#-documentation)
- [🆘 Troubleshooting](#-troubleshooting)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install safety bandit pip-licenses

# Install the IP protection toolkit
chmod +x scripts/ip_protection_toolkit.py
```

### 2. Run Initial Scan

```bash
# Generate comprehensive IP protection report
python scripts/ip_protection_toolkit.py generate-report

# Scan for license compatibility issues
python scripts/ip_protection_toolkit.py scan-licenses

# Add missing copyright headers
python scripts/ip_protection_toolkit.py add-copyright --dry-run
```

### 3. Set Up Automation

```bash
# Install git hooks for automatic checking
python scripts/ip_protection_toolkit.py setup-git-hooks

# The GitHub Actions workflow is automatically configured
# Check .github/workflows/ip-protection.yml
```

## 🏗️ Architecture

The IP Protection Kit consists of several integrated components:

```
🛡️ IP Protection Kit
├── 🔄 GitHub Actions Workflow (.github/workflows/ip-protection.yml)
│   ├── 📜 License & Copyright Compliance
│   ├── 🔒 Security & Code Protection  
│   ├── 📚 Documentation & Attribution
│   ├── ⚖️ Patent & Trademark Analysis
│   └── 📊 Comprehensive Reporting
│
├── 🐍 Python Toolkit (scripts/ip_protection_toolkit.py)
│   ├── License Compatibility Scanning
│   ├── Copyright Header Management
│   ├── Security Vulnerability Detection
│   ├── Innovation Analysis
│   └── Trademark Usage Monitoring
│
├── ⚙️ Configuration (.ip_protection_config.json)
│   ├── Project Settings
│   ├── License Policies
│   ├── Security Rules
│   └── Automation Preferences
│
└── 🔗 Git Hooks Integration
    ├── Pre-commit Checks
    └── Pre-push Validation
```

## 🔧 Installation

### Prerequisites

- Python 3.8+
- Git repository
- GitHub repository (for Actions workflow)

### Core Dependencies

```bash
# Required Python packages
pip install safety bandit pip-licenses

# Optional packages for enhanced functionality
pip install semgrep secretscanner
```

### Setup Script

```bash
#!/bin/bash
# setup_ip_protection.sh

echo "🛡️ Setting up Neuron Framework IP Protection..."

# Create configuration file if it doesn't exist
if [ ! -f ".ip_protection_config.json" ]; then
    cp .ip_protection_config.json.example .ip_protection_config.json
    echo "✅ Created configuration file"
fi

# Install Python dependencies
pip install safety bandit pip-licenses
echo "✅ Installed Python dependencies"

# Make toolkit executable
chmod +x scripts/ip_protection_toolkit.py
echo "✅ Made toolkit executable"

# Set up git hooks
python scripts/ip_protection_toolkit.py setup-git-hooks
echo "✅ Set up git hooks"

# Run initial scan
echo "🔍 Running initial IP protection scan..."
python scripts/ip_protection_toolkit.py generate-report

echo "🎉 IP Protection Kit setup completed!"
echo "📋 Review the generated IP_PROTECTION_REPORT.md for current status"
```

## 📊 Features

### 🔍 Automated Scanning

- **License Compatibility**: Detects GPL/AGPL violations in MIT projects
- **Copyright Headers**: Validates and adds missing copyright notices
- **Security Vulnerabilities**: Scans dependencies and code for security issues
- **Secret Detection**: Identifies potentially exposed API keys, passwords, tokens
- **Innovation Analysis**: Catalogs potentially patentable algorithms and methods
- **Trademark Monitoring**: Ensures consistent trademark symbol usage

### 📈 Comprehensive Reporting

- **Executive Dashboards**: High-level compliance status and metrics
- **Detailed Analysis**: File-by-file breakdown of issues and recommendations
- **Trend Tracking**: Historical compliance data and improvement metrics
- **Multi-format Output**: Markdown, JSON, and HTML report formats
- **Stakeholder Notifications**: Email, Slack, and GitHub issue integration

### 🤖 Automation & CI/CD

- **GitHub Actions**: Automated weekly scans and PR checks
- **Git Hooks**: Pre-commit and pre-push validation
- **Continuous Monitoring**: Real-time compliance status tracking
- **Auto-remediation**: Automatic copyright header insertion
- **Issue Creation**: Automated GitHub issues for compliance violations

## 🎮 Usage

### Command Line Interface

```bash
# Scan for license compatibility issues
python scripts/ip_protection_toolkit.py scan-licenses

# Add copyright headers to all files
python scripts/ip_protection_toolkit.py add-copyright

# Run security vulnerability scan
python scripts/ip_protection_toolkit.py check-security

# Analyze code for innovations
python scripts/ip_protection_toolkit.py analyze-innovation

# Check trademark usage
python scripts/ip_protection_toolkit.py check-trademarks

# Generate comprehensive report
python scripts/ip_protection_toolkit.py generate-report --format json

# Set up git hooks
python scripts/ip_protection_toolkit.py setup-git-hooks
```

### GitHub Actions Integration

The workflow runs automatically on:
- **Weekly Schedule**: Every Monday at 9 AM UTC
- **Push to Main**: On commits to main branch
- **Pull Requests**: On PR creation and updates
- **Manual Trigger**: Via workflow_dispatch

Force copyright header updates:
```bash
# Trigger workflow with copyright update
gh workflow run ip-protection.yml -f force_copyright_update=true
```

### Git Hooks

Automatically installed hooks provide:

**Pre-commit Hook:**
- Copyright header validation
- Basic secret detection
- License compatibility check

**Pre-push Hook:**
- Comprehensive IP report generation
- Full compliance validation

## ⚙️ Configuration

### Main Configuration File

Edit `.ip_protection_config.json` to customize:

```json
{
  "copyright_holder": "Your Organization Name",
  "license_type": "MIT",
  "project_name": "Your Project Name",
  
  "license_compliance": {
    "allowed_licenses": ["MIT", "BSD", "Apache-2.0"],
    "prohibited_licenses": ["GPL", "LGPL", "AGPL"]
  },
  
  "trademark_terms": [
    "Your Product Name",
    "Your Company Name"
  ],
  
  "notifications": {
    "email": {
      "enabled": true,
      "recipients": ["legal@yourcompany.com"]
    }
  }
}
```

### GitHub Secrets Configuration

Set up the following GitHub secrets for full functionality:

```bash
# Email notifications (optional)
SMTP_USERNAME=your-email@company.com
SMTP_PASSWORD=your-app-password

# Slack notifications (optional)  
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Email recipient (repository variable)
NOTIFICATION_EMAIL=legal@yourcompany.com
```

### Environment Variables

```bash
# Repository variables (set in GitHub settings)
NOTIFICATION_EMAIL=legal@yourcompany.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Secrets (set in GitHub secrets)
SMTP_USERNAME=your-email@company.com
SMTP_PASSWORD=your-password
SLACK_WEBHOOK_URL=your-webhook-url
```

## 🤖 Automation

### GitHub Actions Workflow Jobs

1. **License Compliance**
   - Scans dependencies for license violations
   - Checks copyright headers
   - Auto-fixes missing headers (when enabled)

2. **Security Scanning**
   - Runs safety, bandit, and secret detection
   - Creates security vulnerability reports
   - Identifies potential data exposure

3. **Documentation Protection**
   - Validates required documentation files
   - Generates attribution and credits
   - Ensures proper project documentation

4. **Patent & Trademark Analysis**
   - Identifies potentially patentable innovations
   - Monitors trademark usage consistency
   - Generates IP asset reports

5. **Final Reporting**
   - Consolidates all analysis results
   - Creates comprehensive IP protection report
   - Sends notifications to stakeholders

### Workflow Triggers

```yaml
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 9 * * 1'  # Weekly on Monday
  workflow_dispatch:     # Manual trigger
```

### Notification System

- **GitHub Issues**: Automatic creation for compliance violations
- **Email Reports**: Weekly executive summaries
- **Slack Integration**: Real-time compliance alerts
- **PR Comments**: Inline compliance status on pull requests

## 📚 Documentation

### Generated Reports

The system generates several types of reports:

**IP_PROTECTION_REPORT.md**
- Executive summary with overall compliance status
- Detailed analysis of each protection area
- Actionable recommendations and next steps
- Contact information for legal questions

**ip_compliance_report.json**
- Machine-readable compliance data
- Historical tracking information
- Integration data for external systems

**ATTRIBUTION.md**
- Complete project attribution and credits
- Dependency license information
- Usage guidelines and citations

**INNOVATION_ANALYSIS.md**
- Catalog of potentially patentable innovations
- Algorithm and method documentation
- IP strategy recommendations

### Legal Documentation Templates

The kit includes templates for:
- Copyright headers (Python, JavaScript, Markdown, YAML)
- Contribution agreements
- License compatibility guidelines
- Trademark usage policies

## 🆘 Troubleshooting

### Common Issues

**1. "pip-licenses not found" Error**
```bash
pip install pip-licenses
```

**2. "safety check failed" Error**
```bash
pip install --upgrade safety
safety check --json
```

**3. "bandit not installed" Error**
```bash
pip install bandit
```

**4. Git Hooks Not Working**
```bash
# Ensure hooks are executable
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/pre-push

# Reinstall hooks
python scripts/ip_protection_toolkit.py setup-git-hooks
```

**5. GitHub Actions Failing**
```bash
# Check repository secrets are set
gh secret list

# Verify workflow permissions
# Settings → Actions → General → Workflow permissions
```

### Debug Mode

Enable detailed logging:
```bash
export IP_PROTECTION_DEBUG=1
python scripts/ip_protection_toolkit.py generate-report
```

### Validation Commands

```bash
# Test all components
python scripts/ip_protection_toolkit.py scan-licenses
python scripts/ip_protection_toolkit.py check-security  
python scripts/ip_protection_toolkit.py add-copyright --dry-run

# Validate configuration
python -c "
import json
with open('.ip_protection_config.json') as f:
    config = json.load(f)
print('✅ Configuration valid')
"
```

### Support Resources

- **Documentation**: Full documentation at `docs/ip-protection/`
- **GitHub Issues**: Report bugs and request features
- **Email Support**: legal@neuron-framework.org
- **Community**: Join discussions in GitHub Discussions

### Performance Optimization

For large repositories:

```json
{
  "file_processing": {
    "excluded_directories": [
      "large_data_directory",
      "third_party_libraries"
    ],
    "max_file_size_mb": 10
  },
  "reporting": {
    "max_innovation_results": 50,
    "include_file_hashes": false
  }
}
```

## 🔐 Security Considerations

### Secrets Management

The IP Protection Kit handles sensitive information:

- **Never commit secrets** to version control
- **Use environment variables** for configuration
- **Rotate credentials regularly** 
- **Monitor for secret exposure** in code

### Access Control

- Limit access to IP protection reports
- Use GitHub teams for workflow permissions  
- Implement branch protection rules
- Regular access reviews for legal team

### Data Privacy

- IP reports may contain sensitive business information
- Configure appropriate retention policies
- Use private repositories for sensitive projects
- Consider encryption for archived reports

## 📈 Best Practices

### Development Workflow

1. **Pre-development**: Run IP scan to understand current status
2. **During development**: Use git hooks for continuous validation
3. **Pre-release**: Generate comprehensive IP report
4. **Post-release**: Monitor for new dependencies and vulnerabilities

### Legal Team Integration

- Schedule regular IP reviews with legal team
- Provide access to generated reports and dashboards
- Establish escalation procedures for violations
- Document IP protection decisions and rationale

### Continuous Improvement

- Review and update allowed/prohibited license lists
- Monitor industry best practices
- Update trademark terms as project evolves
- Refine innovation analysis keywords

## Success Metrics

Track IP protection effectiveness:

- **Compliance Score**: Percentage of compliant scans
- **Time to Resolution**: Average time to fix violations
- **Coverage Metrics**: Files with proper copyright headers
- **Vulnerability Response**: Time to address security issues
- **Legal Review Efficiency**: Reduced legal team workload

---

*This IP Protection Kit is part of the Neuron Framework project and is licensed under the MIT License. It provides tools and automation to help protect intellectual property but does not constitute legal advice. Consult with qualified legal professionals for specific IP protection strategies.*
