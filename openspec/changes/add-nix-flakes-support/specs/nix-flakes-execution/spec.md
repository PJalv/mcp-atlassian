# Spec: Nix Flakes Execution

## ADDED Requirements

### Requirement: Direct GitHub Execution

The system SHALL allow users to run mcp-atlassian directly from the GitHub repository URL without cloning.

#### Scenario: Run server from GitHub URL

**Given** the user has Nix with Flakes enabled
**When** they execute `nix run github:PJalv/mcp-atlassian -- --help`
**Then** the help text is displayed without requiring repository cloning

#### Scenario: Run server with environment configuration

**Given** the user has Nix with Flakes enabled  
**And** they have set environment variables for Confluence/Jira credentials
**When** they execute `nix run github:PJalv/mcp-atlassian`
**Then** the MCP server starts and connects to configured Atlassian services

#### Scenario: Run OAuth setup wizard from GitHub

**Given** the user has Nix with Flakes enabled
**When** they execute `nix run github:PJalv/mcp-atlassian -- --oauth-setup`
**Then** the OAuth setup wizard starts and guides them through configuration

---

### Requirement: Development Environment Access

The system SHALL provide users with a development environment containing all required tools pre-installed.

#### Scenario: Enter development shell from GitHub

**Given** the user has Nix with Flakes enabled
**When** they execute `nix develop github:PJalv/mcp-atlassian`
**Then** they are dropped into a shell with Python, uv, git, and dev tools available

#### Scenario: Run tests in development shell

**Given** the user is in a `nix develop` shell
**When** they execute `uv run pytest`
**Then** the test suite runs successfully

---

### Requirement: Multi-Platform Support

The Flake MUST build and run successfully on common development platforms (x86_64-linux, aarch64-linux, x86_64-darwin, aarch64-darwin).

#### Scenario: Build on Linux x86_64

**Given** a Linux x86_64 system with Nix
**When** the flake is built
**Then** the package builds successfully and passes smoke tests

#### Scenario: Build on macOS ARM64

**Given** a macOS ARM64 (Apple Silicon) system with Nix
**When** the flake is built
**Then** the package builds successfully and passes smoke tests

#### Scenario: Build on macOS x86_64

**Given** a macOS x86_64 (Intel) system with Nix
**When** the flake is built
**Then** the package builds successfully and passes smoke tests

---

### Requirement: Declarative System Configuration

The system SHALL allow users to add mcp-atlassian to their NixOS or home-manager configurations declaratively.

#### Scenario: Install via NixOS configuration

**Given** a NixOS system configuration
**When** the user adds the flake package to `environment.systemPackages`
**Then** mcp-atlassian is available system-wide after rebuild

#### Scenario: Install via home-manager

**Given** a home-manager configuration
**When** the user adds the flake package to `home.packages`
**Then** mcp-atlassian is available in the user's environment after activation

---

### Requirement: Version Tracking

The built package MUST correctly report its version based on git tags using uv-dynamic-versioning.

#### Scenario: Version from git tag

**Given** the repository has git tags (e.g., v1.2.3)
**When** the package is built
**Then** `mcp-atlassian --version` reports the correct version from git tags

#### Scenario: Version fallback

**Given** git information is not available during build
**When** the package is built
**Then** `mcp-atlassian --version` reports the fallback version "0.0.0"

---

### Requirement: Reproducible Builds

The Flake MUST produce bit-for-bit identical builds given the same locked inputs.

#### Scenario: Reproducible build with locked inputs

**Given** a flake.lock file with pinned dependencies
**When** the same flake is built on different machines
**Then** the resulting package hashes are identical

#### Scenario: Dependency isolation

**Given** the build process runs in Nix sandbox
**When** the package is built
**Then** no network access occurs during build (all dependencies pre-fetched)

---

### Requirement: IDE Integration Support

The system SHALL support configuration in IDEs (Claude Desktop, Cursor) using the Nix Flake installation method.

#### Scenario: Configure Claude Desktop with Nix

**Given** Claude Desktop is installed
**When** the user configures `command: "nix"` with `args: ["run", "github:PJalv/mcp-atlassian", "--"]`
**Then** Claude Desktop can launch and communicate with the MCP server

#### Scenario: Configure Cursor with Nix

**Given** Cursor IDE is installed
**When** the user configures the Nix run command in MCP settings
**Then** Cursor can launch and communicate with the MCP server

---

### Requirement: Backward Compatibility

The system MUST maintain backward compatibility with existing shell.nix workflows for non-Flakes users.

#### Scenario: shell.nix still works

**Given** a user prefers non-Flakes workflow
**When** they execute `nix-shell` in the repository
**Then** they enter the runtime environment as before (without Flakes)

#### Scenario: Documentation shows both options

**Given** the README.md is updated
**When** users read the Nix installation section
**Then** both Flakes and non-Flakes approaches are documented

---

### Requirement: Smoke Testing

The built package MUST pass basic functionality checks including help, version, and startup commands.

#### Scenario: Help command works

**Given** the package is built
**When** `mcp-atlassian --help` is executed
**Then** help text is displayed without errors

#### Scenario: Version command works

**Given** the package is built
**When** `mcp-atlassian --version` is executed
**Then** version information is displayed without errors

#### Scenario: Server starts with minimal config

**Given** the package is built  
**And** minimal environment variables are set (CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN)
**When** `mcp-atlassian` is executed
**Then** the server starts without immediate crashes (validated via process exit code after brief run)
