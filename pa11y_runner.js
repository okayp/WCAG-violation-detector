const pa11y = require('pa11y');
const fs = require('fs');

(async () => {
const url = "https://katalysttech.com/";

  const results = await pa11y(url, {
    standard: 'WCAG2AAA',
    includeWarnings: true,
    includeNotices: true,
    chromeLaunchConfig: {
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
  });

  // Save full raw JSON output
  fs.writeFileSync('pa11y_output.json', JSON.stringify(results, null, 2));
  console.log('✅ Pa11y results saved to pa11y_output.json');

  // Optionally also log to console (processed form)
  const simplified = results.issues.map(issue => ({
    code: issue.code,
    message: issue.message,
    selector: issue.selector,
    context: issue.context,
    type: issue.type
  }));

  console.log(JSON.stringify(simplified, null, 2));
})();
