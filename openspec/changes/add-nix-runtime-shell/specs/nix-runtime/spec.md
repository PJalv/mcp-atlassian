## ADDED Requirements

### Requirement: Nix Runtime Shell Environment

The project SHALL provide a `shell.nix` file that creates a runtime environment for executing the MCP Atlassian server using the Nix package manager.

#### Scenario: User enters nix-shell successfully

- **WHEN** a user with Nix installed runs `nix-shell` in the project root
- **THEN** a shell environment is created with Python 3.10+, uv, and all required system dependencies available

#### Scenario: User runs server from nix-shell

- **WHEN** a user enters the nix-shell and runs `uv sync --frozen`
- **AND** runs `uv run mcp-atlassian` with appropriate environment variables
- **THEN** the MCP server starts successfully and functions identically to Docker/native deployments

#### Scenario: System dependencies are available

- **WHEN** the nix-shell is active
- **THEN** all system-level dependencies required by Python packages (SSL libraries, libffi, build tools) are available in the environment

### Requirement: UV Package Manager Integration

The Nix runtime environment SHALL use `uv` as the Python package manager, consistent with the project's existing tooling.

#### Scenario: UV is available in nix-shell

- **WHEN** a user enters the nix-shell
- **THEN** the `uv` command is available and functional
- **AND** all uv subcommands (sync, run, pip) work as expected

#### Scenario: UV installs dependencies correctly

- **WHEN** a user runs `uv sync` or `uv sync --frozen` inside nix-shell
- **THEN** all Python dependencies from `pyproject.toml` and `uv.lock` are installed successfully
- **AND** the installed packages can import and function correctly

### Requirement: Runtime-Only Environment

The Nix shell environment SHALL be optimized for runtime usage, excluding development dependencies and tooling.

#### Scenario: Minimal runtime packages included

- **WHEN** the nix-shell is created
- **THEN** only runtime-essential packages are included (Python, uv, system libraries)
- **AND** development tools (pre-commit, pytest, ruff) are NOT included in the Nix environment
- **AND** development dependencies are handled by `uv sync --dev` if needed by the user

#### Scenario: Shell startup is fast

- **WHEN** a user runs `nix-shell`
- **THEN** the environment builds and loads within a reasonable time (typically under 30 seconds for cached builds)

### Requirement: Environment Configuration

The Nix shell environment SHALL support standard environment variable configuration for server operation.

#### Scenario: Environment variables work in nix-shell

- **WHEN** a user sets environment variables (JIRA_URL, CONFLUENCE_URL, etc.) in nix-shell
- **AND** runs `uv run mcp-atlassian`
- **THEN** the server receives and uses those environment variables correctly

#### Scenario: Dotenv files are supported

- **WHEN** a user creates a `.env` file with configuration
- **AND** runs `uv run mcp-atlassian --env-file .env` in nix-shell
- **THEN** the server loads configuration from the .env file successfully

### Requirement: Documentation and Usability

The Nix shell SHALL include helpful documentation for users.

#### Scenario: Shell provides usage hints

- **WHEN** a user enters the nix-shell
- **THEN** a welcome message or shellHook displays basic usage instructions
- **AND** instructions mention key commands like `uv sync` and `uv run mcp-atlassian`

#### Scenario: README includes Nix instructions

- **WHEN** a user reads the README.md
- **THEN** there is a section documenting Nix-based installation
- **AND** the section includes example commands for entering the shell and running the server
- **AND** the section clarifies that this is an alternative to Docker deployment
