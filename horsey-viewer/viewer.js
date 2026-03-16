/**
 * Viewer — Manages the webview panel for displaying timber frame data and 3D geometry.
 */

const vscode = require('vscode');

let activePanel = null;

function createFrameViewer() {
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
    return activePanel;
}

function showFrameViewer(frameData, geometryData) {
    const panel = createFrameViewer();
    panel.title = `Horsey Frame Viewer: ${frameData.name || 'Unnamed'}`;
    panel.webview.html = getWebviewContent(frameData, geometryData);
    panel.reveal(vscode.ViewColumn.Two);
}

function getWebviewContent(frameData, geometryData) {
    const frameJson = JSON.stringify(frameData);
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
        html, body { height: 100%; background: #1e1e1e; overflow: auto; color: #ccc; }
        #viewport {
            position: relative;
            width: 100%;
            height: 72vh;
            min-height: 420px;
            border-bottom: 1px solid #333;
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
        #panels {
            max-width: 1200px;
            margin: 16px auto 28px;
            padding: 0 14px;
            display: grid;
            gap: 14px;
        }
        .panel-box {
            background: #161616;
            border: 1px solid #333;
            border-radius: 8px;
            overflow: hidden;
        }
        .panel-title {
            background: #252526;
            color: #9cdcfe;
            font: 12px 'Segoe UI', sans-serif;
            padding: 8px 10px;
            border-bottom: 1px solid #404040;
        }
        #timber-panel {
            max-height: 220px;
            overflow-y: auto;
            overflow-x: auto;
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
        #raw-output {
            max-height: 260px;
            overflow: auto;
            padding: 10px;
            color: #d4d4d4;
            font: 11px/1.5 'Courier New', monospace;
            white-space: pre;
        }
        #to-v3d {
            position: fixed;
            top: 12px;
            left: 50%;
            transform: translateX(-50%);
            padding: 6px 10px;
            border: 1px solid #4a4a4a;
            border-radius: 6px;
            background: #252526;
            color: #9cdcfe;
            font: 12px 'Segoe UI', sans-serif;
            cursor: pointer;
            display: none;
            z-index: 50;
        }
        #to-v3d:hover {
            background: #2f2f31;
        }
        .dim { color: #b5cea8; }
    </style>
</head>
<body>
    <button id="to-v3d" title="Jump back to 3D view">to v3d view</button>
    <div id="viewport">
        <canvas id="c"></canvas>
        <div id="info"></div>
        <div id="hint">drag to orbit &bull; scroll to zoom</div>
    </div>
    <div id="panels">
        <div class="panel-box">
            <div class="panel-title">Timber List</div>
            <div id="timber-panel">
                <table>
                    <thead><tr>
                        <th>#</th><th>Name</th>
                        <th>Length</th><th>Width</th><th>Height</th>
                    </tr></thead>
                    <tbody id="timber-rows"></tbody>
                </table>
            </div>
        </div>
        <div class="panel-box">
            <div class="panel-title">Raw Python Output</div>
            <pre id="raw-output"></pre>
        </div>
    </div>
    ${SS}>
const FRAME_DATA = ${frameJson};
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

document.getElementById('raw-output').textContent = JSON.stringify({
    frame: FRAME_DATA,
    geometry: GEOM,
}, null, 2);

var toV3d = document.getElementById('to-v3d');
toV3d.addEventListener('click', function() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
});
window.addEventListener('scroll', function() {
    toV3d.style.display = window.scrollY > 260 ? 'block' : 'none';
});

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

module.exports = { showFrameViewer, createFrameViewer };
