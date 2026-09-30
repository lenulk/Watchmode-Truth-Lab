// Observe a live DOM. A navigation or closed browser invalidates the adapter.
import { spawn } from 'node:child_process';
import { writeFile, rename } from 'node:fs/promises';
import { chromium, firefox, webkit } from 'playwright-core';

const [viteCLI, workspace, port, output] = process.argv.slice(2);
const engine = process.env.WTL_BROWSER_ENGINE || 'chromium';
const selector = process.env.WTL_DOM_SELECTOR || '#token';
const stateSelector = process.env.WTL_STATE_SELECTOR;
const clickSelector = process.env.WTL_CLICK_SELECTOR;
const browserType = new Map([['chromium', chromium], ['firefox', firefox], ['webkit', webkit]]).get(engine);
if (!browserType) throw new Error(`Unsupported browser engine: ${engine}`);
const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
async function publish(serialized) {
  await writeFile(output + '.tmp', serialized);
  for (let attempt = 0; ; attempt += 1) {
    try {
      await rename(output + '.tmp', output);
      return;
    } catch (error) {
      if (process.platform !== 'win32' || !['EPERM', 'EACCES', 'EBUSY'].includes(error.code) || attempt >= 49) throw error;
      await sleep(10);
    }
  }
}
const vite = spawn(process.execPath, [viteCLI, workspace, '--host', '127.0.0.1', '--port', port, '--strictPort'],
  { cwd: workspace, env: process.env, stdio: ['ignore', 'inherit', 'inherit'], windowsHide: true });
let browser;
let viteExited = false;
vite.on('exit', () => { viteExited = true; });
vite.on('error', (error) => { console.error(error); viteExited = true; });

try {
  const launchOptions = { headless: true };
  if (engine === 'chromium') launchOptions.channel = process.env.WTL_BROWSER_CHANNEL || 'chrome';
  browser = await browserType.launch(launchOptions);
  console.log('WTL_BROWSER_ENGINE ' + engine);
  console.log('WTL_BROWSER_VERSION ' + browser.version());
  const page = await browser.newPage();
  await page.addInitScript(() => { window.__wtl_probe_session = crypto.randomUUID(); });
  page.on('pageerror', (error) => console.error('WTL_PAGE_ERROR ' + error.message));
  const deadline = Date.now() + 10000;
  while (true) {
    if (viteExited) throw new Error('Vite exited before browser readiness');
    try {
      await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: 'domcontentloaded', timeout: 1000 });
      await page.waitForFunction((selector) => typeof document.querySelector(selector)?.textContent === 'string', selector, { timeout: 1000 });
      break;
    } catch (error) {
      if (Date.now() >= deadline) throw error;
      await sleep(50);
    }
  }
  let session;
  if (clickSelector) await page.click(clickSelector, { timeout: 1000 });
  let previous;
  let previousToken;
  let observedChanges = 0;
  let retainedState;
  while (browser.isConnected() && !viteExited) {
    const state = await page.evaluate(({ selector, stateSelector }) => ({
      token: document.querySelector(selector)?.textContent,
      session: window.__wtl_probe_session,
      applicationUpdates: typeof window.__wtl_updates === 'number' ? window.__wtl_updates : null,
      retainedState: stateSelector ? document.querySelector(stateSelector)?.textContent : null,
    }), { selector, stateSelector });
    if (!state.session || typeof state.token !== 'string') throw new Error('DOM fixture is unavailable');
    session ??= state.session;
    if (state.session !== session) throw new Error('Page reloaded; HMR continuity was lost');
    if (stateSelector) {
      if (typeof state.retainedState !== 'string') throw new Error('State selector is unavailable');
      retainedState ??= state.retainedState;
      if (state.retainedState !== retainedState) throw new Error('Application state changed during update');
    }
    if (previousToken !== undefined && state.token !== previousToken) observedChanges += 1;
    previousToken = state.token;
    state.updates = state.applicationUpdates ?? observedChanges;
    state.updateMetric = state.applicationUpdates === null ? 'observed_dom_changes' : 'application_hmr_callbacks';
    const serialized = JSON.stringify(state);
    if (serialized !== previous) {
      await publish(serialized);
      console.log('WTL_BROWSER_STATE ' + serialized);
      previous = serialized;
    }
    await sleep(20);
  }
  throw new Error('Browser or Vite process stopped');
} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  await browser?.close();
  vite.kill();
}
