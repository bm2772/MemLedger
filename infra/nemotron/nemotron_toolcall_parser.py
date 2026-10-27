# SPDX-License-Identifier: Apache-2.0
# Tool-call parser for NVIDIA Nemotron Nano 9B v2 ("<TOOLCALL>[{...}]</TOOLCALL>"), ported to the vLLM 0.32 module
# layout from NVIDIA's nemotron_toolcall_parser_no_streaming.py (model repo). Non-streaming only, as in the original.
import json
from collections.abc import Sequence

import regex as re
from vllm.entrypoints.generate.base.protocol import (
    DeltaMessage,
    ExtractedToolCallInformation,
    FunctionCall,
    ToolCall,
)
from vllm.entrypoints.openai.chat_completion.protocol import ChatCompletionRequest
from vllm.logger import init_logger
from vllm.tokenizers import TokenizerLike
from vllm.tool_parsers.abstract_tool_parser import Tool, ToolParser, ToolParserManager

logger = init_logger(__name__)


@ToolParserManager.register_module("nemotron_json")
class NemotronJSONToolParser(ToolParser):
    tool_call_start_token = "<TOOLCALL>"
    tool_call_regex = re.compile(r"<TOOLCALL>(.*?)</TOOLCALL>|<TOOLCALL>(.*)", re.DOTALL)

    def __init__(self, tokenizer: TokenizerLike, tools: list[Tool] | None = None):
        super().__init__(tokenizer, tools)

    def adjust_request(self, request):
        request = super().adjust_request(request)
        if getattr(request, "tools", None) and getattr(request, "tool_choice", None) != "none":
            request.skip_special_tokens = False  # <TOOLCALL> may be a special token
        return request

    def extract_tool_calls(self, model_output: str, request: ChatCompletionRequest) -> ExtractedToolCallInformation:
        if self.tool_call_start_token not in model_output:
            return ExtractedToolCallInformation(tools_called=False, tool_calls=[], content=model_output)
        try:
            m = self.tool_call_regex.search(model_output)
            raw = (m.group(1) if m.group(1) is not None else m.group(2)).strip()
            if not raw.startswith("["):
                raw = "[" + raw
            if not raw.endswith("]"):
                raw = raw + "]"
            calls = []
            for c in json.loads(raw):
                if not isinstance(c, dict) or "name" not in c:
                    continue
                args = c.get("arguments", {})
                calls.append(ToolCall(type="function", function=FunctionCall(
                    name=c["name"], arguments=args if isinstance(args, str) else json.dumps(args, ensure_ascii=False))))
            content = model_output[:model_output.find(self.tool_call_start_token)].strip()
            return ExtractedToolCallInformation(tools_called=bool(calls), tool_calls=calls, content=content or None)
        except Exception:
            logger.exception("Nemotron tool-call parsing failed; returning the text as content")
            return ExtractedToolCallInformation(tools_called=False, tool_calls=[], content=model_output)

    def extract_tool_calls_streaming(self, previous_text: str, current_text: str, delta_text: str,
                                     previous_token_ids: Sequence[int], current_token_ids: Sequence[int],
                                     delta_token_ids: Sequence[int], request: ChatCompletionRequest
                                     ) -> DeltaMessage | None:
        return DeltaMessage(content=delta_text)  # streaming is not used by the MemLedger agent
