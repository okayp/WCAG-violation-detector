const puppeteer = require('puppeteer');
const fs = require('fs');
const axeSource = require('axe-core').source;

(async () => {
const url = "https://katalysttech.com/";

  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  // Go to the page and wait for network to settle
  await page.goto(url, { waitUntil: 'networkidle0' });

  // Inject axe-core into the page
  await page.evaluate(axeSource);

  // Run axe-core
  const results = await page.evaluate(async () => {
    return await axe.run(document, {
      runOnly: {
        type: 'tag',
        values: ['wcag2a', 'wcag2aa', 'wcag2aaa']
      }
    });
  });

  // Save violations to JSON
  const simplified = results.violations.map(v => {
    return v.nodes.map(n => ({
      rule: v.id,
      impact: v.impact,
      help: v.help,
      helpUrl: v.helpUrl,
      html: n.html,
      selector: n.target.join(' '),
      failureSummary: n.failureSummary
    }));
  }).flat();

  fs.writeFileSync('axe_report.json', JSON.stringify({ url, violations: simplified }, null, 2));

  console.log("✅ Axe accessibility report saved to axe_report.json");

  await browser.close();
})();
