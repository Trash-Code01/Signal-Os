"""Network helpers for fetching user-supplied public website URLs safely."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from typing import Any, Callable, Iterable
from urllib.parse import urljoin, urlsplit, urlunsplit

import aiohttp


class UnsafePublicUrl(ValueError):
    """Raised when a URL could reach a non-public network destination."""


AddressResolver = Callable[..., Iterable[tuple[Any, Any, Any, Any, tuple[Any, ...]]]]
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
NAT64_PUBLIC_PREFIX = ipaddress.IPv6Network('64:ff9b::/96')


def _validate_public_address(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise UnsafePublicUrl("The website hostname did not resolve to an IP address") from exc

    # RFC 6052's well-known NAT64 prefix encodes the destination in the final
    # 32 bits. Python marks the prefix reserved even for public destinations.
    # Validate the embedded IPv4 address with exactly the same safety rules.
    if isinstance(address, ipaddress.IPv6Address) and address in NAT64_PUBLIC_PREFIX:
        _validate_public_address(str(ipaddress.IPv4Address(int(address) & 0xffffffff)))
        return address

    # is_global is deliberately included in addition to the named categories. It
    # also excludes special-purpose ranges that are not consistently classified
    # as private or reserved across Python versions.
    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
        or not address.is_global
    ):
        raise UnsafePublicUrl("The website resolves to a non-public IP address")
    return address


def validate_public_http_url(
    url: str,
    *,
    resolver: AddressResolver = socket.getaddrinfo,
) -> str:
    """Validate and resolve one HTTP(S) URL, returning a normalized URL.

    Every address returned by DNS must be globally routable. Rejecting the whole
    result when even one address is unsafe prevents a dual-stack or multi-record
    hostname from giving the HTTP client a private fallback address.
    """
    if not isinstance(url, str) or not url.strip():
        raise UnsafePublicUrl("A website URL is required")

    parsed = urlsplit(url.strip())
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise UnsafePublicUrl("Only http and https website URLs are allowed")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafePublicUrl("Website URLs cannot contain credentials")

    hostname = parsed.hostname
    if not hostname:
        raise UnsafePublicUrl("The website URL must include a hostname")
    hostname = hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise UnsafePublicUrl("Localhost website URLs are not allowed")

    try:
        port = parsed.port or (443 if scheme == "https" else 80)
    except ValueError as exc:
        raise UnsafePublicUrl("The website URL contains an invalid port") from exc

    try:
        literal_address = ipaddress.ip_address(hostname)
    except ValueError:
        try:
            records = list(resolver(hostname, port, type=socket.SOCK_STREAM))
        except (OSError, socket.gaierror) as exc:
            raise UnsafePublicUrl("The website hostname could not be resolved") from exc
        if not records:
            raise UnsafePublicUrl("The website hostname could not be resolved")
        for record in records:
            sockaddr = record[4]
            if not sockaddr:
                raise UnsafePublicUrl("The website hostname returned an invalid address")
            _validate_public_address(str(sockaddr[0]))
    else:
        _validate_public_address(str(literal_address))

    # Preserve the original (possibly bracketed IPv6) authority after validating
    # its parsed hostname and port. Fragments are never sent in an HTTP request.
    return urlunsplit((scheme, parsed.netloc, parsed.path or "/", parsed.query, ""))


class PublicAddressResolver(aiohttp.abc.AbstractResolver):
    """Validate the exact DNS results aiohttp will use for its connection."""

    def __init__(self, inner: aiohttp.abc.AbstractResolver | None = None) -> None:
        self._inner = inner or aiohttp.resolver.DefaultResolver()

    async def resolve(
        self,
        host: str,
        port: int = 0,
        family: int = socket.AF_INET,
    ) -> list[dict[str, Any]]:
        records = await self._inner.resolve(host, port, family)
        if not records:
            raise UnsafePublicUrl("The website hostname could not be resolved")
        for record in records:
            _validate_public_address(str(record.get("host", "")))
        return records

    async def close(self) -> None:
        await self._inner.close()


@dataclass(frozen=True)
class PublicHttpTextResponse:
    status: int
    url: str
    text: str


async def fetch_public_http_text(
    session: aiohttp.ClientSession,
    url: str,
    *,
    max_redirects: int = 5,
    resolver: AddressResolver = socket.getaddrinfo,
) -> PublicHttpTextResponse:
    """Fetch public text while validating the initial URL and every redirect."""
    if max_redirects < 0:
        raise ValueError("max_redirects cannot be negative")

    current_url = url
    for redirect_count in range(max_redirects + 1):
        # getaddrinfo is blocking, so keep it off the crawler's event loop.
        validated_url = await asyncio.to_thread(
            validate_public_http_url,
            current_url,
            resolver=resolver,
        )
        async with session.get(validated_url, allow_redirects=False) as response:
            if response.status in REDIRECT_STATUSES:
                location = response.headers.get("Location") or response.headers.get("location")
                if not location:
                    raise UnsafePublicUrl("The website returned a redirect without a target")
                if redirect_count >= max_redirects:
                    raise UnsafePublicUrl("The website exceeded the redirect limit")
                # The next loop validates and resolves this exact target before it
                # can be passed to aiohttp.
                current_url = urljoin(validated_url, location)
                continue

            return PublicHttpTextResponse(
                status=response.status,
                url=validated_url,
                text=await response.text(),
            )

    raise UnsafePublicUrl("The website exceeded the redirect limit")
