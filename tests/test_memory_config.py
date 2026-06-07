"""Tests for scripts/lib/memory_config.py"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from lib import memory_config as mc  # noqa: E402


class TestMemoryConfig(unittest.TestCase):
    def test_resolve_override_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            self.assertEqual(
                mc.resolve_memory_home(str(p), script_file=__file__),
                p.resolve(),
            )

    def test_resolve_env_over_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {"MEMORY_HOME": tmp}
            with mock.patch.dict(os.environ, env, clear=False):
                self.assertEqual(
                    mc.resolve_memory_home(None, script_file=__file__),
                    Path(tmp).resolve(),
                )

    def test_default_memory_inside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fw = Path(tmp) / "clone"
            scripts = fw / "scripts"
            scripts.mkdir(parents=True)
            (fw / "INSTRUCTIONS.md").write_text("# x", encoding="utf-8")
            script = scripts / "sync-memory.py"
            script.write_text("", encoding="utf-8")
            with mock.patch.dict(os.environ, {}, clear=True):
                os.environ.pop("MEMORY_HOME", None)
                hub = mc.resolve_memory_home(None, script_file=str(script))
                self.assertEqual(hub, (fw / "memory").resolve())

    def test_framework_root_from_memory_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fw = Path(tmp) / "clone"
            fw.mkdir()
            (fw / "INSTRUCTIONS.md").write_text("# x", encoding="utf-8")
            hub = fw / "memory"
            hub.mkdir()
            self.assertEqual(
                mc.framework_root_from_memory_home(hub),
                fw.resolve(),
            )

    def test_framework_root_from_hub_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp) / "hub"
            fw = Path(tmp) / "framework"
            hub.mkdir()
            fw.mkdir()
            (fw / "INSTRUCTIONS.md").write_text("# x", encoding="utf-8")
            (hub / "config.json").write_text(
                json.dumps({"framework_root": str(fw)}),
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {}, clear=True):
                os.environ.pop("FRAMEWORK_ROOT", None)
                self.assertEqual(
                    mc.resolve_framework_root(hub, None, None),
                    fw.resolve(),
                )

    def test_persist_hub_config_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fw = Path(tmp) / "clone"
            fw.mkdir()
            (fw / "INSTRUCTIONS.md").write_text("# x", encoding="utf-8")
            hub = fw / "memory"
            mc.persist_hub_config(fw, hub)
            cfg = json.loads((hub / "config.json").read_text())
            self.assertEqual(cfg["framework_root"], str(fw.resolve()))
            self.assertEqual(cfg["memory_home"], str(hub.resolve()))

    def test_framework_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fw = Path(tmp)
            (fw / "VERSION").write_text("1.2.3\n", encoding="utf-8")
            self.assertEqual(mc.framework_version(fw), "1.2.3")
            self.assertIsNone(mc.framework_version(None))

    def test_dev_clone_uses_install_hub(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dev = Path(tmp) / "dev"
            install = Path(tmp) / "install"
            for root in (dev, install):
                (root / "scripts").mkdir(parents=True)
                (root / "INSTRUCTIONS.md").write_text("# x", encoding="utf-8")
            script = dev / "scripts" / "sync-memory.py"
            script.write_text("", encoding="utf-8")
            (dev / mc.DEV_CONFIG_NAME).write_text(
                json.dumps({"install_root": str(install)}),
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {}, clear=True):
                os.environ.pop("MEMORY_HOME", None)
                hub = mc.resolve_memory_home(None, script_file=str(script))
                self.assertEqual(hub, (install / "memory").resolve())
                self.assertFalse((dev / "memory").exists())

    def test_dev_clone_rejects_local_memory_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dev = Path(tmp) / "dev"
            dev.mkdir()
            (dev / "scripts").mkdir()
            (dev / "INSTRUCTIONS.md").write_text("# x", encoding="utf-8")
            script = dev / "scripts" / "sync-memory.py"
            script.write_text("", encoding="utf-8")
            (dev / mc.DEV_CONFIG_NAME).write_text(
                json.dumps({"install_root": "/nonexistent/install"}),
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {}, clear=True):
                os.environ.pop("MEMORY_HOME", None)
                with mock.patch.object(mc, "_read_json", return_value={}), mock.patch.object(
                    mc, "_load_cursor_hook_env", return_value={}
                ):
                    with self.assertRaises(RuntimeError) as ctx:
                        mc.resolve_memory_home(None, script_file=str(script))
                    self.assertIn("dev clone", str(ctx.exception).lower())

    def test_legacy_global_config_emits_deprecation_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            legacy_dir = Path(tmp) / ".config" / "cursor-agent-memory"
            legacy_dir.mkdir(parents=True)
            hub = Path(tmp) / "legacy-hub"
            hub.mkdir()
            legacy_cfg = legacy_dir / "config.json"
            legacy_cfg.write_text(
                json.dumps({"memory_home": str(hub)}),
                encoding="utf-8",
            )
            with mock.patch.object(mc, "LEGACY_GLOBAL_CONFIG", legacy_cfg):
                with mock.patch.object(mc, "default_memory_home", return_value=None):
                    with mock.patch.object(
                        mc, "resolve_install_root", return_value=None
                    ):
                        with mock.patch.object(
                            mc, "_load_cursor_hook_env", return_value={}
                        ):
                            with mock.patch.dict(os.environ, {}, clear=True):
                                with warnings.catch_warnings(record=True) as caught:
                                    warnings.simplefilter("always", DeprecationWarning)
                                    resolved = mc.resolve_memory_home(
                                        None, script_file=None
                                    )
                                    self.assertEqual(resolved, hub.resolve())
                                    self.assertGreaterEqual(len(caught), 1)
                                    self.assertTrue(
                                        any(
                                            issubclass(w.category, DeprecationWarning)
                                            for w in caught
                                        )
                                    )

    def test_resolve_install_root_from_dev_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dev = Path(tmp) / "dev"
            install = Path(tmp) / "install"
            for root in (dev, install):
                root.mkdir(parents=True)
                (root / "INSTRUCTIONS.md").write_text("# x", encoding="utf-8")
            (dev / mc.DEV_CONFIG_NAME).write_text(
                json.dumps({"install_root": str(install)}),
                encoding="utf-8",
            )
            self.assertEqual(
                mc.resolve_install_root(dev_root=dev),
                install.resolve(),
            )
            self.assertTrue(mc.is_dev_project(dev))
            self.assertFalse(mc.is_dev_project(install))


if __name__ == "__main__":
    unittest.main()
