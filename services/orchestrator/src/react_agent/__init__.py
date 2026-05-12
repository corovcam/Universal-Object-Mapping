"""React Agent.

This module defines a custom reasoning and action agent graph.
It invokes tools in a simple loop.
"""
import logging
import os

import logfire
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(".env.dev" if os.getenv("DEVELOPMENT") else ".env"))

logfire.configure(
    # sampling=logfire.SamplingOptions.level_or_duration(background_rate=0.3),
    console=False,
    scrubbing=False,
)
# logfire.install_auto_tracing(modules=['react_agent'], min_duration=0.01, check_imported_modules='ignore')
logfire.instrument_pydantic(record="failure")
logfire.instrument_openai(suppress_other_instrumentation=False)
logfire.instrument_requests(capture_all=True)
logfire.instrument_httpx(capture_all=True)
logfire.instrument_aiohttp_client(capture_all=True)
logging.basicConfig(handlers=[logfire.LogfireLoggingHandler()])
logging.getLogger("watchfiles.main").setLevel(logging.WARNING)

from react_agent.graph import build_graph

__all__ = ["build_graph"]
