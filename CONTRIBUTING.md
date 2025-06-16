# Contributing to TracLine

## Development Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure database in `tracline.yaml`
4. Run tests: `python -m pytest tests/`

## Code Style

- Follow PEP 8 for Python code
- Use TypeScript/ES6+ for JavaScript
- Write comprehensive docstrings
- Include unit tests for new features

## Architecture

- **tracline/**: Core application modules
- **web/**: Web interface (FastAPI + HTML/JS)
- **tests/**: Test suites
- **docs/**: Documentation

## Database Schema

The application uses SQLAlchemy models for:
- Projects and team members
- Tasks with status tracking
- File associations and relationships

## Web Interface

Built with:
- FastAPI backend
- Vanilla JavaScript frontend
- CSS3 with flexbox layouts
- WebSocket for real-time updates

## Testing

Run the test suite:
```bash
python -m pytest tests/ -v
```

## Submitting Changes

1. Create a feature branch
2. Make your changes
3. Add/update tests
4. Submit a pull request