import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
import uuid
from pathlib import Path

from watchmode_truth_lab.runner import run
from scripts.test_cycle import redact

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "watchmode_truth_lab/assets/vite/browser_probe.mjs"
CHROME = Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe"
NODE = shutil.which("node")
PLAYWRIGHT = ROOT / "node_modules/playwright-core/package.json"
SUPPORTED_ENGINES = {"chromium", "firefox", "webkit"}


def retain_observation(label, payload):
    directory = ROOT / 'evidence/browser-startup'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (label + '-' + uuid.uuid4().hex + '.json')
    payload = {'adapter_sha256': hashlib.sha256(ADAPTER.read_bytes()).hexdigest(),
               'observation': payload}
    path.write_text(redact(json.dumps(payload, indent=2)) + '\n', encoding='utf-8')


def extract_add_init_callback(source: str) -> str:
    """Extract the complete callback expression with balanced braces."""
    marker = "page.addInitScript("
    start = source.find(marker)
    if start < 0:
        raise AssertionError("Packaged browser adapter has no addInitScript callback")
    argument_start = start + len(marker)
    arrow = source.find("=>", argument_start)
    if arrow < 0:
        raise AssertionError("addInitScript argument is not an arrow callback")
    opening = source.find("{", arrow)
    if opening < 0:
        raise AssertionError("addInitScript callback body is missing")

    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False
    index = opening
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and following == "/":
                block_comment = False
                index += 1
        elif quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and following == "/":
            line_comment = True
            index += 1
        elif char == "/" and following == "*":
            block_comment = True
            index += 1
        elif char in ("'", '"', "`"):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                callback = source[argument_start:index + 1].strip()
                if not source[index + 1:].lstrip().startswith(");"):
                    raise AssertionError("Could not find the addInitScript callback end marker")
                return callback
        index += 1
    raise AssertionError("Unclosed addInitScript callback body")


def browser_node_script() -> str:
    return textwrap.dedent(
        """
        import { chromium, firefox, webkit } from 'playwright-core';
        const engines = { chromium, firefox, webkit };
        const engine = process.env.WTL_BROWSER_ENGINE || 'chromium';
        const browserType = engines[engine];
        if (!browserType) throw new Error(`Unsupported test engine: ${engine}`);
        const callbackSource = Buffer.from(process.argv[1], 'base64').toString('utf8');
        const callback = eval(`(${callbackSource})`);
        const options = { headless: true };
        if (engine === 'chromium') options.channel = process.env.WTL_BROWSER_CHANNEL || 'chrome';
        let browser;
        try {
          browser = await browserType.launch(options);
          const page = await browser.newPage();
          const pageErrors = [];
          page.on('pageerror', error => pageErrors.push(error.message));
          await page.addInitScript(callback);
          const pages = [];
          for (const title of ['first-document', 'second-document']) {
            await page.goto(`data:text/html,<title>${title}</title><p>${title}</p>`, { waitUntil: 'domcontentloaded' });
            pages.push(await page.evaluate(() => ({
              secureContext: isSecureContext,
              cryptoAvailable: typeof globalThis.crypto === 'object',
              randomUUID: typeof globalThis.crypto?.randomUUID,
              session: window.__wtl_probe_session ?? null,
            })));
          }
          console.log('WTL_ACTUAL_BROWSER_FACTS ' + JSON.stringify({ engine, browserVersion: browser.version(), pages, pageErrors }));
        } finally {
          await browser?.close();
        }
        """
    )


def fake_server_source(include_button: bool) -> str:
    button_setup = """
      setTimeout(() => {
        const button = document.createElement('button');
        button.id = 'increment';
        button.textContent = 'Increment';
        button.addEventListener('click', () => {
          const count = document.querySelector('#count');
          count.textContent = String(Number(count.textContent) + 1);
        });
        document.body.append(button);
      }, 1800);
    """ if include_button else ""
    return textwrap.dedent(
        f"""
        import {{ createServer }} from 'node:http';
        import {{ readFileSync }} from 'node:fs';
        import {{ join }} from 'node:path';

        const workspace = process.argv[2];
        const port = Number(process.argv[process.argv.indexOf('--port') + 1]);
        const html = `<!doctype html><html><body>
          <div id="token">seed</div><div id="count">0</div>
          <script>
            setInterval(async () => {{
              try {{
                const response = await fetch('/token');
                document.querySelector('#token').textContent = await response.text();
              }} catch {{}}
            }}, 30);
            {button_setup}
          </script>
        </body></html>`;
        const server = createServer((request, response) => {{
          if (request.url === '/') {{
            response.writeHead(200, {{ 'content-type': 'text/html; charset=utf-8' }});
            response.end(html);
          }} else if (request.url === '/token') {{
            response.writeHead(200, {{ 'content-type': 'text/plain; charset=utf-8' }});
            response.end(readFileSync(join(workspace, 'input.txt'), 'utf8'));
          }} else {{
            response.writeHead(404);
            response.end('missing');
          }}
        }});
        server.listen(port, '127.0.0.1');
        """
    )


@unittest.skipUnless(
    (((os.name == "nt" and CHROME.exists()) or
      (sys.platform.startswith("linux") and os.environ.get("WTL_TEST_BROWSER") == "1")) and
     NODE and PLAYWRIGHT.exists()),
    "Requires installed Windows Chrome or Linux browser opt-in, plus Node and pinned Playwright dependency",
)
class BrowserStartupTests(unittest.TestCase):
    def setUp(self):
        engine = os.environ.get("WTL_BROWSER_ENGINE", "chromium")
        if engine not in SUPPORTED_ENGINES:
            self.skipTest(f"Unsupported browser selection for integration test: {engine}")

    def test_packaged_init_callback_creates_distinct_sessions_in_insecure_documents(self):
        callback = extract_add_init_callback(ADAPTER.read_text(encoding="utf-8"))
        callback_b64 = base64.b64encode(callback.encode("utf-8")).decode("ascii")
        script = browser_node_script()
        completed = subprocess.run(
            [NODE, "--input-type=module", "-e", script, callback_b64],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=45,
            env=os.environ.copy(), check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        facts_line = next((line for line in completed.stdout.splitlines()
                           if line.startswith("WTL_ACTUAL_BROWSER_FACTS ")), None)
        self.assertIsNotNone(facts_line, completed.stdout)
        facts = json.loads(facts_line.removeprefix("WTL_ACTUAL_BROWSER_FACTS "))
        retain_observation('insecure-document', facts)
        self.assertEqual(len(facts["pages"]), 2, facts)
        for page in facts["pages"]:
            self.assertFalse(page["secureContext"], facts)
            self.assertTrue(page["cryptoAvailable"], facts)
            self.assertEqual(page["randomUUID"], "undefined", facts)
            self.assertIsInstance(page["session"], str, facts)
            self.assertTrue(page["session"], facts)
        self.assertNotEqual(facts["pages"][0]["session"], facts["pages"][1]["session"], facts)

    def make_scenario(self, temporary: str, include_button: bool) -> Path:
        temp_root = Path(temporary)
        fixture = temp_root / "fixture"
        fixture.mkdir()
        (fixture / "input.txt").write_text("seed", encoding="utf-8")
        fake_cli = temp_root / "fake-vite.mjs"
        fake_cli.write_text(fake_server_source(include_button), encoding="utf-8")
        config = {
            "fixture_dir": str(fixture),
            "command": [NODE, str(ADAPTER), str(fake_cli), "{workspace}", "{port}",
                        "{workspace}/.wtl-browser-state.json"],
            "mutation_target": "input.txt",
            "oracle": {"type": "file", "path": ".wtl-browser-state.json",
                       "extract_regex": '"token":"([^"]+)"'},
            "timeout_seconds": 3,
            "startup_timeout_seconds": 15,
            "probe_interval_seconds": 0.03,
            "stable_seconds": 0.12,
            "env": {"WTL_DOM_SELECTOR": "#token", "WTL_STATE_SELECTOR": "#count",
                    "WTL_CLICK_SELECTOR": "#increment"},
        }
        path = temp_root / "scenario.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        return path

    def run_in_temp_workspace(self, include_button: bool):
        with tempfile.TemporaryDirectory(prefix="browser-startup-", dir=ROOT / "reports") as temporary:
            config = self.make_scenario(temporary, include_button)
            started = time.monotonic()
            report = run(config, rounds=1, mutation="overwrite")
            elapsed = time.monotonic() - started
            retain_observation('delayed-interaction' if include_button else 'missing-interaction',
                               {'kind': 'Actual browser with controlled HTTP server; not real Vite',
                                'elapsed_seconds': elapsed, 'report': report})
        return report, elapsed

    def test_delayed_interaction_preserves_state_and_session_during_real_mutation(self):
        report, _elapsed = self.run_in_temp_workspace(include_button=True)
        self.assertEqual(report["startup"]["status"], "pass", report)
        self.assertEqual(report["status"], "pass", report)
        self.assertEqual(len(report["attempts"]), 1, report)
        self.assertEqual(report["attempts"][0]["status"], "pass", report)
        states = [json.loads(line.removeprefix("WTL_BROWSER_STATE ")) for line in report["logs"]
                  if line.startswith("WTL_BROWSER_STATE ")]
        self.assertGreaterEqual(len(states), 2, report)
        self.assertEqual(len({state["session"] for state in states}), 1, states)
        self.assertTrue(states[0]["session"], states)
        self.assertEqual({state["retainedState"] for state in states}, {"1"}, states)
        self.assertTrue(any(state["token"] == "seed" for state in states), states)
        self.assertTrue(any(state["token"].startswith("wtl-") for state in states), states)

    def test_missing_interaction_is_inconclusive_before_outer_startup_deadline(self):
        report, elapsed = self.run_in_temp_workspace(include_button=False)
        self.assertEqual(report["status"], "inconclusive", report)
        self.assertEqual(report["startup"]["status"], "inconclusive", report)
        self.assertEqual(report["attempts"], [], report)
        self.assertLess(elapsed, 15, report)
