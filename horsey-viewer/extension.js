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
    const geometryJson = JSON.stringify(geometryData);
    const frameName = JSON.stringify(frameData.name || 'Unnamed');
    const timberCount = frameData.timber_count || 0;
    const accessoriesCount = frameData.accessories_count || 0;

    // Split </script> tags so the HTML parser doesn't terminate the outer script early
    const SE = '<' + '/script>';
    const SS = '<script';

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Horsey Frame Viewer</title>
    ${SS} src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js">${SE}
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { height: 100%; background: #1e1e1e; overflow: hidden; }
        #viewport {
            position: absolute; top: 0; left: 0; right: 0;
            height: calc(100vh - 160px);
        }
        canvas { display: block; width: 100%; height: 100%; }
        #info {
            position: absolute; top: 12px; left: 12px;
            background: rgba(20,20,20,0.88); color: #ccc;
            font: 12px/1.6 'Segoe UI', sans-serif;
            padding: 8px 14px; border-radius: 4px;
            border-left: 3px solid #569cd6; pointer-events: none; user-select: none;
        }
        #info strong { color: #fff; font-size: 13px; }
        #hint {
            position: absolute; bottom: 8px; left: 50%; transform: translateX(-50%);
            color: rgba(160,160,160,0.4); font: 11px 'Segoe UI', sans-serif;
            pointer-events: none; user-select: none; white-space: nowrap;
        }
        #timber-panel {
            position: absolute; bottom: 0; left: 0; right: 0;
            height: 160px; overflow-y: auto; overflow-x: hidden;
            background: #161616; border-top: 1px solid #333;
        }
        #timber-panel table {
            width: 100%; border-collapse: collapse;
            font: 11px/1.5 'Segoe UI', monospace; color: #ccc;
        }
        #timber-panel thead th {
            position: sticky; top: 0; background: #252526;
            color: #9cdcfe; font-weight: 600; text-align: left;
            padding: 4px 10px; border-bottom: 1px solid #404040;
            white-space: nowrap;
        }
        #timber-panel tbody tr:hover { background: #2a2d2e; }
        #timber-panel tbody td {
            padding: 3px 10px; border-bottom: 1px solid #2a2a2a;
            white-space: nowrap; font-family: 'Courier New', monospace;
        }
        #timber-panel tbody td:first-child {
            color: #ce9178; font-family: 'Segoe UI', sans-serif;
        }
        .dim { color: #b5cea8; }
    </style>
</head>
<body>
    <div id="viewport">
        <canvas id="c"></canvas>
        <div id="info"></div>
        <div id="hint">drag to orbit &bull; scroll to zoom</div>
    </div>
    <div id="timber-panel">
        <table>
            <thead><tr>
                <th>#</th><th>Name</th>
                <th>Length</th><th>Width</th><th>Height</th>
            </tr></thead>
            <tbody id="timber-rows"></tbody>
        </table>
    </div>
    ${SS}>
const GEOM = ${geometryJson};
const FRAME_NAME = ${frameName};
const TIMBER_COUNT = ${timberCount};
const ACCESSORIES_COUNT = ${accessoriesCount};

document.getElementById('info').innerHTML =
    '<strong>' + FRAME_NAME + '</strong><br>' +
    TIMBER_COUNT + ' timbers &bull; ' + ACCESSORIES_COUNT + ' accessories';

// Populate timber table
var tbody = document.getElementById('timber-rows');
for (var ti = 0; ti < GEOM.meshes.length; ti++) {
    var m = GEOM.meshes[ti];
    var tr = document.createElement('tr');
    function fmt(v) { return (v * 1000).toFixed(1) + ' mm'; }
    tr.innerHTML = '<td>' + (ti + 1) + '</td>' +
        '<td>' + (m.name || '?') + '</td>' +
        '<td class="dim">' + (m.prism_length !== undefined ? fmt(m.prism_length) : '—') + '</td>' +
        '<td class="dim">' + (m.prism_width  !== undefined ? fmt(m.prism_width)  : '—') + '</td>' +
        '<td class="dim">' + (m.prism_height !== undefined ? fmt(m.prism_height) : '—') + '</td>';
    tbody.appendChild(tr);
}

var viewport = document.getElementById('viewport');
var canvas = document.getElementById('c');
var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
// false = don't set inline style on canvas; CSS controls display size
renderer.setSize(viewport.offsetWidth, viewport.offsetHeight, false);

var scene = new THREE.Scene();
scene.background = new THREE.Color(0x1e1e1e);

var camera = new THREE.PerspectiveCamera(45, viewport.offsetWidth / viewport.offsetHeight, 0.01, 10000);

// Lighting: warm sun from upper-right + soft blue fill
scene.add(new THREE.AmbientLight(0xffffff, 0.5));
var sun = new THREE.DirectionalLight(0xfff5e0, 0.85);
sun.position.set(5, 8, 4);
scene.add(sun);
var fill = new THREE.DirectionalLight(0xe0f0ff, 0.25);
fill.position.set(-4, 3, -6);
scene.add(fill);

var solidMat = new THREE.MeshPhongMaterial({ color: 0xC8954A, shininess: 30 });
var edgeMat  = new THREE.LineBasicMaterial({ color: 0x3a1800 });

// Build meshes and accumulate vertex extents for camera fit
var minX =  Infinity, minY =  Infinity, minZ =  Infinity;
var maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;

for (var mi = 0; mi < GEOM.meshes.length; mi++) {
    var mesh = GEOM.meshes[mi];
    var positions = new Float32Array(mesh.vertices);
    for (var vi = 0; vi < positions.length; vi += 3) {
        var vx = positions[vi], vy = positions[vi+1], vz = positions[vi+2];
        if (vx < minX) minX = vx;  if (vx > maxX) maxX = vx;
        if (vy < minY) minY = vy;  if (vy > maxY) maxY = vy;
        if (vz < minZ) minZ = vz;  if (vz > maxZ) maxZ = vz;
    }
    var geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geom.setIndex(mesh.indices);
    geom.computeVertexNormals();
    scene.add(new THREE.Mesh(geom, solidMat));
    scene.add(new THREE.LineSegments(new THREE.EdgesGeometry(geom, 25), edgeMat));
}

// Fit camera to the frame's bounding sphere
var cx = (minX + maxX) / 2, cy = (minY + maxY) / 2, cz = (minZ + maxZ) / 2;
var dx = maxX - minX, dy = maxY - minY, dz = maxZ - minZ;
var radius = Math.sqrt(dx*dx + dy*dy + dz*dz) / 2 || 5;
var fovRad = camera.fov * Math.PI / 180;
var orbitDist = radius / Math.sin(fovRad / 2) * 1.3;
camera.near = radius * 0.001;
camera.far  = radius * 50;
camera.updateProjectionMatrix();

// Orbit state: theta = horizontal angle, phi = vertical angle from +Y axis
var theta = -Math.PI / 5;
var phi   =  Math.PI / 3;

function updateCamera() {
    camera.position.set(
        cx + orbitDist * Math.sin(phi) * Math.sin(theta),
        cy + orbitDist * Math.cos(phi),
        cz + orbitDist * Math.sin(phi) * Math.cos(theta)
    );
    camera.lookAt(cx, cy, cz);
}
updateCamera();

// Mouse orbit (left drag) and scroll zoom
var dragging = false, lastX = 0, lastY = 0;
canvas.addEventListener('mousedown', function(e) { dragging = true; lastX = e.clientX; lastY = e.clientY; });
window.addEventListener('mouseup', function() { dragging = false; });
window.addEventListener('mousemove', function(e) {
    if (!dragging) return;
    theta -= (e.clientX - lastX) * 0.008;
    phi = Math.max(0.05, Math.min(Math.PI - 0.05, phi - (e.clientY - lastY) * 0.008));
    lastX = e.clientX; lastY = e.clientY;
    updateCamera();
});
viewport.addEventListener('wheel', function(e) {
    e.preventDefault();
    orbitDist *= e.deltaY > 0 ? 1.1 : 0.9;
    updateCamera();
}, { passive: false });

window.addEventListener('resize', function() {
    var w = viewport.offsetWidth, h = viewport.offsetHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
});

(function animate() { requestAnimationFrame(animate); renderer.render(scene, camera); })();
    ${SE}
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
