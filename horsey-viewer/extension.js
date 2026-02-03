const vscode = require('vscode');
const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
    console.log('Horsey Viewer extension activated');

    let disposable = vscode.commands.registerCommand('horsey-viewer.renderHorsey', async function () {
        const editor = vscode.window.activeTextEditor;

        if (!editor) {
            vscode.window.showErrorMessage('No active editor!');
            return;
        }

        const document = editor.document;

        // Check if it's a Python file
        if (document.languageId !== 'python') {
            vscode.window.showErrorMessage('Current file is not a Python file!');
            return;
        }

        const filePath = document.fileName;

        // Save the file if it has unsaved changes
        if (document.isDirty) {
            await document.save();
        }

        vscode.window.showInformationMessage('Rendering Horsey...');

        // Run the Python runner script
        runPythonScript(filePath, context);
    });

    context.subscriptions.push(disposable);
}

function runPythonScript(filePath, context) {
    const runnerScriptPath = path.join(context.extensionPath, 'runner.py');
    const projectRoot = path.dirname(path.dirname(filePath)); // Assume file is in code_goes_here or examples

    // Try to use venv python if it exists, otherwise fall back to python3
    const venvPython = path.join(projectRoot, 'venv', 'bin', 'python');
    const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3';

    // Build the command to run Python
    const command = `cd "${projectRoot}" && ${pythonCmd} "${runnerScriptPath}" "${filePath}"`;

    exec(command, { maxBuffer: 10 * 1024 * 1024 }, (error, stdout, stderr) => {
        if (error) {
            vscode.window.showErrorMessage(`Error running Python: ${error.message}`);
            console.error('stderr:', stderr);
            return;
        }

        if (stderr) {
            console.warn('Python stderr:', stderr);
        }

        try {
            // Parse the JSON output from the Python script
            const frameData = JSON.parse(stdout);

            // Show the webview with the frame data
            showFrameViewer(frameData, context);
        } catch (e) {
            vscode.window.showErrorMessage(`Error parsing Frame data: ${e.message}`);
            console.error('stdout:', stdout);
            console.error('Parse error:', e);
        }
    });
}

function showFrameViewer(frameData, context) {
    // Create and show a new webview
    const panel = vscode.window.createWebviewPanel(
        'horseyViewer',
        'Horsey Frame Viewer',
        vscode.ViewColumn.Two,
        {
            enableScripts: true
        }
    );

    // Set the webview's HTML content
    panel.webview.html = getWebviewContent(frameData);
}

function getWebviewContent(frameData) {
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
        <h1>🐴 Horsey Frame Viewer</h1>

        <div class="info-section">
        <h2>Frame Overview</h2>
        <div>
            <span class="stat">Frame: ${frameData.name || 'Unnamed'}</span>
            <span class="stat">${frameData.timber_count} Timbers</span>
            <span class="stat">${frameData.accessories_count} Accessories</span>
        </div>
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

    <h2>Accessories (${frameData.accessories_count})</h2>
    ${frameData.accessories.length > 0 ? `
        <div class="info-section">
            ${frameData.accessories.map((acc, index) => `
                <div style="margin: 10px 0;">
                    <strong>${index + 1}. ${acc.type}</strong>
                    ${acc.details ? `<pre>${JSON.stringify(acc.details, null, 2)}</pre>` : ''}
                </div>
            `).join('')}
        </div>
    ` : '<div class="info-section">No accessories in this frame.</div>'}

    <h2>Raw JSON Data</h2>
    <pre>${JSON.stringify(frameData, null, 2)}</pre>
    </div>

    <script>
        // Three.js scene setup
        const container = document.getElementById('three-container');
        const canvas = document.getElementById('three-canvas');

        // Create scene
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x1e1e1e);

        // Create camera
        const camera = new THREE.PerspectiveCamera(
            75,
            container.clientWidth / container.clientHeight,
            0.1,
            1000
        );
        camera.position.z = 5;

        // Create renderer
        const renderer = new THREE.WebGLRenderer({
            canvas: canvas,
            antialias: true
        });
        renderer.setSize(container.clientWidth, container.clientHeight);
        renderer.setPixelRatio(window.devicePixelRatio);

        // Create a cube
        const geometry = new THREE.BoxGeometry(2, 2, 2);
        const material = new THREE.MeshPhongMaterial({
            color: 0x4488ff,
            shininess: 100
        });
        const cube = new THREE.Mesh(geometry, material);
        scene.add(cube);

        // Add lights
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
        scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(5, 5, 5);
        scene.add(directionalLight);

        // Animation loop
        function animate() {
            requestAnimationFrame(animate);

            // Rotate the cube
            cube.rotation.x += 0.01;
            cube.rotation.y += 0.01;

            renderer.render(scene, camera);
        }

        // Handle window resize
        window.addEventListener('resize', () => {
            const width = container.clientWidth;
            const height = container.clientHeight;

            camera.aspect = width / height;
            camera.updateProjectionMatrix();

            renderer.setSize(width, height);
        });

        // Start animation
        animate();
    </script>
</body>
</html>`;
}

function deactivate() {}

module.exports = {
    activate,
    deactivate
};
