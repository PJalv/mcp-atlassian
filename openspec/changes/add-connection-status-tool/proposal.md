## Why

Users and administrators need a way to verify their MCP server configuration and validate that authentication credentials are working correctly for both Jira and Confluence services. Currently, the only way to discover authentication or connectivity issues is by attempting to use a tool and experiencing a failure. This creates a poor user experience and makes troubleshooting difficult.

## What Changes

- Add a new `get_connection_status` tool to the main MCP server that checks connectivity and authentication for configured Atlassian services
- The tool returns status information for both Jira and Confluence (if configured), including:
  - Whether the service is configured
  - Whether authentication is successful
  - Basic instance information (URL, deployment type, authenticated user)
  - Error details if connection/authentication fails
- The tool is tagged as `read` and `status` (new tag category)
- The tool does not require service-specific configuration - it reports on whatever services are available

## Impact

- **Affected specs**: `connection-status` (new capability)
- **Affected code**: 
  - `src/mcp_atlassian/servers/main.py` - Add new tool implementation
  - `src/mcp_atlassian/servers/dependencies.py` - May need helper functions for status checking
  - `tests/unit/servers/test_main_server.py` - Add tests for new tool
- **User experience**: Provides a diagnostic tool for configuration validation
- **Breaking changes**: None - purely additive feature
