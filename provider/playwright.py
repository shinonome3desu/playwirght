import json
from typing import Any, Literal
from urllib.request import Request, urlopen

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from playwright.sync_api import sync_playwright


def validate_connection(uri: str, uri_type: Literal["ws", "cdp"]) -> None:
    with sync_playwright() as p:
        if uri_type == "ws":
            browser = p.chromium.connect(ws_endpoint=uri, timeout=30_000)
        else:
            browser = p.chromium.connect_over_cdp(endpoint_url=uri, timeout=30_000)
        browser.close()


def validate_mcp_connection(uri: str) -> None:
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }
    ).encode("utf-8")
    request = Request(
        uri,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))
    if "error" in data:
        raise ValueError(data["error"])


class PlaywrightProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            mcp_uri = credentials.get("mcp_uri")
            if mcp_uri:
                validate_mcp_connection(mcp_uri)
                return
            uri = credentials.get("playwright_uri")
            if not uri:
                raise ToolProviderCredentialValidationError(
                    "playwright_uri or mcp_uri is required"
                )
            uri_type = credentials.get("uri_type", "ws")
            validate_connection(uri, uri_type)
        except Exception as e:
            raise ToolProviderCredentialValidationError(str(e))
