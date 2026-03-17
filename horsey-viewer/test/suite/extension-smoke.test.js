const assert = require('assert');
const path = require('path');
const vscode = require('vscode');

async function waitFor(condition, timeoutMs = 12000, intervalMs = 100) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (condition()) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error(`Timed out waiting for condition after ${timeoutMs}ms`);
}

function getAllTabs() {
  return vscode.window.tabGroups.all.flatMap((group) => group.tabs);
}

describe('Horsey Viewer extension smoke', () => {
  it('registers the Render Horsey command', async () => {
    const extension = vscode.extensions.all.find((candidate) =>
      candidate.id.toLowerCase().endsWith('.horsey-viewer')
    );
    assert.ok(extension, 'Expected Horsey Viewer extension to be available in Extension Host');

    await extension.activate();

    const commands = await vscode.commands.getCommands(true);
    assert.ok(commands.includes('horsey-viewer.renderHorsey'));
  });

  it('executes Render Horsey command without crashing when no editor is active', async () => {
    await vscode.commands.executeCommand('workbench.action.closeAllEditors');
    await assert.doesNotReject(async () => {
      await vscode.commands.executeCommand('horsey-viewer.renderHorsey');
    });
  });

  it('opens fixture and renders Horsey webview panel with frame name', async function () {
    this.timeout(30000);

    const fixturePath = path.resolve(__dirname, '..', '..', 'test-fixtures', 'minimal_frame.py');
    const fixtureUri = vscode.Uri.file(fixturePath);

    await vscode.commands.executeCommand('workbench.action.closeAllEditors');
    const document = await vscode.workspace.openTextDocument(fixtureUri);
    await vscode.window.showTextDocument(document, { preview: false });

    await vscode.commands.executeCommand('horsey-viewer.renderHorsey');

    await waitFor(() => {
      const tabs = getAllTabs();
      return tabs.some((tab) => tab.label === 'Horsey: minimal_frame.py (Runner Test Frame)');
    }, 20000, 120);

    const tabs = getAllTabs();
    assert.ok(
      tabs.some((tab) => tab.label === 'Horsey: minimal_frame.py (Runner Test Frame)'),
      'Expected Horsey webview tab for minimal_frame.py with rendered frame name'
    );
  });
});
