"""Callback Handler streams to stdout on new llm token."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from io import TextIOWrapper
from typing import TYPE_CHECKING, Any

import httpx
from langchain_core.callbacks.base import BaseCallbackHandler
from pythonjsonlogger.orjson import OrjsonFormatter as JsonFormatter

if TYPE_CHECKING:
    from langchain_core.agents import AgentAction, AgentFinish
    from langchain_core.messages import BaseMessage
    from langchain_core.outputs import LLMResult


TIMESTAMP = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOGS_DIR = "logs"

class LoggingCallbackHandler(BaseCallbackHandler):
    """Callback Handler that logs all events to a file in JSON format."""
    
    out: dict[str, TextIOWrapper] = {}
    timestamp = TIMESTAMP
    
    def __init__(self, logs_dir: str = LOGS_DIR, log_string_max_length: int = 50) -> None:
        """Initialize the callback handler."""
        super().__init__()
        self.log_string_max_length = log_string_max_length
        self.logger = logging.getLogger(self.__class__.__name__)
        os.makedirs(f"{logs_dir}/{self.timestamp}", exist_ok=True)
        handler = logging.FileHandler(f"{logs_dir}/{self.timestamp}/langgraph_logging_{self.timestamp}.log")
        # handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s] %(message)s :: Exception: %(exc_info)s"))
        handler.setFormatter(JsonFormatter())
        handler.setLevel(logging.DEBUG)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
        logging.debug(f"Initialized {self.logger.name}.")

    def on_llm_start(
        self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any
    ) -> None:
        """Run when LLM starts running.

        Args:
            serialized: The serialized LLM.
            prompts: The prompts to run.
            **kwargs: Additional keyword arguments.
        """
        self.logger.debug("LLM start", extra={"serialized": serialized, "prompts": prompts, "kwargs": kwargs})

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        **kwargs: Any,
    ) -> None:
        """Run when LLM starts running.

        Args:
            serialized: The serialized LLM.
            messages: The messages to run.
            **kwargs: Additional keyword arguments.
        """
        self.logger.debug("Chat model start", extra={"serialized": serialized, "messages": messages, "kwargs": kwargs})
        
    # @override
    # def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
    #     """Run on new LLM token. Only available when streaming is enabled.

    #     Args:
    #         token: The new token.
    #         **kwargs: Additional keyword arguments.
    #     """
    #     # self.logger.debug("LLM new token", extra={"kwargs": kwargs})
        
    #     # out = self.out.get(kwargs.get("run_id", "default"), sys.stdout)
    #     # out.write(token)
    #     # out.flush()
    #     # os.fsync(out.fileno())

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when LLM ends running.

        Args:
            response: The response from the LLM.
            **kwargs: Additional keyword arguments.
        """
        response_dump = response.model_dump(exclude={"generations"})
        self.logger.debug("LLM end", extra={"response": response_dump, "kwargs": kwargs})
        # out = self.out.get(kwargs.get("run_id", "default"))
        # if out and not out.closed:
        #     out.close()

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        """Run when LLM errors.

        Args:
            error: The error that occurred.
            **kwargs: Additional keyword arguments.
        """
        self.logger.debug("LLM error.", exc_info=error, extra={"kwargs": kwargs})
        # out = self.out.get(kwargs.get("run_id", "default"))
        # if out and not out.closed:
        #     out.close()

    def on_chain_start(
        self, serialized: dict[str, Any], inputs: dict[str, Any], **kwargs: Any
    ) -> None:
        """Run when a chain starts running.

        Args:
            serialized: The serialized chain.
            inputs: The inputs to the chain.
            **kwargs: Additional keyword arguments.
        """
        self.logger.debug("Chain start", extra={"serialized": serialized, "inputs": inputs, "kwargs": kwargs})
        # if self.out.get(kwargs.get("run_id", "default")) is None:
        #     self.out[kwargs.get("run_id", "default")] = open(f"logs/{self.timestamp}/llm_out_{kwargs.get('run_id', 'default')}.log", "a")

    def on_chain_end(self, outputs: dict[str, Any], **kwargs: Any) -> None:
        """Run when a chain ends running.

        Args:
            outputs: The outputs of the chain.
            **kwargs: Additional keyword arguments.
        """
        for key, value in outputs.items():
            if isinstance(value, str):
                value = value if len(value) <= self.log_string_max_length else f"{value[:self.log_string_max_length]}... [truncated]"
                outputs[key] = value
        self.logger.debug("Chain end", extra={"outputs": outputs, "kwargs": kwargs})
        # for out in self.out.values():
        #     if not out.closed:
        #         out.close()

    def on_chain_error(self, error: BaseException, **kwargs: Any) -> None:
        """Run when chain errors.

        Args:
            error: The error that occurred.
            **kwargs: Additional keyword arguments.
        """
        self.logger.debug("Chain error.", exc_info=error, extra={"kwargs": kwargs})
        # for out in self.out.values():
        #     if not out.closed:
        #         out.close()

    def on_tool_start(
        self, serialized: dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Run when the tool starts running.

        Args:
            serialized: The serialized tool.
            input_str: The input string.
            **kwargs: Additional keyword arguments.
        """
        self.logger.debug("Tool start", extra={"serialized": serialized, "input_str": input_str, "kwargs": kwargs})

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> Any:
        """Run on agent action.

        Args:
            action: The agent action.
            **kwargs: Additional keyword arguments.
        """
        self.logger.debug("Agent action", extra={"action": action, "kwargs": kwargs})

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        """Run when tool ends running.

        Args:
            output: The output of the tool.
            **kwargs: Additional keyword arguments.
        """
        output = str(output)
        output = output if len(output) <= self.log_string_max_length else f"{output[:self.log_string_max_length]}... [truncated]"
        self.logger.debug("Tool end", extra={"output": output, "kwargs": kwargs})

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        """Run when tool errors.

        Args:
            error: The error that occurred.
            **kwargs: Additional keyword arguments.
        """
        self.logger.debug("Tool error.", exc_info=error, extra={"kwargs": kwargs})

    def on_text(self, text: str, **kwargs: Any) -> None:
        """Run on an arbitrary text.

        Args:
            text: The text to print.
            **kwargs: Additional keyword arguments.
        """
        self.logger.debug("Text", extra={"text": text, "kwargs": kwargs})

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """Run on the agent end.

        Args:
            finish: The agent finish.
            **kwargs: Additional keyword arguments.
        """
        self.logger.debug("Agent finish", extra={"finish": finish, "kwargs": kwargs})


class LLMRequestLogger():
    
    timestamp = TIMESTAMP
    logger = logging.getLogger("LLMRequestLogger")
    
    def __init__(self):
        os.makedirs(f"logs/{self.timestamp}", exist_ok=True)
        handler = logging.FileHandler(f"logs/{self.timestamp}/request_logging_{self.timestamp}.log")
        # handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s] %(message)s"))
        handler.setFormatter(JsonFormatter())
        handler.setLevel(logging.DEBUG)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
        self.logger.debug(f"Initialized {self.logger.name}.")
        
    def log_request(self, request: httpx.Request):
        self.logger.debug(f"Request: {request.method} {request.url}", 
                          extra={"request": { "method": request.method, "url": request.url, "headers": request.headers, "content": request.content.decode() }})
        
    def log_response(self, response: httpx.Response):
        request = response.request
        self.logger.debug(f"Response: {request.method} {request.url} - {response.status_code}", 
                          extra={"request": { "method": request.method, "url": request.url, "headers": request.headers, "content": request.content.decode() }, 
                                 "response": { "status_code": response.status_code, "headers": response.headers, "extensions": response.extensions, "cookies": response.cookies }})

    class LogRequest(httpx.Request):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            LLMRequestLogger.logger.debug(f"Request: {self.method} {self.url} - Headers: {self.headers} - Body: {self.content}")
        
    class LogResponse(httpx.Response):
        def iter_bytes(self, *args, **kwargs):
            for chunk in super().iter_bytes(*args, **kwargs):  # noqa: UP028
                # LLMRequestLogger.logger.debug(chunk)
                yield chunk
        
        async def aiter_bytes(self, *args, **kwargs):
            async for chunk in super().aiter_bytes(*args, **kwargs):
                # LLMRequestLogger.logger.debug(chunk)
                yield chunk
    
    class LogTransport(httpx.BaseTransport):
        def __init__(self, transport: httpx.BaseTransport):
            self.transport = transport

        def handle_request(self, request: httpx.Request) -> httpx.Response:
            response = self.transport.handle_request(request)

            return LLMRequestLogger.LogResponse(
                status_code=response.status_code,
                headers=response.headers,
                stream=response.stream,
                extensions=response.extensions,
            )

    class AsyncLogTransport(httpx.AsyncBaseTransport):
        def __init__(self, transport: httpx.AsyncBaseTransport):
            self.transport = transport

        async def handle_async_request(self, request: httpx.Request):
            response = await self.transport.handle_async_request(request)

            return LLMRequestLogger.LogResponse(
                status_code=response.status_code,
                headers=response.headers,
                stream=response.stream,
                extensions=response.extensions,
            )
