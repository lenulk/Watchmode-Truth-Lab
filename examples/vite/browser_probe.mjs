// Observe a live DOM. A navigation or closed browser invalidates the adapter.
import { spawn } from 'node:child_process';
import { writeFile, rename } from 'node:fs/promises';
import { chromium, firefox, webkit } from 'playwright-core';

const [viteCLI, workspace, port, output] = process.argv.slice(2);
const engine = process.env.WTL_BROWSER_ENGINE || 'chromium';
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
  page.on('pageerror', (error) => console.error('WTL_PAGE_ERROR ' + error.message));
  const deadline = Date.now() + 10000;
  while (true) {
    if (viteExited) throw new Error('Vite exited before browser readiness');
    try {
      await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: 'domcontentloaded', timeout: 1000 });
      await page.waitForFunction(() => Boolean(window.__wtl_session), { timeout: 1000 });
      break;
    } catch (error) {
      if (Date.now() >= deadline) throw error;
      await sleep(50);
    }
  }
  let session;
  let previous;
  while (browser.isConnected() && !viteExited) {
    const state = await page.evaluate(() => ({
      token: document.querySelector('#token')?.textContent,
      session: window.__wtl_session,
      updates: window.__wtl_updates,
    }));
    if (!state.session || typeof state.token !== 'string') throw new Error('DOM fixture is unavailable');
    session ??= state.session;
    if (state.session !== session) throw new Error('Page reloaded; HMR continuity was lost');
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
