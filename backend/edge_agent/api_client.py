from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class EdgeAPIError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        retryable: bool = True,
    ):
        super().__init__(message)
        self.retryable = retryable


class EdgeAPIClient:
    def __init__(
        self,
        base_url: str,
        device_key: str,
        timeout_seconds: int = 15,
    ):
        self.base_url = base_url.rstrip("/")
        self.device_key = device_key
        self.timeout_seconds = timeout_seconds
        self._validate_url()

    def _validate_url(self) -> None:
        parsed = urlparse(self.base_url)
        host = (parsed.hostname or "").lower()

        if parsed.scheme == "https":
            return

        if (
            parsed.scheme == "http"
            and host in {
                "127.0.0.1",
                "localhost",
                "::1",
            }
        ):
            return

        raise EdgeAPIError(
            "Edge API must use HTTPS. Plain HTTP is "
            "allowed only for localhost testing.",
            retryable=False,
        )

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "x-smart-classroom-device-key": self.device_key,
        }
        body = None

        if payload is not None:
            body = json.dumps(
                payload,
                separators=(",", ":"),
            ).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(
            url=f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                raw = response.read().decode(
                    "utf-8",
                    errors="replace",
                )
                if not raw:
                    return {}
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise EdgeAPIError(
                        "Edge API returned non-object JSON."
                    )
                return data

        except HTTPError as exc:
            raw = exc.read().decode(
                "utf-8",
                errors="replace",
            )
            detail = raw[:500]

            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    detail = str(
                        parsed.get("detail")
                        or parsed.get("message")
                        or parsed
                    )
            except json.JSONDecodeError:
                pass

            retryable = (
                exc.code >= 500
                or exc.code in {408, 429}
            )
            raise EdgeAPIError(
                f"Edge API HTTP {exc.code}: {detail}",
                retryable=retryable,
            ) from exc

        except (URLError, TimeoutError) as exc:
            raise EdgeAPIError(
                f"Edge API connection failed: {exc}"
            ) from exc

        except json.JSONDecodeError as exc:
            raise EdgeAPIError(
                "Edge API returned invalid JSON."
            ) from exc

    def heartbeat(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/edge/v1/heartbeat",
            payload,
        )

    def context(self) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/edge/v1/context",
        )

    def inference_event(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/edge/v1/inference-events",
            payload,
        )
