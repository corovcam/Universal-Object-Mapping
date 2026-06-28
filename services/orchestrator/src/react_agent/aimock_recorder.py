"""Manage per-thread aimock recording instances for evaluation runs.

When the environment variable ``EVALUATION_RUN=true`` is set, the orchestrator
spawns a dedicated aimock proxy for every thread execution so that each LLM
request/response pair is recorded as a fixture file.  Fixtures are written to::

    tests/experiments/{dataset}/{thread_id}__{timestamp}/

The aimock process is started with ``--record --proxy-only`` (no ``--watch``),
forwarding traffic to the upstream LLM provider.

Typical lifecycle (called from graph nodes):

1. ``extract_input`` calls :func:`maybe_start_recorder` once the thread_id is
   known.  The function is a no-op unless ``EVALUATION_RUN`` is truthy.
2. The returned :class:`AimockRecorder` (if any) is stashed in a module-level
   registry keyed by thread_id so cleanup can find it later.
3. When the graph finishes (or on explicit call), :func:`stop_recorder` tears
   down the aimock subprocess.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Module-level registry: thread_id -> AimockRecorder
_active_recorders: dict[str, "AimockRecorder"] = {}

# Root directory for experiment fixture output, relative to the orchestrator package root.
_ORCHESTRATOR_ROOT = Path(__file__).resolve().parents[2]  # services/orchestrator
_EXPERIMENTS_ROOT = _ORCHESTRATOR_ROOT / "tests" / "experiments"

# Default upstream provider URL (matches the Makefile record_requests target).
_DEFAULT_UPSTREAM_OPENAI = "https://llm.ai.e-infra.cz"

# Port range for dynamically-assigned aimock instances.  Each thread gets its own
# port so multiple evaluation threads can record concurrently.
_BASE_PORT = 14020
_port_counter = 0


def _next_port() -> int:
    """Return the next available port for an aimock instance."""
    global _port_counter
    port = _BASE_PORT + _port_counter
    _port_counter += 1
    return port


class AimockRecorder:
    """Wraps a single aimock subprocess recording fixtures for one thread.

    Attributes:
        thread_id: The LangGraph thread ID this recorder is bound to.
        fixture_dir: Absolute path to the directory where aimock writes fixtures.
        port: The TCP port the aimock proxy listens on.
        process: The underlying ``asyncio.subprocess.Process``, or ``None`` before start.
    """

    def __init__(
        self,
        thread_id: str,
        fixture_dir: Path,
        port: int,
        *,
        upstream_openai: str = _DEFAULT_UPSTREAM_OPENAI,
    ) -> None:
        self.thread_id = thread_id
        self.fixture_dir = fixture_dir
        self.port = port
        self.upstream_openai = upstream_openai
        self.process: asyncio.subprocess.Process | None = None

    async def start(self, *, timeout: float = 15.0) -> None:
        """Spawn the aimock process and wait until it is listening.

        Args:
            timeout: Maximum seconds to wait for aimock to become ready.

        Raises:
            RuntimeError: If aimock fails to start within *timeout* seconds.
        """
        self.fixture_dir.mkdir(parents=True, exist_ok=True)

        # Resolve the npx binary path.
        npx = shutil.which("npx")
        if npx is None:
            raise RuntimeError("npx is not available on PATH; cannot start aimock")

        cmd = [
            npx,
            "-p", "@copilotkit/aimock",
            "llmock",
            "--port", str(self.port),
            "--record",
            "--proxy-only",
            "--latency", "5",
            "--upstream-timeout-ms", "300000",
            "--body-timeout-ms", "300000",
            "--log-level", "debug",
            "--provider-openai", self.upstream_openai,
            "-f", str(self.fixture_dir),
        ]

        logger.info(
            "aimock_recorder: starting aimock for thread %s on port %d → %s",
            self.thread_id,
            self.port,
            self.fixture_dir,
        )

        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait for aimock to print its "listening" banner, which signals readiness.
        # We poll stderr/stdout for the port number or a known ready string.
        ready = asyncio.Event()

        async def _watch_output(stream: asyncio.StreamReader | None) -> None:
            if stream is None:
                return
            while True:
                line = await stream.readline()
                if not line:
                    break
                text = line.decode(errors="replace").strip()
                logger.debug("aimock[%s]: %s", self.thread_id, text)
                # aimock logs "Listening on port XXXX" or similar when ready.
                if str(self.port) in text and ("listen" in text.lower() or "start" in text.lower() or "ready" in text.lower()):
                    ready.set()

        watch_stdout = asyncio.create_task(_watch_output(self.process.stdout))
        watch_stderr = asyncio.create_task(_watch_output(self.process.stderr))

        try:
            await asyncio.wait_for(ready.wait(), timeout=timeout)
        except TimeoutError:
            # Check if the process is still alive — if it crashed, surface the error.
            if self.process.returncode is not None:
                raise RuntimeError(
                    f"aimock exited prematurely with code {self.process.returncode}"
                )
            # Process is alive but hasn't printed the expected banner yet.  Some
            # versions of aimock don't print a "listening" line — assume ready
            # after timeout if the process is still running.
            logger.warning(
                "aimock_recorder: timed out waiting for ready banner on port %d; "
                "assuming aimock is ready (process pid=%d still alive)",
                self.port,
                self.process.pid,
            )
        finally:
            # Don't cancel the watchers — let them keep draining so the pipe
            # buffer doesn't fill and block the subprocess.
            # They'll finish when the process exits.
            pass

        logger.info(
            "aimock_recorder: aimock started for thread %s (pid=%d, port=%d)",
            self.thread_id,
            self.process.pid,
            self.port,
        )

    async def stop(self) -> None:
        """Terminate the aimock process gracefully."""
        if self.process is None:
            return
        if self.process.returncode is not None:
            logger.info(
                "aimock_recorder: aimock for thread %s already exited (code=%d)",
                self.thread_id,
                self.process.returncode,
            )
            return
        logger.info(
            "aimock_recorder: stopping aimock for thread %s (pid=%d)",
            self.thread_id,
            self.process.pid,
        )
        self.process.terminate()
        try:
            await asyncio.wait_for(self.process.wait(), timeout=10.0)
        except TimeoutError:
            logger.warning(
                "aimock_recorder: aimock pid=%d did not exit after SIGTERM; sending SIGKILL",
                self.process.pid,
            )
            self.process.kill()
            await self.process.wait()


async def maybe_start_recorder(
    thread_id: str,
    *,
    dataset: str | None = None,
    timestamp: str | None = None,
    upstream_openai: str | None = None,
) -> AimockRecorder | None:
    """Start an aimock recorder for *thread_id* if ``EVALUATION_RUN`` is set.

    This is the main entry point called from the ``extract_input`` graph node.
    It is safe to call multiple times for the same thread_id — subsequent calls
    return the existing recorder.

    Args:
        thread_id: The LangGraph thread ID for the current execution.
        dataset: Dataset name for the fixture directory (default: env ``EVALUATION_DATASET`` or ``"wwi"``).
        timestamp: ISO-ish timestamp string; defaults to ``datetime.now(UTC)``.
        upstream_openai: Override the upstream OpenAI-compatible URL.

    Returns:
        The :class:`AimockRecorder` instance, or ``None`` if ``EVALUATION_RUN``
        is not set.
    """
    if not os.environ.get("EVALUATION_RUN", "").lower() in ("true", "1", "yes"):
        return None

    # Already running for this thread?
    if thread_id in _active_recorders:
        logger.debug(
            "aimock_recorder: recorder already active for thread %s", thread_id
        )
        return _active_recorders[thread_id]

    dataset = dataset or os.environ.get("EVALUATION_DATASET", "wwi")
    if timestamp is None:
        timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H-%M-%S")

    folder_name = f"{thread_id}__{timestamp}"
    fixture_dir = _EXPERIMENTS_ROOT / dataset / folder_name

    port = _next_port()
    upstream = upstream_openai or os.environ.get(
        "AIMOCK_UPSTREAM_OPENAI", _DEFAULT_UPSTREAM_OPENAI
    )

    recorder = AimockRecorder(
        thread_id=thread_id,
        fixture_dir=fixture_dir,
        port=port,
        upstream_openai=upstream,
    )
    await recorder.start()
    _active_recorders[thread_id] = recorder
    return recorder


async def stop_recorder(thread_id: str) -> None:
    """Stop and de-register the aimock recorder for *thread_id* (if any)."""
    recorder = _active_recorders.pop(thread_id, None)
    if recorder is not None:
        await recorder.stop()


async def stop_all_recorders() -> None:
    """Stop every active aimock recorder.  Called during graceful shutdown."""
    for tid in list(_active_recorders):
        await stop_recorder(tid)


def get_recorder(thread_id: str) -> AimockRecorder | None:
    """Return the active recorder for *thread_id*, or ``None``."""
    return _active_recorders.get(thread_id)
