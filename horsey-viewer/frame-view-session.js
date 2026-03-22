const path = require('path');
const fs = require('fs');
const vscode = require('vscode');
const { PythonRunnerSession } = require('./runner-session');
const { FileWatcher } = require('./file-watcher');
const { createFrameViewer, renderFrameViewer, requestViewerScreenshot } = require('./viewer');

const VIEWER_LOG_LEVEL_ORDER = {
    debug: 10,
    info: 20,
    warn: 30,
    error: 40,
};

// Minimum level to allow per log source. Lower levels are suppressed.
const VIEWER_LOG_SOURCE_MIN_LEVEL = {
};

function normalizeViewerLogLevel(level) {
    if (typeof level !== 'string') {
        return 'info';
    }
    const normalized = level.toLowerCase();
    if (!Object.prototype.hasOwnProperty.call(VIEWER_LOG_LEVEL_ORDER, normalized)) {
        return 'info';
    }
    return normalized;
}

function shouldSuppressViewerLog(source, level) {
    const effectiveSource = typeof source === 'string' && source ? source : 'webview';
    const incomingLevel = normalizeViewerLogLevel(level);
    const minLevel = normalizeViewerLogLevel(VIEWER_LOG_SOURCE_MIN_LEVEL[effectiveSource] || 'debug');
    return VIEWER_LOG_LEVEL_ORDER[incomingLevel] < VIEWER_LOG_LEVEL_ORDER[minLevel];
}

class FrameViewSession {
    constructor(filePath, context, channel, onDispose) {
        this.filePath = filePath;
        this.context = context;
        this.channel = channel;
        this.onDispose = onDispose;
        this.panel = null;
        this.runnerSession = null;
        this.fileWatcher = null;
        this.isDisposed = false;
        this.isRefreshing = false;
    }

    async initialize() {
        if (this.isDisposed) {
            throw new Error(`Cannot initialize disposed frame view session for ${this.filePath}`);
        }
        if (this.panel) {
            return;
        }

        this.panel = createFrameViewer(this.filePath);
        this.panel.onDidDispose(() => {
            this.panel = null;
            void this.dispose();
        });
        this.panel.webview.onDidReceiveMessage((message) => {
            if (!message || message.type !== 'viewerLog') {
                return;
            }
            const eventName = typeof message.event === 'string' ? message.event : 'unknown';
            const source = typeof message.source === 'string' ? message.source : 'webview';
            const level = normalizeViewerLogLevel(message.level);
            if (shouldSuppressViewerLog(source, level)) {
                return;
            }
            const version = typeof message.version === 'string' ? message.version : 'unknown';
            const details = message.details && typeof message.details === 'object'
                ? JSON.stringify(message.details)
                : '{}';
            this.log(`[webview:${source}:${level}] ${eventName} v${version} ${details}`);
        });
        this.log('[webview] viewer log bridge active');

        this.runnerSession = new PythonRunnerSession(this.filePath, this.context, this.channel);
        await this.runnerSession.start();

        this.fileWatcher = new FileWatcher(
            this.filePath,
            this.runnerSession.projectRoot,
            (source) => this.onFileChanged(source),
            (message) => this.log(`[watcher] ${message}`)
        );
        this.fileWatcher.start();

        this.log(`Session initialized for ${this.filePath}`);
    }

    reveal() {
        if (this.panel) {
            this.panel.reveal();
        }
    }

    async ensureRunnerSession() {
        if (this.isDisposed) {
            throw new Error(`Session is disposed for ${this.filePath}`);
        }

        if (this.runnerSession && this.runnerSession.isAlive()) {
            return;
        }

        if (this.runnerSession) {
            try {
                await this.runnerSession.dispose();
            } catch (error) {
                this.log(`[runner] dispose after failure: ${error.message || error}`);
            }
        }

        this.log(`[runner] Restarting Python runner for ${path.basename(this.filePath)}`);
        this.runnerSession = new PythonRunnerSession(this.filePath, this.context, this.channel);
        await this.runnerSession.start();
    }

    async refresh(reason = 'manual render') {
        if (this.isDisposed) {
            return;
        }
        if (this.isRefreshing) {
            this.log(`[refresh] Skipping overlapping refresh for ${this.filePath}`);
            return;
        }

        this.isRefreshing = true;
        this.log(`[refresh] Reloading ${path.basename(this.filePath)} (${reason})`);
        try {
            await this.ensureRunnerSession();
            const reloadResult = await this.runnerSession.request('reload_example', { filePath: this.filePath });
            const frameData = await this.runnerSession.request('get_frame');
            const geometryData = await this.runnerSession.request('get_geometry');
            const profiling = {
                reload_s: reloadResult && reloadResult.profiling ? reloadResult.profiling.reload_s : null,
                geometry_s: geometryData && geometryData.profiling ? geometryData.profiling.geometry_s : null,
            };
            renderFrameViewer(this.panel, this.filePath, frameData, geometryData, profiling);
            this.log(`[refresh] Reload complete for ${path.basename(this.filePath)}`);
        } catch (error) {
            await this.reportRunnerError(error, `[refresh] ${path.basename(this.filePath)} (${reason})`);
            throw error;
        } finally {
            this.isRefreshing = false;
        }
    }

    async captureScreenshot(options = {}) {
        if (this.isDisposed || !this.panel) {
            throw new Error(`Viewer panel is not available for ${this.filePath}`);
        }

        const timeoutMs = typeof options.timeoutMs === 'number' ? options.timeoutMs : 8000;
        const result = await requestViewerScreenshot(this.panel, { timeoutMs });

        const dataUrl = result.dataUrl || '';
        const match = /^data:image\/png;base64,(.+)$/u.exec(dataUrl);
        if (!match) {
            throw new Error('Screenshot payload is not a PNG data URL');
        }

        const imageBuffer = Buffer.from(match[1], 'base64');
        if (options.outputPath) {
            fs.mkdirSync(path.dirname(options.outputPath), { recursive: true });
            fs.writeFileSync(options.outputPath, imageBuffer);
            this.log(`[screenshot] Wrote ${options.outputPath}`);
        }

        return {
            outputPath: options.outputPath || null,
            byteLength: imageBuffer.length,
            width: result.width,
            height: result.height,
        };
    }

    async onFileChanged(source) {
        if (this.isDisposed) {
            return;
        }

        this.log(`[watcher] Auto-reloading due to ${source} change...`);
        try {
            await this.refresh(`${source} change`);
        } catch (error) {
            this.log(`[watcher] Auto-reload failed for ${path.basename(this.filePath)}: ${error.message || error}`);
        }
    }

    extractRunnerErrorDetails(error) {
        const payload = error && error.runnerError && typeof error.runnerError === 'object'
            ? error.runnerError
            : null;
        const message = payload && typeof payload.message === 'string'
            ? payload.message
            : (error && error.message ? error.message : String(error));
        const traceback = payload && typeof payload.traceback === 'string'
            ? payload.traceback
            : (error && typeof error.runnerTraceback === 'string' ? error.runnerTraceback : null);
        const type = payload && typeof payload.type === 'string'
            ? payload.type
            : (error && typeof error.runnerErrorType === 'string' ? error.runnerErrorType : null);
        return { message, traceback, type };
    }

    parseTracebackLocation(traceback) {
        if (!traceback || typeof traceback !== 'string') {
            return null;
        }
        const fileLineRegex = /File "([^"]+)", line (\d+)/g;
        const candidates = [];
        let match = fileLineRegex.exec(traceback);
        while (match) {
            candidates.push({ filePath: match[1], lineNumber: Number(match[2]) });
            match = fileLineRegex.exec(traceback);
        }
        for (let index = candidates.length - 1; index >= 0; index -= 1) {
            const candidate = candidates[index];
            if (candidate.filePath && fs.existsSync(candidate.filePath) && Number.isFinite(candidate.lineNumber)) {
                return candidate;
            }
        }
        return null;
    }

    async openTracebackLocation(location) {
        if (!location) {
            return;
        }
        try {
            const uri = vscode.Uri.file(location.filePath);
            const document = await vscode.workspace.openTextDocument(uri);
            const editor = await vscode.window.showTextDocument(document, { preview: false });
            const lineIndex = Math.max(0, location.lineNumber - 1);
            const range = new vscode.Range(lineIndex, 0, lineIndex, 0);
            editor.selection = new vscode.Selection(range.start, range.end);
            editor.revealRange(range, vscode.TextEditorRevealType.InCenter);
        } catch (openError) {
            this.log(`[error] Failed to open traceback location: ${openError.message || openError}`);
        }
    }

    async reportRunnerError(error, contextLabel) {
        const details = this.extractRunnerErrorDetails(error);
        const errorTypePart = details.type ? `${details.type}: ` : '';
        this.log(`[error] ${contextLabel} -> ${errorTypePart}${details.message}`);

        if (details.traceback) {
            this.channel.appendLine(`[${path.basename(this.filePath)}] [traceback] BEGIN`);
            for (const tracebackLine of details.traceback.split('\n')) {
                this.channel.appendLine(`[${path.basename(this.filePath)}] ${tracebackLine}`);
            }
            this.channel.appendLine(`[${path.basename(this.filePath)}] [traceback] END`);
        }

        this.channel.show(true);
        const location = this.parseTracebackLocation(details.traceback);
        const actions = ['Open Horsey Output'];
        if (location) {
            actions.push('Go to Error');
        }

        const choice = await vscode.window.showErrorMessage(
            `Horsey Viewer Python error: ${details.message}`,
            ...actions
        );

        if (choice === 'Open Horsey Output') {
            this.channel.show(true);
        }
        if (choice === 'Go to Error' && location) {
            await this.openTracebackLocation(location);
        }

        if (error && typeof error === 'object') {
            error.horseyErrorNotified = true;
        }
    }

    async dispose() {
        if (this.isDisposed) {
            return;
        }
        this.isDisposed = true;

        this.log(`Disposing session for ${this.filePath}`);

        if (this.fileWatcher) {
            this.fileWatcher.dispose();
            this.fileWatcher = null;
        }

        if (this.runnerSession) {
            await this.runnerSession.dispose();
            this.runnerSession = null;
        }

        if (this.panel) {
            const panel = this.panel;
            this.panel = null;
            panel.dispose();
        }

        if (this.onDispose) {
            this.onDispose(this.filePath);
        }
    }

    log(message) {
        this.channel.appendLine(`[${path.basename(this.filePath)}] ${message}`);
    }
}

module.exports = { FrameViewSession };
