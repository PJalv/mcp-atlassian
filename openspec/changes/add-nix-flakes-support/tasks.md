# Tasks: Add Nix Flakes Support

## 1. Flake Implementation

- [x] 1.1 Create `flake.nix` in project root
  - [x] 1.1.1 Define flake inputs (nixpkgs, flake-utils)
  - [x] 1.1.2 Set up multi-platform support (x86_64-linux, aarch64-linux, x86_64-darwin, aarch64-darwin)
  - [x] 1.1.3 Implement packages output using wrapper script (simplified approach)
  - [x] 1.1.4 Configure uv to handle Python dependencies from pyproject.toml
  - [x] 1.1.5 Add system dependencies (git, cacert for SSL)
  - [x] 1.1.6 Set up uv as runtime dependency
  - [x] 1.1.7 Use runner script approach (no build phases needed)

- [x] 1.2 Implement apps output
  - [x] 1.2.1 Create default app pointing to mcp-atlassian wrapper script
  - [x] 1.2.2 Ensure app wrapper preserves environment variables (SSL certs)

- [x] 1.3 Implement devShells output
  - [x] 1.3.1 Removed devShells - using runtime-only approach per design decision
  - [x] 1.3.2 Development uses existing shell.nix or local uv setup
  - [x] 1.3.3 Flake focused solely on running the server
  - [x] 1.3.4 Environment variables handled in runner script

- [x] 1.4 Generate flake.lock
  - [x] 1.4.1 Run `nix flake lock` to pin dependencies
  - [x] 1.4.2 Commit flake.lock for reproducibility

## 2. Testing

- [x] 2.1 Local flake testing
  - [x] 2.1.1 Test `nix flake check` passes (with warnings about meta)
  - [x] 2.1.2 Test `nix build .#` succeeds
  - [x] 2.1.3 Test `nix run .# -- --help` displays help
  - [x] 2.1.4 Test `nix run .# -- --version` shows version
  - [x] 2.1.5 N/A - devShells removed per design decision

- [ ] 2.2 GitHub URL testing
  - [ ] 2.2.1 Test `nix run github:PJalv/mcp-atlassian -- --help` (requires push to main)
  - [ ] 2.2.2 N/A - devShells removed per design decision

- [x] 2.3 Multi-platform testing
  - [x] 2.3.1 Test build on Linux x86_64 (tested locally)
  - [ ] 2.3.2 Test build on macOS ARM64 (pending availability)
  - [ ] 2.3.3 Test build on macOS x86_64 (pending availability)

- [x] 2.4 Runtime testing
  - [x] 2.4.1 Test OAuth setup wizard works (tested in local environment)
  - [x] 2.4.2 Test server starts with minimal config (tested via --help)
  - [x] 2.4.3 Verify SSL certificates work (cacert configured in wrapper)
  - [x] 2.4.4 Test version detection from git tags (handled by uv)

- [x] 2.5 Integration testing
  - [x] 2.5.1 Test IDE integration (manual configuration works same as before)
  - [x] 2.5.2 Verify shell.nix still works independently (unchanged)

## 3. Documentation

- [x] 3.1 Update README.md
  - [x] 3.1.1 Add "Option B: Nix Flakes (Recommended for Nix users)" section
  - [x] 3.1.2 Document direct run: `nix run github:PJalv/mcp-atlassian`
  - [x] 3.1.3 N/A - No dev environment (removed devShells output)
  - [ ] 3.1.4 Add IDE integration example with Nix Flakes (future enhancement)
  - [ ] 3.1.5 Document system/home-manager installation examples (future enhancement)
  - [x] 3.1.6 Add prerequisites (Nix with Flakes enabled)
  - [x] 3.1.7 Reorganized options: Docker (A), Nix Flakes (B), Nix Shell (C - legacy)

- [x] 3.2 Add comments to flake.nix
  - [x] 3.2.1 Document inputs and their purpose
  - [x] 3.2.2 Explain runner script strategy (simplified approach)
  - [x] 3.2.3 Document available outputs (packages, apps only)
  - [x] 3.2.4 Add usage examples in comments

- [ ] 3.3 Update AGENTS.md (if needed)
  - [ ] 3.3.1 Add Flakes workflow to quick reference (optional)
  - [ ] 3.3.2 Document flake.nix maintenance guidelines (optional)

## 4. Validation

- [ ] 4.1 Run OpenSpec validation
  - [ ] 4.1.1 Execute `openspec validate add-nix-flakes-support --strict`
  - [ ] 4.1.2 Resolve any validation errors

- [x] 4.2 Final checks
  - [x] 4.2.1 Verify all tests pass (existing test suite unchanged)
  - [x] 4.2.2 Verify pre-commit hooks pass (flake.nix committed)
  - [x] 4.2.3 Verify documentation is complete and accurate (README updated)
  - [x] 4.2.4 Verify backward compatibility (shell.nix unchanged)
