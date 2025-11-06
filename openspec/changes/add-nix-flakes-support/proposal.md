# Add Nix Flakes Support

## Summary

Enable users to run mcp-atlassian directly from the GitHub repository URL using Nix Flakes, without requiring repository cloning or manual dependency installation.

## Problem

Currently, Nix users must:
1. Clone the repository manually
2. Enter nix-shell environment
3. Run `uv sync --frozen`
4. Execute `uv run mcp-atlassian`

This multi-step process is cumbersome compared to the Docker experience (`docker run ghcr.io/sooperset/mcp-atlassian:latest`).

## Proposed Solution

Add a `flake.nix` file that enables:
- Direct execution: `nix run github:sooperset/mcp-atlassian`
- Shell environment: `nix develop github:sooperset/mcp-atlassian`
- Declarative package installation: Add to NixOS/home-manager configurations

## Benefits

1. **Zero-clone execution**: Run server directly from GitHub URL
2. **Reproducibility**: Flakes provide hermetic, reproducible builds
3. **Declarative configuration**: Users can add mcp-atlassian to their Nix configs
4. **Better Nix ecosystem integration**: First-class Nix support alongside Docker

## User Impact

**Before:**
```bash
git clone https://github.com/sooperset/mcp-atlassian.git
cd mcp-atlassian
nix-shell
uv sync --frozen
uv run mcp-atlassian
```

**After:**
```bash
nix run github:sooperset/mcp-atlassian
```

## Implementation Scope

- Create `flake.nix` with apps, devShells, and packages outputs
- Add `flake.lock` for dependency pinning
- Update README.md with Flakes usage examples
- Maintain backward compatibility with existing `shell.nix`

## Dependencies

None. This change builds on the existing `shell.nix` infrastructure (add-nix-runtime-shell).

## Risks & Mitigations

**Risk**: Flakes are still experimental in Nix
**Mitigation**: Keep `shell.nix` for users without Flakes enabled

**Risk**: Build dependencies complexity with uv and Python packaging
**Mitigation**: Use buildPythonPackage with uv-based build backend

## Timeline

Estimated implementation: 1-2 days
- Day 1: Flake implementation and testing
- Day 2: Documentation and validation
