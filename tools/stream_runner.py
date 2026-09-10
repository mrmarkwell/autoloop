#!/usr/bin/env python3
"""Live streaming telemetry and event formatter for Jetski CLI NDJSON output.

Zero external dependencies (Python 3 standard library only per ADR-003).
Ingests `--output-format stream-json` lines from stdin and renders live terminal
progress: active tool calls, arguments, completion status, and streaming text.
"""

from datetime import datetime
import json
import os
import sys
from typing import Any, Dict, Iterator, Optional, TextIO


def supports_color(stream: TextIO) -> bool:
    """Check if the given stream supports ANSI color output."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    return hasattr(stream, "isatty") and stream.isatty()


class ANSIStyler:
    """Zero-dependency ANSI terminal styling helper."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def _wrap(self, code: str, text: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    def dim(self, text: str) -> str:
        return self._wrap("2", text)

    def bold(self, text: str) -> str:
        return self._wrap("1", text)

    def cyan(self, text: str) -> str:
        return self._wrap("36", text)

    def yellow(self, text: str) -> str:
        return self._wrap("33", text)

    def green(self, text: str) -> str:
        return self._wrap("32", text)

    def red(self, text: str) -> str:
        return self._wrap("31", text)

    def magenta(self, text: str) -> str:
        return self._wrap("35", text)

    def blue(self, text: str) -> str:
        return self._wrap("34", text)


def summarize_tool_parameters(params: Optional[Dict[str, Any]]) -> str:
    """Extract a concise human-readable summary of tool parameters."""
    if not params or not isinstance(params, dict):
        return ""

    if "CommandLine" in params:
        cmd = str(params["CommandLine"]).strip().replace("\n", " ")
        if len(cmd) > 90:
            cmd = cmd[:87] + "..."
        return cmd
    if "TargetFile" in params:
        return str(params["TargetFile"])
    if "AbsolutePath" in params:
        return str(params["AbsolutePath"])
    if "Query" in params:
        return f'"{params["Query"]}"'
    if "toolSummary" in params:
        return str(params["toolSummary"])
    if "Instruction" in params:
        return str(params["Instruction"])

    pairs = [f"{k}={v}" for k, v in list(params.items())[:2]]
    summary = ", ".join(pairs)
    if len(summary) > 90:
        summary = summary[:87] + "..."
    return summary


class StreamFormatter:
    """Parses and formats a stream of Jetski NDJSON events."""

    def __init__(self, out: TextIO = sys.stdout, err: TextIO = sys.stderr):
        self.out = out
        self.err = err
        self.color = supports_color(out)
        self.style = ANSIStyler(self.color)
        self.current_tool: Optional[str] = None
        self.last_step_index: Optional[int] = None
        self.has_streamed_text = False
        self.seen_result = False
        self.exit_code = 0

    def format_timestamp(self) -> str:
        """Return current HH:MM:SS timestamp in dim styling."""
        ts = datetime.now().strftime("%H:%M:%S")
        return self.style.dim(f"[{ts}]")

    def handle_init(self, init: Dict[str, Any], conv_id: Optional[str] = None) -> None:
        """Handle 'init' event."""
        model = init.get("model", "default")
        tools = init.get("tools", [])
        tool_count = len(tools) if isinstance(tools, list) else 0
        cid = conv_id or init.get("conversation_id", "")
        cid_short = cid[:8] if cid else "new"

        banner = (
            f"{self.format_timestamp()} "
            f"{self.style.cyan('⚡ Jetski Initialized')} "
            f"{self.style.dim(f'(model: {model}, conv: {cid_short}, tools: {tool_count})')}\n"
        )
        self.out.write(banner)
        self.out.flush()

    def handle_step_update(self, payload: Dict[str, Any]) -> None:
        """Handle 'step_update' event."""
        step_index = payload.get("step_index")
        tool_name = payload.get("tool_name")
        tool_info = payload.get("tool_info") or {}
        text_delta = payload.get("text_delta", "")
        state = payload.get("state", "")
        duration = payload.get("duration_seconds")

        resolved_tool = tool_name or tool_info.get("name")
        if resolved_tool:
            params = tool_info.get("parameters")
            summary = summarize_tool_parameters(params)

            if step_index != self.last_step_index or resolved_tool != self.current_tool:
                if self.has_streamed_text:
                    self.out.write("\n")
                    self.has_streamed_text = False

                param_str = f" : {self.style.yellow(summary)}" if summary else ""
                msg = (
                    f"{self.format_timestamp()} "
                    f"{self.style.blue('⚙ [TOOL]')} "
                    f"{self.style.bold(resolved_tool)}"
                    f"{param_str}\n"
                )
                self.out.write(msg)
                self.out.flush()
                self.current_tool = resolved_tool
                self.last_step_index = step_index

            if state in ("DONE", "COMPLETED", "SUCCESS") and duration is not None:
                dur_str = f"{duration:.2f}s"
                msg = (
                    f"{self.format_timestamp()} "
                    f"{self.style.green('✔ [DONE]')} "
                    f"{self.style.dim(f'{resolved_tool} ({dur_str})')}\n"
                )
                self.out.write(msg)
                self.out.flush()
                self.current_tool = None

        if text_delta:
            if not self.has_streamed_text:
                self.has_streamed_text = True
            self.out.write(text_delta)
            self.out.flush()

    def handle_result(self, result: Dict[str, Any]) -> None:
        """Handle 'result' event."""
        self.seen_result = True
        status = result.get("status", "UNKNOWN")
        error_msg = result.get("error", "")
        usage = result.get("usage", {})
        total_tokens = usage.get("total_tokens", 0)
        num_turns = result.get("num_turns", 1)

        if self.has_streamed_text:
            self.out.write("\n")
            self.has_streamed_text = False

        if status == "SUCCESS":
            self.exit_code = 0
            summary = (
                f"\n{self.format_timestamp()} "
                f"{self.style.green('🏁 [SUCCESS]')} "
                f"{self.style.dim(f'Turns: {num_turns} | Tokens: {total_tokens:,}')}\n"
            )
            self.out.write(summary)
        else:
            self.exit_code = 1
            summary = (
                f"\n{self.format_timestamp()} "
                f"{self.style.red('❌ [ERROR]')} "
                f"{self.style.bold(f'Status: {status}')}\n"
            )
            if error_msg:
                summary += f"   {self.style.red(error_msg)}\n"
            self.out.write(summary)

        self.out.flush()

    def process_line(self, line: str) -> None:
        """Parse and process a single line from the NDJSON stream."""
        line = line.strip()
        if not line:
            return

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            self.out.write(f"{line}\n")
            self.out.flush()
            return

        if not isinstance(event, dict):
            return

        event_type = event.get("event")
        if event_type == "init":
            self.handle_init(event.get("init", {}), event.get("conversation_id"))
        elif event_type == "step_update":
            self.handle_step_update(event.get("step_update", {}))
        elif event_type == "result":
            self.handle_result(event.get("result", {}))

    def process_stream(self, lines: Iterator[str]) -> int:
        """Process the entire stream of lines and return exit status code."""
        for line in lines:
            self.process_line(line)
        return self.exit_code


def main() -> int:
    formatter = StreamFormatter(sys.stdout, sys.stderr)
    return formatter.process_stream(sys.stdin)


if __name__ == "__main__":
    sys.exit(main())
