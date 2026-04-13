/**
 * PythonRunnerSession — Manages a long-lived Python runner process via stdio.
 * The runner handles loading examples, reloading on edits, and returning frame data.
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

class PythonRunnerSession {
    constructor(filePath, context, channel) {
        this.filePath = filePath;
        this.context = context;
        this.channel = channel;
        this.process = null;
        this.stdoutBuffer = '';
        this.requestId = 1;
        this.pending = new Map();
        this.startPromise = null;
        this.ready = false;
        this.onMilestone = null;
        const env = this.resolveEnvironment(filePath);
        this.projectRoot = env.projectRoot;
        this.isLocalDev = env.isLocalDev;
        this.runnerScriptPath = path.join(context.extensionPath, 'runner.py');
    }


    resolveEnvironment(filePath) {
        let candidate = path.dirname(path.resolve(filePath));
        let projectRoot = null;
        let isLocalDev = false;

        while (true) {
            if (fs.existsSync(path.join(candidate, 'giraffecad'))) {
                projectRoot = candidate;
                isLocalDev = true;
                break;
            }
            if (fs.existsSync(path.join(candidate, '.giraffe.yaml'))) {
                projectRoot = candidate;
                isLocalDev = false;
                break;
            }
            const parent = path.dirname(candidate);
            if (parent === candidate) {
                break;
            }
            candidate = parent;
        }

        if (!projectRoot) {
            // Not found, default to folder of the filePath and create .giraffe.yaml
            projectRoot = path.dirname(path.resolve(filePath));
            const envYamlPath = path.join(projectRoot, '.giraffe.yaml');
            if (!fs.existsSync(envYamlPath)) {
                fs.writeFileSync(envYamlPath, 'giraffecad_version: latest\n', 'utf8');
            }
            isLocalDev = false;
        }

        return { projectRoot, isLocalDev };
    }


    isAlive() {
        return this.process && !this.process.killed && this.process.exitCode === null;
    }

    getPythonCommand() {
        const searchRoots = [];

        // First: workspace folders (most reliable — VS Code knows the open project)
        const vscode = require('vscode');
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (workspaceFolders) {
            for (const folder of workspaceFolders) {
                searchRoots.push(folder.uri.fsPath);
            }
        }

        // Second: project root derived from the target file path
        if (this.projectRoot) {
            searchRoots.push(this.projectRoot);
        }

        for (const root of searchRoots) {
            for (const rel of ['.venv/bin/python3', '.venv/bin/python', 'venv/bin/python3', 'venv/bin/python']) {
                const candidate = path.join(root, rel);
                if (fs.existsSync(candidate)) {
                    return candidate;
                }
            }
        }

        return 'python3';
    }

    start() {
        if (this.startPromise) {
            return this.startPromise;
        }

        this.startPromise = new Promise((resolve, reject) => {
            const pythonCmd = this.getPythonCommand();
            this.channel.appendLine(`Starting runner: ${pythonCmd} ${this.runnerScriptPath} ${this.filePath}`);

            this.process = spawn(pythonCmd, [this.runnerScriptPath, this.filePath], {
                cwd: this.projectRoot,
                stdio: ['pipe', 'pipe', 'pipe'],
            });

            this.process.stdout.on('data', (chunk) => {
                this.handleStdout(chunk, resolve, reject);
            });

            this.process.stderr.on('data', (chunk) => {
                this.channel.append(chunk.toString());
            });

            this.process.on('error', (error) => {
                this.rejectAllPending(error);
                reject(error);
            });

            this.process.on('exit', (code, signal) => {
                this.ready = false;
                const error = new Error(`Runner exited (code=${code}, signal=${signal})`);
                this.rejectAllPending(error);
                if (!this.startResolved) {
                    reject(error);
                }
                this.startPromise = null;
                this.process = null;
            });
        });

        return this.startPromise;
    }

    handleStdout(chunk, resolveStart, rejectStart) {
        this.stdoutBuffer += chunk.toString();

        let newlineIndex = this.stdoutBuffer.indexOf('\n');
        while (newlineIndex >= 0) {
            const line = this.stdoutBuffer.slice(0, newlineIndex).trim();
            this.stdoutBuffer = this.stdoutBuffer.slice(newlineIndex + 1);

            if (line) {
                this.handleProtocolLine(line, resolveStart, rejectStart);
            }

            newlineIndex = this.stdoutBuffer.indexOf('\n');
        }
    }

    handleProtocolLine(line, resolveStart, rejectStart) {
        let message;
        try {
            message = JSON.parse(line);
        } catch (error) {
            this.channel.appendLine(`Protocol parse error: ${error.message}`);
            this.channel.appendLine(`Raw stdout: ${line}`);
            return;
        }

        if (message.type === 'ready') {
            this.ready = true;
            this.startResolved = true;
            resolveStart(message);
            return;
        }

        if (message.type === 'fatal_error') {
            const error = this.createRunnerError(message.error, 'Runner fatal error');
            this.channel.appendLine(`Runner fatal error: ${this.extractErrorMessage(message.error)}`);
            this.startResolved = true;
            rejectStart(error);
            return;
        }

        if (message.type === 'milestone') {
            if (typeof this.onMilestone === 'function') {
                this.onMilestone(message);
            }
            return;
        }

        if (Object.prototype.hasOwnProperty.call(message, 'id')) {
            const pending = this.pending.get(message.id);
            if (!pending) {
                this.channel.appendLine(`No pending request for response id ${message.id}`);
                return;
            }

            this.pending.delete(message.id);
            if (message.ok) {
                pending.resolve(message.result);
            } else {
                pending.reject(this.createRunnerError(message.error, `Runner command '${message.command || 'unknown'}' failed`));
            }
            return;
        }

        this.channel.appendLine(`Unhandled protocol message: ${line}`);
    }

    extractErrorMessage(errorPayload) {
        if (!errorPayload) {
            return 'Unknown runner error';
        }
        if (typeof errorPayload === 'string') {
            return errorPayload;
        }
        if (typeof errorPayload.message === 'string') {
            return errorPayload.message;
        }
        return JSON.stringify(errorPayload);
    }

    createRunnerError(errorPayload, prefix = 'Runner error') {
        const message = this.extractErrorMessage(errorPayload);
        const error = new Error(`${prefix}: ${message}`);
        error.runnerError = errorPayload || null;
        error.runnerTraceback = errorPayload && typeof errorPayload.traceback === 'string'
            ? errorPayload.traceback
            : null;
        error.runnerErrorType = errorPayload && typeof errorPayload.type === 'string'
            ? errorPayload.type
            : null;
        return error;
    }

    async request(command, payload = {}) {
        await this.start();

        const id = this.requestId;
        this.requestId += 1;

        const request = { id, command, payload };
        const serialized = JSON.stringify(request) + '\n';

        return new Promise((resolve, reject) => {
            this.pending.set(id, { resolve, reject });
            this.process.stdin.write(serialized, (error) => {
                if (!error) {
                    return;
                }
                this.pending.delete(id);
                reject(error);
            });
        });
    }

    /**
     * Send a slot-scoped request.  Merges {slot} into the payload automatically.
     */
    async slotRequest(command, slot, payload = {}) {
        return this.request(command, { ...payload, slot });
    }

    async dispose() {
        if (!this.process) {
            return;
        }

        try {
            if (this.isAlive()) {
                await this.request('shutdown');
            }
        } catch (error) {
            this.channel.appendLine(`Runner shutdown request failed: ${error.message}`);
        }

        if (this.process && this.isAlive()) {
            this.process.kill();
        }

        this.rejectAllPending(new Error('Runner session disposed'));
        this.process = null;
        this.startPromise = null;
        this.ready = false;
    }

    rejectAllPending(error) {
        for (const pending of this.pending.values()) {
            pending.reject(error);
        }
        this.pending.clear();
    }
}

module.exports = { PythonRunnerSession };
