import { spawn } from "node:child_process";
import fs from "node:fs";

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

class CDPClient {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.ws = null;
    this.id = 1;
    this.pending = new Map();
    this.events = [];
    this.consoleErrors = [];
    this.exceptions = [];
  }

  async connect() {
    this.ws = new WebSocket(this.wsUrl);
    await new Promise((resolve, reject) => {
      this.ws.onopen = resolve;
      this.ws.onerror = reject;
    });

    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) {
          reject(new Error(msg.error.message));
        } else {
          resolve(msg.result);
        }
      } else if (msg.method) {
        if (msg.method === "Runtime.consoleAPICalled" && msg.params.type === "error") {
          this.consoleErrors.push(msg.params.args.map((a) => a.value ?? a.description).join(" "));
        } else if (msg.method === "Runtime.exceptionThrown") {
          this.exceptions.push(msg.params.exceptionDetails);
        }
        for (const handler of this.events) {
          if (handler.event === msg.method) {
            handler.cb(msg.params);
          }
        }
      }
    };
  }

  send(method, params = {}) {
    const id = this.id++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async evaluate(expression) {
    const res = await this.send("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    if (res.exceptionDetails) {
      throw new Error("Evaluation error: " + JSON.stringify(res.exceptionDetails));
    }
    return res.result?.value;
  }

  async screenshot(filename) {
    const res = await this.send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(filename, Buffer.from(res.data, "base64"));
    console.log(`[Screenshot] Saved ${filename}`);
  }

  close() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

async function verify() {
  const browser = spawn("brave-browser", [
    "--headless=new",
    "--remote-debugging-port=9222",
    "--no-sandbox",
    "--disable-gpu",
    "--window-size=1440,900",
    "--user-data-dir=/tmp/brave_verify_final_" + Date.now(),
  ]);

  try {
    await sleep(1500);
    const listRes = await fetch("http://127.0.0.1:9222/json/list");
    const targets = await listRes.json();
    const pageTarget = targets.find((t) => t.type === "page") || targets[0];

    const client = new CDPClient(pageTarget.webSocketDebuggerUrl);
    await client.connect();

    await client.send("Page.enable");
    await client.send("Runtime.enable");
    await client.send("DOM.enable");
    await client.send("Emulation.setDeviceMetricsOverride", {
      width: 1440,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false,
    });

    // Test live Cloudflare tunnel URL
    console.log("\n=== 1. Loading https://ranger-tons-delivered-wayne.trycloudflare.com/ ===");
    await client.send("Page.navigate", { url: "https://ranger-tons-delivered-wayne.trycloudflare.com/" });

    // Wait up to 15 seconds for React to mount .app-header
    console.log("Waiting for app-header to mount...");
    const startMount = Date.now();
    let mounted = false;
    while (Date.now() - startMount < 15000) {
      try {
        mounted = await client.evaluate("!!document.querySelector('.app-header')");
        if (mounted) break;
      } catch {}
      await sleep(300);
    }
    console.log("Mounted:", mounted, "after", Date.now() - startMount, "ms");

    const title = await client.evaluate("document.title");
    console.log("Page title:", title);

    // Check Header rendering
    const headerCheck = await client.evaluate(`
      (() => {
        const header = document.querySelector('.app-header');
        const nav = document.querySelector('.top-nav');
        const tabs = Array.from(document.querySelectorAll('.top-nav a')).map(a => a.innerText.trim());
        const selects = Array.from(document.querySelectorAll('.header-select select')).map(s => s.value);
        return {
          headerH: header ? Math.round(header.getBoundingClientRect().height) : 0,
          tabs,
          selects
        };
      })()
    `);
    console.log("Header check:", JSON.stringify(headerCheck, null, 2));

    const overviewPanelsCheck = await client.evaluate(`
      (() => {
        return {
          hasPerformancePanel: !!document.querySelector('.performance-panel'),
          hasScenarioPanel: !!document.querySelector('.scenario-panel'),
          hasDiagnosticsPanel: !!document.querySelector('.diagnostics-panel'),
          hasRiskSummaryEngine: !!document.getElementById('risk-summary-engine'),
          hasDataStatus: !!document.querySelector('.data-status'),
          hasSettingsMenu: !!document.querySelector('.settings-menu')
        };
      })()
    `);
    console.log("Overview panels check:", JSON.stringify(overviewPanelsCheck, null, 2));

    await client.screenshot("verify_1_overview_desktop.png");

    // 2. Check Overview Teasers
    console.log("\n=== 2. Testing Overview Teasers ===");
    const teaserTexts = await client.evaluate(`
      Array.from(document.querySelectorAll('.overview-allocation-teaser, .overview-compare-teaser')).map(t => ({
        text: t.innerText.replace(/\\n/g, ' '),
        linkText: t.querySelector('a')?.innerText,
        href: t.querySelector('a')?.getAttribute('href')
      }))
    `);
    console.log("Overview teasers:", JSON.stringify(teaserTexts, null, 2));

    // Click "Explore allocation" teaser
    console.log("Clicking 'Explore allocation' teaser...");
    await client.evaluate(`document.querySelector('.overview-allocation-teaser a')?.click()`);
    await sleep(800);
    console.log("Current URL after teaser click:", await client.evaluate("window.location.href"));
    await client.screenshot("verify_2_allocation_from_teaser.png");

    // 3. Test Stress Lab page
    console.log("\n=== 3. Testing Stress Lab Page ===");
    await client.evaluate(`
      (() => {
        const a = Array.from(document.querySelectorAll('.top-nav a')).find(el => el.getAttribute('href')?.includes('page=stresslab'));
        if (a) a.click();
      })()
    `);
    await sleep(1000);
    console.log("Current URL:", await client.evaluate("window.location.href"));

    // Select Custom Scenario
    console.log("Selecting Custom Scenario...");
    await client.evaluate(`
      (() => {
        const btns = Array.from(document.querySelectorAll('.scenario-choice'));
        const custom = btns.find(b => b.innerText.includes('Custom scenario'));
        if (custom) custom.click();
      })()
    `);
    await sleep(600);

    // Run Full Quantitative Engine
    console.log("Running Full Quantitative Engine in Stress Lab...");
    await client.evaluate(`
      (() => {
        const btn = document.querySelector('.api-run-button');
        if (btn) btn.click();
      })()
    `);
    await sleep(3000);

    const stressResult = await client.evaluate(`
      (() => {
        const error = document.querySelector('.api-error')?.innerText;
        const summary = document.querySelector('.api-summary-grid');
        const trades = document.querySelectorAll('.rebalance-list li');
        const adoptBtn = document.querySelector('.api-risk-panel .action-button.primary');
        return {
          hasError: !!error,
          errorText: error,
          hasSummary: !!summary,
          tradesCount: trades.length,
          hasAdoptBtn: !!adoptBtn,
          adoptBtnText: adoptBtn?.innerText?.trim()
        };
      })()
    `);
    console.log("Stress Lab simulation result:", JSON.stringify(stressResult, null, 2));
    await client.screenshot("verify_3_stresslab_ran.png");

    // 4. Test Compare page
    console.log("\n=== 4. Testing Compare Page ===");
    await client.evaluate(`
      (() => {
        const a = Array.from(document.querySelectorAll('.top-nav a')).find(el => el.getAttribute('href')?.includes('page=compare'));
        if (a) a.click();
      })()
    `);
    await sleep(1000);

    const compareState = await client.evaluate(`
      (() => {
        const adoptBtn = document.querySelector('.alternative-editor .action-button.primary');
        const submitBtn = document.querySelector('.custom-controls .action-button.primary, .scenario-panel .action-button.primary');
        const rows = Array.from(document.querySelectorAll('.comparison-table tbody tr')).map(r => ({
          measure: r.querySelector('th')?.innerText,
          current: r.querySelectorAll('td')[0]?.innerText,
          alt: r.querySelectorAll('td')[1]?.innerText
        }));
        return {
          hasAdoptBtn: !!adoptBtn,
          adoptBtnText: adoptBtn?.innerText?.trim(),
          submitBtnText: submitBtn?.innerText?.trim(),
          rowsCount: rows.length,
          rows: rows.slice(0, 4)
        };
      })()
    `);
    console.log("Compare page state:", JSON.stringify(compareState, null, 2));
    await client.screenshot("verify_4_compare.png");

    // Test clicking Adopt Alternative
    console.log("Clicking 'Adopt Alternative as Live Portfolio' on Compare page...");
    await client.evaluate(`document.querySelector('.alternative-editor .action-button.primary')?.click()`);
    await sleep(600);

    // 5. Test Butterfly Contagion page
    console.log("\n=== 5. Testing Butterfly Contagion Page ===");
    await client.evaluate(`
      (() => {
        const a = Array.from(document.querySelectorAll('.top-nav a')).find(el => el.getAttribute('href')?.includes('page=butterfly'));
        if (a) a.click();
      })()
    `);
    await sleep(1000);

    console.log("Running Contagion Simulation...");
    await client.evaluate(`document.querySelector('.butterfly-controls button[type="submit"]')?.click()`);
    await sleep(2500);

    const butterflyState = await client.evaluate(`
      (() => {
        const cards = Array.from(document.querySelectorAll('.api-contagion-summary > div')).map(d => ({
          label: d.querySelector('span')?.innerText,
          val: d.querySelector('strong')?.innerText?.replace(/\\n/g, ' ')
        }));
        const stages = document.querySelectorAll('.cascade-stage').length;
        return { cards, stages };
      })()
    `);
    console.log("Butterfly contagion cards:", JSON.stringify(butterflyState, null, 2));
    await client.screenshot("verify_5_butterfly_ran.png");

    // 6. Test Reverse Stress Test page
    console.log("\n=== 6. Testing Reverse Stress Test Page ===");
    await client.evaluate(`
      (() => {
        const a = Array.from(document.querySelectorAll('.top-nav a')).find(el => el.getAttribute('href')?.includes('page=reverse'));
        if (a) a.click();
      })()
    `);
    await sleep(1000);

    console.log("Running Reverse Stress Solver...");
    await client.evaluate(`document.querySelector('.reverse-controls button[type="submit"]')?.click()`);
    await sleep(2500);

    const reverseState = await client.evaluate(`
      (() => {
        const dist = document.querySelector('.reverse-distance-card strong')?.innerText;
        const prob = document.querySelectorAll('.reverse-distance-card strong')[1]?.innerText;
        const rows = document.querySelectorAll('.fragility-table tbody tr').length;
        const targetVal = document.querySelector('.reverse-target-value')?.innerText;
        return { dist, prob, rows, targetVal };
      })()
    `);
    console.log("Reverse stress state:", JSON.stringify(reverseState, null, 2));
    await client.screenshot("verify_6_reverse_ran.png");

    // 7. Test News Intelligence page
    console.log("\n=== 7. Testing News Intelligence Page ===");
    await client.evaluate(`
      (() => {
        const a = Array.from(document.querySelectorAll('.top-nav a')).find(el => el.getAttribute('href')?.includes('page=news'));
        if (a) a.click();
      })()
    `);
    await sleep(1000);

    // Test clicking news headline
    console.log("Clicking headline of first news article...");
    await client.evaluate(`document.querySelector('.news-widget__story-headline')?.click()`);
    await sleep(600);

    const newsSidebarState = await client.evaluate(`
      (() => {
        const sidebar = document.querySelector('.news-widget__scenario-card');
        const triggerBtn = document.querySelector('.news-widget__launch-stresslab-btn');
        return {
          hasCard: !!sidebar,
          triggerBtnText: triggerBtn?.innerText?.replace(/\\n/g, ' '),
          mappedScenario: document.querySelector('.news-widget__scenario-mapped')?.innerText
        };
      })()
    `);
    console.log("News selected catalyst state:", JSON.stringify(newsSidebarState, null, 2));
    await client.screenshot("verify_7_news_catalyst.png");

    // Click "Model Catalyst in Stress Lab" button
    console.log("Clicking 'Model Catalyst in Stress Lab' button...");
    await client.evaluate(`document.querySelector('.news-widget__launch-stresslab-btn')?.click()`);
    await sleep(1200);
    console.log("URL after clicking Model Catalyst in Stress Lab:", await client.evaluate("window.location.href"));
    await client.screenshot("verify_8_stresslab_from_news.png");

    // 8. Test Light Mode Theme
    console.log("\n=== 8. Testing Light Mode Header & Dashboard ===");
    await client.evaluate(`document.querySelector('.theme-toggle-btn')?.click()`);
    await sleep(800);

    const lightModeCheck = await client.evaluate(`
      (() => {
        const header = document.querySelector('.app-header');
        const brand = document.querySelector('.brand-name');
        const csHeader = window.getComputedStyle(header);
        const csBrand = window.getComputedStyle(brand);
        return {
          themeAttr: document.querySelector('main.aperture-app')?.getAttribute('data-theme'),
          headerBg: csHeader.backgroundColor,
          brandColor: csBrand.color
        };
      })()
    `);
    console.log("Light mode header check:", JSON.stringify(lightModeCheck, null, 2));
    await client.screenshot("verify_9_light_mode.png");

    // 9. Test Mobile Viewport (375x667)
    console.log("\n=== 9. Testing Mobile Viewport (375x667) ===");
    await client.send("Emulation.setDeviceMetricsOverride", {
      width: 375,
      height: 667,
      deviceScaleFactor: 2,
      mobile: true,
    });
    await sleep(800);

    const mobileCheck = await client.evaluate(`
      (() => {
        return {
          docScrollW: document.documentElement.scrollWidth,
          docClientW: document.documentElement.clientWidth,
          hasHScroll: document.documentElement.scrollWidth > document.documentElement.clientWidth
        };
      })()
    `);
    console.log("Mobile viewport overflow:", JSON.stringify(mobileCheck, null, 2));
    await client.screenshot("verify_10_mobile_viewport.png");

    console.log("\n=== Final Console Errors & Exceptions ===");
    console.log("Console errors count:", client.consoleErrors.length, client.consoleErrors);
    console.log("Runtime exceptions count:", client.exceptions.length, client.exceptions);

    client.close();
  } finally {
    browser.kill();
    process.exit(0);
  }
}

verify().catch((err) => {
  console.error(err);
  process.exit(1);
});
