const path = require('path');
const { PythonRunnerSession } = require('./runner-session');
const { FileWatcher } = require('./file-watcher');
const { createFrameViewer, renderFrameViewer } = require('./viewer');

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

    async refresh(reason = 'manual render') {
        if (this.isDisposed) {
            return;
        }
        if (!this.runnerSession || !this.runnerSession.isAlive()) {
            throw new Error(`Runner session is not available for ${this.filePath}`);
        }
        if (this.isRefreshing) {
            this.log(`[refresh] Skipping overlapping refresh for ${this.filePath}`);
            return;
        }

        this.isRefreshing = true;
        this.log(`[refresh] Reloading ${path.basename(this.filePath)} (${reason})`);
        try {
            await this.runnerSession.request('reload_example', { filePath: this.filePath });
            const frameData = await this.runnerSession.request('get_frame');
            const geometryData = await this.runnerSession.request('get_geometry');
            renderFrameViewer(this.panel, this.filePath, frameData, geometryData);
            this.log(`[refresh] Reload complete for ${path.basename(this.filePath)}`);
        } finally {
            this.isRefreshing = false;
        }
    }

    async onFileChanged(source) {
        if (this.isDisposed || !this.runnerSession || !this.runnerSession.isAlive()) {
            return;
        }

        this.log(`[watcher] Auto-reloading due to ${source} change...`);
        try {
            await this.refresh(`${source} change`);
        } catch (error) {
            this.log(`[watcher] Auto-reload failed for ${path.basename(this.filePath)}: ${error.message}`);
            this.channel.show(true);
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
