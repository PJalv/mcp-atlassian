## 1. Design and Planning
- [x] 1.1 Review existing authentication and configuration patterns in `servers/dependencies.py`
- [x] 1.2 Design status check response schema (JSON structure)
- [x] 1.3 Identify which API calls to use for connectivity validation (lightweight endpoints)

## 2. Implementation
- [x] 2.1 Create status checking helper functions in `servers/dependencies.py`
  - [x] 2.1.1 Implement `check_jira_connection_status()` function
  - [x] 2.1.2 Implement `check_confluence_connection_status()` function
- [x] 2.2 Add `get_connection_status` tool to `servers/main.py`
  - [x] 2.2.1 Define tool with appropriate tags (`read`, `status`)
  - [x] 2.2.2 Implement tool logic to check both services
  - [x] 2.2.3 Format response as structured JSON
  - [x] 2.2.4 Handle cases where services are not configured
  - [x] 2.2.5 Handle authentication failures gracefully

## 3. Testing
- [x] 3.1 Create unit tests in `tests/unit/servers/test_main_server.py`
  - [x] 3.1.1 Test with both services configured and working
  - [x] 3.1.2 Test with only Jira configured
  - [x] 3.1.3 Test with only Confluence configured
  - [x] 3.1.4 Test with neither service configured
  - [x] 3.1.5 Test with authentication failures
  - [x] 3.1.6 Test with network/connectivity errors
- [x] 3.2 Create integration test in `tests/integration/test_mcp_protocol.py`
  - [x] 3.2.1 Test tool listing includes `get_connection_status`
  - [x] 3.2.2 Test tool execution returns expected structure
- [x] 3.3 Manual testing with real Atlassian instances

## 4. Documentation
- [x] 4.1 Add tool description to README.md tools table
- [x] 4.2 Update any relevant documentation about diagnostics/troubleshooting
