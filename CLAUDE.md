# Backpack Volume Auto - Development Guidelines

## Commands
- **Setup**: `pip install -r requirements.txt`
- **Run**: `python main.py`
- **Windows Quick Start**: `INSTALL.bat` then `START.bat`

## Code Style
- **Naming**: snake_case for variables/functions, CamelCase for classes
- **Types**: Always use type hints (from typing module)
- **Imports**: Group standard library first, then third-party, then local
- **Line Length**: Max 120 characters
- **Docstrings**: Required for public functions/classes
- **Error Handling**: Use custom exception classes in core/exceptions
- **Async**: Use asyncio for concurrency, follow async/await patterns

## Architecture
- Modular design with core/ for functionality, inputs/ for configuration
- Retry patterns using tenacity for network operations
- Comprehensive logging with loguru
- Configuration in inputs/config.py

## Testing
If adding tests, place them in tests/ directory and follow pytest conventions.