"""Signal Hub contract: importable UI entry point, Streamlit only under ui/, slug-namespaced keys, Hub mode.

Written by signal-hub/scripts/scaffold_app.py and extended for Learn Signal's pages. Every page is rendered, and the
"1 · Add your data" page is rendered once per input mode (spreadsheet, manual, AI prompt), because each mode draws
different widgets.
"""

import ast
import builtins
import io
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest
from streamlit.testing.v1 import AppTest

from learnsignal import __version__

ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "src" / "learnsignal"
UI = PACKAGE / "ui"
UI_ONLY = {"streamlit", "plotly"}
RENDER = "from learnsignal.ui import render\n\nrender()\n"
PAGES = ["Overview", "1 · Add your data", "2 · Edit & review", "3 · Decision & research value",
         "4 · Results & sensitivity", "5 · Export", "Research & limits"]
MODES = ["Excel or CSV", "Enter manually", "Use your AI"]
GENERATED = {"signal_theme.py", "signal_font.py"}


def _imported_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_app_info_matches_the_hub_registry() -> None:
    from learnsignal.ui import APP_INFO, render

    assert callable(render)
    assert APP_INFO == {"product": "Learn Signal", "version": __version__, "repo": "research-prioritization",
                        "slug": "learn"}


def test_only_the_ui_package_imports_streamlit_or_plotly() -> None:
    offenders = {str(p.relative_to(PACKAGE)): sorted(_imported_roots(p) & UI_ONLY)
                 for p in PACKAGE.rglob("*.py") if UI not in p.parents and _imported_roots(p) & UI_ONLY}
    assert not offenders, offenders


def test_core_imports_without_streamlit_in_a_fresh_interpreter() -> None:
    code = "\n".join([
        "import importlib, pkgutil, sys",
        f"sys.path.insert(0, {str(ROOT / 'src')!r})",
        "import learnsignal",
        "for m in pkgutil.iter_modules(learnsignal.__path__):",
        "    if m.name != 'ui':",
        "        importlib.import_module('learnsignal.' + m.name)",
        "assert 'streamlit' not in sys.modules and 'plotly' not in sys.modules",
    ])
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr


def test_render_never_sets_page_config_or_navigation() -> None:
    for path in UI.rglob("*.py"):
        if path.name in GENERATED:
            continue
        source = path.read_text(encoding="utf-8")
        for call in ("st.set_page_config(", "st.navigation(", "st.Page("):
            assert call not in source, (path.name, call)


def test_session_state_and_widget_keys_go_through_the_namespace_helper() -> None:
    from learnsignal.ui.keys import NS, k

    assert NS == "learn" and k("page") == "learn:page"
    for path in UI.glob("*.py"):
        if path.name in GENERATED or path.name in {"__init__.py", "keys.py"}:
            continue
        source = path.read_text(encoding="utf-8")
        state_keys = re.findall(r"session_state(?:\[|\.get\(|\.pop\(|\.update\(\{)\s*([^,\])]+)", source)
        widget_keys = re.findall(r"\bkey=([^,)\n]+)", source)
        forms = re.findall(r"st\.form\(([^,)\n]+)", source)
        for key in state_keys + widget_keys + forms:
            assert key.startswith("k("), (path.name, key)
        # The slug lives in keys.py only; the UI never spells it out or builds keys by hand.
        assert '"learn' not in source, path.name
        assert "use_container_width" not in source, path.name


def _widgets(app: AppTest) -> list:
    return [*app.radio, *app.selectbox, *app.multiselect, *app.checkbox, *app.button, *app.slider,
            *app.number_input, *app.text_input, *app.text_area, *app.toggle, *app.date_input]


def _visit_every_page(app: AppTest, check=None) -> None:
    for page in PAGES:
        app.sidebar.radio(key="learn:page").set_value(page).run()
        assert not app.exception, (page, [e.value for e in app.exception])
        if check:
            check(app, page)
        if page == "1 · Add your data":
            for mode in MODES:
                app.radio(key="learn:input_mode").set_value(mode).run()
                assert not app.exception, (page, mode, [e.value for e in app.exception])
                if check:
                    check(app, page + " / " + mode)


def test_render_runs_without_set_page_config_and_keys_are_namespaced() -> None:
    app = AppTest.from_string(RENDER, default_timeout=120).run()
    assert not app.exception, [e.value for e in app.exception]
    assert app.sidebar.radio(key="learn:page").options == PAGES

    def namespaced(app: AppTest, where: str) -> None:
        assert not app.error, (where, [e.value for e in app.error])
        unkeyed = [(type(w).__name__, w.label) for w in _widgets(app) if not (w.key or "").startswith("learn:")]
        assert not unkeyed, (where, unkeyed)

    _visit_every_page(app, namespaced)
    body = "\n".join(str(item.value) for item in app.markdown)
    assert f"v{__version__}" in body


def test_hub_mode_writes_nothing_and_makes_no_network_calls(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    real_connect = socket.socket.connect

    def no_network(sock, address, *args, **kwargs):
        # asyncio's event loop on Windows builds its self-pipe from a loopback socket pair; that is not network I/O.
        if isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1"}:
            return real_connect(sock, address, *args, **kwargs)
        raise AssertionError(f"network call in Hub mode: {address!r}")

    monkeypatch.setenv("SIGNAL_HUB", "1")
    for name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "XDG_DATA_HOME", "XDG_CACHE_HOME"):
        monkeypatch.setenv(name, str(tmp_path / "home"))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(socket.socket, "connect", no_network)
    app = AppTest.from_string(RENDER, default_timeout=120).run()
    assert not app.exception, [e.value for e in app.exception]
    # Hub mode opens on the reviewed fictional demo, not an empty upload screen.
    assert any("FICTIONAL DEMO" in str(t.value) for t in app.text)
    seen = set()

    def hub_page(app: AppTest, where: str) -> None:
        seen.add(where)
        if where == "3 · Decision & research value":
            assert len(app.metric) == 3  # the demo's EVPI is calculated without any upload or click
        if where == "5 · Export":
            assert any("lives only in your browser session" in str(c.value) for c in app.caption)
        if where.endswith("Use your AI"):
            assert any("No API key or automatic data transfer" in str(c.value) for c in app.caption)

    _visit_every_page(app, hub_page)
    assert {"3 · Decision & research value", "5 · Export", "1 · Add your data / Use your AI"} <= seen
    written = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert not written, written
    assert os.environ["SIGNAL_HUB"] == "1"


def test_standalone_mode_has_no_hub_note(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIGNAL_HUB", raising=False)
    app = AppTest.from_string(RENDER, default_timeout=120).run()
    app.sidebar.radio(key="learn:page").set_value("5 · Export").run()
    assert not app.exception
    assert not any("lives only in your browser session" in str(c.value) for c in app.caption)


def test_render_reads_no_repo_root_files(monkeypatch: pytest.MonkeyPatch) -> None:
    """Signal Hub installs the release as a normal package: only src/learnsignal (and its package data) exists there.

    Render every page and record every file opened. Nothing may come from the repository root (assets/, docs/, ...):
    the demo and the Excel and CSV templates are generated in code, the font is embedded in signal_font.py, and the
    marks ship as package data under learnsignal/ui/assets/marks.
    """
    opened: list[Path] = []
    real_open = builtins.open

    def spy(file, *args, **kwargs):
        if isinstance(file, (str, os.PathLike)):
            opened.append(Path(os.fspath(file)).resolve())
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy)
    monkeypatch.setattr(io, "open", spy)
    app = AppTest.from_string(RENDER, default_timeout=120).run()
    _visit_every_page(app)

    package = PACKAGE.resolve()
    root = ROOT.resolve()

    def from_repo_root(path: Path) -> bool:
        if root not in path.parents or package in path.parents:
            return False
        # Libraries probe for files that don't exist and read project config; neither is app data.
        if not path.is_file() or path.name in {"pyproject.toml", "setup.cfg", "tox.ini"}:
            return False
        # Streamlit's own config and installed-distribution metadata are not app data.
        return ".streamlit" not in path.parts and not any(
            part.endswith((".egg-info", ".dist-info")) for part in path.parts
        )

    outside = sorted({str(path) for path in opened if from_repo_root(path)})
    assert not outside, outside
    # The theme reads its mark from package data. Checked directly: on Python 3.10 pathlib keeps its own reference
    # to io.open, so the spy above does not see Path.read_text calls.
    from learnsignal.ui import signal_theme

    assert package in Path(signal_theme.ASSETS).resolve().parents
    marks = [path for path in opened if path.name == "learnsignal-mark.svg"]
    assert all(package in path.parents for path in marks)
    for name in ("learnsignal-mark.svg", "learnsignal-mark-32.png", "learnsignal-mark-64.png"):
        assert (UI / "assets" / "marks" / name).exists()


def test_upload_cap_is_10000_mb_and_demo_caps_live_in_one_module(monkeypatch: pytest.MonkeyPatch) -> None:
    from learnsignal import limits

    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert re.search(r"^maxUploadSize = 10000$", config, re.M)
    docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "STREAMLIT_SERVER_MAX_UPLOAD_SIZE=10000" in docker and "maxUploadSize" not in docker
    assert "set LEARNSIGNAL_MAX_UPLOAD_MB=10000" in (ROOT / "run_app.bat").read_text(encoding="utf-8")
    assert "${LEARNSIGNAL_MAX_UPLOAD_MB:-10000}" in (ROOT / "run_app.command").read_text(encoding="utf-8")
    assert b"\r\n" not in (ROOT / "run_app.command").read_bytes()
    # No other module hard-codes a size cap: every one comes from limits.py. (Short field lengths such as the
    # 2,500-character case brief are format rules shared with the JSON schema, not data limits.)
    for path in PACKAGE.rglob("*.py"):
        if path.name in GENERATED | {"limits.py"}:
            continue
        source = path.read_text(encoding="utf-8")
        assert not re.search(r'MAX_[A-Z]+\s*=|max_chars=\d{5,}|"maxItems": \d', source), path.name
    monkeypatch.delenv("SIGNAL_PUBLIC", raising=False)
    assert all(limits.cap(name) is None for name in limits.DEMO)
    monkeypatch.setenv("SIGNAL_PUBLIC", "1")
    assert limits.cap("upload_bytes") == 50 * 1024 * 1024 and limits.cap("states") == 30


def test_public_demo_shows_its_limits_and_local_does_not(monkeypatch: pytest.MonkeyPatch) -> None:
    for public in (False, True):
        if public:
            monkeypatch.setenv("SIGNAL_PUBLIC", "1")
        else:
            monkeypatch.delenv("SIGNAL_PUBLIC", raising=False)
        app = AppTest.from_string(RENDER, default_timeout=120).run()
        app.sidebar.radio(key="learn:page").set_value("1 · Add your data").run()
        assert not app.exception
        shown = any("Public demo limits" in str(c.value) for c in app.caption)
        assert shown is public
        ai = app.radio(key="learn:input_mode").set_value("Use your AI").run()
        assert bool(ai.text_area(key="learn:ai_json").max_chars) is public  # AppTest reports no limit as 0
