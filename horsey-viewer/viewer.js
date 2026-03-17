/**
 * Viewer — Manages the webview panel for displaying timber frame data and 3D geometry.
 */

const vscode = require('vscode');
const path = require('path');

const initializedPanels = new WeakSet();

function createFrameViewer(filePath) {
    return vscode.window.createWebviewPanel(
        'horseyViewer',
        getViewerTitle(filePath),
        vscode.ViewColumn.Two,
        {
            enableScripts: true,
        }
    );
}

function renderFrameViewer(panel, filePath, frameData, geometryData) {
    panel.title = getViewerTitle(filePath, frameData.name);
    if (!initializedPanels.has(panel)) {
        panel.webview.html = getWebviewContent(frameData, geometryData);
        initializedPanels.add(panel);
    } else {
        panel.webview.postMessage({
            type: 'refresh',
            frame: frameData,
            geometry: geometryData,
        });
    }
    panel.reveal(vscode.ViewColumn.Two);
}

function getViewerTitle(filePath, frameName = null) {
    const fileName = path.basename(filePath);
    if (frameName) {
        return `Horsey: ${fileName} (${frameName})`;
    }
    return `Horsey: ${fileName}`;
}

function getWebviewContent(frameData, geometryData) {
    const frameJson = JSON.stringify(frameData);
    const geometryJson = JSON.stringify(geometryData);

    const SE = '<' + '/script>';
    const SS = '<script';

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Horsey Frame Viewer</title>
    ${SS} src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js">${SE}
</head>
<body>
    <horsey-viewer-app></horsey-viewer-app>
    ${SS} type="module">
import { LitElement, html, css } from 'https://unpkg.com/lit@3.2.0/index.js?module';

const INITIAL_PAYLOAD = {
    frame: ${frameJson},
    geometry: ${geometryJson},
};

class HorseyViewerApp extends LitElement {
    static styles = css\`
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :host {
            --hv-bg-top: #fff8dc;
            --hv-bg-bottom: #ffeef4;
            --hv-panel-bg: rgba(255, 255, 255, 0.78);
            --hv-panel-border: #d7dbe8;
            --hv-text: #3a4152;
            --hv-title: #5873a6;
            --hv-dim: #6e7691;
            --hv-accent: #8ca4cf;
            --hv-mesh: #afbccf;
            --hv-edge: #5d6882;
            display: block;
            min-height: 100vh;
            background: linear-gradient(180deg, var(--hv-bg-top) 0%, var(--hv-bg-bottom) 100%);
            color: var(--hv-text);
            overflow: auto;
        }
        #viewport {
            position: relative;
            width: 100%;
            height: 72vh;
            min-height: 420px;
            border-bottom: 1px solid var(--hv-panel-border);
        }
        canvas { display: block; width: 100%; height: 100%; }
        #info {
            position: absolute; top: 12px; left: 12px;
            background: var(--hv-panel-bg);
            color: var(--hv-text);
            font: 12px/1.6 'Segoe UI', sans-serif;
            padding: 8px 14px; border-radius: 4px;
            border: 1px solid var(--hv-panel-border);
            border-left: 3px solid var(--hv-accent);
            pointer-events: none;
            user-select: none;
            backdrop-filter: blur(4px);
        }
        #info strong { color: #39496e; font-size: 13px; }
        #debug {
            position: absolute;
            top: 12px;
            right: 12px;
            background: var(--hv-panel-bg);
            color: var(--hv-text);
            font: 12px/1.6 'Segoe UI', sans-serif;
            padding: 8px 12px;
            border-radius: 4px;
            border: 1px solid var(--hv-panel-border);
            border-left: 3px solid #9eb5dc;
            pointer-events: none;
            user-select: none;
            text-align: right;
            backdrop-filter: blur(4px);
        }
        #debug strong { color: #39496e; font-size: 13px; }
        #hint {
            position: absolute; bottom: 8px; left: 50%; transform: translateX(-50%);
            color: rgba(72, 77, 94, 0.58); font: 11px 'Segoe UI', sans-serif;
            pointer-events: none; user-select: none; white-space: nowrap;
        }
        #panels {
            max-width: 1200px;
            margin: 16px auto 28px;
            padding: 0 14px;
            display: grid;
            gap: 14px;
        }
        .panel-box {
            background: var(--hv-panel-bg);
            border: 1px solid var(--hv-panel-border);
            border-radius: 8px;
            overflow: hidden;
            backdrop-filter: blur(4px);
        }
        .panel-title {
            background: rgba(255, 255, 255, 0.6);
            color: var(--hv-title);
            font: 12px 'Segoe UI', sans-serif;
            padding: 8px 10px;
            border-bottom: 1px solid var(--hv-panel-border);
        }
        #timber-panel {
            max-height: 220px;
            overflow-y: auto;
            overflow-x: auto;
        }
        #timber-panel table {
            width: 100%; border-collapse: collapse;
            font: 11px/1.5 'Segoe UI', monospace; color: var(--hv-text);
        }
        #timber-panel thead th {
            position: sticky; top: 0; background: rgba(255, 255, 255, 0.95);
            color: var(--hv-title); font-weight: 600; text-align: left;
            padding: 4px 10px; border-bottom: 1px solid var(--hv-panel-border);
            white-space: nowrap;
        }
        #timber-panel tbody tr:hover { background: rgba(145, 161, 192, 0.12); }
        #timber-panel tbody td {
            padding: 3px 10px; border-bottom: 1px solid #e8ebf3;
            white-space: nowrap; font-family: 'Courier New', monospace;
        }
        #timber-panel tbody td:first-child {
            color: #707a97; font-family: 'Segoe UI', sans-serif;
        }
        #raw-output {
            max-height: 260px;
            overflow: auto;
            padding: 10px;
            color: var(--hv-text);
            font: 11px/1.5 'Courier New', monospace;
            white-space: pre;
        }
        #to-v3d {
            position: fixed;
            top: 12px;
            left: 50%;
            transform: translateX(-50%);
            padding: 6px 10px;
            border: 1px solid var(--hv-panel-border);
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.92);
            color: var(--hv-title);
            font: 12px 'Segoe UI', sans-serif;
            cursor: pointer;
            display: none;
            z-index: 50;
        }
        #to-v3d:hover {
            background: #ffffff;
        }
        .dim { color: var(--hv-dim); }
    \`;

    constructor() {
        super();
        this.meshObjectsByKey = new Map();
        this.cx = 0;
        this.cy = 0;
        this.cz = 0;
        this.orbitDist = 10;
        this.theta = -Math.PI / 5;
        this.phi = Math.PI / 3;
        this.dragging = false;
        this.lastX = 0;
        this.lastY = 0;
        this.animationHandle = null;
        this.onWindowMessage = this.onWindowMessage.bind(this);
        this.onWindowScroll = this.onWindowScroll.bind(this);
        this.onWindowMouseUp = this.onWindowMouseUp.bind(this);
        this.onWindowMouseMove = this.onWindowMouseMove.bind(this);
        this.onWindowResize = this.onWindowResize.bind(this);
    }

    render() {
        return html\`
            <button id="to-v3d" title="Jump back to 3D view">to v3d view</button>
            <div id="viewport">
                <canvas id="c"></canvas>
                <div id="info"></div>
                <div id="debug"></div>
                <div id="hint">drag to orbit • scroll to zoom</div>
            </div>
            <div id="panels">
                <div class="panel-box">
                    <div class="panel-title">Timber List</div>
                    <div id="timber-panel">
                        <table>
                            <thead>
                                <tr>
                                    <th>#</th><th>Name</th>
                                    <th>Length</th><th>Width</th><th>Height</th>
                                </tr>
                            </thead>
                            <tbody id="timber-rows"></tbody>
                        </table>
                    </div>
                </div>
                <div class="panel-box">
                    <div class="panel-title">Raw Python Output</div>
                    <pre id="raw-output"></pre>
                </div>
            </div>
        \`;
    }

    firstUpdated() {
        this.setupUiEvents();
        this.setupThreeScene();
        window.addEventListener('message', this.onWindowMessage);
        this.applyPayload(INITIAL_PAYLOAD);
    }

    disconnectedCallback() {
        super.disconnectedCallback();
        window.removeEventListener('message', this.onWindowMessage);
        window.removeEventListener('scroll', this.onWindowScroll);
        window.removeEventListener('mouseup', this.onWindowMouseUp);
        window.removeEventListener('mousemove', this.onWindowMouseMove);
        window.removeEventListener('resize', this.onWindowResize);
        if (this.animationHandle) {
            cancelAnimationFrame(this.animationHandle);
            this.animationHandle = null;
        }
        for (const bundle of this.meshObjectsByKey.values()) {
            this.disposeMeshBundle(bundle);
        }
        this.meshObjectsByKey.clear();
    }

    setupUiEvents() {
        const toV3d = this.shadowRoot.getElementById('to-v3d');
        const canvas = this.shadowRoot.getElementById('c');
        const viewport = this.shadowRoot.getElementById('viewport');

        toV3d.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });

        canvas.addEventListener('mousedown', (event) => {
            this.dragging = true;
            this.lastX = event.clientX;
            this.lastY = event.clientY;
        });

        viewport.addEventListener('wheel', (event) => {
            event.preventDefault();
            this.orbitDist *= event.deltaY > 0 ? 1.1 : 0.9;
            this.updateCamera();
        }, { passive: false });

        window.addEventListener('scroll', this.onWindowScroll);
        window.addEventListener('mouseup', this.onWindowMouseUp);
        window.addEventListener('mousemove', this.onWindowMouseMove);
        window.addEventListener('resize', this.onWindowResize);
    }

    setupThreeScene() {
        const viewport = this.shadowRoot.getElementById('viewport');
        const canvas = this.shadowRoot.getElementById('c');

        this.renderer = new THREE.WebGLRenderer({
            canvas: canvas,
            antialias: true,
            logarithmicDepthBuffer: true,
        });
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.setSize(viewport.offsetWidth, viewport.offsetHeight, false);
        this.renderer.outputEncoding = THREE.sRGBEncoding;

        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xfff8dc);

        this.camera = new THREE.PerspectiveCamera(45, viewport.offsetWidth / viewport.offsetHeight, 0.01, 10000);

        this.scene.add(new THREE.AmbientLight(0xffffff, 0.8));
        const sun = new THREE.DirectionalLight(0xffffff, 0.75);
        sun.position.set(5, 8, 4);
        this.scene.add(sun);
        const fill = new THREE.DirectionalLight(0xecf2ff, 0.45);
        fill.position.set(-4, 3, -6);
        this.scene.add(fill);

        this.solidMat = new THREE.MeshStandardMaterial({
            color: 0xafbccf,
            metalness: 0.02,
            roughness: 0.68,
            flatShading: true,
            polygonOffset: true,
            polygonOffsetFactor: 0.6,
            polygonOffsetUnits: 2,
        });
        this.edgeMat = new THREE.LineBasicMaterial({
            color: 0x5d6882,
            transparent: true,
            opacity: 0.4,
            depthTest: false,
            depthWrite: false,
        });

        this.updateCamera();
        const animate = () => {
            this.animationHandle = requestAnimationFrame(animate);
            this.renderer.render(this.scene, this.camera);
        };
        animate();
    }

    onWindowMessage(event) {
        const message = event.data || {};
        if (message.type === 'refresh') {
            this.applyPayload({ frame: message.frame || {}, geometry: message.geometry || { meshes: [] } });
        }
    }

    onWindowScroll() {
        const toV3d = this.shadowRoot.getElementById('to-v3d');
        toV3d.style.display = window.scrollY > 260 ? 'block' : 'none';
    }

    onWindowMouseUp() {
        this.dragging = false;
    }

    onWindowMouseMove(event) {
        if (!this.dragging) {
            return;
        }
        this.theta -= (event.clientX - this.lastX) * 0.008;
        this.phi = Math.max(0.05, Math.min(Math.PI - 0.05, this.phi - (event.clientY - this.lastY) * 0.008));
        this.lastX = event.clientX;
        this.lastY = event.clientY;
        this.updateCamera();
    }

    onWindowResize() {
        const viewport = this.shadowRoot.getElementById('viewport');
        const width = viewport.offsetWidth;
        const height = viewport.offsetHeight;
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height, false);
    }

    fmt(value) {
        return (value * 1000).toFixed(1) + ' mm';
    }

    disposeMeshBundle(bundle) {
        if (!bundle) {
            return;
        }
        this.scene.remove(bundle.mesh);
        this.scene.remove(bundle.edges);
        bundle.mesh.geometry.dispose();
        bundle.edges.geometry.dispose();
    }

    rebuildTimberTable(meshes) {
        const tbody = this.shadowRoot.getElementById('timber-rows');
        tbody.textContent = '';
        for (let index = 0; index < meshes.length; index += 1) {
            const mesh = meshes[index];
            const row = document.createElement('tr');
            row.innerHTML = '<td>' + (index + 1) + '</td>' +
                '<td>' + (mesh.name || '?') + '</td>' +
                '<td class="dim">' + (mesh.prism_length !== undefined ? this.fmt(mesh.prism_length) : '—') + '</td>' +
                '<td class="dim">' + (mesh.prism_width  !== undefined ? this.fmt(mesh.prism_width)  : '—') + '</td>' +
                '<td class="dim">' + (mesh.prism_height !== undefined ? this.fmt(mesh.prism_height) : '—') + '</td>';
            tbody.appendChild(row);
        }
    }

    updateInfo(frameData) {
        const frameName = frameData && frameData.name ? frameData.name : 'Unnamed';
        const timberCount = frameData && frameData.timber_count ? frameData.timber_count : 0;
        const accessoriesCount = frameData && frameData.accessories_count ? frameData.accessories_count : 0;
        this.shadowRoot.getElementById('info').innerHTML =
            '<strong>' + frameName + '</strong><br>' +
            timberCount + ' timbers • ' + accessoriesCount + ' accessories';
    }

    updateDebug(geometryData) {
        const meshes = (geometryData && geometryData.meshes) ? geometryData.meshes : [];
        const changedKeys = (geometryData && geometryData.changedKeys) ? geometryData.changedKeys : [];
        const removedKeys = (geometryData && geometryData.removedKeys) ? geometryData.removedKeys : [];
        const rebuilt = changedKeys.length;
        const removed = removedKeys.length;
        const total = meshes.length;
        const reused = Math.max(0, total - rebuilt);

        this.shadowRoot.getElementById('debug').innerHTML =
            '<strong>Refresh Debug</strong><br>' +
            'total: ' + total + '<br>' +
            'rebuilt: ' + rebuilt + '<br>' +
            'reused: ' + reused + '<br>' +
            'removed: ' + removed;
    }

    updateMeshScene(geometryData) {
        const meshes = (geometryData && geometryData.meshes) ? geometryData.meshes : [];
        const nextKeys = new Set();

        for (let index = 0; index < meshes.length; index += 1) {
            const mesh = meshes[index];
            const key = mesh.timberKey || ('index-' + index);
            const hash = mesh.hash || '';
            nextKeys.add(key);

            const existing = this.meshObjectsByKey.get(key);
            if (existing && existing.hash === hash) {
                continue;
            }

            if (existing) {
                this.disposeMeshBundle(existing);
                this.meshObjectsByKey.delete(key);
            }

            const positions = new Float32Array(mesh.vertices || []);
            const geometry = new THREE.BufferGeometry();
            geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
            geometry.setIndex(mesh.indices || []);
            geometry.computeVertexNormals();
            geometry.computeBoundingSphere();

            const solidMesh = new THREE.Mesh(geometry, this.solidMat);
            const edgeGeometry = new THREE.EdgesGeometry(geometry, 25);
            const edgeMesh = new THREE.LineSegments(edgeGeometry, this.edgeMat);
            solidMesh.renderOrder = 1;
            edgeMesh.renderOrder = 2;

            this.scene.add(solidMesh);
            this.scene.add(edgeMesh);
            this.meshObjectsByKey.set(key, { hash: hash, mesh: solidMesh, edges: edgeMesh });
        }

        for (const existingKey of Array.from(this.meshObjectsByKey.keys())) {
            if (!nextKeys.has(existingKey)) {
                const bundle = this.meshObjectsByKey.get(existingKey);
                this.disposeMeshBundle(bundle);
                this.meshObjectsByKey.delete(existingKey);
            }
        }

        this.rebuildTimberTable(meshes);
    }

    getSceneBounds() {
        let minX = Infinity;
        let minY = Infinity;
        let minZ = Infinity;
        let maxX = -Infinity;
        let maxY = -Infinity;
        let maxZ = -Infinity;
        let hasAny = false;

        this.meshObjectsByKey.forEach((bundle) => {
            const positions = bundle.mesh.geometry.getAttribute('position').array;
            for (let index = 0; index < positions.length; index += 3) {
                hasAny = true;
                const vx = positions[index];
                const vy = positions[index + 1];
                const vz = positions[index + 2];
                if (vx < minX) minX = vx;
                if (vx > maxX) maxX = vx;
                if (vy < minY) minY = vy;
                if (vy > maxY) maxY = vy;
                if (vz < minZ) minZ = vz;
                if (vz > maxZ) maxZ = vz;
            }
        });

        if (!hasAny) {
            return { minX: -1, minY: -1, minZ: -1, maxX: 1, maxY: 1, maxZ: 1 };
        }

        return { minX, minY, minZ, maxX, maxY, maxZ };
    }

    applyPayload(payload) {
        const frameData = payload.frame || {};
        const geometryData = payload.geometry || { meshes: [] };

        this.updateInfo(frameData);
        this.updateDebug(geometryData);
        this.updateMeshScene(geometryData);

        this.shadowRoot.getElementById('raw-output').textContent = JSON.stringify({
            frame: frameData,
            geometry: geometryData,
        }, null, 2);

        const bounds = this.getSceneBounds();
        this.cx = (bounds.minX + bounds.maxX) / 2;
        this.cy = (bounds.minY + bounds.maxY) / 2;
        this.cz = (bounds.minZ + bounds.maxZ) / 2;
        const dx = bounds.maxX - bounds.minX;
        const dy = bounds.maxY - bounds.minY;
        const dz = bounds.maxZ - bounds.minZ;
        const radius = Math.sqrt(dx * dx + dy * dy + dz * dz) / 2 || 5;
        const fovRad = this.camera.fov * Math.PI / 180;
        this.orbitDist = radius / Math.sin(fovRad / 2) * 1.3;
        this.camera.near = Math.max(0.05, radius * 0.05);
        this.camera.far = Math.max(this.camera.near * 20, radius * 20);
        this.camera.updateProjectionMatrix();
        this.updateCamera();
    }

    updateCamera() {
        if (!this.camera) {
            return;
        }
        this.camera.position.set(
            this.cx + this.orbitDist * Math.sin(this.phi) * Math.sin(this.theta),
            this.cy + this.orbitDist * Math.cos(this.phi),
            this.cz + this.orbitDist * Math.sin(this.phi) * Math.cos(this.theta)
        );
        this.camera.lookAt(this.cx, this.cy, this.cz);
    }
}

customElements.define('horsey-viewer-app', HorseyViewerApp);
    ${SE}
</body>
</html>`;
}

module.exports = { createFrameViewer, renderFrameViewer };
