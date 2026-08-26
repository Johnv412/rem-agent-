"""
Tests for `remagent export --markdown` — the human-readable memory mirror.

The mirror must be faithful (active facts/rules only), deterministic
(diffable), self-cleaning (stale entity files removed, foreign files
untouched), and honest (missing DB/profile fails without writing).
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from remagent.export import MARKER, default_out_dir, export_markdown, ExportError
from remagent.schemas import Fact, MemoryProfile, OperationalRule
from remagent.storage.sqlite import SQLiteStorageAdapter


def run_export_cli(db_path: str, out: str) -> subprocess.CompletedProcess:
    args = ["remagent", "export", "--markdown", "--db", db_path, "--agent", "a", "--out", out]
    return subprocess.run(
        [sys.executable, "-c",
         f"import sys; sys.argv = {args!r}; from remagent.cli import main; main()"],
        capture_output=True, text=True, timeout=60,
    )


class TestMarkdownExport(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.dir = tempfile.mkdtemp(prefix="export_test_")
        self.db_path = os.path.join(self.dir, "memory.db")
        self.out = os.path.join(self.dir, "mirror")
        self.storage = SQLiteStorageAdapter(db_path=self.db_path)
        await self.storage.initialize()

    async def asyncTearDown(self):
        await self.storage.close()
        shutil.rmtree(self.dir, ignore_errors=True)

    async def seed(self, facts=None, rules=None):
        await self.storage.save_memory_profile(
            MemoryProfile(agent_id="a", facts=facts or [], rules=rules or [])
        )

    async def test_renders_entities_and_rules_active_only(self):
        await self.seed(
            facts=[
                Fact(entity="Vendor", attribute="price", value="$52"),
                Fact(entity="Vendor", attribute="region", value="us-west"),
                Fact(entity="Project Alpha", attribute="db", value="PostgreSQL"),
                Fact(entity="Vendor", attribute="price", value="$40",
                     is_active=False, superseded_by="x"),
            ],
            rules=[
                OperationalRule(category="coding_standard", rule="Pin versions",
                                rationale="reproducibility", priority=1),
                OperationalRule(category="user_preference", rule="Old rule",
                                rationale="", priority=3, is_active=False),
            ],
        )
        files = export_markdown(self.db_path, "a", self.out)
        names = {os.path.basename(p) for p in files}
        self.assertEqual(names, {"vendor.md", "project-alpha.md", "rules.md", "README.md"})

        vendor = open(os.path.join(self.out, "vendor.md")).read()
        self.assertTrue(vendor.startswith(MARKER))
        self.assertIn("$52", vendor)
        self.assertNotIn("$40", vendor, "inactive facts must not appear in the mirror")

        rules_md = open(os.path.join(self.out, "rules.md")).read()
        self.assertIn("Pin versions", rules_md)
        self.assertNotIn("Old rule", rules_md, "inactive rules must not appear")

    async def test_low_confidence_active_facts_render(self):
        """The audit value of the mirror is seeing weak beliefs too — active
        facts render regardless of confidence."""
        await self.seed(facts=[
            Fact(entity="Hunch", attribute="maybe", value="probably-x", confidence=0.25),
        ])
        export_markdown(self.db_path, "a", self.out)
        hunch = open(os.path.join(self.out, "hunch.md")).read()
        self.assertIn("probably-x", hunch)
        self.assertIn("0.25", hunch)

    async def test_deterministic_output(self):
        await self.seed(facts=[Fact(entity="Vendor", attribute="price", value="$52")])
        export_markdown(self.db_path, "a", self.out)
        first = open(os.path.join(self.out, "vendor.md")).read()
        export_markdown(self.db_path, "a", self.out)
        second = open(os.path.join(self.out, "vendor.md")).read()
        self.assertEqual(first, second, "regeneration must be byte-identical for diffability")

    async def test_stale_generated_files_removed_foreign_files_kept(self):
        await self.seed(facts=[Fact(entity="OldEntity", attribute="x", value="1")])
        export_markdown(self.db_path, "a", self.out)
        self.assertTrue(os.path.exists(os.path.join(self.out, "oldentity.md")))

        foreign = os.path.join(self.out, "my-notes.md")
        open(foreign, "w").write("# my own notes, no marker\n")

        await self.seed(facts=[Fact(entity="NewEntity", attribute="y", value="2")])
        export_markdown(self.db_path, "a", self.out)
        self.assertFalse(os.path.exists(os.path.join(self.out, "oldentity.md")),
                         "stale generated file must be removed")
        self.assertTrue(os.path.exists(os.path.join(self.out, "newentity.md")))
        self.assertTrue(os.path.exists(foreign), "files without the marker must never be touched")

    def test_missing_db_fails_writing_nothing(self):
        ghost = os.path.join(self.dir, "ghost.db")
        with self.assertRaises(ExportError):
            export_markdown(ghost, "a", self.out)
        self.assertFalse(os.path.exists(self.out), "failure must write nothing")

    async def test_missing_profile_fails(self):
        with self.assertRaises(ExportError):
            export_markdown(self.db_path, "nobody", self.out)
        self.assertFalse(os.path.exists(self.out))

    async def test_cli_export_command(self):
        await self.seed(facts=[Fact(entity="Vendor", attribute="price", value="$52")])
        proc = run_export_cli(self.db_path, self.out)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("Memory mirror written", proc.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.out, "vendor.md")))

    def test_cli_export_missing_db_exits_nonzero(self):
        proc = run_export_cli(os.path.join(self.dir, "ghost.db"), self.out)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAILED", proc.stderr)

    def test_default_out_dir_derived_from_db(self):
        self.assertEqual(default_out_dir("/x/y/memory.db"), "/x/y/memory_md")


if __name__ == "__main__":
    unittest.main()
