const vscode = require('vscode');
const { FrameViewSession } = require('./frame-view-session');

let outputChannel = null;
const frameSessions = new Map();

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
            session.reveal();
            await session.refresh();
        } catch (error) {
            outputChannel.show(true);
            if (!error || !error.horseyErrorNotified) {
                vscode.window.showErrorMessage(`Horsey Viewer error: ${error.message}`);
            }
        }
    });

    context.subscriptions.push(disposable);

    const screenshotDisposable = vscode.commands.registerCommand(
        'horsey-viewer.captureRenderedScreenshot',
        async (options = {}) => {
            const targetFilePath =
                typeof options.filePath === 'string' && options.filePath
                    ? options.filePath
                    : vscode.window.activeTextEditor && vscode.window.activeTextEditor.document
                        ? vscode.window.activeTextEditor.document.fileName
                        : null;

            if (!targetFilePath) {
                throw new Error('No target file path available for screenshot capture');
            }

            const session = frameSessions.get(targetFilePath);
            if (!session || session.isDisposed) {
                throw new Error(`No active Horsey viewer session for ${targetFilePath}`);
            }

            const timeoutMs =
                typeof options.timeoutMs === 'number' ? options.timeoutMs : undefined;
            const outputPath =
                typeof options.outputPath === 'string' && options.outputPath ? options.outputPath : undefined;

            return session.captureScreenshot({ timeoutMs, outputPath });
        }
    );

    context.subscriptions.push(screenshotDisposable);
    context.subscriptions.push({
        dispose: async () => {
            const sessions = Array.from(frameSessions.values());
            frameSessions.clear();
            await Promise.allSettled(sessions.map((session) => session.dispose()));
        },
    });
}

/**
 * Get or create a session for the given file path.
 * Reuses an existing session for the same file or creates a new panel/session.
 */
async function getOrCreateSession(filePath, context) {
    const existingSession = frameSessions.get(filePath);
    if (existingSession && !existingSession.isDisposed) {
        return existingSession;
    }

    const session = new FrameViewSession(
        filePath,
        context,
        outputChannel,
        (disposedFilePath) => {
            if (frameSessions.get(disposedFilePath) === session) {
                frameSessions.delete(disposedFilePath);
            }
        }
    );
    frameSessions.set(filePath, session);
    await session.initialize();
    return session;
}

async function deactivate() {
    const sessions = Array.from(frameSessions.values());
    frameSessions.clear();
    await Promise.allSettled(sessions.map((session) => session.dispose()));
}

module.exports = {
    activate,
    deactivate,
};
