"""TCP proxy that adds a fixed one-way delay, for latency measurement.

Inserts a configurable delay on every byte it forwards in either direction, so one
connection sees roughly twice the configured delay as round-trip time. It answers
one question: does interactive record selection still meet its p95 budget when the
Shape Shifter backend and the Authority Service are not on the same host?

The proxy is deliberately minimal. It forwards bytes and delays them; it does not
parse HTTP, reorder connections, or buffer more than it needs to. It is
measurement tooling and must never appear on a deployed request path.

Usage:
    python3 scripts/pilot/delay_proxy.py --upstream pilot-authority:8000 --delay-ms 50
    python3 scripts/pilot/delay_proxy.py --listen 8001 --upstream host:8000 --delay-ms 100
"""

from __future__ import annotations

import argparse
import asyncio
import sys

BUFFER_SIZE = 65536
CONNECT_TIMEOUT = 10.0


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, delay: float) -> None:
    """Forward everything from reader to writer, pausing before each write."""
    try:
        while True:
            chunk = await reader.read(BUFFER_SIZE)
            if not chunk:
                break
            if delay:
                await asyncio.sleep(delay)
            writer.write(chunk)
            await writer.drain()
    except (ConnectionError, asyncio.IncompleteReadError):
        pass
    finally:
        try:
            writer.close()
        except OSError:
            pass


async def _handle_client(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    upstream_host: str,
    upstream_port: int,
    delay: float,
) -> None:
    """Open one upstream connection and relay both directions."""
    try:
        upstream_reader, upstream_writer = await asyncio.wait_for(
            asyncio.open_connection(upstream_host, upstream_port),
            timeout=CONNECT_TIMEOUT,
        )
    except (OSError, asyncio.TimeoutError):
        client_writer.close()
        return

    await asyncio.gather(
        _pipe(client_reader, upstream_writer, delay),
        _pipe(upstream_reader, client_writer, delay),
    )


async def serve(host: str, port: int, upstream_host: str, upstream_port: int, delay_ms: float) -> None:
    """Run the proxy until cancelled."""
    delay = delay_ms / 1000.0
    server = await asyncio.start_server(
        lambda reader, writer: _handle_client(reader, writer, upstream_host, upstream_port, delay),
        host=host,
        port=port,
    )
    print(
        f"delay proxy: {host}:{port} -> {upstream_host}:{upstream_port} "
        f"one-way delay {delay_ms:.1f} ms (about {delay_ms * 2:.1f} ms round trip)",
        flush=True,
    )
    async with server:
        await server.serve_forever()


def split_upstream(value: str) -> tuple[str, int]:
    """Split a `host:port` value, defaulting the port to 8000."""
    host, _, port = value.rpartition(":")
    if not host:
        return value, 8000
    return host, int(port or 8000)


def main() -> int:
    """Parse arguments and run the proxy."""
    parser = argparse.ArgumentParser(description="TCP proxy that adds a fixed one-way delay.")
    parser.add_argument("--listen-host", default="0.0.0.0", help="Address to bind (default: 0.0.0.0)")
    parser.add_argument("--listen", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--upstream", required=True, help="host:port of the real service")
    parser.add_argument("--delay-ms", type=float, default=0.0, help="one-way delay in milliseconds")
    args = parser.parse_args()

    upstream_host, upstream_port = split_upstream(args.upstream)
    try:
        asyncio.run(serve(args.listen_host, args.listen, upstream_host, upstream_port, args.delay_ms))
    except KeyboardInterrupt:
        return 0
    except OSError as error:
        print(f"delay proxy failed to bind {args.listen_host}:{args.listen}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
