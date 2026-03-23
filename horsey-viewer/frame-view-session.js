const path = require('path');
const fs = require('fs');
const vscode = require('vscode');
const { PythonRunnerSession } = require('./runner-session');
const { FileWatcher } = require('./file-watcher');
const { createFrameViewer, initializeFrameViewer, renderFrameViewer, requestViewerScreenshot } = require('./viewer');

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
        this.pendingRefreshReason = null;
    }

    getRefreshStatsPath() {
        const projectRoot = this.runnerSession && this.runnerSession.projectRoot
            ? this.runnerSession.projectRoot
            : path.dirname(this.filePath);
        return path.join(projectRoot, '.horsey', 'refresh-stats.json');
    }

    postLoadingStatus(stage, details = {}) {
        if (!this.panel) {
            return;
        }
        this.panel.webview.postMessage({
            type: 'loadingStatus',
            stage,
            details,
        }).catch((error) => {
            this.log(`[webview] Failed to post loading status '${stage}': ${error.message || error}`);
        });
    }

    writeRefreshStats(statsPayload) {
        try {
            const outputPath = this.getRefreshStatsPath();
            fs.mkdirSync(path.dirname(outputPath), { recursive: true });
            fs.writeFileSync(outputPath, `${JSON.stringify(statsPayload, null, 2)}\n`, 'utf8');
            return outputPath;
        } catch (error) {
            this.log(`[refresh] Failed to write stats JSON: ${error.message || error}`);
            return null;
        }
    }

    async initialize() {
        if (this.isDisposed) {
            throw new Error(`Cannot initialize disposed frame view session for ${this.filePath}`);
        }
        if (this.panel) {
            return;
        }

        this.panel = createFrameViewer(this.filePath);
        initializeFrameViewer(this.panel, this.filePath, { loadingText: 'initial creation' });
        this.panel.onDidDispose(() => {
            this.panel = null;
            void this.dispose();
        });
        this.panel.webview.onDidReceiveMessage((message) => {
            if (!message) {
                return;
            }
            if (message.type === 'requestRefresh') {
                this.log('[webview] Manual refresh requested from viewer');
                this.onFileChanged('manual refresh button');
                return;
            }
            if (message.type !== 'viewerLog') {
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
        this.postLoadingStatus('initial creation', { reason: 'session initialize' });

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
            this.pendingRefreshReason = reason;
            this.log(`[refresh] Queuing pending refresh for ${this.filePath} (${reason})`);
            return;
        }

        this.isRefreshing = true;
        this.pendingRefreshReason = null;
        this.log(`[refresh] Reloading ${path.basename(this.filePath)} (${reason})`);
        this.postLoadingStatus('initial creation', { reason });
        let refreshError = null;
        try {
            const refreshStartNs = process.hrtime.bigint();
            await this.ensureRunnerSession();
            const reloadResult = await this.runnerSession.request('reload_example', { filePath: this.filePath });
            const frameData = await this.runnerSession.request('get_frame');
            const geometryData = await this.runnerSession.request('get_geometry');
            const refresh_total_s = Number(process.hrtime.bigint() - refreshStartNs) / 1e9;

            const changedKeys = Array.isArray(geometryData && geometryData.changedKeys) ? geometryData.changedKeys : [];
            const removedKeys = Array.isArray(geometryData && geometryData.removedKeys) ? geometryData.removedKeys : [];
            const meshes = Array.isArray(geometryData && geometryData.meshes) ? geometryData.meshes : [];
            const remeshMetrics = Array.isArray(geometryData && geometryData.remeshMetrics) ? geometryData.remeshMetrics : [];
            const totalTimbers = geometryData && geometryData.counts && Number.isFinite(geometryData.counts.totalTimbers)
                ? geometryData.counts.totalTimbers
                : meshes.length;

            const refreshStatsPayload = {
                timestamp: new Date().toISOString(),
                sourceFile: this.filePath,
                reason,
                refresh: {
                    scriptReloadDuration_ms: reloadResult && reloadResult.profiling && typeof reloadResult.profiling.reload_s === 'number'
                        ? Math.round(reloadResult.profiling.reload_s * 1000)
                        : null,
                    meshBuildDuration_ms: geometryData && geometryData.profiling && typeof geometryData.profiling.geometry_s === 'number'
                        ? Math.round(geometryData.profiling.geometry_s * 1000)
                        : null,
                    totalRefreshDuration_ms: Math.round(refresh_total_s * 1000),
                    changedTimberCount: changedKeys.length,
                    removedTimberCount: removedKeys.length,
                    totalTimberCount: totalTimbers,
                    changedTimberKeys: changedKeys,
                    removedTimberKeys: removedKeys,
                    perTimberMetrics: remeshMetrics.map((entry) => ({
                        timberKey: entry.timberKey,
                        remeshDuration_ms: typeof entry.remesh_s === 'number' ? Math.round(entry.remesh_s * 1000) : null,
                        csgDepth: typeof entry.csg_depth === 'number' ? entry.csg_depth : null,
                        triangleCount: typeof entry.triangle_count === 'number' ? entry.triangle_count : null,
                    })),
                },
            };

            const statsPath = this.writeRefreshStats(refreshStatsPayload);
            const profiling = {
                reload_s: reloadResult && reloadResult.profiling ? reloadResult.profiling.reload_s : null,
                geometry_s: geometryData && geometryData.profiling ? geometryData.profiling.geometry_s : null,
                refresh_total_s,
                changed_timbers: changedKeys.length,
                removed_timbers: removedKeys.length,
                total_timbers: totalTimbers,
                remesh_metrics: remeshMetrics,
                stats_path: statsPath,
            };
            renderFrameViewer(this.panel, this.filePath, frameData, geometryData, profiling);
            this.log(`[refresh] Reload complete for ${path.basename(this.filePath)}`);
        } catch (error) {
            refreshError = error;
        } finally {
            this.isRefreshing = false;
        }

        // Drain pending refresh before blocking on error reporting
        if (this.pendingRefreshReason) {
            const pendingReason = this.pendingRefreshReason;
            this.pendingRefreshReason = null;
            this.log(`[refresh] Draining pending refresh (${pendingReason})`);
            // Fire-and-forget so it doesn't block error reporting
            this.refresh(pendingReason).catch((err) => {
                this.log(`[refresh] Pending refresh failed: ${err.message || err}`);
            });
        }

        if (refreshError) {
            await this.reportRunnerError(refreshError, `[refresh] ${path.basename(this.filePath)} (${reason})`);
            throw refreshError;
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
