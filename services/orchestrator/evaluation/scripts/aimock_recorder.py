#!/usr/bin/env python3
"""aimock_recorder.py — spawn a throwaway aimock instance that RECORDS LLM traffic to disk.

One instance per call (one per thread/run): the context manager starts `llmock --record` on a
free local port, waits for `/health`, yields the base URL to point the orchestrator at, and tears
the process down on exit (even if the body raises). Each instance writes the run's fixtures into
its OWN directory, so a thread's recorded traffic never mingles with another's.

Why `--record` and NOT `--record --proxy-only`:
  In aimock, `--proxy-only` means *forward to upstream but write NOTHING to disk* — when proxyOnly
  is set, `persistFixture` early-returns "skipped" (recorder.ts). The two flags together therefore
  record nothing; proxy-only wins. To actually SAVE fixtures you pass `--record` alone. The one cost
  of dropping proxy-only: an *identical* request recurring within a single run replays aimock's
  in-memory cache instead of re-hitting the provider (distinct prompts never trigger this — only an
  exact retry would), which is harmless for recording.

Routing: the orchestrator's model base URL comes from `Context.openai_api_url` (get_model in
react_agent/utils/utils.py). Set it to this instance's `base_url` for the run and every einfra LLM
call (chat, embeddings, reranker) flows through aimock → real upstream, recorded on the way back.
aimock forwards auth upstream but strips it from saved fixtures, so the real key never lands on disk.

CLI/SDK note: aimock ships a TS `LLMock` SDK, but it is in-process Node; the orchestrator is Python,
so we drive the published CLI as a subprocess (the same pattern aimock documents for pytest
`conftest.py`, here without pytest). No Node dependency beyond `npx`.
"""
from __future__ import annotations

import contextlib
import socket
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Generator
from pathlib import Path

# e-INFRA upstream WITHOUT the trailing /v1 — aimock appends the incoming request path. Matches the
# `--provider-openai` value in the Makefile `record_requests` target.
DEFAULT_UPSTREAM = "https://llm.ai.e-infra.cz"


def _pick_free_port() -> int:
    """A free localhost TCP port whose last digit is NOT '1'.

    The einfra branch builds its api_base as `openai_api_url.rstrip("/v1")` (utils.py). `rstrip`
    strips a CHARACTER SET, not a suffix, so a port ending in '1' (e.g. 4021 → '...402') is silently
    mangled and the run proxies to a dead host. Re-roll until the port is safe.
    """
    for _ in range(50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        if not str(port).endswith("1"):
            return port
    raise RuntimeError("could not find a free port whose last digit is not '1'")


def _wait_healthy(port: int, proc: subprocess.Popen, timeout_s: float) -> None:
    """Poll GET /health until ready; fail loudly if aimock exits early or never comes up."""
    deadline = time.monotonic() + timeout_s
    url = f"http://127.0.0.1:{port}/health"
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(
                f"aimock exited early with code {proc.returncode} before becoming healthy"
            )
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:  # noqa: S310 (localhost only)
                if resp.status == 200:
                    return
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(0.25)
    raise RuntimeError(f"aimock did not become healthy at {url} within {timeout_s}s")


@contextlib.contextmanager
def record_fixtures(
    out_dir: str | Path,
    *,
    upstream: str = DEFAULT_UPSTREAM,
    port: int | None = None,
    latency_ms: int = 5,
    upstream_timeout_ms: int = 300000,
    body_timeout_ms: int = 300000,
    log_level: str = "info",
    health_timeout_s: float = 60.0,
) -> Generator[str]:
    """Run one `llmock --record` instance for the duration of the `with` block.

    Args:
        out_dir: fixture base dir for THIS instance. aimock writes captures to `<out_dir>/recorded/`
            (the `recorded` segment is hardcoded by aimock's record path).
        upstream: real OpenAI-compatible provider to proxy to (no trailing /v1).
        port: fixed port, or None to auto-pick a safe free one (recommended).
        Remaining args mirror the Makefile `record_requests` flags.

    Yields:
        The base URL (`http://127.0.0.1:<port>/v1`) to assign to `Context.openai_api_url`.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    chosen = port if port is not None else _pick_free_port()
    if str(chosen).endswith("1"):
        # See _pick_free_port: a trailing '1' is eaten by utils.py's rstrip("/v1").
        raise ValueError(
            f"aimock port {chosen} ends in '1'; pick another (utils.py rstrip('/v1') mangles it)"
        )

    cmd = [
        # --yes: don't block on npx's first-run install confirmation (the health poll would
        # otherwise time out waiting on a stdin prompt). Harmless once the package is cached.
        "npx", "--yes", "-p", "@copilotkit/aimock", "llmock",
        "--port", str(chosen),
        "--record",
        "--latency", str(latency_ms),
        "--upstream-timeout-ms", str(upstream_timeout_ms),
        "--body-timeout-ms", str(body_timeout_ms),
        "--log-level", log_level,
        "--provider-openai", upstream,
        "-f", str(out),
    ]
    proc = subprocess.Popen(cmd)
    try:
        _wait_healthy(chosen, proc, health_timeout_s)
        yield f"http://127.0.0.1:{chosen}/v1"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            with contextlib.suppress(subprocess.TimeoutExpired):
                proc.wait(timeout=5)
