const vscode = require('vscode');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

let runnerSession = null;
let outputChannel = null;
let activePanel = null;

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
        this.projectRoot = this.findProjectRoot(filePath) || path.dirname(context.extensionPath);
        this.runnerScriptPath = path.join(context.extensionPath, 'runner.py');
    }

    findProjectRoot(filePath) {
        let candidate = path.dirname(path.resolve(filePath));
        while (true) {
            if (fs.existsSync(path.join(candidate, 'code_goes_here'))) {
                return candidate;
            }
            const parent = path.dirname(candidate);
            if (parent === candidate) {
                return null;
            }
            candidate = parent;
        }
    }

    isAlive() {
        return this.process && !this.process.killed && this.process.exitCode === null;
    }

    getPythonCommand() {
        const searchRoots = [];

        // First: workspace folders (most reliable — VS Code knows the open project)
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
            const error = new Error(this.extractErrorMessage(message.error));
            this.channel.appendLine(`Runner fatal error: ${this.extractErrorMessage(message.error)}`);
            this.startResolved = true;
            rejectStart(error);
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
                pending.reject(new Error(this.extractErrorMessage(message.error)));
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

/**
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
            await session.request('reload_example', { filePath });
            const frameData = await session.request('get_frame');
            const geometryData = await session.request('get_geometry');
            showFrameViewer(frameData, geometryData);
        } catch (error) {
            outputChannel.show(true);
            vscode.window.showErrorMessage(`Horsey Viewer error: ${error.message}`);
        }
    });

    context.subscriptions.push(disposable);
    context.subscriptions.push({
        dispose: () => {
            if (runnerSession) {
                runnerSession.dispose();
                runnerSession = null;
            }
        },
    });
}

async function getOrCreateSession(filePath, context) {
    if (runnerSession && runnerSession.filePath === filePath && runnerSession.isAlive()) {
        return runnerSession;
    }

    if (runnerSession) {
        await runnerSession.dispose();
    }

    runnerSession = new PythonRunnerSession(filePath, context, outputChannel);
    await runnerSession.start();
    return runnerSession;
}

function showFrameViewer(frameData, geometryData) {
    if (!activePanel) {
        activePanel = vscode.window.createWebviewPanel(
            'horseyViewer',
            'Horsey Frame Viewer',
            vscode.ViewColumn.Two,
            {
                enableScripts: true,
            }
        );

        activePanel.onDidDispose(() => {
            activePanel = null;
        });
    }

    activePanel.title = `Horsey Frame Viewer: ${frameData.name || 'Unnamed'}`;
    activePanel.webview.html = getWebviewContent(frameData, geometryData);
    activePanel.reveal(vscode.ViewColumn.Two);
}

function getWebviewContent(frameData, geometryData) {
    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Horsey Frame Viewer</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 0;
            margin: 0;
            color: var(--vscode-foreground);
            background-color: var(--vscode-editor-background);
        }
        #three-container {
            width: 100%;
            height: 400px;
            background-color: #1e1e1e;
            border-bottom: 2px solid var(--vscode-textLink-foreground);
            position: relative;
        }
        #three-canvas {
            width: 100%;
            height: 100%;
            display: block;
        }
        .content {
            padding: 20px;
        }
        h1 {
            color: var(--vscode-foreground);
            border-bottom: 2px solid var(--vscode-textLink-foreground);
            padding-bottom: 10px;
            margin-top: 0;
        }
        h2 {
            color: var(--vscode-textLink-foreground);
            margin-top: 30px;
        }
        .info-section {
            background-color: var(--vscode-textBlockQuote-background);
            border-left: 4px solid var(--vscode-textLink-foreground);
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }
        .timber-item {
            background-color: var(--vscode-editor-background);
            border: 1px solid var(--vscode-panel-border);
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
        }
        .timber-name {
            font-weight: bold;
            color: var(--vscode-textLink-foreground);
            font-size: 1.1em;
            margin-bottom: 10px;
        }
        .timber-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }
        .detail-item {
            display: flex;
            flex-direction: column;
        }
        .detail-label {
            font-weight: 600;
            color: var(--vscode-descriptionForeground);
            font-size: 0.9em;
        }
        .detail-value {
            font-family: 'Courier New', monospace;
            color: var(--vscode-foreground);
            margin-top: 4px;
        }
        pre {
            background-color: var(--vscode-textCodeBlock-background);
            border: 1px solid var(--vscode-panel-border);
            border-radius: 4px;
            padding: 10px;
            overflow-x: auto;
            font-size: 0.9em;
        }
        .stat {
            display: inline-block;
            background-color: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            padding: 5px 15px;
            border-radius: 15px;
            margin: 5px;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div id="three-container">
        <canvas id="three-canvas"></canvas>
    </div>

    <div class="content">
        <h1>Horsey Frame Viewer</h1>

        <div class="info-section">
            <h2>Frame Overview</h2>
            <div>
                <span class="stat">Frame: ${frameData.name || 'Unnamed'}</span>
                <span class="stat">${frameData.timber_count} Timbers</span>
                <span class="stat">${frameData.accessories_count} Accessories</span>
            </div>
        </div>

        <div class="info-section">
            <h2>Geometry Pipeline</h2>
            <pre>${JSON.stringify(geometryData, null, 2)}</pre>
        </div>

        <h2>Timbers (${frameData.timber_count})</h2>
        ${frameData.timbers.map((timber, index) => `
            <div class="timber-item">
                <div class="timber-name">${index + 1}. ${timber.name || 'Unnamed Timber'}</div>
                <div class="timber-details">
                    <div class="detail-item">
                        <span class="detail-label">Length</span>
                        <span class="detail-value">${timber.length}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Width</span>
                        <span class="detail-value">${timber.width}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Height</span>
                        <span class="detail-value">${timber.height}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Position</span>
                        <span class="detail-value">[${timber.bottom_position.join(', ')}]</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Cuts</span>
                        <span class="detail-value">${timber.cuts_count} cut operations</span>
                    </div>
                </div>
            </div>
        `).join('')}

        <h2>Raw Frame JSON</h2>
        <pre>${JSON.stringify(frameData, null, 2)}</pre>
    </div>

    <script>
        const container = document.getElementById('three-container');
        const canvas = document.getElementById('three-canvas');

        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x1e1e1e);

        const camera = new THREE.PerspectiveCamera(
            75,
            container.clientWidth / container.clientHeight,
            0.1,
            1000
        );
        camera.position.z = 5;

        const renderer = new THREE.WebGLRenderer({
            canvas: canvas,
            antialias: true
        });
        renderer.setSize(container.clientWidth, container.clientHeight);
        renderer.setPixelRatio(window.devicePixelRatio);

        const geometry = new THREE.BoxGeometry(2, 2, 2);
        const material = new THREE.MeshPhongMaterial({
            color: 0x4488ff,
            shininess: 100
        });
        const cube = new THREE.Mesh(geometry, material);
        scene.add(cube);

        const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
        scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(5, 5, 5);
        scene.add(directionalLight);

        function animate() {
            requestAnimationFrame(animate);
            cube.rotation.x += 0.01;
            cube.rotation.y += 0.01;
            renderer.render(scene, camera);
        }

        window.addEventListener('resize', () => {
            const width = container.clientWidth;
            const height = container.clientHeight;
            camera.aspect = width / height;
            camera.updateProjectionMatrix();
            renderer.setSize(width, height);
        });

        animate();
    </script>
</body>
</html>`;
}

function deactivate() {
    if (runnerSession) {
        runnerSession.dispose();
        runnerSession = null;
    }
}

module.exports = {
    activate,
    deactivate,
};
