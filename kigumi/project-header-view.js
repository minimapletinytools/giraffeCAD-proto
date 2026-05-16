const vscode = require('vscode');
const { getInitializationStatus, isInitializationInProgress } = require('./project-initializer');

/**
 * WebviewView provider that renders the Kigumi project header as a real
 * HTML button with a progress indicator. Replaces the previous tree-based
 * "[ Initialize Current Project ]" row in the sidebar.
 */
class KigumiProjectHeaderProvider {
    /**
     * @param {vscode.ExtensionContext} context
     * @param {{ getWorkspaceRoot: () => string | null, getActivePythonFilePath: () => string | null, runInitialize: () => Promise<void> }} options
     */
    constructor(context, options) {
        this.context = context;
        this.options = options;
        this._view = null;
        this._initializing = false;
    }

    resolveWebviewView(webviewView, _context, _token) {
        this._view = webviewView;
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [],
        };
        webviewView.webview.html = this._getHtml(webviewView.webview);

        webviewView.webview.onDidReceiveMessage(async (message) => {
            if (!message || typeof message.type !== 'string') {
                return;
            }
            if (message.type === 'ready') {
                this.update();
                return;
            }
            if (message.type === 'initialize') {
                await this._handleInitializeRequest();
            }
        });

        webviewView.onDidChangeVisibility(() => {
            if (webviewView.visible) {
                this.update();
            }
        });
    }

    /**
     * Push the current status to the webview.
     */
    update() {
        if (!this._view) {
            return;
        }
        const status = this._computeStatus();
        void this._view.webview.postMessage({ type: 'status', payload: status });
    }

    setInitializing(initializing) {
        this._initializing = !!initializing;
        this.update();
    }

    _computeStatus() {
        const workspaceRoot = this.options.getWorkspaceRoot();
        const activeFilePath = this.options.getActivePythonFilePath();
        const initializing = this._initializing || isInitializationInProgress();

        if (!workspaceRoot && !activeFilePath) {
            return {
                phase: 'no-workspace',
                title: 'No Workspace',
                description: 'Open a folder or a Python file to initialize.',
                buttonLabel: 'Open Folder…',
                buttonAction: 'open-folder',
                buttonDisabled: false,
                initializing,
            };
        }

        const rootHint = workspaceRoot || require('path').dirname(activeFilePath);
        let initStatus;
        try {
            initStatus = getInitializationStatus(rootHint, activeFilePath);
        } catch (err) {
            return {
                phase: 'error',
                title: 'Project Status Unavailable',
                description: String(err && err.message ? err.message : err),
                buttonLabel: 'Retry',
                buttonAction: 'initialize',
                buttonDisabled: initializing,
                initializing,
            };
        }

        if (initStatus.projectStatus === 'local-dev') {
            return {
                phase: 'local-dev',
                title: 'Local Development Mode',
                description: 'Workspace is the Kumiki source; initialization is disabled.',
                buttonLabel: null,
                buttonAction: null,
                buttonDisabled: true,
                initializing: false,
            };
        }

        if (initStatus.isInitialized) {
            return {
                phase: 'initialized',
                title: 'Project Initialized',
                description: '.kigumi config and .venv are ready.',
                buttonLabel: null,
                buttonAction: null,
                buttonDisabled: true,
                initializing: false,
            };
        }

        if (initStatus.hasExistingProject) {
            return {
                phase: 'partial',
                title: 'Finish Project Setup',
                description: 'Project files detected — finish setup to enable rendering.',
                buttonLabel: initializing ? 'Initializing…' : 'Finish Setup',
                buttonAction: 'initialize',
                buttonDisabled: initializing,
                initializing,
            };
        }

        return {
            phase: 'uninitialized',
            title: 'Initialize Kigumi Project',
            description: 'Create .kigumi config and .venv in the current workspace.',
            buttonLabel: initializing ? 'Initializing…' : 'Initialize Project',
            buttonAction: 'initialize',
            buttonDisabled: initializing,
            initializing,
        };
    }

    async _handleInitializeRequest() {
        if (this._initializing || isInitializationInProgress()) {
            this.update();
            return;
        }
        this._initializing = true;
        this.update();
        try {
            await this.options.runInitialize();
        } finally {
            this._initializing = false;
            this.update();
        }
    }

    _getHtml(webview) {
        const nonce = _generateNonce();
        const csp = [
            "default-src 'none'",
            `style-src ${webview.cspSource} 'unsafe-inline'`,
            `script-src 'nonce-${nonce}'`,
        ].join('; ');

        return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta http-equiv="Content-Security-Policy" content="${csp}" />
<style>
    body {
        margin: 0;
        padding: 10px 12px;
        font-family: var(--vscode-font-family);
        font-size: var(--vscode-font-size);
        color: var(--vscode-foreground);
    }
    .header-title {
        font-weight: 600;
        margin-bottom: 2px;
    }
    .header-description {
        opacity: 0.75;
        margin-bottom: 8px;
        font-size: 0.92em;
        line-height: 1.3;
    }
    button.init-button {
        display: block;
        width: 100%;
        padding: 6px 10px;
        border: 1px solid var(--vscode-button-border, transparent);
        background: var(--vscode-button-background);
        color: var(--vscode-button-foreground);
        font-family: var(--vscode-font-family);
        font-size: var(--vscode-font-size);
        cursor: pointer;
        border-radius: 2px;
        text-align: center;
    }
    button.init-button:hover:not(:disabled) {
        background: var(--vscode-button-hoverBackground);
    }
    button.init-button:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }
    .progress-track {
        margin-top: 8px;
        height: 3px;
        width: 100%;
        background: var(--vscode-progressBar-background, rgba(128,128,128,0.2));
        overflow: hidden;
        position: relative;
        border-radius: 2px;
        display: none;
    }
    .progress-track.active {
        display: block;
    }
    .progress-bar {
        position: absolute;
        height: 100%;
        width: 30%;
        background: var(--vscode-progressBar-background, #0e70c0);
        background: linear-gradient(90deg, transparent, var(--vscode-button-background, #0e70c0), transparent);
        animation: kigumi-progress 1.4s ease-in-out infinite;
    }
    @keyframes kigumi-progress {
        0%   { left: -30%; }
        100% { left: 100%; }
    }
    .phase-badge {
        display: inline-block;
        font-size: 0.78em;
        padding: 1px 6px;
        border-radius: 8px;
        background: var(--vscode-badge-background);
        color: var(--vscode-badge-foreground);
        margin-left: 6px;
        vertical-align: middle;
    }
</style>
</head>
<body>
    <div class="header-title" id="title">Loading…</div>
    <div class="header-description" id="description"></div>
    <button class="init-button" id="actionButton" style="display:none;"></button>
    <div class="progress-track" id="progressTrack"><div class="progress-bar"></div></div>

<script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    const titleEl = document.getElementById('title');
    const descEl = document.getElementById('description');
    const buttonEl = document.getElementById('actionButton');
    const progressEl = document.getElementById('progressTrack');

    buttonEl.addEventListener('click', () => {
        if (buttonEl.disabled) {
            return;
        }
        const action = buttonEl.dataset.action;
        if (action === 'initialize') {
            buttonEl.disabled = true;
            progressEl.classList.add('active');
            vscode.postMessage({ type: 'initialize' });
        } else if (action === 'open-folder') {
            vscode.postMessage({ type: 'open-folder' });
        }
    });

    window.addEventListener('message', (event) => {
        const msg = event.data;
        if (!msg || msg.type !== 'status') return;
        const s = msg.payload || {};
        titleEl.textContent = s.title || '';
        descEl.textContent = s.description || '';
        if (s.buttonLabel) {
            buttonEl.style.display = 'block';
            buttonEl.textContent = s.buttonLabel;
            buttonEl.disabled = !!s.buttonDisabled;
            buttonEl.dataset.action = s.buttonAction || '';
        } else {
            buttonEl.style.display = 'none';
        }
        if (s.initializing) {
            progressEl.classList.add('active');
        } else {
            progressEl.classList.remove('active');
        }
    });

    vscode.postMessage({ type: 'ready' });
</script>
</body>
</html>`;
    }
}

function _generateNonce() {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}

module.exports = {
    KigumiProjectHeaderProvider,
};
