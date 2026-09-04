from scripts import mcp_client


def test_tool_description_summary_handles_missing_description():
    assert mcp_client.tool_description_summary(None) == "(no description)"
    assert mcp_client.tool_description_summary("") == "(no description)"


def test_tool_description_summary_returns_first_non_empty_line():
    description = "\n  Search the authorized corpus.\nMore details."

    assert mcp_client.tool_description_summary(description) == "Search the authorized corpus."
