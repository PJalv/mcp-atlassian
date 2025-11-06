{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "mcp-atlassian-runtime";

  buildInputs = with pkgs; [
    # Python runtime (3.10 minimum required)
    python310
    
    # uv package manager (required for dependency management)
    uv
    
    # Git (required by uv-dynamic-versioning)
    git
    
    # SSL certificates for HTTPS requests
    cacert
  ];

  shellHook = ''
    echo "MCP Atlassian Runtime Environment"
    echo "================================="
    echo "Python: $(python --version)"
    echo "uv: $(uv --version)"
    echo ""
    echo "To install dependencies: uv sync --frozen"
    echo "To run the server: uv run mcp-atlassian"
    echo ""
    echo "For OAuth setup: uv run mcp-atlassian --oauth-setup"
    echo "For verbose mode: uv run mcp-atlassian -v"
  '';

  # Environment variables for runtime
  SSL_CERT_FILE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
  
  # Ensure Python can find SSL certificates
  NIX_SSL_CERT_FILE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
}
