# Project Context

## Purpose
MCP Atlassian is a Model Context Protocol (MCP) server implementation that bridges Atlassian products (Jira and Confluence) with AI language models. The project enables secure, contextual AI interactions with Atlassian tools while maintaining data privacy and security. Key goals include:

- Providing AI assistants with read/write access to Jira issues, projects, boards, and sprints
- Enabling AI-powered Confluence content search, creation, and management
- Supporting multiple authentication methods (API tokens, PAT, OAuth 2.0)
- Working with both Cloud and Server/Data Center deployments
- Maintaining enterprise-grade security and compliance standards

## Tech Stack
- **Language**: Python 3.10+
- **MCP Framework**: FastMCP 2.3.4+ (built on MCP 1.8.0+)
- **HTTP Server**: Starlette + Uvicorn
- **API Client**: atlassian-python-api 4.0.0+
- **HTTP Clients**: httpx, requests (with SOCKS proxy support)
- **Data Models**: Pydantic 2.10.6+
- **Async Runtime**: Trio 0.29.0+
- **Content Processing**: BeautifulSoup4, markdownify, markdown-to-confluence
- **Authentication**: keyring (token storage), OAuth 2.0 with token refresh
- **Package Manager**: uv (UV)
- **Testing**: pytest, pytest-asyncio, pytest-cov
- **Code Quality**: ruff (linting + formatting), pyright/mypy (type checking), pre-commit
- **CI/CD**: GitHub Actions
- **Distribution**: Docker (ghcr.io), PyPI

## Project Conventions

### Code Style
- **Line length**: 88 characters maximum
- **Formatting**: Managed by Ruff (follows Black-compatible style)
- **Imports**: Absolute imports only, sorted automatically by Ruff
- **Naming conventions**:
  - `snake_case` for functions, variables, and modules
  - `PascalCase` for classes and type aliases
  - `UPPER_SNAKE_CASE` for constants
- **Type hints**: Required for all function signatures
  - Use modern syntax: `list[str]`, `dict[str, Any]`, `str | None`
  - Use `type[T]` for class types
- **Docstrings**: Google-style format for all public APIs
- **String quotes**: Double quotes preferred
- **Indentation**: 4 spaces (no tabs)

### Architecture Patterns
- **Mixin-based architecture**: Functionality split into focused mixins extending base clients
- **Base model pattern**: All data structures extend `ApiModel` base class
- **Configuration management**: Environment-based configuration with Pydantic models
- **FastMCP server pattern**: Separate server implementations for Jira, Confluence, and main
- **Context management**: Request-scoped context with per-request auth override support
- **Tool categorization**: Tools split into read vs write operations for access control
- **Preprocessing layer**: Separate preprocessing logic for content transformation
- **Client separation**: Separate fetcher classes (`JiraFetcher`, `ConfluenceFetcher`) for API interactions

### Testing Strategy
- **Framework**: pytest with pytest-asyncio for async tests
- **Coverage**: pytest-cov for coverage reporting
- **Test organization**:
  - `tests/unit/` - Unit tests organized by module (jira/, confluence/, models/, servers/, utils/)
  - `tests/integration/` - Integration tests for cross-service and protocol testing
  - `tests/fixtures/` - Reusable test fixtures and mocks
- **Mocking**: Comprehensive fixtures in `jira_mocks.py` and `confluence_mocks.py`
- **Requirements**: All new features need tests, bug fixes need regression tests
- **Test execution**: Run `uv run pytest` before committing
- **Ignored in tests**: Security (S), annotations (ANN), B017 rules

### Git Workflow
- **Branching strategy**:
  - NEVER work directly on `main` branch
  - Feature branches: `feature/description`
  - Bug fixes: `fix/issue-description`
- **Commit messages**:
  - Clear, concise messages focusing on "why" not "what"
  - Use conventional commit style when applicable
  - Add trailers for attribution: `--trailer "Reported-by:<name>"`
  - Reference issues: `--trailer "Github-Issue:#<number>"`
  - NEVER mention AI tools or assistants in commit messages
- **Pre-commit hooks**: Required - runs Ruff, Prettier, Pyright
- **Pull requests**: Fill out PR template, ensure CI passes, request maintainer review

## Domain Context

### MCP (Model Context Protocol)
- MCP is Anthropic's specification for connecting AI models with external tools and data sources
- Tool naming convention: `{service}_{action}` (e.g., `jira_create_issue`, `confluence_search`)
- Supports multiple transport types: stdio, SSE (Server-Sent Events), streamable-http
- Tools can return structured data that AI models can process and act upon

### Atlassian Products
- **Jira**: Issue tracking and project management
  - Supports JQL (Jira Query Language) for issue search
  - Agile features: boards, sprints, epics
  - Custom fields, workflows, and issue types vary by installation
  - API versions differ between Cloud and Server/Data Center
- **Confluence**: Wiki and documentation platform
  - Uses CQL (Confluence Query Language) for search
  - Content organized in spaces with hierarchical pages
  - Storage format (XHTML) vs editor format differences
  - Attachments, comments, and labels as first-class features

### Authentication Methods
- **API Token** (Cloud): Username + API token from id.atlassian.com
- **Personal Access Token** (Server/DC): PAT from user profile
- **OAuth 2.0** (Cloud): Full OAuth flow with automatic token refresh, requires cloud ID

## Important Constraints

### Technical Constraints
- **Python version**: Must support Python 3.10+
- **Package management**: ONLY use `uv`, NEVER `pip` or other package managers
- **MCP version**: Locked to MCP 1.8.0+ but <2.0.0 for API stability
- **FastMCP version**: Locked to 2.3.4+ but <2.4.0 for API stability
- **Line length**: Maximum 88 characters (enforced by Ruff)
- **Type safety**: All functions require type hints (enforced by pre-commit)
- **Docker-first**: Primary distribution method is Docker, not direct Python installation

### Development Constraints
- **No file creation**: Prefer editing existing files over creating new ones
- **Branching**: Never commit directly to `main` branch
- **Pre-commit**: All commits must pass pre-commit hooks (Ruff, Pyright, Prettier)
- **Testing**: Tests must pass before committing
- **Attribution**: Never mention AI tools in commit messages or code comments

### API Constraints
- **Atlassian API rate limits**: Respect rate limits for both Cloud and Server
- **OAuth token expiry**: Handle token refresh gracefully
- **API version differences**: Cloud vs Server/Data Center have different capabilities
- **Markdown limitations**: Confluence storage format has specific requirements

## External Dependencies

### Core Atlassian APIs
- **Jira REST API**: v2 (Server/DC) and v3 (Cloud)
- **Confluence REST API**: v1 (legacy) and v2 (modern, limited availability)
- **Atlassian OAuth 2.0**: For Cloud authentication
- **Atlassian Cloud ID**: Required for OAuth multi-cloud support

### Third-party Services
- **GitHub**: Repository hosting, CI/CD (GitHub Actions), issue tracking
- **GitHub Container Registry (ghcr.io)**: Docker image distribution
- **PyPI**: Python package distribution
- **Atlassian Developer Console**: OAuth app management

### Development Tools
- **pre-commit.ci**: Automated pre-commit hook execution
- **Dependabot**: Automated dependency updates
- **Docker Hub**: Alternative container registry (legacy)

### Python Package Dependencies
- **atlassian-python-api**: Core Atlassian API wrapper
- **FastMCP**: MCP server framework
- **Pydantic**: Data validation and settings management
- **httpx/requests**: HTTP client libraries with proxy support
- **BeautifulSoup4**: HTML parsing for content extraction
- **markdownify**: HTML to Markdown conversion
- **markdown-to-confluence**: Markdown to Confluence storage format
- **keyring**: Secure credential storage for OAuth tokens
- **cachetools**: TTL-based caching for API responses
- **trio**: Async runtime for MCP protocol
- **click**: CLI argument parsing
- **python-dotenv**: Environment variable management
