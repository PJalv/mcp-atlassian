# Design: Nix Flakes Support

## Architecture Overview

The Nix Flakes implementation will provide three main outputs:

1. **packages.default**: Installable Python package
2. **apps.default**: Executable application wrapper
3. **devShells.default**: Development environment

## Technical Design

### Flake Structure

```nix
{
  description = "MCP Atlassian server for Confluence and Jira";
  
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };
  
  outputs = { self, nixpkgs, flake-utils }:
    # Multi-platform support (x86_64-linux, aarch64-linux, x86_64-darwin, aarch64-darwin)
}
```

### Package Build Strategy

**Option 1: buildPythonPackage with uv (Recommended)**
- Use nixpkgs' buildPythonPackage
- Leverage uv for dependency resolution (already in pyproject.toml)
- Build from source using hatchling backend
- Pin Python 3.10+ as minimum version

**Option 2: mkDerivation with uv direct installation**
- Simpler but less integrated with Nix Python ecosystem
- Direct uv sync + uv build approach
- May have cache/reproducibility trade-offs

**Chosen: Option 1** for better Nix ecosystem integration

### Build Phases

1. **Fetch Phase**: Get source from GitHub
2. **Build Phase**: Run `uv build` via hatchling backend
3. **Install Phase**: Install built wheel to Nix store
4. **Check Phase**: Run basic smoke tests (`mcp-atlassian --help`)

### Dependency Handling

**Runtime Dependencies (from pyproject.toml):**
- Python 3.10+
- All Python packages handled by buildPythonPackage's propagatedBuildInputs
- System dependencies: git (for uv-dynamic-versioning), cacert (SSL)

**Build Dependencies:**
- hatchling
- uv-dynamic-versioning
- uv (package manager)

### Apps Output

```nix
apps.default = {
  type = "app";
  program = "${self.packages.${system}.default}/bin/mcp-atlassian";
};
```

This enables `nix run github:sooperset/mcp-atlassian`.

### DevShells Output

Reuse existing shell.nix structure but add development tools:
- Python runtime + uv
- pre-commit, ruff, pytest (dev dependencies)
- Git for versioning

### Version Management

- Use uv-dynamic-versioning for git-based version tagging
- Ensure git repository metadata is available during build
- Fallback version: "0.0.0" (as configured in pyproject.toml)

## Integration Points

### With Existing Infrastructure

1. **shell.nix**: Kept for backward compatibility (non-Flakes users)
2. **pyproject.toml**: Single source of truth for dependencies
3. **Docker**: Remains primary distribution (Flakes as alternative)
4. **PyPI**: No conflict; Flakes build from source

### With Nix Ecosystem

1. **NixOS Configuration**: Users can add to system packages
2. **Home Manager**: Can be added to user environment
3. **Flake Registries**: Can be added to user/system registries for shortcuts

## User Experience Scenarios

### Scenario 1: Quick Try (Zero Install)
```bash
nix run github:sooperset/mcp-atlassian -- --help
```

### Scenario 2: Development Environment
```bash
nix develop github:sooperset/mcp-atlassian
# Now in shell with all dev tools
uv run pytest
```

### Scenario 3: System Installation (NixOS)
```nix
# configuration.nix
environment.systemPackages = [
  (builtins.getFlake "github:sooperset/mcp-atlassian").packages.${system}.default
];
```

### Scenario 4: IDE Integration
```json
{
  "mcpServers": {
    "mcp-atlassian": {
      "command": "nix",
      "args": [
        "run",
        "github:sooperset/mcp-atlassian",
        "--",
        "--transport",
        "stdio"
      ],
      "env": {
        "CONFLUENCE_URL": "https://your-company.atlassian.net/wiki",
        "CONFLUENCE_USERNAME": "your.email@company.com",
        "CONFLUENCE_API_TOKEN": "your_api_token"
      }
    }
  }
}
```

## Testing Strategy

### Build Testing
1. Test on multiple platforms (x86_64-linux, aarch64-darwin at minimum)
2. Verify version detection works (git describe)
3. Check all runtime dependencies are included

### Runtime Testing
1. `nix run .# -- --help` succeeds
2. `nix run .# -- --oauth-setup` wizard works
3. Server starts with minimal config
4. Basic tool operations work (smoke tests)

### Integration Testing
1. Test with NixOS VM configuration
2. Test with home-manager integration
3. Verify flake.lock pins dependencies correctly

## Backward Compatibility

- `shell.nix` remains functional for non-Flakes workflows
- No breaking changes to existing Docker/PyPI distributions
- Documentation shows both Flakes and non-Flakes options

## Performance Considerations

- **Build time**: First build may take 5-10 minutes (building Python dependencies)
- **Cache**: Nix binary cache can significantly reduce rebuild times
- **Disk space**: Nix store will contain full dependency closure (~500MB-1GB)

## Security Considerations

- Flake inputs pinned via flake.lock (reproducibility)
- No network access during build (Nix sandbox)
- All dependencies traceable via Nix store paths
- SSL certificates bundled via cacert package

## Future Enhancements

1. **Cachix integration**: Pre-built binaries for faster installs
2. **Overlay support**: Allow users to override dependencies
3. **Multiple apps**: Separate apps for oauth-setup, verbose mode
4. **Cross-compilation**: ARM builds for Raspberry Pi, etc.
