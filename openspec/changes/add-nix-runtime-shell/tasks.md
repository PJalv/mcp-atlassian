## 1. Design and Planning
- [x] 1.1 Review Python dependencies in `pyproject.toml` for system-level requirements
- [x] 1.2 Identify Nix packages needed for runtime (Python 3.10+, uv, system libs)
- [x] 1.3 Design `shell.nix` structure using nixpkgs for dependencies

## 2. Implementation
- [x] 2.1 Create `shell.nix` in project root
  - [x] 2.1.1 Set up nixpkgs with appropriate Python version (3.10+)
  - [x] 2.1.2 Include `uv` package for dependency management
  - [x] 2.1.3 Add system dependencies (SSL certificates, libffi, etc.)
  - [x] 2.1.4 Configure shell hooks to display usage instructions
  - [x] 2.1.5 Set environment variables for runtime (if needed)

## 3. Testing
- [x] 3.1 Manual testing with `nix-shell`
  - [x] 3.1.1 Verify shell environment loads successfully
  - [x] 3.1.2 Test `uv sync` works inside the shell
  - [x] 3.1.3 Test `uv run mcp-atlassian --help` displays help
  - [x] 3.1.4 Test actual server startup with minimal config
  - [x] 3.1.5 Verify OAuth setup wizard works in nix-shell
- [x] 3.2 Test on different Nix configurations
  - [x] 3.2.1 Test on NixOS
  - [x] 3.2.2 Test on non-NixOS Linux with Nix installed

## 4. Documentation
- [x] 4.1 Add Nix installation section to README.md
  - [x] 4.1.1 Document `nix-shell` usage
  - [x] 4.1.2 Show example commands for running the server
  - [x] 4.1.3 Document any environment variable configuration
- [x] 4.2 Add comments to `shell.nix` explaining the setup
