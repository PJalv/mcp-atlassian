## Context

Currently, MCP Atlassian users have no built-in way to verify their configuration is working correctly. The only indication of misconfiguration or authentication issues is when they attempt to use a tool and it fails. This creates a poor diagnostic experience, especially when:

- Initial setup of authentication credentials
- Troubleshooting connection issues
- Verifying multi-service configurations (both Jira and Confluence)
- Diagnosing OAuth token expiration or PAT validity
- Confirming proxy settings are working

The proposed `get_connection_status` tool provides a dedicated diagnostic endpoint that validates both Jira and Confluence connectivity and authentication in a single call.

## Goals / Non-Goals

**Goals:**
- Provide a simple, non-invasive way to check Atlassian service connectivity
- Validate authentication credentials are working for configured services
- Return actionable error messages when connections fail
- Support both single-service and multi-service configurations
- Use lightweight API calls that don't impact rate limits significantly
- Return structured status information for programmatic consumption

**Non-Goals:**
- Detailed health monitoring (e.g., response times, API rate limit status)
- Configuration validation beyond connectivity/authentication
- Automatic credential refresh or remediation
- Service availability monitoring (uptime tracking)
- Detailed API endpoint testing beyond basic connectivity

## Decisions

### Decision: Implement as main server tool, not per-service tools
**Rationale:** The status check is a cross-cutting concern that benefits from checking all configured services at once. Putting it in the main server allows a single tool call to check both Jira and Confluence status, providing a holistic view of the MCP server configuration.

**Alternatives considered:**
- Separate `jira_get_status` and `confluence_get_status` tools: More granular but requires multiple calls and doesn't provide a unified view
- Health endpoint in HTTP transport: Useful but wouldn't be accessible in stdio transport mode

### Decision: Use `/rest/api/2/myself` (Jira) and `/rest/api/user/current` (Confluence) for validation
**Rationale:** These lightweight endpoints:
- Require authentication (perfect for validation)
- Return user information (confirms identity)
- Work on both Cloud and Server/Data Center
- Don't consume significant API quota
- Provide deployment type hints (Cloud vs Server)

**Alternatives considered:**
- `/rest/api/2/serverInfo`: Doesn't require auth on some installations
- Project/space listing: Heavier calls that could impact rate limits
- Custom lightweight endpoints: Not standardized across versions

### Decision: Return structured JSON with service-level status objects
**Rationale:** Enables both human-readable diagnostics and programmatic status checking. Structure includes:
```json
{
  "overall_status": "healthy|degraded|unavailable",
  "services": {
    "jira": {
      "configured": true,
      "connected": true,
      "authenticated": true,
      "url": "https://company.atlassian.net",
      "deployment_type": "cloud",
      "authenticated_user": "user@example.com",
      "error": null
    },
    "confluence": {
      "configured": true,
      "connected": false,
      "authenticated": false,
      "url": "https://company.atlassian.net/wiki",
      "deployment_type": "cloud",
      "authenticated_user": null,
      "error": "Authentication failed: Invalid credentials"
    }
  },
  "timestamp": "2025-10-27T12:34:56Z"
}
```

**Alternatives considered:**
- Simple boolean "healthy/unhealthy": Not actionable enough
- Plain text status messages: Not machine-parseable
- Separate status calls per service: Inefficient

### Decision: Tag as both `read` and `status` (new tag)
**Rationale:** The `read` tag ensures it's available in read-only mode. The `status` tag creates a new category for diagnostic/meta tools that can be filtered separately if needed.

**Alternatives considered:**
- Only `read` tag: Works but doesn't distinguish diagnostic tools
- New `diagnostic` tag: Too generic, "status" is more precise

## Risks / Trade-offs

### Risk: Exposing configuration details
**Mitigation:** The tool only returns non-sensitive information (URLs, deployment types, authenticated usernames). API tokens, passwords, and OAuth tokens are never returned.

### Risk: Additional API calls impacting rate limits
**Mitigation:** The status check uses extremely lightweight endpoints (`/myself` and `/user/current`) that consume minimal quota. The tool is intended for occasional diagnostic use, not continuous polling.

### Trade-off: Error handling complexity
The tool must gracefully handle various failure scenarios (network errors, authentication failures, malformed responses). This adds complexity but is necessary for a robust diagnostic tool.

### Trade-off: Maintenance of "current user" endpoints
If Atlassian deprecates or changes these endpoints, the tool will need updates. However, these are stable, long-standing endpoints unlikely to change significantly.

## Migration Plan

This is a new additive feature with no migration required. Existing installations will automatically have access to the new tool upon upgrade.

**Rollout steps:**
1. Implement tool in main server
2. Add unit and integration tests
3. Update documentation
4. Release in next minor version (backwards compatible)

**Rollback:** If issues arise, the tool can be disabled via `ENABLED_TOOLS` environment variable without affecting existing functionality.

## Open Questions

1. **Should we cache status check results?**
   - Initial answer: No - status checks should always be fresh for diagnostic purposes
   - Could revisit if users report rate limit issues

2. **Should we include OAuth token expiry information?**
   - Initial answer: Yes, if OAuth is configured, include token expiry timestamp
   - This helps users understand when they need to refresh tokens

3. **Should we expose this in the health check endpoint for HTTP transport?**
   - Initial answer: Maybe in a future enhancement - keep scope focused for now
   - Could add `/health` endpoint that calls this tool internally
