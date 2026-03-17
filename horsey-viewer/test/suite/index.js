const path = require('path');
const Mocha = require('mocha');

async function run() {
  const mocha = new Mocha({
    ui: 'bdd',
    color: true,
    timeout: 30000,
  });

  const testFile = path.resolve(__dirname, 'extension-smoke.test.js');
  mocha.addFile(testFile);

  return new Promise((resolve, reject) => {
    mocha.run((failures) => {
      if (failures > 0) {
        reject(new Error(`${failures} extension test(s) failed.`));
        return;
      }
      resolve();
    });
  });
}

module.exports = { run };
