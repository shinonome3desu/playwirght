from typing import Any, Literal

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


class PlaywrightProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            uri = credentials.get("playwright_uri")
            uri_type = credentials.get("uri_type", "ws")
            validate_connection(uri, uri_type)
        except Exception as e:
            raise ToolProviderCredentialValidationError(str(e))
