from collections.abc import Generator
from typing import Any, Literal

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


class PlaywrightTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        commands = tool_parameters.get("script", "")
        try:
            result = run_playwright(
                self.runtime.credentials.get("playwright_uri"),
                commands,
                self.runtime.credentials.get("uri_type", "ws"),
            )
        except Exception as e:
            yield self.create_text_message(f"Playwright error: {e}")
            return

        if isinstance(result, str):
            yield self.create_text_message(result)
        elif isinstance(result, (bytes, bytearray)):
            yield self.create_blob_message(blob=bytes(result), meta={"mime_type": "image/png"})
        else:
            yield self.create_text_message("Nothing output")
