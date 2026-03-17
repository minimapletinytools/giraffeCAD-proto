/**
 * Viewer — Manages the webview panel for displaying timber frame data and 3D geometry.
 */

const vscode = require('vscode');
const path = require('path');
const fs = require('fs');

const initializedPanels = new WeakSet();
const webviewDir = path.join(__dirname, 'webview');

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
        return `Horsey: ${fileName} (${frameName})`;
    }
    return `Horsey: ${fileName}`;
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

module.exports = { createFrameViewer, renderFrameViewer };
