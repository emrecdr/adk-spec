"""Q1: does google-adk 2.15.0 import cleanly on Python 3.14? Record versions + warnings."""
import importlib
import importlib.metadata as md
import platform
import sys
import warnings

print("python      :", sys.version)
print("platform    :", platform.platform(), platform.machine())

caught = []
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    mods = [
        "google.adk",
        "google.adk.agents",
        "google.adk.agents.llm_agent",
        "google.adk.agents.base_agent",
        "google.adk.agents.sequential_agent",
        "google.adk.agents.loop_agent",
        "google.adk.agents.parallel_agent",
        "google.adk.workflow",
        "google.adk.workflow._workflow",
        "google.adk.workflow._function_node",
        "google.adk.runners",
        "google.adk.apps",
        "google.adk.events",
        "google.adk.plugins",
        "google.adk.tools",
        "google.adk.tools.function_tool",
        "google.adk.sessions",
        "google.adk.sessions.sqlite_session_service",
        "google.adk.artifacts",
        "google.adk.models",
        "google.adk.models.base_llm",
        "google.adk.evaluation",
        "google.adk.cli.cli_tools_click",
    ]
    for m in mods:
        try:
            importlib.import_module(m)
            print(f"import ok   : {m}")
        except Exception as e:  # noqa: BLE001
            print(f"import FAIL : {m}: {type(e).__name__}: {e}")
    from google.adk import Agent, Context, Event, Runner, Workflow  # noqa: F401
    caught = list(w)

print("\nwarnings raised during imports:", len(caught))
for c in caught:
    print(f"  {c.category.__name__}: {str(c.message)[:300]}  [{c.filename.split('site-packages/')[-1]}:{c.lineno}]")

import google.adk
print("\ngoogle.adk.__version__ :", google.adk.__version__)
for pkg in ["google-adk", "google-genai", "pydantic", "pydantic-core", "fastapi", "starlette",
            "uvicorn", "aiosqlite", "opentelemetry-api", "opentelemetry-sdk", "google-auth",
            "authlib", "click", "httpx", "tenacity", "typing-extensions", "jsonschema",
            "graphviz", "pyyaml", "websockets", "watchdog", "pytest", "pytest-asyncio"]:
    try:
        print(f"  {pkg:<24}{md.version(pkg)}")
    except md.PackageNotFoundError:
        print(f"  {pkg:<24}NOT INSTALLED")
for absent in ["sqlalchemy", "litellm", "mcp", "anthropic", "google-cloud-aiplatform"]:
    try:
        print(f"  {absent:<24}{md.version(absent)}")
    except md.PackageNotFoundError:
        print(f"  {absent:<24}NOT INSTALLED (not a core dependency)")
print("\nrequires-python:", md.metadata("google-adk")["Requires-Python"])
print("classifiers py :", [c.split("::")[-1].strip() for c in md.metadata("google-adk").get_all("Classifier") if "Python ::" in c])
print("extras         :", md.metadata("google-adk").get_all("Provides-Extra"))
