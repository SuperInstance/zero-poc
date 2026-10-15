"""Unit tests for .github/scripts/agent.py — the zero agent's brain.

Runs offline: every vault/network/git-remote touch is mocked or pointed at
a temp directory. Green under BOTH:
    python3 -m unittest discover -s . -p "test_*.py" -v   (agent.py fallback)
    python3 -m pytest tests/ -q                           (if pytest present)
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".github" / "scripts"))
import agent  # noqa: E402


class TempCwdTestCase(unittest.TestCase):
    """Base: run each test from an empty temp dir so the repo's own
    MEMORY.md / TASKS.md / scratch/ are never read or written."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._old_cwd = os.getcwd()
        os.chdir(self.tmp.name)
        self.addCleanup(os.chdir, self._old_cwd)


class TestParseLLMDecision(unittest.TestCase):
    def test_clean_json(self):
        raw = '{"tool_calls": [{"tool": "read_file", "args": {"path": "README.md"}}], "done": false, "thinking": "hmm"}'
        d = agent.parse_llm_decision(raw)
        self.assertIsInstance(d, dict)
        self.assertFalse(d["done"])
        self.assertEqual(d["tool_calls"][0]["tool"], "read_file")

    def test_clean_done_object(self):
        d = agent.parse_llm_decision('{"thinking": "x", "done": true, "summary": "all set"}')
        self.assertTrue(d["done"])
        self.assertEqual(d["summary"], "all set")

    def test_fenced_json_block(self):
        self.assertTrue(agent.parse_llm_decision('```json\n{"done": true}\n```')["done"])

    def test_fenced_plain_block(self):
        self.assertTrue(agent.parse_llm_decision('```\n{"done": true}\n```')["done"])

    def test_json_wrapped_in_prose(self):
        r = 'Sure, here is my plan:\n{"done": false, "tool_calls": []}\nHope that helps!'
        self.assertFalse(agent.parse_llm_decision(r)["done"])

    def test_no_json_returns_none(self):
        self.assertIsNone(agent.parse_llm_decision("I cannot answer that."))

    def test_invalid_json_returns_none(self):
        self.assertIsNone(agent.parse_llm_decision("{not valid json}"))

    def test_empty_string_returns_none(self):
        self.assertIsNone(agent.parse_llm_decision("   "))


class TestGetRepo(unittest.TestCase):
    def test_env_var_takes_priority(self):
        with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "Foo/barbaz"}, clear=False):
            self.assertEqual(agent.get_repo(), ("Foo", "barbaz"))

    def test_https_remote(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_REPOSITORY", None)
            with mock.patch.object(
                agent.subprocess, "run",
                return_value=mock.Mock(stdout="https://github.com/owner/repo.git\n")
            ):
                self.assertEqual(agent.get_repo(), ("owner", "repo"))

    def test_ssh_remote(self):
        with mock.patch.dict(os.environ):  # pops restored afterwards
            os.environ.pop("GITHUB_REPOSITORY", None)
            with mock.patch.object(
                agent.subprocess, "run",
                return_value=mock.Mock(stdout="git@github.com:owner/repo.git\n")
            ):
                self.assertEqual(agent.get_repo(), ("owner", "repo"))

    def test_fallback_to_template_default(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("GITHUB_REPOSITORY", None)
            with mock.patch.object(
                agent.subprocess, "run",
                side_effect=Exception("no git")
            ):
                self.assertEqual(agent.get_repo(), ("purplepincher", "zero"))


class TestPermissions(unittest.TestCase):
    def test_tiers(self):
        self.assertEqual(agent.check_permission("read_file"), "auto")
        self.assertEqual(agent.check_permission("api_github"), "vault")
        self.assertEqual(agent.check_permission("write_workflow"), "deferred")
        self.assertEqual(agent.check_permission("git_push_main"), "deferred")

    def test_unknown_tool_is_deferred(self):
        self.assertEqual(agent.check_permission("obliterate_repo"), "deferred")


class TestExecuteToolGuards(TempCwdTestCase):
    def test_write_file_protects_workflows(self):
        ok, msg = agent.execute_tool({"tool": "write_file",
                                      "args": {"path": ".github/workflows/evil.yml", "content": "x"}})
        self.assertFalse(ok)
        self.assertEqual(msg, "Protected path")
        self.assertFalse(Path(".github/workflows/evil.yml").exists())

    def test_write_file_blocks_traversal(self):
        ok, _ = agent.execute_tool({"tool": "write_file",
                                    "args": {"path": "../escape.txt", "content": "x"}})
        self.assertFalse(ok)

    def test_write_file_normal_path(self):
        ok, msg = agent.execute_tool({"tool": "write_file",
                                      "args": {"path": "notes/deep/file.txt", "content": "hello"}})
        self.assertTrue(ok)
        self.assertEqual(Path("notes/deep/file.txt").read_text(), "hello")

    def test_read_file_blocks_traversal(self):
        ok, msg = agent.execute_tool({"tool": "read_file", "args": {"path": "../secrets"}})
        self.assertFalse(ok)
        self.assertIn("traversal", msg.lower())

    def test_write_scratch_rejects_paths_and_traversal(self):
        scratch = Path(self.tmp.name) / "scratch"
        with mock.patch.object(agent, "SCRATCH_DIR", scratch):
            for bad in ["../evil.txt", "sub/dir.txt"]:
                ok, _ = agent.execute_tool({"tool": "write_scratch",
                                            "args": {"filename": bad, "content": "x"}})
                self.assertFalse(ok, bad)

    def test_write_scratch_ok(self):
        scratch = Path(self.tmp.name) / "scratch"
        with mock.patch.object(agent, "SCRATCH_DIR", scratch):
            ok, _ = agent.execute_tool({"tool": "write_scratch",
                                        "args": {"filename": "notes.md", "content": "wip"}})
            self.assertTrue(ok)
            self.assertEqual((scratch / "notes.md").read_text(), "wip")


class TestCommentIssueIdentity(TempCwdTestCase):
    """The echo-loop fix: comments prefer gh (github-actions[bot] identity,
    which react.yml filters); vault is the fallback (owner identity)."""

    def _run(self, tool_args):
        with mock.patch.dict(os.environ,
                             {"GH_TOKEN": "t", "GITHUB_REPOSITORY": "o/r"}, clear=False):
            return agent.execute_tool(tool_args)

    def test_gh_path_used_when_token_present(self):
        with mock.patch.object(
            agent.subprocess, "run",
            return_value=subprocess.CompletedProcess([], 0, stdout="https://issue/1#comment")
        ) as run:
            ok, msg = self._run({"tool": "comment_issue",
                                 "args": {"issue": 5, "body": "status"}})
        self.assertTrue(ok)
        self.assertIn("github-actions[bot]", msg)
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[:3], ["gh", "issue", "comment"])
        self.assertIn("5", cmd)

    def test_vault_fallback_when_gh_fails(self):
        with mock.patch.object(
            agent.subprocess, "run",
            return_value=subprocess.CompletedProcess([], 1, stderr="gh: failed")
        ), mock.patch.object(agent, "vault_call",
                             return_value={"success": True}) as vc:
            ok, msg = self._run({"tool": "comment_issue",
                                 "args": {"issue": 5, "body": "status"}})
        self.assertTrue(ok)
        self.assertIn("via vault", msg)
        self.assertEqual(vc.call_args.args[0:2], ("github", "comment_issue"))

    def test_vault_error_reported_as_failure(self):
        """Regression: the vault path used to return success even when the
        vault answered with an error dict — the LLM believed it had
        replied when the comment was silently lost."""
        with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "o/r"}, clear=False), \
             mock.patch.dict(os.environ, {}, clear=False), \
             mock.patch.object(agent, "vault_call",
                               return_value={"error": "not allowed"}):
            os.environ.pop("GH_TOKEN", None)
            ok, msg = agent.execute_tool({"tool": "comment_issue",
                                          "args": {"issue": 5, "body": "x"}})
        self.assertFalse(ok)
        self.assertIn("Vault comment failed", msg)

    def test_missing_gh_binary_still_reaches_vault(self):
        """Regression: FileNotFoundError from a missing gh binary used to
        escape execute_tool's outer except before the vault fallback ran."""
        with mock.patch.dict(os.environ,
                             {"GH_TOKEN": "t", "GITHUB_REPOSITORY": "o/r"}, clear=False), \
             mock.patch.object(agent.subprocess, "run",
                               side_effect=FileNotFoundError("no gh")), \
             mock.patch.object(agent, "vault_call",
                               return_value={"success": True}):
            ok, msg = agent.execute_tool({"tool": "comment_issue",
                                          "args": {"issue": 5, "body": "x"}})
        self.assertTrue(ok)
        self.assertIn("via vault", msg)

    def test_create_issue_gh_path(self):
        with mock.patch.object(
            agent.subprocess, "run",
            return_value=subprocess.CompletedProcess([], 0, stdout="https://issue/9")
        ) as run:
            ok, msg = self._run({"tool": "create_issue",
                                 "args": {"title": "T", "body": "B"}})
        self.assertTrue(ok)
        self.assertIn("https://issue/9", msg)
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[:3], ["gh", "issue", "create"])


class TestFetchOpenIssues(TempCwdTestCase):
    """Vault-first with gh fallback — the mitigation for the vault's
    list_issues 404 (docs/maintenance-notes.md #1)."""

    def test_vault_success(self):
        env = {"GITHUB_REPOSITORY": "o/r"}
        with mock.patch.dict(os.environ, env, clear=False), \
             mock.patch.object(agent, "vault_call",
                               return_value={"success": True,
                                             "result": [{"number": 1, "title": "T", "body": "B"}]}):
            issues, source = agent.fetch_open_issues()
        self.assertEqual(source, "vault")
        self.assertEqual(issues[0]["number"], 1)

    def test_gh_fallback_when_vault_fails(self):
        gh_json = json.dumps([{"number": 2, "title": "T2", "body": "B2"}])
        with mock.patch.dict(os.environ,
                             {"GITHUB_REPOSITORY": "o/r", "GH_TOKEN": "t"}, clear=False), \
             mock.patch.object(agent, "vault_call", return_value={"error": "404"}), \
             mock.patch.object(agent.subprocess, "run",
                               return_value=subprocess.CompletedProcess([], 0, stdout=gh_json)):
            issues, source = agent.fetch_open_issues()
        self.assertEqual(source, "gh")
        self.assertEqual(issues[0]["number"], 2)

    def test_total_failure(self):
        with mock.patch.dict(os.environ):  # pops restored afterwards
            os.environ.pop("GH_TOKEN", None)
            with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "o/r"}, clear=False), \
                 mock.patch.object(agent, "vault_call", return_value={"error": "404"}):
                self.assertEqual(agent.fetch_open_issues(), (None, "failed"))

    def test_empty_board_is_not_fetch_failure(self):
        """Regression: build_context used `if issues:` — an honestly-empty
        board ([]) rendered as FETCH FAILED and baited the LLM into
        re-listing issues every cycle."""
        with mock.patch.object(agent, "fetch_open_issues",
                               return_value=([], "vault")):
            ctx = agent.build_context(None)
        self.assertIn("none open — the board is empty", ctx)
        self.assertNotIn("FETCH FAILED", ctx)

    def test_fetch_failure_wording_present(self):
        with mock.patch.object(agent, "fetch_open_issues",
                               return_value=(None, "failed")):
            ctx = agent.build_context(None)
        self.assertIn("FETCH FAILED", ctx)


class TestStatePersistence(TempCwdTestCase):
    def test_roundtrip(self):
        state_file = Path(self.tmp.name) / ".agent-state.json"
        with mock.patch.object(agent, "STATE_FILE", state_file):
            agent.save_state({"schema": 1, "outcome": "completed: test",
                              "iterations_used": 3})
            loaded = agent.load_state()
        self.assertEqual(loaded["outcome"], "completed: test")
        self.assertEqual(loaded["iterations_used"], 3)

    def test_load_missing_or_garbage_returns_empty(self):
        with mock.patch.object(agent, "STATE_FILE", Path(self.tmp.name) / "nope.json"):
            self.assertEqual(agent.load_state(), {})
        garbage = Path(self.tmp.name) / "garbage.json"
        garbage.write_text("{not json")
        with mock.patch.object(agent, "STATE_FILE", garbage):
            self.assertEqual(agent.load_state(), {})


class TestUpdateMemory(TempCwdTestCase):
    def test_appends_timestamped_entry(self):
        Path("MEMORY.md").write_text("# What I've Learned\n")
        agent.update_memory("did a thing")
        content = Path("MEMORY.md").read_text()
        self.assertIn("- [", content)          # timestamped bullet
        self.assertIn("did a thing", content)
        self.assertTrue(content.startswith("# What I've Learned\n"))  # append-only


class TestLocalBrainMode(unittest.TestCase):
    """Hermit-crab mode (LOCAL_LLM_URL): the loop thinks via a local
    OpenAI-compatible server and never touches the vault."""

    @staticmethod
    def _fake_urlopen(body):
        # MagicMock (not Mock) so the response object supports the
        # context-manager protocol urllib.request.urlopen is used with.
        fake = mock.MagicMock()
        fake.__enter__.return_value.read.return_value = json.dumps(body).encode()
        return fake

    def _local_env(self):
        return {"LOCAL_LLM_URL": "http://localhost:11434/v1",
                "LOCAL_LLM_MODEL": "test-model"}

    def test_local_path_bypasses_vault(self):
        env = self._local_env()
        ok_body = {"choices": [{"message": {"role": "assistant",
                                            "content": "local says hi"}}]}
        with mock.patch.dict(os.environ, env, clear=False), \
             mock.patch.object(agent, "LOCAL_LLM_URL", env["LOCAL_LLM_URL"]), \
             mock.patch.object(agent, "LOCAL_LLM_MODEL", env["LOCAL_LLM_MODEL"]), \
             mock.patch("urllib.request.urlopen",
                        return_value=self._fake_urlopen(ok_body)) as urlopen, \
             mock.patch.object(agent, "vault_call") as vc:
            out = agent.llm_think([{"role": "user", "content": "ping"}])
        self.assertEqual(out, "local says hi")
        vc.assert_not_called()
        req = urlopen.call_args.args[0]
        self.assertTrue(req.full_url.endswith("/chat/completions"))
        sent = json.loads(req.data.decode())
        self.assertEqual(sent["model"], "test-model")
        self.assertEqual(sent["messages"][0]["content"], "ping")
        self.assertFalse(sent["stream"])

    def test_local_failure_returns_none(self):
        env = self._local_env()
        with mock.patch.dict(os.environ, env, clear=False), \
             mock.patch.object(agent, "LOCAL_LLM_URL", env["LOCAL_LLM_URL"]), \
             mock.patch("urllib.request.urlopen",
                        side_effect=ConnectionError("refused")), \
             mock.patch.object(agent, "vault_call") as vc:
            self.assertIsNone(agent.llm_think([{"role": "user", "content": "x"}]))
        vc.assert_not_called()

    def test_vault_path_when_no_local_url(self):
        with mock.patch.dict(os.environ, {"LOCAL_LLM_URL": ""}, clear=False), \
             mock.patch.object(agent, "LOCAL_LLM_URL", ""), \
             mock.patch.object(agent, "vault_call",
                               return_value={"result": {"content": "vault says hi"}}):
            out = agent.llm_think([{"role": "user", "content": "ping"}])
        self.assertEqual(out, "vault says hi")


class TestToolPrompt(unittest.TestCase):
    def test_lists_core_tools_and_deferred_perms(self):
        prompt = agent.build_tool_prompt()
        for needle in ["tool_calls", "read_file", "write_scratch", "run_tests",
                       "comment_issue", "create_issue", "git_commit",
                       "write_workflow", "ONE JSON object"]:
            self.assertIn(needle, prompt)


if __name__ == "__main__":
    unittest.main()
