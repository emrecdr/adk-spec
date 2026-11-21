"""The package's layers are its architecture: every import points one way, and the domain runs nothing.

Each layer may import itself and the layers before it: `domain`, `workspace`, `orchestration`, `interfaces`. Read off
the syntax tree, so a new module is placed by where it sits; and once at runtime, in a fresh interpreter with the
engine made unimportable, because the tree cannot see what importing a module loads.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import PACKAGE, ROOT

LAYERS = ("domain", "workspace", "orchestration", "interfaces")
#: What a pure layer may not name: anything that calls a model, runs a process or talks to a network, and for the
#: domain anything that touches a file.
FORBIDDEN = {
    "domain": (
        "google",
        "litellm",
        "subprocess",
        "httpx",
        "asyncio",
        "os",
        "socket",
        "urllib",
        "http",
        "ssl",
        "pathlib",
        "shutil",
        "tempfile",
    ),
    "workspace": ("google", "litellm", "httpx", "asyncio", "socket", "urllib", "http", "ssl"),
}
ENGINE = ("google.", "litellm")


def _layer(path: Path) -> str:
    parts = path.relative_to(PACKAGE).parts
    return parts[0] if len(parts) > 1 else "root"


def _rank(layer: str) -> int:
    return LAYERS.index(layer) if layer in LAYERS else len(LAYERS)


def _relative_imports(path: Path):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.level:
            target = path.parents[node.level - 1] / (node.module or "").replace(".", "/")
            yield node, target


def _absolute_imports(path: Path) -> list[str]:
    """Every module name `path` imports by its full name: `import x.y`, `from x.y import z`."""
    names: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and not node.level:
            names.append(node.module or "")
    return names


def test_no_layer_imports_a_layer_after_it() -> None:
    upward = []
    for path in sorted(PACKAGE.rglob("*.py")):
        for node, target in _relative_imports(path):
            source, reached = _layer(path), _layer(target)
            if node.module is None:  # `from . import x`: x names the module or package
                reached = _layer(target / node.names[0].name)
            if _rank(reached) > _rank(source):
                upward.append(f"{path.relative_to(PACKAGE)} imports {reached} ({source} may not)")
    assert upward == [], "\n".join(upward)


def test_the_package_imports_its_own_modules_only_relatively() -> None:
    """The direction test reads relative imports; one spelled from the top would pass it whatever it pointed at."""
    absolute = [
        f"{path.relative_to(PACKAGE)}: {name}"
        for path in sorted(PACKAGE.rglob("*.py"))
        for name in _absolute_imports(path)
        if name.split(".")[0] == PACKAGE.name
    ]
    assert absolute == [], absolute


@pytest.mark.parametrize("layer", sorted(FORBIDDEN))
def test_a_pure_layer_names_nothing_it_may_not(layer: str) -> None:
    offenders = [
        f"{path.name}: {name}"
        for path in sorted((PACKAGE / layer).rglob("*.py"))
        for name in _absolute_imports(path)
        if name.split(".")[0] in FORBIDDEN[layer]
    ]
    assert offenders == [], offenders


def test_no_module_below_the_root_is_named_agent() -> None:
    """`adk web`'s loader reads any folder holding an `agent.py` as an agent of its own."""
    assert [p for p in PACKAGE.rglob("agent.py") if p.parent != PACKAGE] == []


def test_each_layer_says_what_it_may_import() -> None:
    for layer in LAYERS:
        module = ast.parse((PACKAGE / layer / "__init__.py").read_text(encoding="utf-8"))
        assert "may import" in (ast.get_docstring(module) or ""), layer


def _probe(body: str) -> str:
    """What `body` prints in a fresh interpreter where the engine cannot be imported, as where it is not installed."""
    blocked = "import sys\nsys.modules['google'] = None\nsys.modules['litellm'] = None\n"
    done = subprocess.run(
        [sys.executable, "-c", blocked + body], cwd=ROOT, capture_output=True, encoding="utf-8", check=False
    )
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def test_the_pure_layers_import_with_the_engine_absent() -> None:
    body = (
        "import pkgutil\nimport adk_spec.domain, adk_spec.workspace\n"
        "for layer in (adk_spec.domain, adk_spec.workspace):\n"
        "    for found in pkgutil.walk_packages(layer.__path__, layer.__name__ + '.'):\n"
        "        __import__(found.name)\n"
        "print(sorted(m for m in sys.modules if m.startswith(('adk_spec.orchestration', 'adk_spec.interfaces'))))\n"
    )
    assert _probe(body) == "[]"


def test_the_command_starts_with_the_engine_absent() -> None:
    body = (
        "import contextlib, io\nfrom adk_spec.interfaces.cli import main\n"
        "with contextlib.redirect_stdout(io.StringIO()):\n"
        "    try:\n        code = main(['--version'])\n    except SystemExit as stopped:\n        code = stopped.code\n"
        f"print(code, sorted(m for m in sys.modules if sys.modules[m] and m.startswith({ENGINE!r})))\n"
    )
    assert _probe(body) == "0 []"
