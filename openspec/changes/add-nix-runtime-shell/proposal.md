## Why

Users running NixOS or using the Nix package manager need a straightforward way to run the MCP Atlassian server without Docker. Currently, the project only provides Docker-based deployment, which requires Docker to be installed and configured. A `shell.nix` file would allow Nix users to enter a runtime environment with all dependencies available, making it easier to run the server directly on their system.

## What Changes

- Add a `shell.nix` file to the project root that provides a runtime environment for running the MCP server
- The shell will use `uv` (already the project's package manager) to manage Python dependencies
- The shell includes Python 3.10+, `uv`, and system-level dependencies required by the project
- Users can run `nix-shell` to enter the environment, then use `uv run mcp-atlassian` to start the server
- The implementation is runtime-focused (not development tooling) and minimal

## Impact

- **Affected specs**: `nix-runtime` (new capability)
- **Affected code**: 
  - `shell.nix` (new file) - Provides Nix runtime environment
- **User experience**: Enables Nix users to run the server without Docker
- **Breaking changes**: None - purely additive feature
- **Existing workflows**: No impact on Docker, PyPI, or uv-based workflows
