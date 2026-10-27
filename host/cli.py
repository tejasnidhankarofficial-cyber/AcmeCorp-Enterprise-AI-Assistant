"""Interactive CLI for the MCP assistant.

  python -m host.cli --user alice                 interactive chat
  python -m host.cli --user alice --list-tools    show discovered tools per server
  python -m host.cli --user alice --ask "..."     one-shot question
  python -m host.cli --audit 10                   show the last 10 audit entries
"""
import argparse
import asyncio
import json

from host import config
from host.assistant import Assistant
from host.audit import tail


async def ask_in_terminal(server: str, tool: str, args: dict) -> bool:
    try:
        reply = await asyncio.to_thread(input, f"  ⚠ approve {server}.{tool}({json.dumps(args)})? [y/N] ")
    except EOFError:  # no terminal attached: fail closed
        return False
    return reply.strip().lower() in {"y", "yes"}


async def auto_yes(server: str, tool: str, args: dict) -> bool:
    return True


def print_tools(assistant: Assistant) -> None:
    print(f"user={assistant.identity.user} role={assistant.identity.role} "
          f"servers={', '.join(assistant.identity.servers)}")
    for t in assistant.mcp.tools.values():
        print(f"  {t.qualified:<28} {'read-only' if t.read_only else 'SIDE-EFFECT':<12} {t.description.splitlines()[0]}")


def print_trace(trace: list[dict]) -> None:
    for e in trace:
        flag = f"  flags={e['flags']}" if e["flags"] else ""
        print(f"  ↳ {e['server']}.{e['tool']}({json.dumps(e['args'])}) -> {e['decision']} [{e['duration_ms']}ms]{flag}")


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user", default="alice")
    ap.add_argument("--ask")
    ap.add_argument("--list-tools", action="store_true")
    ap.add_argument("--audit", type=int, metavar="N")
    ap.add_argument("--offline", action="store_true", help="use the keyword planner instead of Claude")
    ap.add_argument("--auto-approve", action="store_true", help="approve side-effecting tools without asking")
    opts = ap.parse_args()

    if opts.audit:
        for entry in tail(config.AUDIT_LOG, opts.audit):
            print(json.dumps(entry))
        return

    approver = auto_yes if opts.auto_approve else ask_in_terminal
    async with Assistant(opts.user, approver=approver, offline=opts.offline) as assistant:
        if opts.list_tools:
            print_tools(assistant)
            return
        if opts.ask:
            answer = await assistant.ask(opts.ask)
            print_trace(answer.trace)
            print(answer.text)
            return
        planner = type(assistant.planner).__name__
        print(f"MCP assistant ({planner}) - {assistant.identity.user}/{assistant.identity.role}. "
              "Commands: /tools /audit /quit")
        while True:
            question = (await asyncio.to_thread(input, "\nyou> ")).strip()
            if question in {"/quit", "/exit"}:
                break
            if question == "/tools":
                print_tools(assistant)
            elif question == "/audit":
                for entry in tail(config.AUDIT_LOG, 5):
                    print(json.dumps(entry))
            elif question:
                answer = await assistant.ask(question)
                print_trace(answer.trace)
                print(answer.text)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        pass
