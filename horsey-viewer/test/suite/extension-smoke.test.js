const assert = require('assert');
const vscode = require('vscode');

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
});
