# Contributing to ContextFlow

Thank you for your interest in contributing to ContextFlow! We welcome contributions from the community.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/contextflow.git`
3. Create a feature branch: `git checkout -b feature/your-feature`
4. Make your changes
5. Test your changes: `pytest`
6. Commit: `git commit -m "Add your feature"`
7. Push: `git push origin feature/your-feature`
8. Open a Pull Request

## Development Setup

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=contextflow
```

## Code Style

- Follow PEP 8
- Use type hints
- Write docstrings
- Add tests for new features

## Testing

All new features must include tests. Run the test suite with:

```bash
pytest tests/
```

## Feature Flags

New experimental features should use feature flags:

```python
from contextflow.src.config import FeatureFlags

if FeatureFlags.USE_EXPERIMENTAL_FEATURE:
    # New code
else:
    # Stable fallback
```

## Questions?

Open an issue or start a discussion on GitHub.

Thank you for contributing!