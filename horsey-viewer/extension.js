const vscode = require('vscode');
const { PythonRunnerSession } = require('./runner-session');
const { FileWatcher } = require('./file-watcher');
const { showFrameViewer } = require('./viewer');

let runnerSession = null;
let outputChannel = null;
let fileWatcher = null;

/**
 * Main activation function for the Horsey Viewer extension.
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
    outputChannel = vscode.window.createOutputChannel('Horsey Viewer');
    context.subscriptions.push(outputChannel);

    const disposable = vscode.commands.registerCommand('horsey-viewer.renderHorsey', async function () {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active editor!');
            return;
        }

        const document = editor.document;
        if (document.languageId !== 'python') {
            vscode.window.showErrorMessage('Current file is not a Python file!');
            return;
        }

        if (document.isDirty) {
            await document.save();
        }

        const filePath = document.fileName;

        try {
            const session = await getOrCreateSession(filePath, context);
            await reloadAndRefreshFrame(session);
        } catch (error) {
            outputChannel.show(true);
            vscode.window.showErrorMessage(`Horsey Viewer error: ${error.message}`);
        }
    });

    context.subscriptions.push(disposable);
    context.subscriptions.push({
        dispose: () => {
            if (fileWatcher) {
                fileWatcher.dispose();
                fileWatcher = null;
            }
            if (runnerSession) {
                runnerSession.dispose();
                runnerSession = null;
            }
        },
    });
}

/**
 * Get or create a session for the given file path.
 * Disposes the old file watcher and creates a new one for the new session.
 */
async function getOrCreateSession(filePath, context) {
    if (runnerSession && runnerSession.filePath === filePath && runnerSession.isAlive()) {
        return runnerSession;
    }

    if (runnerSession) {
        await runnerSession.dispose();
    }

    if (fileWatcher) {
        fileWatcher.dispose();
        fileWatcher = null;
    }

    runnerSession = new PythonRunnerSession(filePath, context, outputChannel);
    await runnerSession.start();

    // Set up file watcher for auto-reload on save
    fileWatcher = new FileWatcher(
        filePath,
        runnerSession.projectRoot,
        (source) => onFileChanged(source)
    );
    fileWatcher.start();

    return runnerSession;
}

/**
 * Callback when a watched file changes.
 * Reloads the example and refreshes the viewer.
 */
async function onFileChanged(source) {
    if (!runnerSession || !runnerSession.isAlive()) {
        return;
    }

    outputChannel.appendLine(`Auto-reloading due to ${source} change...`);
    try {
        await reloadAndRefreshFrame(runnerSession);
    } catch (error) {
        outputChannel.appendLine(`Auto-reload failed: ${error.message}`);
        outputChannel.show(true);
    }
}

/**
 * Reload the example in the runner and refresh the viewer.
 */
async function reloadAndRefreshFrame(session) {
    await session.request('reload_example', { filePath: session.filePath });
    const frameData = await session.request('get_frame');
    const geometryData = await session.request('get_geometry');
    showFrameViewer(frameData, geometryData);
}

function deactivate() {
    if (fileWatcher) {
        fileWatcher.dispose();
        fileWatcher = null;
    }
    if (runnerSession) {
        runnerSession.dispose();
        runnerSession = null;
    }
}

module.exports = {
    activate,
    deactivate,
};
