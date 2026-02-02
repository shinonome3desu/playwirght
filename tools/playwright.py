import json
from collections.abc import Generator, Iterable
from typing import Any, Literal
from urllib.request import Request, urlopen

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from playwright.sync_api import sync_playwright


def run_playwright(uri: str, commands: str, uri_type: Literal["ws", "cdp"]) -> str | bytes | None:
    with sync_playwright() as p:
        if uri_type == "ws":
            browser = p.chromium.connect(ws_endpoint=uri, timeout=30_000)
        else:
            browser = p.chromium.connect_over_cdp(endpoint_url=uri, timeout=30_000)

        local_vars = {"browser": browser}
        try:
            exec(commands, {}, local_vars)  # 互換優先（※危険：後述）
            return local_vars.get("result")
        finally:
            try:
                browser.close()
            except Exception:
                pass


def run_mcp_actions(uri: str, actions: Iterable[dict[str, Any]]) -> Any:
    result: Any = None
    for action in actions:
        if not isinstance(action, dict):
            raise ValueError("Each MCP action must be an object.")
        method = action.get("method")
        params = action.get("params", {})
        if not method:
            raise ValueError("Each MCP action must include a method.")
        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params,
            }
        ).encode("utf-8")
        request = Request(
            uri,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        if "error" in data:
            raise RuntimeError(data["error"])
        result = data.get("result")
    return result


class PlaywrightTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        actions = tool_parameters.get("actions")
        commands = tool_parameters.get("script", "")
        try:
            if actions:
                mcp_uri = self.runtime.credentials.get("mcp_uri")
                if not mcp_uri:
                    raise ValueError("mcp_uri is required when actions are provided.")
                result = run_mcp_actions(mcp_uri, actions)
            elif commands:
                result = run_playwright(
                    self.runtime.credentials.get("playwright_uri"),
                    commands,
                    self.runtime.credentials.get("uri_type", "ws"),
                )
            else:
                raise ValueError("Either actions or script must be provided.")
        except Exception as e:
            yield self.create_text_message(f"Playwright error: {e}")
            return

        if isinstance(result, (bytes, bytearray)):
            yield self.create_blob_message(blob=bytes(result), meta={"mime_type": "image/png"})
        elif isinstance(result, str):
            yield self.create_text_message(result)
        elif result is None:
            yield self.create_text_message("Nothing output")
        else:
            yield self.create_text_message(json.dumps(result, ensure_ascii=False))
