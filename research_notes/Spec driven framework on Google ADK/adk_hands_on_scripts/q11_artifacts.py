"""Q11: save two versions of a markdown file through FileArtifactService and InMemoryArtifactService,
from workflow function nodes (ctx.save_artifact) and directly through the service API.
Records the on-disk layout, how versions are addressed and how an artifact is read back."""
import asyncio
import os
import shutil
from pathlib import Path

from google.genai import types

from google.adk import Agent, Context, Runner, Workflow
from google.adk.artifacts import FileArtifactService, InMemoryArtifactService
from google.adk.sessions import InMemorySessionService

from fake_llm import FakeLlm, describe, user

ROOT = Path(os.environ.get("SPIKE_DATA", "data")) / "q11_artifacts"


async def save_v0(ctx: Context, node_input: str):
    part = types.Part.from_bytes(data=f"# Spec: {node_input}\n\nv0 body\n".encode(), mime_type="text/markdown")
    version = await ctx.save_artifact("spec.md", part)
    return {"saved_version": version}


async def save_v1(ctx: Context, node_input: dict):
    part = types.Part.from_bytes(data=b"# Spec\n\nv1 body (revised)\n", mime_type="text/markdown")
    v_session = await ctx.save_artifact("spec.md", part, custom_metadata={"stage": "review"})
    v_nested = await ctx.save_artifact("specs/001-login/plan.md", types.Part.from_text(text="# Plan\n"))
    v_user = await ctx.save_artifact("user:glossary.md", types.Part.from_bytes(data=b"# Glossary\n", mime_type="text/markdown"))
    return {"spec.md": v_session, "specs/001-login/plan.md": v_nested, "user:glossary.md": v_user}


async def read_back(ctx: Context, node_input: dict):
    latest = await ctx.load_artifact("spec.md")
    first = await ctx.load_artifact("spec.md", version=0)
    missing = await ctx.load_artifact("spec.md", version=7)
    nested = await ctx.load_artifact("specs/001-login/plan.md")
    info = await ctx.get_artifact_version("spec.md")
    return {
        "list_artifacts": await ctx.list_artifacts(),
        "latest": latest.inline_data.data.decode() if latest and latest.inline_data else repr(latest),
        "latest_mime": latest.inline_data.mime_type if latest and latest.inline_data else None,
        "v0": first.inline_data.data.decode() if first and first.inline_data else repr(first),
        "v7": missing,
        "nested_part": {"text": nested.text, "inline": bool(nested.inline_data)} if nested else None,
        "version_info": info.model_dump(mode="json") if info else None,
    }


async def run(label, artifact_service):
    print(f"\n=== {label}")
    ss = InMemorySessionService()
    wf = Workflow(name="arts", edges=[("START", save_v0, save_v1, read_back)])
    runner = Runner(node=wf, session_service=ss, artifact_service=artifact_service)
    s = await ss.create_session(app_name=runner.app_name, user_id="u1", session_id="sess-1")
    n = 0
    async for ev in runner.run_async(user_id="u1", session_id=s.id, new_message=user("Login")):
        n += 1
        if ev.node_info.path.endswith("read_back@1"):
            print(f"  [{n:02d}] read_back output:")
            for k, v in ev.output.items():
                print(f"        {k}: {v!r}")
        else:
            print(f"  [{n:02d}] {describe(ev)}")

    print("  -- direct service API (outside any agent run) --")
    kw = dict(app_name=runner.app_name, user_id="u1", session_id="sess-1")
    print("  list_artifact_keys :", await artifact_service.list_artifact_keys(**kw))
    print("  list_versions      :", await artifact_service.list_versions(filename="spec.md", **kw))
    p = await artifact_service.load_artifact(filename="spec.md", version=0, **kw)
    print("  load_artifact(v=0) :", p.inline_data.data.decode() if p and p.inline_data else p)
    try:
        vs = await artifact_service.list_artifact_versions(filename="spec.md", **kw)
        for v in vs:
            print("  artifact version   :", v.model_dump(mode="json"))
    except Exception as e:  # noqa: BLE001
        print(f"  list_artifact_versions RAISED {type(e).__name__}: {e}")
    other = await artifact_service.list_artifact_keys(app_name=runner.app_name, user_id="u1", session_id="sess-OTHER")
    print("  keys visible from ANOTHER session of the same user:", other)
    return runner


async def templating(artifact_service):
    print("\n=== extra: does `{artifact.spec.md}` in an instruction inline the artifact text?")
    llm = FakeLlm(replies=["ok"])
    agent = Agent(name="reviewer", model=llm, instruction="Review this spec:\n{artifact.spec.md}\nEND")
    ss = InMemorySessionService()
    runner = Runner(agent=agent, app_name="arts", session_service=ss, artifact_service=artifact_service)
    await ss.create_session(app_name="arts", user_id="u1", session_id="sess-1")
    try:
        async for _ in runner.run_async(user_id="u1", session_id="sess-1", new_message=user("review")):
            pass
        print("  system_instruction sent to the model:", repr(llm.requests[0].config.system_instruction))
    except Exception as e:  # noqa: BLE001
        print(f"  RAISED {type(e).__name__}: {e}")


async def no_service():
    print("\n=== extra: ctx.save_artifact with NO artifact service configured on the Runner")
    ss = InMemorySessionService()
    runner = Runner(node=Workflow(name="arts", edges=[("START", save_v0)]), session_service=ss)
    s = await ss.create_session(app_name=runner.app_name, user_id="u1")
    try:
        async for _ in runner.run_async(user_id="u1", session_id=s.id, new_message=user("x")):
            pass
    except Exception as e:  # noqa: BLE001
        print(f"  RAISED {type(e).__name__}: {e}")


async def main():
    shutil.rmtree(ROOT, ignore_errors=True)
    file_service = FileArtifactService(root_dir=ROOT)
    await run(f"FileArtifactService(root_dir={str(ROOT)!r})", file_service)
    print("\n  -- on-disk layout --")
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        print(f"  {'  ' * (len(rel.parts) - 1)}{rel.name}{'/' if path.is_dir() else f'   ({path.stat().st_size} bytes)'}")
    meta = sorted(ROOT.rglob("spec.md/versions/1/metadata.json"))[0]
    print(f"\n  -- {meta.relative_to(ROOT)} --\n  {meta.read_text()}")
    body = sorted(ROOT.rglob("spec.md/versions/1/spec.md"))[0]
    print(f"  -- {body.relative_to(ROOT)} (plain file on disk) --\n  {body.read_text()!r}")
    await templating(file_service)

    await run("InMemoryArtifactService()", InMemoryArtifactService())
    import logging
    logging.getLogger("google_adk").setLevel(logging.CRITICAL)
    await no_service()


asyncio.run(main())
