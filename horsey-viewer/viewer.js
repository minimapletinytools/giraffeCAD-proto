/**
 * Viewer — Manages the webview panel for displaying timber frame data and 3D geometry.
 */

const vscode = require('vscode');
const path = require('path');
const fs = require('fs');

const initializedPanels = new WeakSet();
const webviewDir = path.join(__dirname, 'webview');
let screenshotRequestCounter = 1;
const VIEWER_APP_VERSION = '2026.03.17.4';

function getNonce() {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let index = 0; index < 32; index += 1) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
}

function escapeScriptJson(value) {
    return value
        .replace(/</g, '\\u003c')
        .replace(/>/g, '\\u003e')
        .replace(/&/g, '\\u0026')
        .replace(/\u2028/g, '\\u2028')
        .replace(/\u2029/g, '\\u2029');
}

function createFrameViewer(filePath) {
    return vscode.window.createWebviewPanel(
        'horseyViewer',
        getViewerTitle(filePath),
        vscode.ViewColumn.Two,
        {
            enableScripts: true,
            localResourceRoots: [vscode.Uri.file(webviewDir)],
        }
    );
}

function renderFrameViewer(panel, filePath, frameData, geometryData) {
    panel.title = getViewerTitle(filePath, frameData.name);
    if (!initializedPanels.has(panel)) {
        panel.webview.html = getWebviewContent(panel.webview, frameData, geometryData);
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
        return `Horsey: ${fileName} (${frameName}) · v${VIEWER_APP_VERSION}`;
    }
    return `Horsey: ${fileName} · v${VIEWER_APP_VERSION}`;
}

function getWebviewContent(webview, frameData, geometryData) {
    const templatePath = path.join(webviewDir, 'viewer.html');
    const template = fs.readFileSync(templatePath, 'utf8');

    const appJsUri = webview.asWebviewUri(vscode.Uri.file(path.join(webviewDir, 'viewer-app.js'))).toString();
    const stylesCssUri = webview.asWebviewUri(vscode.Uri.file(path.join(webviewDir, 'viewer.css'))).toString();
    const nonce = getNonce();

    const payloadJson = escapeScriptJson(JSON.stringify({
        frame: frameData,
        geometry: geometryData,
    }));

    return template
        .replace(/__CSP_SOURCE__/g, webview.cspSource)
        .replace(/__NONCE__/g, nonce)
        .replace('__INITIAL_PAYLOAD_JSON__', payloadJson)
        .replace('__APP_JS_URI__', appJsUri)
        .replace('__STYLES_CSS_URI__', stylesCssUri);
}

function requestViewerScreenshot(panel, options = {}) {
    if (!panel) {
        return Promise.reject(new Error('Viewer panel is not available'));
    }

    const timeoutMs = typeof options.timeoutMs === 'number' ? options.timeoutMs : 8000;
    const requestId = `capture-${Date.now()}-${screenshotRequestCounter}`;
    screenshotRequestCounter += 1;

    return new Promise((resolve, reject) => {
        let settled = false;
        let timeoutHandle = null;

        const cleanup = () => {
            if (timeoutHandle) {
                clearTimeout(timeoutHandle);
                timeoutHandle = null;
            }
            listener.dispose();
        };

        const listener = panel.webview.onDidReceiveMessage((message) => {
            if (!message || message.type !== 'captureScreenshotResult' || message.requestId !== requestId) {
                return;
            }
            if (settled) {
                return;
            }
            settled = true;
            cleanup();
            if (message.ok) {
                resolve({
                    dataUrl: message.dataUrl,
                    width: message.width,
                    height: message.height,
                });
                return;
            }
            reject(new Error(message.error || 'Screenshot capture failed'));
        });

        if (timeoutMs > 0) {
            timeoutHandle = setTimeout(() => {
                if (settled) {
                    return;
                }
                settled = true;
                cleanup();
                reject(new Error(`Timed out waiting for screenshot (${timeoutMs}ms)`));
            }, timeoutMs);
        }

        panel.webview.postMessage({ type: 'captureScreenshotRequest', requestId }).then((posted) => {
            if (!posted && !settled) {
                settled = true;
                cleanup();
                reject(new Error('Failed to send screenshot request to webview'));
            }
        }, (error) => {
            if (!settled) {
                settled = true;
                cleanup();
                reject(error);
            }
        });
    });
}

module.exports = { createFrameViewer, renderFrameViewer, requestViewerScreenshot };
