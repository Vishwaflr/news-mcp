# Contributing to News MCP

Thank you for your interest in contributing to News MCP! This document provides guidelines for contributing to the project.

## 🤝 How to Contribute

### Reporting Issues
- Use the GitHub issue tracker
- Include detailed information about your environment
- Provide steps to reproduce the issue
- Include relevant logs and configuration

### Feature Requests
- Open an issue with the "enhancement" label
- Describe the feature and its use case
- Discuss the implementation approach

### Code Contributions
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Update documentation
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## 🏗️ Development Setup

### Prerequisites
- Python 3.11 or higher (3.12 recommended)
- Git
- Virtual environment tool

### Setup Instructions
```bash
# Clone the repository
git clone https://github.com/your-org/news-mcp.git
cd news-mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\\Scripts\\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Copy configuration
cp .env.example .env

# Run the application
PYTHONPATH=. python app/main.py
```

### Running Tests
```bash
# Unit tests
pytest tests/

# Integration tests
python jobs/scheduler_manager.py config --json

# Template validation
curl -X GET http://localhost:8000/htmx/templates-list
```

## 📝 Coding Standards

### Python Style
- Follow PEP 8
- Use type hints
- Write docstrings for public methods
- Maximum line length: 120 characters

### Code Quality
- Write unit tests for new features
- Maintain test coverage above 80%
- Use meaningful variable and function names
- Keep functions focused and small

### Git Conventions
- Use conventional commit messages
- Keep commits atomic and focused
- Rebase feature branches before merging
- Update CHANGELOG.md for significant changes

### Commit Message Format
```
<type>(<scope>): <description>

<body>

<footer>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(templates): add auto-assignment feature

fix(fetcher): resolve RSS parsing issue with special characters

docs(deployment): update production setup guide
```

## 🧪 Testing Guidelines

### Unit Tests
- Place tests in the `tests/` directory
- Mirror the source code structure
- Use descriptive test names
- Test edge cases and error conditions

### Integration Tests
- Test complete workflows
- Use test databases
- Clean up test data
- Test API endpoints

### Manual Testing
- Test template management UI
- Verify RSS feed processing
- Check scheduler functionality
- Test error handling

## 📚 Documentation

### Code Documentation
- Document public APIs
- Include usage examples
- Explain complex algorithms
- Keep documentation up to date

### User Documentation
- Update README.md for new features
- Add deployment instructions
- Create troubleshooting guides
- Include configuration examples

## 🏷️ Release Process

### Version Numbers
Follow Semantic Versioning (semver.org):
- MAJOR.MINOR.PATCH
- Breaking changes increment MAJOR
- New features increment MINOR
- Bug fixes increment PATCH

### Release Checklist
- [ ] Update CHANGELOG.md
- [ ] Update version numbers
- [ ] Run full test suite
- [ ] Update documentation
- [ ] Create release notes
- [ ] Tag the release
- [ ] Deploy to staging
- [ ] Test deployment
- [ ] Deploy to production

## 🚀 Deployment

### Development
```bash
# Start all services
python app/main.py  # Terminal 1
python jobs/scheduler_manager.py start --debug  # Terminal 2
```

### Production
See [DEPLOYMENT.md](DEPLOYMENT.md) for complete production deployment instructions.

## 📋 Project Structure

```
news-mcp/
├── app/                    # FastAPI application
│   ├── api/               # REST API endpoints
│   ├── services/          # Business logic services
│   ├── routes/            # Route handlers
│   └── processors/        # Content processors
├── jobs/                  # Background services
├── templates/             # HTML templates
├── tests/                 # Test suite
├── docs/                  # Documentation
└── systemd/              # Service configurations
```

## 🛠️ Development Tools

### Recommended Tools
- **IDE**: VSCode with Python extension
- **Database**: DB Browser for SQLite / pgAdmin
- **API Testing**: Postman / Insomnia
- **Monitoring**: Browser DevTools

### Useful Commands
```bash
# Code formatting
black app/ jobs/ tests/

# Type checking
mypy app/ jobs/

# Linting
flake8 app/ jobs/ tests/

# Security scanning
bandit -r app/ jobs/

# Dependency checking
pip-audit
```

## 🎯 Focus Areas

### Current Priorities
1. **Template System**: Enhance dynamic template features
2. **Performance**: Optimize RSS processing
3. **UI/UX**: Improve web interface
4. **Testing**: Increase test coverage
5. **Documentation**: Keep guides current

### Future Roadmap
- Advanced analytics and monitoring
- Content intelligence features
- Multi-user support
- Cloud-native deployment
- API extensions

## 💬 Community

### Communication
- GitHub Issues for bug reports and feature requests
- GitHub Discussions for questions and ideas
- Pull Requests for code contributions

### Code of Conduct
- Be respectful and inclusive
- Focus on constructive feedback
- Help newcomers get started
- Collaborate openly

## ❓ Getting Help

### Resources
- [README.md](README.md) - Project overview and quick start
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment instructions
- [CHANGELOG.md](CHANGELOG.md) - Version history
- GitHub Issues - Bug reports and discussions

### Contact
- Create an issue for bugs or feature requests
- Use discussions for questions
- Tag maintainers in urgent issues

Thank you for contributing to News MCP! 🙏