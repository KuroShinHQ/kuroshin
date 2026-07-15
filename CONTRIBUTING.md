# Contributing to Kuroshin OS

Thank you for your interest in contributing! This project follows a structured development workflow.

## Development Workflow

1. **Fork & Clone** the repository
2. **Create a branch**: `git checkout -b feature/your-feature-name`
3. **Make changes** following the code style below
4. **Test**: ensure existing functionality isn't broken
5. **Commit**: use meaningful commit messages
6. **Push & PR**: open a Pull Request with a clear description

## Code Style

- Python 3.10+ with type hints
- Follow existing patterns in the codebase
- No comments unless explicitly requested
- Async-first: FastAPI endpoints use `async def` + `await`

## Architecture Rules

- **API endpoint** → write request/response schema first
- **DB model** → write ORM class first  
- **Then** implement router and scraper logic

## Commit Messages

Use conventional-style prefixes:
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `refactor:` code restructuring
- `test:` test additions

## Testing

- Type checking with mypy (static)
- Unit tests for router functions (isolated)
- Integration tests with real DB + HTTP client
- Live proof via curl or log analysis (no manual testing)

## Security

- Never commit secrets, API keys, or credentials
- Never expose or log sensitive information
- Follow KILIC-KALKAN security principles

## Issues

Report bugs and request features via GitHub Issues.
