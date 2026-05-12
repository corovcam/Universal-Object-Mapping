"""React Agent.

This module defines a custom reasoning and action agent graph.
It invokes tools in a simple loop.
"""
import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(".env.dev" if os.getenv("DEVELOPMENT") else ".env"))

from react_agent.graph import graph

__all__ = ["graph"]
