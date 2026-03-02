{
  # Nix Flake for MCP Atlassian
  # Provides direct GitHub execution: nix run github:PJalv/mcp-atlassian
  # Development environment: nix develop github:PJalv/mcp-atlassian
  # System installation: Add to NixOS/home-manager configurations
  
  description = "Model Context Protocol (MCP) server for Atlassian products (Confluence and Jira)";

  # Inputs: External flakes this flake depends on
  inputs = {
    # Use nixos-unstable for latest packages
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    
    # Utility functions for multi-platform support
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    # Generate outputs for multiple systems (Linux x86_64/ARM64, macOS x86_64/ARM64)
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        # Python version to use (minimum 3.10 required)
        python = pkgs.python312;
        
        # Create a wrapper script that runs mcp-atlassian using uv
        # This avoids building a full package and instead just runs the project directly
        mcp-atlassian-runner = pkgs.writeShellScriptBin "mcp-atlassian" ''
          export PATH="${pkgs.lib.makeBinPath [ pkgs.uv pkgs.git python pkgs.libxml2 pkgs.libxslt ]}:$PATH"
          export SSL_CERT_FILE="${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
          export NIX_SSL_CERT_FILE="${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
          
          # Expose libxml2 and libxslt headers/libraries for building lxml
          export C_INCLUDE_PATH="${pkgs.libxml2.dev}/include/libxml2:${pkgs.libxslt.dev}/include:$C_INCLUDE_PATH"
          export LIBRARY_PATH="${pkgs.libxml2.out}/lib:${pkgs.libxslt.out}/lib:$LIBRARY_PATH"
          export PKG_CONFIG_PATH="${pkgs.libxml2.dev}/lib/pkgconfig:${pkgs.libxslt.dev}/lib/pkgconfig:$PKG_CONFIG_PATH"
          
          # Disable build isolation so native deps are accessible during package builds
          export UV_NO_BUILD_ISOLATION=1
          
          # Get the source directory (read-only in nix store)
          SOURCE_DIR="${./.}"
          
          # Create a temporary working directory
          WORK_DIR=$(mktemp -d)
          trap "rm -rf $WORK_DIR" EXIT
          
          # Copy source to temporary directory
          cp -r "$SOURCE_DIR"/. "$WORK_DIR/"
          cd "$WORK_DIR"
          
          # Create venv and install build dependencies (needed with UV_NO_BUILD_ISOLATION)
          ${pkgs.uv}/bin/uv venv
          ${pkgs.uv}/bin/uv pip install hatchling setuptools
          
          # Run using uv (will create .venv in temp dir and respect pyproject.toml)
          exec ${pkgs.uv}/bin/uv run mcp-atlassian "$@"
        '';
      in
      {
        # Package outputs - installable via `nix build`
        # This creates the wrapper script as a package
        packages = {
          default = mcp-atlassian-runner;
          mcp-atlassian = mcp-atlassian-runner;
        };
        
        # App outputs - executable via `nix run`
        # Enables: nix run github:PJalv/mcp-atlassian
        apps = {
          default = {
            type = "app";
            program = "${mcp-atlassian-runner}/bin/mcp-atlassian";
          };
          mcp-atlassian = {
            type = "app";
            program = "${mcp-atlassian-runner}/bin/mcp-atlassian";
          };
        };

      }
    );
}
