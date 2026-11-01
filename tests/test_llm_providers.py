"""Provider-adapter tests with a stubbed OpenAI client: no network, no API key."""
import json
from types import SimpleNamespace as NS

import pytest

from host import llm
from host.llm import OfflinePlanner, OpenAIPlanner, make_planner, to_openai_messages

HISTORY = [
    {"role": "user", "content": "Create a ticket: broken keyboard"},
    {"role": "assistant", "content": [{"type": "text", "text": "On it."},
                                       {"type": "tool_use", "id": "c1", "name": "tickets__create_ticket",
                                        "input": {"title": "broken keyboard"}}]},
    {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "c1", "content": "DENIED: no"}]},
]


def test_history_conversion_to_openai_format():
    msgs = to_openai_messages(HISTORY)
    assert msgs[0]["role"] == "system"
    assert msgs[1] == {"role": "user", "content": "Create a ticket: broken keyboard"}
    call = msgs[2]["tool_calls"][0]
    assert call["id"] == "c1" and json.loads(call["function"]["arguments"]) == {"title": "broken keyboard"}
    assert msgs[3] == {"role": "tool", "tool_call_id": "c1", "content": "DENIED: no"}


def _planner_returning(message):
    planner = OpenAIPlanner.__new__(OpenAIPlanner)
    planner.model = "stub"
    async def create(**kwargs):
        create.kwargs = kwargs
        return NS(choices=[NS(message=message)])
    planner.client = NS(chat=NS(completions=NS(create=create)))
    return planner, create


TOOLS = [{"name": "docs__search_docs", "description": "d", "input_schema": {"type": "object", "properties": {}}}]


async def test_openai_tool_call_is_normalized():
    msg = NS(content=None, tool_calls=[NS(id="x1", function=NS(name="docs__search_docs", arguments='{"query": "vpn"}'))])
    planner, create = _planner_returning(msg)
    turn = await planner.next_turn(HISTORY[:1], TOOLS)
    assert [(c.id, c.name, c.args) for c in turn.tool_calls] == [("x1", "docs__search_docs", {"query": "vpn"})]
    assert turn.assistant_content[0]["type"] == "tool_use"
    assert create.kwargs["tools"][0]["function"]["name"] == "docs__search_docs"


async def test_openai_malformed_arguments_do_not_crash():
    msg = NS(content=None, tool_calls=[NS(id="x1", function=NS(name="docs__search_docs", arguments="{not json"))])
    planner, _ = _planner_returning(msg)
    assert (await planner.next_turn(HISTORY[:1], TOOLS)).tool_calls[0].args == {}


async def test_openai_final_text_answer():
    planner, _ = _planner_returning(NS(content="All done.", tool_calls=None))
    turn = await planner.next_turn(HISTORY[:1], TOOLS)
    assert turn.text == "All done." and not turn.tool_calls


def test_provider_selection(monkeypatch):
    for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LLM_PROVIDER"):
        monkeypatch.delenv(var, raising=False)
    assert isinstance(make_planner(), OfflinePlanner)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert isinstance(make_planner(), OpenAIPlanner)
    assert isinstance(make_planner(offline=True), OfflinePlanner)
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    assert isinstance(make_planner(), OfflinePlanner)
    monkeypatch.setenv("LLM_PROVIDER", "nonsense")
    with pytest.raises(SystemExit):
        make_planner()
