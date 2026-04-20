"""Commercial-tier MCP tool registrations.

Each workflow in simploy.workflows gets wrapped into an MCP tool via
`register_workflow_tools(server, prismhr_client)`. Tools instantiate
the workflow's live reader, call run_*, and return a serializable
dict suitable for an LLM agent to read.
"""
