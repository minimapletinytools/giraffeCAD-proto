/**
 * FileWatcher — Manages file system watchers for auto-reloading frames on save.
 *
 * Watches:
 * 1. The example file itself (always)
 * 2. The code_goes_here library tree (optional, local dev only)
 *
 * Debounces rapid file changes and notifies via callback.
 */

const vscode = require('vscode');
const path = require('path');
const fs = require('fs');

class FileWatcher {
    constructor(exampleFilePath, projectRoot, onChangeCallback) {
        this.exampleFilePath = exampleFilePath;
        this.projectRoot = projectRoot;
        this.onChangeCallback = onChangeCallback;
        this.watchers = [];
        this.debounceTimer = null;
        this.debounceDelay = 300; // ms
        this.isDisposed = false;
    }

    /**
     * Start watching the example file and optionally the code_goes_here library.
     */
    start() {
        if (this.isDisposed) {
            return;
        }

        // Watch the example file itself
        this.watchExampleFile();

        // Watch code_goes_here library (local dev only)
        if (this.projectRoot && this.hasLocalCodeGoesHere()) {
            this.watchLibrary();
        }
    }

    /**
     * Check if code_goes_here exists under the project root (local checkout detection).
     */
    hasLocalCodeGoesHere() {
        if (!this.projectRoot) {
            return false;
        }
        return fs.existsSync(path.join(this.projectRoot, 'code_goes_here'));
    }

    /**
     * Create a watcher for the example file.
     */
    watchExampleFile() {
        const watcher = vscode.workspace.createFileSystemWatcher(this.exampleFilePath);

        watcher.onDidChange(() => {
            this.logChange(`Example file changed: ${this.exampleFilePath}`);
            this.debounceReload('example file');
        });

        watcher.onDidCreate(() => {
            this.logChange(`Example file created: ${this.exampleFilePath}`);
            this.debounceReload('example file');
        });

        watcher.onDidDelete(() => {
            this.logChange(`Example file deleted: ${this.exampleFilePath}`);
            this.debounceReload('example file');
        });

        this.watchers.push(watcher);
    }

    /**
     * Create a watcher for the code_goes_here library tree.
     */
    watchLibrary() {
        const pattern = new vscode.RelativePattern(this.projectRoot, 'code_goes_here/**/*.py');
        const watcher = vscode.workspace.createFileSystemWatcher(pattern);

        watcher.onDidChange(() => {
            this.logChange('Library file changed');
            this.debounceReload('library file');
        });

        watcher.onDidCreate(() => {
            this.logChange('Library file created');
            this.debounceReload('library file');
        });

        watcher.onDidDelete(() => {
            this.logChange('Library file deleted');
            this.debounceReload('library file');
        });

        this.watchers.push(watcher);
    }

    /**
     * Debounce the reload callback. Multiple rapid changes collapse into one reload.
     */
    debounceReload(source) {
        if (this.isDisposed) {
            return;
        }

        if (this.debounceTimer !== null) {
            clearTimeout(this.debounceTimer);
        }

        this.debounceTimer = setTimeout(() => {
            if (!this.isDisposed && this.onChangeCallback) {
                this.onChangeCallback(source);
            }
            this.debounceTimer = null;
        }, this.debounceDelay);
    }

    /**
     * Log a change event to console (for testing and debugging).
     */
    logChange(message) {
        if (this.isDisposed) {
            return;
        }
        // Intentionally minimal logging here; callers can add output channel logging
    }

    /**
     * Stop all watchers and clean up.
     */
    dispose() {
        this.isDisposed = true;

        if (this.debounceTimer !== null) {
            clearTimeout(this.debounceTimer);
            this.debounceTimer = null;
        }

        for (const watcher of this.watchers) {
            watcher.dispose();
        }
        this.watchers = [];
    }
}

module.exports = { FileWatcher };
