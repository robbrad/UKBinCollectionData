"""Small fail-closed proxy for the separately approved live SKDC canary.

The proxy deliberately has no general forwarding mode.  It accepts only the two
published South Kesteven origins, never records a request target or payload, and
applies a small global connection delay/budget.  It is intended to be the only
container attached to both the canary's internal network and its egress network.
"""

from __future__ import annotations

import argparse
import logging
import selectors
import socket
import socketserver
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

ALLOWED_HOSTS = frozenset(
    {
        "www.southkesteven.gov.uk",
        "selfservice.southkesteven.gov.uk",
    }
)
ALLOWED_PORTS = frozenset({80, 443})
ALLOWED_HTTP_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "POST"})
MAX_HEADER_BYTES = 64 * 1024
SOCKET_TIMEOUT_SECONDS = 15
TUNNEL_IDLE_TIMEOUT_SECONDS = 45

_LOGGER = logging.getLogger("ukbcd.live_allowlist_proxy")


class ProxyRequestDenied(ValueError):
    """The request is outside the deliberately tiny egress policy."""


class ProxyRateLimitExceeded(RuntimeError):
    """The one-shot canary exhausted its bounded proxy request budget."""


@dataclass(frozen=True)
class ProxyRequest:
    """Validated upstream request metadata.

    ``forward_header`` may contain a URL path and must never be logged.
    """

    method: str
    host: str
    port: int
    is_tunnel: bool
    forward_header: bytes | None


class RequestLimiter:
    """Serialize upstream connection starts and enforce a hard request budget."""

    def __init__(
        self,
        *,
        max_requests: int,
        minimum_interval_seconds: float,
        clock=time.monotonic,
        sleeper=time.sleep,
    ) -> None:
        if max_requests < 1:
            raise ValueError("max_requests must be positive")
        if minimum_interval_seconds < 0:
            raise ValueError("minimum_interval_seconds cannot be negative")
        self._max_requests = max_requests
        self._minimum_interval = minimum_interval_seconds
        self._clock = clock
        self._sleeper = sleeper
        self._count = 0
        self._last_started: float | None = None
        self._lock = threading.Lock()

    @property
    def count(self) -> int:
        return self._count

    def acquire(self) -> None:
        with self._lock:
            if self._count >= self._max_requests:
                raise ProxyRateLimitExceeded("proxy request budget exhausted")

            now = self._clock()
            if self._last_started is not None:
                delay = self._minimum_interval - (now - self._last_started)
                if delay > 0:
                    self._sleeper(delay)
                    now = self._clock()

            self._count += 1
            self._last_started = now


def _parse_authority(authority: str) -> tuple[str, int]:
    """Return a validated exact allowlisted host and explicit/default port."""
    if not authority or any(character in authority for character in "/?#"):
        raise ProxyRequestDenied("invalid proxy authority")

    parsed = urlsplit(f"//{authority}")
    if parsed.username is not None or parsed.password is not None:
        raise ProxyRequestDenied("credentials are forbidden in proxy authorities")
    if not parsed.hostname:
        raise ProxyRequestDenied("proxy authority has no hostname")

    host = parsed.hostname.casefold()
    if host not in ALLOWED_HOSTS:
        raise ProxyRequestDenied("hostname is not allowlisted")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ProxyRequestDenied("invalid proxy port") from exc
    port = 443 if port is None else port
    if port not in ALLOWED_PORTS:
        raise ProxyRequestDenied("port is not allowlisted")
    return host, port


def parse_proxy_request(header: bytes) -> ProxyRequest:
    """Validate a single HTTP proxy header without contacting the network."""
    if not header.endswith(b"\r\n\r\n") or len(header) > MAX_HEADER_BYTES:
        raise ProxyRequestDenied("invalid proxy header framing")
    try:
        text = header.decode("iso-8859-1")
    except UnicodeDecodeError as exc:  # pragma: no cover - ISO-8859-1 is total
        raise ProxyRequestDenied("invalid proxy header encoding") from exc

    lines = text[:-4].split("\r\n")
    if not lines:
        raise ProxyRequestDenied("missing request line")
    request_parts = lines[0].split(" ")
    if len(request_parts) != 3:
        raise ProxyRequestDenied("invalid request line")
    method, target, version = request_parts
    method = method.upper()
    if version not in {"HTTP/1.0", "HTTP/1.1"}:
        raise ProxyRequestDenied("unsupported HTTP version")
    if any(line.startswith((" ", "\t")) for line in lines[1:]):
        raise ProxyRequestDenied("folded proxy headers are forbidden")

    if method == "CONNECT":
        host, port = _parse_authority(target)
        return ProxyRequest(method, host, port, True, None)

    if method not in ALLOWED_HTTP_METHODS:
        raise ProxyRequestDenied("HTTP method is not allowlisted")

    parsed = urlsplit(target)
    if (
        parsed.scheme.casefold() != "http"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ProxyRequestDenied("only absolute allowlisted HTTP targets are accepted")
    host = parsed.hostname.casefold()
    if host not in ALLOWED_HOSTS:
        raise ProxyRequestDenied("hostname is not allowlisted")
    try:
        port = parsed.port or 80
    except ValueError as exc:
        raise ProxyRequestDenied("invalid proxy port") from exc
    if port not in ALLOWED_PORTS:
        raise ProxyRequestDenied("port is not allowlisted")

    origin_target = parsed.path or "/"
    if parsed.query:
        origin_target = f"{origin_target}?{parsed.query}"

    forwarded_headers: list[str] = []
    for line in lines[1:]:
        if not line or ":" not in line:
            if line:
                raise ProxyRequestDenied("malformed proxy header")
            continue
        name, value = line.split(":", 1)
        normalized_name = name.strip().casefold()
        if normalized_name in {
            "connection",
            "host",
            "proxy-authorization",
            "proxy-connection",
        }:
            continue
        forwarded_headers.append(f"{name.strip()}:{value}")

    host_header = host if port == 80 else f"{host}:{port}"
    forward_lines = [
        f"{method} {origin_target} {version}",
        f"Host: {host_header}",
        *forwarded_headers,
        "Connection: close",
        "",
        "",
    ]
    return ProxyRequest(
        method,
        host,
        port,
        False,
        "\r\n".join(forward_lines).encode("iso-8859-1"),
    )


def safe_log_line(host: str | None, status: int) -> str:
    """Return a log line containing no URL, payload, or denied hostname."""
    safe_host = host if host in ALLOWED_HOSTS else "[DENIED]"
    return f"host={safe_host} status={int(status)}"


def _read_header(connection: socket.socket) -> tuple[bytes, bytes]:
    buffer = bytearray()
    while b"\r\n\r\n" not in buffer:
        chunk = connection.recv(4096)
        if not chunk:
            raise ProxyRequestDenied("connection ended before proxy header")
        buffer.extend(chunk)
        if len(buffer) > MAX_HEADER_BYTES:
            raise ProxyRequestDenied("proxy header is too large")
    marker = buffer.index(b"\r\n\r\n") + 4
    return bytes(buffer[:marker]), bytes(buffer[marker:])


def _relay(left: socket.socket, right: socket.socket) -> None:
    selector = selectors.DefaultSelector()
    selector.register(left, selectors.EVENT_READ, right)
    selector.register(right, selectors.EVENT_READ, left)
    try:
        while True:
            events = selector.select(TUNNEL_IDLE_TIMEOUT_SECONDS)
            if not events:
                return
            for key, _ in events:
                source = key.fileobj
                destination = key.data
                chunk = source.recv(64 * 1024)
                if not chunk:
                    return
                destination.sendall(chunk)
    finally:
        selector.close()


class AllowlistProxyHandler(socketserver.BaseRequestHandler):
    """Handle one validated tunnel or one close-delimited HTTP exchange."""

    server: "AllowlistProxyServer"

    def handle(self) -> None:
        self.request.settimeout(SOCKET_TIMEOUT_SECONDS)
        allowed_host: str | None = None
        try:
            header, buffered_body = _read_header(self.request)
            decision = parse_proxy_request(header)
            allowed_host = decision.host
            self.server.limiter.acquire()

            with socket.create_connection(
                (decision.host, decision.port), timeout=SOCKET_TIMEOUT_SECONDS
            ) as upstream:
                upstream.settimeout(TUNNEL_IDLE_TIMEOUT_SECONDS)
                self.request.settimeout(TUNNEL_IDLE_TIMEOUT_SECONDS)
                if decision.is_tunnel:
                    self.request.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                else:
                    assert decision.forward_header is not None
                    upstream.sendall(decision.forward_header)
                    if buffered_body:
                        upstream.sendall(buffered_body)
                _LOGGER.info(safe_log_line(decision.host, 200))
                _relay(self.request, upstream)
        except ProxyRateLimitExceeded:
            self._send_error(429)
            _LOGGER.warning(safe_log_line(allowed_host, 429))
        except ProxyRequestDenied:
            self._send_error(403)
            _LOGGER.warning(safe_log_line(None, 403))
        except (OSError, TimeoutError):
            self._send_error(502)
            _LOGGER.warning(safe_log_line(allowed_host, 502))

    def _send_error(self, status: int) -> None:
        reason = {403: "Forbidden", 429: "Too Many Requests", 502: "Bad Gateway"}[
            status
        ]
        response = (
            f"HTTP/1.1 {status} {reason}\r\n"
            "Content-Length: 0\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii")
        try:
            self.request.sendall(response)
        except OSError:
            pass


class AllowlistProxyServer(socketserver.ThreadingTCPServer):
    """Threaded proxy server with a process-wide limiter."""

    allow_reuse_address = False
    daemon_threads = True

    def __init__(self, address, handler, *, limiter: RequestLimiter):
        self.limiter = limiter
        super().__init__(address, handler)

    def handle_error(self, request, client_address) -> None:
        """Suppress default tracebacks so unexpected failures cannot leak data."""
        del request, client_address
        _LOGGER.error(safe_log_line(None, 500))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=3128)
    parser.add_argument("--max-requests", type=int, default=256)
    parser.add_argument("--minimum-interval-ms", type=int, default=25)
    args = parser.parse_args()

    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    if not 1 <= args.max_requests <= 256:
        parser.error("max-requests must be between 1 and 256")
    if not 25 <= args.minimum_interval_ms <= 10_000:
        parser.error("minimum-interval-ms must be between 25 and 10000")

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    limiter = RequestLimiter(
        max_requests=args.max_requests,
        minimum_interval_seconds=args.minimum_interval_ms / 1000,
    )
    with AllowlistProxyServer(
        (args.listen, args.port), AllowlistProxyHandler, limiter=limiter
    ) as server:
        server.serve_forever(poll_interval=0.25)


if __name__ == "__main__":
    main()
