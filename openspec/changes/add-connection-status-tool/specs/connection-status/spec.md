## ADDED Requirements

### Requirement: Connection Status Tool

The system SHALL provide a `get_connection_status` tool that checks connectivity and authentication status for all configured Atlassian services (Jira and Confluence).

#### Scenario: Both services configured and healthy

- **GIVEN** Jira and Confluence are both configured with valid credentials
- **WHEN** the `get_connection_status` tool is called
- **THEN** the tool returns a JSON response with:
  - `overall_status` set to `"healthy"`
  - `services.jira.configured` set to `true`
  - `services.jira.connected` set to `true`
  - `services.jira.authenticated` set to `true`
  - `services.jira.url` containing the Jira instance URL
  - `services.jira.deployment_type` indicating `"cloud"` or `"server"`
  - `services.jira.authenticated_user` containing the authenticated user identifier
  - `services.jira.error` set to `null`
  - `services.confluence.configured` set to `true`
  - `services.confluence.connected` set to `true`
  - `services.confluence.authenticated` set to `true`
  - `services.confluence.url` containing the Confluence instance URL
  - `services.confluence.deployment_type` indicating `"cloud"` or `"server"`
  - `services.confluence.authenticated_user` containing the authenticated user identifier
  - `services.confluence.error` set to `null`
  - `timestamp` containing the ISO 8601 timestamp of the check

#### Scenario: Only Jira configured

- **GIVEN** only Jira is configured with valid credentials
- **AND** Confluence is not configured
- **WHEN** the `get_connection_status` tool is called
- **THEN** the tool returns a JSON response with:
  - `overall_status` set to `"healthy"`
  - `services.jira` containing complete status information as defined above
  - `services.confluence.configured` set to `false`
  - `services.confluence.connected` set to `false`
  - `services.confluence.authenticated` set to `false`
  - `services.confluence.error` set to `null` or a message indicating service not configured

#### Scenario: Authentication failure for one service

- **GIVEN** Jira is configured with valid credentials
- **AND** Confluence is configured with invalid or expired credentials
- **WHEN** the `get_connection_status` tool is called
- **THEN** the tool returns a JSON response with:
  - `overall_status` set to `"degraded"`
  - `services.jira` showing successful authentication
  - `services.confluence.configured` set to `true`
  - `services.confluence.connected` may be `true` or `false` depending on error type
  - `services.confluence.authenticated` set to `false`
  - `services.confluence.error` containing a descriptive error message
  - `services.confluence.authenticated_user` set to `null`

#### Scenario: Network connectivity error

- **GIVEN** Jira is configured with valid credentials
- **AND** the Jira instance is unreachable due to network issues
- **WHEN** the `get_connection_status` tool is called
- **THEN** the tool returns a JSON response with:
  - `overall_status` set to `"unavailable"` or `"degraded"` (if other services are healthy)
  - `services.jira.configured` set to `true`
  - `services.jira.connected` set to `false`
  - `services.jira.authenticated` set to `false`
  - `services.jira.error` containing a descriptive network error message
  - `services.jira.url` containing the configured URL
  - `services.jira.deployment_type` set to `null` or `"unknown"`
  - `services.jira.authenticated_user` set to `null`

#### Scenario: No services configured

- **GIVEN** neither Jira nor Confluence are configured
- **WHEN** the `get_connection_status` tool is called
- **THEN** the tool returns a JSON response with:
  - `overall_status` set to `"unavailable"`
  - `services.jira.configured` set to `false`
  - `services.confluence.configured` set to `false`
  - All other service fields indicating unconfigured state

### Requirement: Status Check API Endpoints

The system SHALL use lightweight API endpoints for status validation that require authentication but do not significantly impact API rate limits.

#### Scenario: Jira status check endpoint

- **GIVEN** Jira service connectivity needs to be verified
- **WHEN** the status check is performed
- **THEN** the system uses the `/rest/api/2/myself` endpoint (Jira Cloud/Server)
- **AND** extracts the authenticated user information from the response
- **AND** determines deployment type from API response characteristics

#### Scenario: Confluence status check endpoint

- **GIVEN** Confluence service connectivity needs to be verified
- **WHEN** the status check is performed
- **THEN** the system uses the `/rest/api/user/current` endpoint
- **AND** extracts the authenticated user information from the response
- **AND** determines deployment type from API response characteristics

### Requirement: Tool Metadata and Categorization

The system SHALL register the `get_connection_status` tool with appropriate metadata for discovery and filtering.

#### Scenario: Tool registration

- **GIVEN** the MCP server is initializing
- **WHEN** tools are registered
- **THEN** the `get_connection_status` tool is registered with:
  - Tags: `["read", "status"]`
  - Name: `"get_connection_status"`
  - Description: A clear description of the tool's purpose for diagnostic checks
- **AND** the tool is available in read-only mode (due to `"read"` tag)
- **AND** the tool does not require specific service configuration to be listed (but returns appropriate status for unconfigured services)

#### Scenario: Tool availability in read-only mode

- **GIVEN** the MCP server is running in read-only mode
- **WHEN** tools are listed
- **THEN** the `get_connection_status` tool is included in the available tools
- **BECAUSE** it is tagged as `"read"` and performs no write operations

### Requirement: OAuth Token Expiry Information

The system SHALL include OAuth token expiration information in the status response when OAuth authentication is configured.

#### Scenario: OAuth authentication with token expiry

- **GIVEN** Jira is configured with OAuth 2.0 authentication
- **AND** the OAuth token has an expiration timestamp
- **WHEN** the `get_connection_status` tool is called
- **THEN** the `services.jira` response includes an additional field:
  - `oauth_token_expires_at` containing the ISO 8601 timestamp of token expiration
- **AND** if the token is within 24 hours of expiry, includes a warning in the status

#### Scenario: Non-OAuth authentication

- **GIVEN** Jira is configured with API token or PAT authentication
- **WHEN** the `get_connection_status` tool is called
- **THEN** the `services.jira` response does not include `oauth_token_expires_at`
- **OR** the field is set to `null`

### Requirement: Error Message Quality

The system SHALL provide actionable error messages that help users diagnose and resolve configuration issues.

#### Scenario: Authentication error message

- **GIVEN** Confluence authentication fails due to invalid credentials
- **WHEN** the status check is performed
- **THEN** the error message clearly indicates authentication failure
- **AND** suggests checking credentials configuration
- **AND** does not expose sensitive information (tokens, passwords)

#### Scenario: Network error message

- **GIVEN** Jira is unreachable due to network issues
- **WHEN** the status check is performed
- **THEN** the error message indicates connection failure
- **AND** includes relevant details (e.g., "Connection timeout", "Host not found")
- **AND** suggests checking URL configuration and network connectivity

#### Scenario: Configuration error message

- **GIVEN** a service is configured with an invalid URL format
- **WHEN** the status check is performed
- **THEN** the error message indicates URL configuration issue
- **AND** provides guidance on proper URL format
