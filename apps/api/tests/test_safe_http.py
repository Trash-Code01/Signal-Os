import asyncio
import socket

import pytest

from core.safe_http import (
    PublicAddressResolver,
    UnsafePublicUrl,
    fetch_public_http_text,
    validate_public_http_url,
)


def _record(address: str, port: int = 443):
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    sockaddr = (address, port, 0, 0) if family == socket.AF_INET6 else (address, port)
    return (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr)


def test_public_nat64_dns_answers_are_accepted():
    resolver = lambda *args, **kwargs: [_record('34.10.149.3'), _record('64:ff9b::220a:9503')]
    assert validate_public_http_url('https://business.example/', resolver=resolver) == 'https://business.example/'


@pytest.mark.parametrize('address', ['64:ff9b::7f00:1', '64:ff9b::a00:1', '64:ff9b::a9fe:a9fe',
                                     '64:ff9b::c0a8:1', '64:ff9b::e000:1', '64:ff9b::',
                                     '64:ff9b::6440:1', '64:ff9b:1::220a:9503'])
def test_nat64_never_allows_internal_or_non_global_destinations(address):
    with pytest.raises(UnsafePublicUrl):
        validate_public_http_url(f'https://[{address}]/')


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/admin",
        "http://service.localhost/admin",
        "http://127.0.0.1/admin",
        "http://10.0.0.1/admin",
        "http://169.254.169.254/latest/meta-data",
        "http://224.0.0.1/",
        "http://240.0.0.1/",
        "http://0.0.0.0/",
        "http://[::1]/",
        "http://[fc00::1]/",
        "http://[fe80::1]/",
        "http://[ff02::1]/",
        "http://[::]/",
    ],
)
def test_validate_public_http_url_rejects_non_public_literals(url):
    with pytest.raises(UnsafePublicUrl):
        validate_public_http_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/file",
        "javascript:alert(1)",
        "https://user:password@example.com/",
        "https:///missing-host",
        "https://example.com:invalid/",
    ],
)
def test_validate_public_http_url_rejects_invalid_url_shapes(url):
    with pytest.raises(UnsafePublicUrl):
        validate_public_http_url(url, resolver=lambda *_args, **_kwargs: [_record("93.184.216.34")])


def test_validate_public_http_url_resolves_every_dns_address():
    calls = []

    def public_resolver(host, port, **kwargs):
        calls.append((host, port, kwargs))
        return [_record("93.184.216.34", port), _record("2606:2800:220:1:248:1893:25c8:1946", port)]

    assert validate_public_http_url(
        "HTTPS://example.com/path?q=1#fragment",
        resolver=public_resolver,
    ) == "https://example.com/path?q=1"
    assert calls == [("example.com", 443, {"type": socket.SOCK_STREAM})]

    def mixed_resolver(_host, port, **_kwargs):
        return [_record("93.184.216.34", port), _record("127.0.0.1", port)]

    with pytest.raises(UnsafePublicUrl):
        validate_public_http_url("https://mixed.example/", resolver=mixed_resolver)


class _FakeResponse:
    def __init__(self, status, *, headers=None, text=""):
        self.status = status
        self.headers = headers or {}
        self._text = text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def text(self):
        return self._text


class _FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requested = []

    def get(self, url, **kwargs):
        self.requested.append((url, kwargs))
        return self.responses.pop(0)


def test_fetch_revalidates_redirect_before_second_request():
    session = _FakeSession(
        [_FakeResponse(302, headers={"Location": "http://internal.example/secret"})]
    )

    def resolver(host, port, **_kwargs):
        address = "93.184.216.34" if host == "public.example" else "10.0.0.5"
        return [_record(address, port)]

    with pytest.raises(UnsafePublicUrl):
        asyncio.run(
            fetch_public_http_text(
                session,
                "https://public.example/start",
                resolver=resolver,
            )
        )

    assert session.requested == [
        ("https://public.example/start", {"allow_redirects": False})
    ]


def test_fetch_allows_public_relative_redirect_and_disables_auto_redirects():
    session = _FakeSession(
        [
            _FakeResponse(301, headers={"Location": "/final"}),
            _FakeResponse(200, text="safe body"),
        ]
    )
    resolver = lambda _host, port, **_kwargs: [_record("93.184.216.34", port)]

    response = asyncio.run(
        fetch_public_http_text(
            session,
            "https://public.example/start",
            resolver=resolver,
        )
    )

    assert response.status == 200
    assert response.url == "https://public.example/final"
    assert response.text == "safe body"
    assert session.requested == [
        ("https://public.example/start", {"allow_redirects": False}),
        ("https://public.example/final", {"allow_redirects": False}),
    ]


def test_connector_resolver_rejects_the_address_used_for_connection():
    class InnerResolver:
        async def resolve(self, host, port, family):
            return [
                {
                    "hostname": host,
                    "host": "127.0.0.1",
                    "port": port,
                    "family": family,
                    "proto": socket.IPPROTO_TCP,
                    "flags": 0,
                }
            ]

        async def close(self):
            return None

    resolver = PublicAddressResolver(InnerResolver())
    with pytest.raises(UnsafePublicUrl):
        asyncio.run(resolver.resolve("rebinding.example", 443))
    asyncio.run(resolver.close())
