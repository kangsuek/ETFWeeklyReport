# Development Guide

## Code Quality Standards

### Python (Backend)
- Adherence to **PEP 8**, 4 spaces indentation
- Use of type hints, Docstrings mandatory
- Asynchronous I/O: Use of `async/await`

### JavaScript/React (Frontend)
- Adhere to **ESLint** rules, use 2 spaces for indentation
- Functional components + Hooks
- Document props (PropTypes mandatory, JSDoc recommended)

## Project Structure
Refer to [ARCHITECTURE.md](./ARCHITECTURE.md) and [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md) for detailed structure.

## Naming Conventions

### Backend (Python)
- Variables/Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_CASE`

### Frontend (JavaScript/React)
- Variables/Functions: `camelCase`
- Components: `PascalCase`
- Constants: `UPPER_CASE`

**Type**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## Testing Strategy
- **Coverage Targets**: Backend 80%, Frontend 70%, Critical Path 100%
- **Pattern**: Given-When-Then structure
- **Testing Policy**: Refer to [AGENTS.md](../AGENTS.md)

## Performance Optimisation

### Backend
- Asynchronous I/O: `async/await`, `asyncio.gather()`
- Database index optimisation

### Frontend
- React.memo: Prevent unnecessary re-rendering
- Code Splitting: Use `React.lazy()`

## Security
Refer to [SECURITY_CHECKLIST.md](./SECURITY_CHECKLIST.md) for detailed items.