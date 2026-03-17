import { LitElement, html } from 'https://unpkg.com/lit@3.2.0/index.js?module';

const INITIAL_PAYLOAD = window.__HORSEY_INITIAL_PAYLOAD__ || { frame: {}, geometry: { meshes: [] } };
const vscode = typeof acquireVsCodeApi === 'function' ? acquireVsCodeApi() : null;

class HorseyViewerApp extends LitElement {
    constructor() {
        super();
        this.meshObjectsByKey = new Map();
        this.lastBounds = { minX: -1, minY: -1, minZ: -1, maxX: 1, maxY: 1, maxZ: 1 };

        this.cx = 0;
        this.cy = 0;
        this.cz = 0;
        this.orbitDist = 10;
        this.theta = -Math.PI / 5;
        this.phi = Math.PI / 3;
        this.cameraUpVector = new THREE.Vector3(0, 0, 1);

        this.cameraAnimation = null;

        this.dragging = false;
        this.lastX = 0;
        this.lastY = 0;

        this.lightAzimuth = 0;
        this.lightElevation = 0.8;
        this.lightDistance = 16;
        this.lightDialDragging = false;

        this.shadowSize = 60;

        this.gizmoDragging = false;
        this.gizmoMoved = false;
        this.gizmoLastX = 0;
        this.gizmoLastY = 0;
        this.gizmoRenderer = null;
        this.gizmoScene = null;
        this.gizmoCamera = null;
        this.gizmoCube = null;
        this.gizmoRaycaster = new THREE.Raycaster();
        this.gizmoPointer = new THREE.Vector2();

        this.sun = null;
        this.shadowCatcher = null;

        this.animationHandle = null;
        this.onWindowMessage = this.onWindowMessage.bind(this);
        this.onWindowScroll = this.onWindowScroll.bind(this);
        this.onWindowMouseUp = this.onWindowMouseUp.bind(this);
        this.onWindowMouseMove = this.onWindowMouseMove.bind(this);
        this.onWindowResize = this.onWindowResize.bind(this);
        this.onGizmoPointerMove = this.onGizmoPointerMove.bind(this);
        this.onGizmoPointerUp = this.onGizmoPointerUp.bind(this);
        this.onLightDialPointerMove = this.onLightDialPointerMove.bind(this);
        this.onLightDialPointerUp = this.onLightDialPointerUp.bind(this);
    }

    createRenderRoot() {
        return this;
    }

    render() {
        return html`
            <button id="to-v3d" title="Jump back to 3D view">to v3d view</button>
            <div id="viewport">
                <canvas id="c"></canvas>
                <div id="info"></div>
                <div id="gizmo-panel" aria-label="Camera and light gizmos">
                    <div class="gizmo-block">
                        <div class="gizmo-title">camera</div>
                        <canvas id="gizmo-cube-c"></canvas>
                    </div>
                    <button id="focus-btn" type="button" title="Focus selection">focus</button>
                    <div class="gizmo-block">
                        <div class="gizmo-title">light</div>
                        <canvas id="light-dial-c"></canvas>
                    </div>
                </div>
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
        `;
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
        window.removeEventListener('pointermove', this.onGizmoPointerMove);
        window.removeEventListener('pointerup', this.onGizmoPointerUp);
        window.removeEventListener('pointermove', this.onLightDialPointerMove);
        window.removeEventListener('pointerup', this.onLightDialPointerUp);
        if (this.animationHandle) {
            cancelAnimationFrame(this.animationHandle);
            this.animationHandle = null;
        }
        if (this.gizmoRenderer) {
            this.gizmoRenderer.dispose();
            this.gizmoRenderer = null;
        }
        if (this.shadowCatcher) {
            this.scene.remove(this.shadowCatcher);
            this.shadowCatcher.geometry.dispose();
            this.shadowCatcher.material.dispose();
            this.shadowCatcher = null;
        }
        for (const bundle of this.meshObjectsByKey.values()) {
            this.disposeMeshBundle(bundle);
        }
        this.meshObjectsByKey.clear();
    }

    setupUiEvents() {
        const toV3d = this.renderRoot.querySelector('#to-v3d');
        const canvas = this.renderRoot.querySelector('#c');
        const viewport = this.renderRoot.querySelector('#viewport');
        const gizmoCanvas = this.renderRoot.querySelector('#gizmo-cube-c');
        const focusButton = this.renderRoot.querySelector('#focus-btn');
        const lightDialCanvas = this.renderRoot.querySelector('#light-dial-c');

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
            this.cameraAnimation = null;
            this.updateCamera();
        }, { passive: false });

        gizmoCanvas.addEventListener('pointerdown', (event) => {
            event.preventDefault();
            this.gizmoDragging = true;
            this.gizmoMoved = false;
            this.gizmoLastX = event.clientX;
            this.gizmoLastY = event.clientY;
            gizmoCanvas.setPointerCapture(event.pointerId);
        });

        focusButton.addEventListener('click', () => {
            this.focusSelection();
        });

        lightDialCanvas.addEventListener('pointerdown', (event) => {
            event.preventDefault();
            this.lightDialDragging = true;
            lightDialCanvas.setPointerCapture(event.pointerId);
            this.applyLightDialFromPointer(event);
        });

        window.addEventListener('scroll', this.onWindowScroll);
        window.addEventListener('mouseup', this.onWindowMouseUp);
        window.addEventListener('mousemove', this.onWindowMouseMove);
        window.addEventListener('pointermove', this.onGizmoPointerMove);
        window.addEventListener('pointerup', this.onGizmoPointerUp);
        window.addEventListener('pointermove', this.onLightDialPointerMove);
        window.addEventListener('pointerup', this.onLightDialPointerUp);
        window.addEventListener('resize', this.onWindowResize);
    }

    setupThreeScene() {
        const viewport = this.renderRoot.querySelector('#viewport');
        const canvas = this.renderRoot.querySelector('#c');

        this.renderer = new THREE.WebGLRenderer({
            canvas: canvas,
            antialias: true,
            logarithmicDepthBuffer: true,
        });
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.setSize(viewport.offsetWidth, viewport.offsetHeight, false);
        this.renderer.outputEncoding = THREE.sRGBEncoding;
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xfff8dc);

        this.camera = new THREE.PerspectiveCamera(45, viewport.offsetWidth / viewport.offsetHeight, 0.01, 10000);
        this.camera.up.set(0, 0, 1);

        this.scene.add(new THREE.AmbientLight(0xffffff, 0.8));
        this.sun = new THREE.DirectionalLight(0xffffff, 0.75);
        this.sun.position.set(3, 2, 12);
        this.sun.castShadow = true;
        this.sun.shadow.bias = -0.00008;
        this.sun.shadow.mapSize.set(2048, 2048);
        this.scene.add(this.sun);
        const fill = new THREE.DirectionalLight(0xecf2ff, 0.45);
        fill.position.set(-4, 3, -6);
        this.scene.add(fill);

        this.solidMat = new THREE.MeshStandardMaterial({
            color: 0xafbccf,
            metalness: 0.02,
            roughness: 0.68,
            flatShading: true,
            polygonOffset: true,
            polygonOffsetFactor: 2,
            polygonOffsetUnits: 2,
            side: THREE.FrontSide,
        });
        this.edgeMat = new THREE.LineBasicMaterial({
            color: 0x5d6882,
            transparent: true,
            opacity: 0.42,
            depthTest: false,
            depthWrite: false,
        });

        this.createOrUpdateShadowCatcher(this.lastBounds);
        this.setupCameraGizmoScene();
        this.syncLightAnglesFromSun();
        this.drawLightDial();

        this.updateCamera();
        const animate = () => {
            this.animationHandle = requestAnimationFrame(animate);
            this.stepCameraAnimation();
            this.renderCameraGizmo();
            this.renderer.render(this.scene, this.camera);
        };
        animate();
    }

    onWindowMessage(event) {
        const message = event.data || {};
        if (message.type === 'refresh') {
            this.applyPayload({ frame: message.frame || {}, geometry: message.geometry || { meshes: [] } });
            return;
        }

        if (message.type === 'captureScreenshotRequest') {
            this.handleCaptureScreenshotRequest(message);
        }
    }

    async handleCaptureScreenshotRequest(message) {
        const requestId = message && message.requestId;
        const canvas = this.renderRoot.querySelector('#c');

        if (!vscode || !requestId) {
            return;
        }

        if (!canvas) {
            vscode.postMessage({
                type: 'captureScreenshotResult',
                requestId,
                ok: false,
                error: 'Renderer canvas was not found',
            });
            return;
        }

        await new Promise((resolve) => requestAnimationFrame(() => resolve()));

        try {
            const dataUrl = canvas.toDataURL('image/png');
            vscode.postMessage({
                type: 'captureScreenshotResult',
                requestId,
                ok: true,
                dataUrl,
                width: canvas.width,
                height: canvas.height,
            });
        } catch (error) {
            vscode.postMessage({
                type: 'captureScreenshotResult',
                requestId,
                ok: false,
                error: error && error.message ? error.message : 'Unknown screenshot capture error',
            });
        }
    }

    onWindowScroll() {
        const toV3d = this.renderRoot.querySelector('#to-v3d');
        toV3d.style.display = window.scrollY > 260 ? 'block' : 'none';
    }

    onWindowMouseUp() {
        this.dragging = false;
    }

    onWindowMouseMove(event) {
        if (!this.dragging) {
            return;
        }
        this.cameraUpVector.set(0, 0, 1);
        this.theta -= (event.clientX - this.lastX) * 0.008;
        this.phi = this.clampPhi(this.phi - (event.clientY - this.lastY) * 0.008);
        this.lastX = event.clientX;
        this.lastY = event.clientY;
        this.cameraAnimation = null;
        this.updateCamera();
    }

    onWindowResize() {
        const viewport = this.renderRoot.querySelector('#viewport');
        const width = viewport.offsetWidth;
        const height = viewport.offsetHeight;
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height, false);
        this.resizeGizmoRenderer();
        this.drawLightDial();
    }

    onGizmoPointerMove(event) {
        if (!this.gizmoDragging) {
            return;
        }
        const dx = event.clientX - this.gizmoLastX;
        const dy = event.clientY - this.gizmoLastY;
        if (Math.abs(dx) + Math.abs(dy) > 1) {
            this.gizmoMoved = true;
        }
        this.cameraUpVector.set(0, 0, 1);
        this.theta -= dx * 0.008;
        this.phi = this.clampPhi(this.phi - dy * 0.008);
        this.gizmoLastX = event.clientX;
        this.gizmoLastY = event.clientY;
        this.cameraAnimation = null;
        this.updateCamera();
    }

    onGizmoPointerUp(event) {
        if (!this.gizmoDragging) {
            return;
        }
        this.gizmoDragging = false;
        if (this.gizmoMoved) {
            return;
        }
        const canvas = this.renderRoot.querySelector('#gizmo-cube-c');
        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        this.snapCameraFromGizmoFace(x, y);
    }

    onLightDialPointerMove(event) {
        if (!this.lightDialDragging) {
            return;
        }
        this.applyLightDialFromPointer(event);
    }

    onLightDialPointerUp() {
        this.lightDialDragging = false;
    }

    fmt(value) {
        return (value * 1000).toFixed(1) + ' mm';
    }

    clampPhi(value) {
        return Math.max(0.05, Math.min(Math.PI - 0.05, value));
    }

    normalizeAngle(value) {
        let out = value;
        while (out <= -Math.PI) {
            out += Math.PI * 2;
        }
        while (out > Math.PI) {
            out -= Math.PI * 2;
        }
        return out;
    }

    shortestAngleDelta(from, to) {
        return this.normalizeAngle(to - from);
    }

    directionToAngles(direction) {
        const length = Math.sqrt(direction.x * direction.x + direction.y * direction.y + direction.z * direction.z) || 1;
        const nx = direction.x / length;
        const ny = direction.y / length;
        const nz = direction.z / length;
        const theta = Math.atan2(ny, nx);
        const phi = this.clampPhi(Math.acos(Math.max(-1, Math.min(1, nz))));
        return { theta, phi };
    }

    animateCameraTo(targetTheta, targetPhi, targetOrbitDist, durationMs = 260, targetUpVector = null) {
        const nextUp = targetUpVector || { x: 0, y: 0, z: 1 };
        this.cameraAnimation = {
            startedAt: performance.now(),
            durationMs,
            startTheta: this.theta,
            startPhi: this.phi,
            startDist: this.orbitDist,
            startUpX: this.cameraUpVector.x,
            startUpY: this.cameraUpVector.y,
            startUpZ: this.cameraUpVector.z,
            deltaTheta: this.shortestAngleDelta(this.theta, targetTheta),
            deltaPhi: targetPhi - this.phi,
            deltaDist: targetOrbitDist - this.orbitDist,
            targetUpX: nextUp.x,
            targetUpY: nextUp.y,
            targetUpZ: nextUp.z,
        };
    }

    stepCameraAnimation() {
        if (!this.cameraAnimation) {
            return;
        }
        const now = performance.now();
        const elapsed = now - this.cameraAnimation.startedAt;
        const t = Math.max(0, Math.min(1, elapsed / this.cameraAnimation.durationMs));
        const eased = 1 - Math.pow(1 - t, 3);

        this.theta = this.cameraAnimation.startTheta + this.cameraAnimation.deltaTheta * eased;
        this.phi = this.clampPhi(this.cameraAnimation.startPhi + this.cameraAnimation.deltaPhi * eased);
        this.orbitDist = Math.max(0.01, this.cameraAnimation.startDist + this.cameraAnimation.deltaDist * eased);
        this.cameraUpVector.set(
            this.cameraAnimation.startUpX + (this.cameraAnimation.targetUpX - this.cameraAnimation.startUpX) * eased,
            this.cameraAnimation.startUpY + (this.cameraAnimation.targetUpY - this.cameraAnimation.startUpY) * eased,
            this.cameraAnimation.startUpZ + (this.cameraAnimation.targetUpZ - this.cameraAnimation.startUpZ) * eased,
        ).normalize();
        this.updateCamera();

        if (t >= 1) {
            this.cameraAnimation = null;
        }
    }

    getSelectionBounds() {
        return this.getSceneBounds();
    }

    focusSelection() {
        const bounds = this.getSelectionBounds();
        this.lastBounds = bounds;
        this.cx = (bounds.minX + bounds.maxX) / 2;
        this.cy = (bounds.minY + bounds.maxY) / 2;
        this.cz = (bounds.minZ + bounds.maxZ) / 2;
        const dx = bounds.maxX - bounds.minX;
        const dy = bounds.maxY - bounds.minY;
        const dz = bounds.maxZ - bounds.minZ;
        const radius = Math.sqrt(dx * dx + dy * dy + dz * dz) / 2 || 5;
        const fovRad = this.camera.fov * Math.PI / 180;
        const targetDist = radius / Math.sin(fovRad / 2) * 1.3;
        this.animateCameraTo(-Math.PI / 2, Math.PI / 2, targetDist, 280, { x: 0, y: 0, z: 1 });
        this.updateLightFromAngles();
    }

    createGizmoFaceMaterial(label, backgroundColor) {
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 256;
        const context = canvas.getContext('2d');

        context.fillStyle = backgroundColor;
        context.fillRect(0, 0, canvas.width, canvas.height);

        context.strokeStyle = 'rgba(93, 104, 130, 0.35)';
        context.lineWidth = 10;
        context.strokeRect(16, 16, canvas.width - 32, canvas.height - 32);

        context.fillStyle = '#39496e';
        context.textAlign = 'center';
        context.textBaseline = 'middle';
        context.font = '600 42px Segoe UI';
        context.fillText(label, canvas.width / 2, canvas.height / 2);

        const texture = new THREE.CanvasTexture(canvas);
        texture.needsUpdate = true;
        return new THREE.MeshStandardMaterial({ color: 0xffffff, map: texture });
    }

    createOrUpdateShadowCatcher(bounds) {
        const dx = bounds.maxX - bounds.minX;
        const dy = bounds.maxY - bounds.minY;
        const centerX = (bounds.minX + bounds.maxX) / 2;
        const centerY = (bounds.minY + bounds.maxY) / 2;
        const groundZ = bounds.minZ - 0.0005;
        this.shadowSize = Math.max(60, Math.max(dx, dy) * 8 || 60);

        if (!this.shadowCatcher) {
            this.shadowCatcher = new THREE.Mesh(
                new THREE.PlaneBufferGeometry(1, 1),
                new THREE.ShadowMaterial({ opacity: 0.22 })
            );
            this.shadowCatcher.receiveShadow = true;
            this.shadowCatcher.renderOrder = 1;
            this.scene.add(this.shadowCatcher);
        } else {
            this.shadowCatcher.geometry.dispose();
            this.shadowCatcher.geometry = new THREE.PlaneBufferGeometry(1, 1);
        }

        this.shadowCatcher.position.set(centerX, centerY, groundZ + 0.0001);
        this.shadowCatcher.scale.set(this.shadowSize, this.shadowSize, 1);
        this.configureShadowCamera(bounds, this.shadowSize);
    }

    configureShadowCamera(bounds, size) {
        if (!this.sun || !this.sun.shadow || !this.sun.shadow.camera) {
            return;
        }
        const shadowCam = this.sun.shadow.camera;
        const half = size / 2;
        shadowCam.left = -half;
        shadowCam.right = half;
        shadowCam.top = half;
        shadowCam.bottom = -half;
        shadowCam.near = 0.5;
        shadowCam.far = Math.max(40, (bounds.maxZ - bounds.minZ) * 8 || 40);
        shadowCam.updateProjectionMatrix();
        const centerX = (bounds.minX + bounds.maxX) / 2;
        const centerY = (bounds.minY + bounds.maxY) / 2;
        const centerZ = (bounds.minZ + bounds.maxZ) / 2;
        this.sun.target.position.set(centerX, centerY, centerZ);
        if (!this.sun.target.parent) {
            this.scene.add(this.sun.target);
        }
    }

    setupCameraGizmoScene() {
        const canvas = this.renderRoot.querySelector('#gizmo-cube-c');
        this.gizmoRenderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
        this.gizmoRenderer.setClearColor(0x000000, 0);

        this.gizmoScene = new THREE.Scene();
        this.gizmoCamera = new THREE.PerspectiveCamera(35, 1, 0.1, 20);

        this.gizmoScene.add(new THREE.AmbientLight(0xffffff, 0.82));
        const light = new THREE.DirectionalLight(0xffffff, 0.65);
        light.position.set(2, 2, 3);
        this.gizmoScene.add(light);

        const materials = [
            this.createGizmoFaceMaterial('right', '#c9d6ea'),
            this.createGizmoFaceMaterial('left', '#bfcee4'),
            this.createGizmoFaceMaterial('back', '#d6deee'),
            this.createGizmoFaceMaterial('front', '#c4d2e8'),
            this.createGizmoFaceMaterial('top', '#bccbe2'),
            this.createGizmoFaceMaterial('bottom', '#b6c6df'),
        ];
        this.gizmoCube = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), materials);
        this.gizmoScene.add(this.gizmoCube);
        this.resizeGizmoRenderer();
    }

    getCameraSnapForDirection(direction) {
        const angles = this.directionToAngles(direction);
        if (direction.z > 0) {
            return { theta: angles.theta, phi: angles.phi, upVector: { x: 0, y: 1, z: 0 } };
        }
        if (direction.z < 0) {
            return { theta: angles.theta, phi: angles.phi, upVector: { x: 0, y: -1, z: 0 } };
        }
        return { theta: angles.theta, phi: angles.phi, upVector: { x: 0, y: 0, z: 1 } };
    }

    resizeGizmoRenderer() {
        if (!this.gizmoRenderer || !this.gizmoCamera) {
            return;
        }
        const canvas = this.renderRoot.querySelector('#gizmo-cube-c');
        const width = Math.max(1, canvas.clientWidth);
        const height = Math.max(1, canvas.clientHeight);
        this.gizmoRenderer.setPixelRatio(window.devicePixelRatio || 1);
        this.gizmoRenderer.setSize(width, height, false);
        this.gizmoCamera.aspect = width / height;
        this.gizmoCamera.updateProjectionMatrix();
    }

    renderCameraGizmo() {
        if (!this.gizmoRenderer || !this.gizmoCamera || !this.camera) {
            return;
        }
        const dx = this.camera.position.x - this.cx;
        const dy = this.camera.position.y - this.cy;
        const dz = this.camera.position.z - this.cz;
        const length = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1;
        this.gizmoCamera.position.set((dx / length) * 2.8, (dy / length) * 2.8, (dz / length) * 2.8);
        this.gizmoCamera.up.set(0, 0, 1);
        this.gizmoCamera.lookAt(0, 0, 0);
        this.gizmoRenderer.render(this.gizmoScene, this.gizmoCamera);
    }

    snapCameraFromGizmoFace(localX, localY) {
        if (!this.gizmoCube || !this.gizmoCamera) {
            return;
        }
        const canvas = this.renderRoot.querySelector('#gizmo-cube-c');
        const width = canvas.clientWidth || 1;
        const height = canvas.clientHeight || 1;

        this.gizmoPointer.x = (localX / width) * 2 - 1;
        this.gizmoPointer.y = -((localY / height) * 2 - 1);
        this.gizmoRaycaster.setFromCamera(this.gizmoPointer, this.gizmoCamera);
        const hits = this.gizmoRaycaster.intersectObject(this.gizmoCube, false);
        if (!hits.length || !hits[0].face) {
            return;
        }

        const normal = hits[0].face.normal;
        const ax = Math.abs(normal.x);
        const ay = Math.abs(normal.y);
        const az = Math.abs(normal.z);
        let direction;

        if (ax >= ay && ax >= az) {
            direction = { x: Math.sign(normal.x), y: 0, z: 0 };
        } else if (ay >= ax && ay >= az) {
            direction = { x: 0, y: Math.sign(normal.y), z: 0 };
        } else {
            direction = { x: 0, y: 0, z: Math.sign(normal.z) };
        }

        const snap = this.getCameraSnapForDirection(direction);
        this.animateCameraTo(snap.theta, snap.phi, this.orbitDist, 260, snap.upVector);
    }

    syncLightAnglesFromSun() {
        if (!this.sun) {
            return;
        }
        const dx = this.sun.position.x - this.cx;
        const dy = this.sun.position.y - this.cy;
        const dz = this.sun.position.z - this.cz;
        const distance = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1;
        this.lightDistance = distance;
        this.lightAzimuth = Math.atan2(dy, dx);
        this.lightElevation = Math.max(0.2, Math.min(1.3, Math.asin(dz / distance)));
    }

    updateLightFromAngles() {
        if (!this.sun) {
            return;
        }
        const cosElevation = Math.cos(this.lightElevation);
        const dx = cosElevation * Math.cos(this.lightAzimuth) * this.lightDistance;
        const dy = cosElevation * Math.sin(this.lightAzimuth) * this.lightDistance;
        const dz = Math.sin(this.lightElevation) * this.lightDistance;

        this.sun.position.set(this.cx + dx, this.cy + dy, this.cz + dz);
        this.sun.target.position.set(this.cx, this.cy, this.cz);
        if (!this.sun.target.parent) {
            this.scene.add(this.sun.target);
        }
        this.configureShadowCamera(this.lastBounds, this.shadowSize || 60);
    }

    drawLightDial() {
        const canvas = this.renderRoot.querySelector('#light-dial-c');
        if (!canvas) {
            return;
        }
        const width = Math.max(1, canvas.clientWidth);
        const height = Math.max(1, canvas.clientHeight);
        const ratio = window.devicePixelRatio || 1;
        canvas.width = Math.floor(width * ratio);
        canvas.height = Math.floor(height * ratio);

        const context = canvas.getContext('2d');
        context.setTransform(ratio, 0, 0, ratio, 0, 0);
        context.clearRect(0, 0, width, height);

        const cx = width / 2;
        const cy = height / 2;
        const radius = Math.min(width, height) * 0.36;

        context.strokeStyle = 'rgba(88, 115, 166, 0.5)';
        context.lineWidth = 2;
        context.beginPath();
        context.arc(cx, cy, radius, 0, Math.PI * 2);
        context.stroke();

        const minElevation = 0.2;
        const maxElevation = 1.3;
        const elevationRatio = (this.lightElevation - minElevation) / (maxElevation - minElevation);
        const knobRadius = radius * (1 - elevationRatio * 0.85);
        const knobX = cx + Math.cos(this.lightAzimuth) * knobRadius;
        const knobY = cy + Math.sin(this.lightAzimuth) * knobRadius;

        context.strokeStyle = 'rgba(88, 115, 166, 0.45)';
        context.lineWidth = 1.5;
        context.beginPath();
        context.moveTo(cx, cy);
        context.lineTo(knobX, knobY);
        context.stroke();

        context.fillStyle = '#5873a6';
        context.beginPath();
        context.arc(knobX, knobY, 5, 0, Math.PI * 2);
        context.fill();
    }

    applyLightDialFromPointer(event) {
        const canvas = this.renderRoot.querySelector('#light-dial-c');
        if (!canvas) {
            return;
        }
        const rect = canvas.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        const dx = event.clientX - cx;
        const dy = event.clientY - cy;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const maxDistance = Math.min(rect.width, rect.height) * 0.36;

        const minElevation = 0.2;
        const maxElevation = 1.3;
        const clampedDistance = Math.min(maxDistance, distance);

        this.lightAzimuth = Math.atan2(dy, dx);
        this.lightElevation = minElevation + (1 - clampedDistance / Math.max(1, maxDistance)) * (maxElevation - minElevation);
        this.updateLightFromAngles();
        this.drawLightDial();
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
        const tbody = this.renderRoot.querySelector('#timber-rows');
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
        this.renderRoot.querySelector('#info').innerHTML =
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

        this.renderRoot.querySelector('#debug').innerHTML =
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
            const indexedGeometry = new THREE.BufferGeometry();
            indexedGeometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
            indexedGeometry.setIndex(mesh.indices || []);

            const geometry = indexedGeometry.toNonIndexed();
            geometry.computeVertexNormals();
            geometry.computeBoundingSphere();
            indexedGeometry.dispose();

            const solidMesh = new THREE.Mesh(geometry, this.solidMat);
            const edgeGeometry = new THREE.EdgesGeometry(geometry, 25);
            const edgeMesh = new THREE.LineSegments(edgeGeometry, this.edgeMat);
            solidMesh.renderOrder = 1;
            edgeMesh.renderOrder = 2;
            solidMesh.castShadow = true;
            solidMesh.receiveShadow = true;

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

        this.renderRoot.querySelector('#raw-output').textContent = JSON.stringify({
            frame: frameData,
            geometry: geometryData,
        }, null, 2);

        const bounds = this.getSceneBounds();
        this.lastBounds = bounds;
        this.createOrUpdateShadowCatcher(bounds);
        this.cx = (bounds.minX + bounds.maxX) / 2;
        this.cy = (bounds.minY + bounds.maxY) / 2;
        this.cz = (bounds.minZ + bounds.maxZ) / 2;
        const dx = bounds.maxX - bounds.minX;
        const dy = bounds.maxY - bounds.minY;
        const dz = bounds.maxZ - bounds.minZ;
        const radius = Math.sqrt(dx * dx + dy * dy + dz * dz) / 2 || 5;
        const fovRad = this.camera.fov * Math.PI / 180;
        this.orbitDist = radius / Math.sin(fovRad / 2) * 1.3;
        this.lightDistance = Math.max(12, radius * 4);
        this.camera.near = Math.max(0.1, radius * 0.03);
        this.camera.far = Math.max(200, radius * 20);
        this.camera.updateProjectionMatrix();
        this.updateCamera();
        this.updateLightFromAngles();
        this.drawLightDial();
    }

    updateCamera() {
        if (!this.camera) {
            return;
        }
        this.camera.position.set(
            this.cx + this.orbitDist * Math.sin(this.phi) * Math.cos(this.theta),
            this.cy + this.orbitDist * Math.sin(this.phi) * Math.sin(this.theta),
            this.cz + this.orbitDist * Math.cos(this.phi)
        );
        this.camera.up.copy(this.cameraUpVector);
        this.camera.lookAt(this.cx, this.cy, this.cz);
    }
}

customElements.define('horsey-viewer-app', HorseyViewerApp);
