import { LitElement, html } from 'https://unpkg.com/lit@3.2.0/index.js?module';

const INITIAL_PAYLOAD = window.__HORSEY_INITIAL_PAYLOAD__ || { frame: {}, geometry: { meshes: [] } };

class HorseyViewerApp extends LitElement {
    constructor() {
        super();
        this.meshObjectsByKey = new Map();
        this.enableShadows = true;
        this.enableReflections = false;
        this.ground = null;
        this.shadowCatcher = null;
        this.sun = null;
        this.lastBounds = null;
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

    createRenderRoot() {
        return this;
    }

    render() {
        return html`
            <button id="to-v3d" title="Jump back to 3D view">to v3d view</button>
            <div id="viewport">
                <canvas id="c"></canvas>
                <div id="info"></div>
                <div id="debug"></div>
                <div id="render-controls">
                    <label><input id="toggle-shadows" type="checkbox" checked> shadows</label>
                    <label><input id="toggle-reflections" type="checkbox"> reflections</label>
                </div>
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
        if (this.animationHandle) {
            cancelAnimationFrame(this.animationHandle);
            this.animationHandle = null;
        }
        for (const bundle of this.meshObjectsByKey.values()) {
            this.disposeMeshBundle(bundle);
        }
        this.meshObjectsByKey.clear();
        this.disposeGround();
        if (this.shadowCatcher) {
            this.scene.remove(this.shadowCatcher);
            this.shadowCatcher.geometry.dispose();
            this.shadowCatcher.material.dispose();
            this.shadowCatcher = null;
        }
    }

    setupUiEvents() {
        const toV3d = this.renderRoot.querySelector('#to-v3d');
        const canvas = this.renderRoot.querySelector('#c');
        const viewport = this.renderRoot.querySelector('#viewport');
        const shadowToggle = this.renderRoot.querySelector('#toggle-shadows');
        const reflectionToggle = this.renderRoot.querySelector('#toggle-reflections');

        shadowToggle.checked = this.enableShadows;
        reflectionToggle.checked = this.enableReflections;

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

        shadowToggle.addEventListener('change', () => {
            this.enableShadows = shadowToggle.checked;
            this.syncRenderMode();
        });

        reflectionToggle.addEventListener('change', () => {
            this.enableReflections = reflectionToggle.checked;
            this.createOrUpdateGround(this.lastBounds || { minX: -1, minY: -1, minZ: -1, maxX: 1, maxY: 1, maxZ: 1 });
        });

        window.addEventListener('scroll', this.onWindowScroll);
        window.addEventListener('mouseup', this.onWindowMouseUp);
        window.addEventListener('mousemove', this.onWindowMouseMove);
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
        this.renderer.shadowMap.enabled = this.enableShadows;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xfff8dc);

        this.camera = new THREE.PerspectiveCamera(45, viewport.offsetWidth / viewport.offsetHeight, 0.01, 10000);
        this.camera.up.set(0, 0, 1);

        this.scene.add(new THREE.AmbientLight(0xffffff, 0.8));
        this.sun = new THREE.DirectionalLight(0xffffff, 0.75);
        this.sun.position.set(3, 2, 12);
        this.sun.castShadow = this.enableShadows;
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

        this.createOrUpdateGround({ minX: -1, minY: -1, minZ: -1, maxX: 1, maxY: 1, maxZ: 1 });
        this.syncRenderMode();

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
        this.theta -= (event.clientX - this.lastX) * 0.008;
        this.phi = Math.max(0.05, Math.min(Math.PI - 0.05, this.phi - (event.clientY - this.lastY) * 0.008));
        this.lastX = event.clientX;
        this.lastY = event.clientY;
        this.updateCamera();
    }

    onWindowResize() {
        const viewport = this.renderRoot.querySelector('#viewport');
        const width = viewport.offsetWidth;
        const height = viewport.offsetHeight;
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height, false);
    }

    fmt(value) {
        return (value * 1000).toFixed(1) + ' mm';
    }

    disposeGround() {
        if (!this.ground) {
            return;
        }
        this.scene.remove(this.ground);
        if (this.ground.geometry) {
            this.ground.geometry.dispose();
        }
        if (this.ground.material && this.ground.material.dispose) {
            this.ground.material.dispose();
        }
        this.ground = null;
    }

    createOrUpdateGround(bounds) {
        const dx = bounds.maxX - bounds.minX;
        const dy = bounds.maxY - bounds.minY;
        const centerX = (bounds.minX + bounds.maxX) / 2;
        const centerY = (bounds.minY + bounds.maxY) / 2;
        const groundZ = bounds.minZ - 0.0005;
        const reflectorSize = Math.max(6, Math.max(dx, dy) * 1.8 || 6);
        const shadowSize = Math.max(60, Math.max(dx, dy) * 8 || 60);

        this.disposeGround();

        if (this.enableReflections && THREE.Reflector) {
            this.ground = new THREE.Reflector(new THREE.PlaneBufferGeometry(reflectorSize, reflectorSize), {
                clipBias: 0.003,
                textureWidth: Math.max(256, Math.floor(window.innerWidth * window.devicePixelRatio)),
                textureHeight: Math.max(256, Math.floor(window.innerHeight * window.devicePixelRatio)),
                color: 0xfff8dc,
            });
            this.ground.position.set(centerX, centerY, groundZ);
            this.ground.material.transparent = true;
            this.ground.material.opacity = 0.5;
            this.ground.material.depthWrite = false;
            this.scene.add(this.ground);
        }

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
        this.shadowCatcher.scale.set(shadowSize, shadowSize, 1);
        this.syncRenderMode();
        this.configureShadowCamera(bounds, shadowSize);
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

    syncRenderMode() {
        if (!this.renderer) {
            return;
        }
        this.renderer.shadowMap.enabled = this.enableShadows;

        if (this.sun) {
            this.sun.castShadow = this.enableShadows;
        }

        this.meshObjectsByKey.forEach((bundle) => {
            bundle.mesh.castShadow = this.enableShadows;
            bundle.mesh.receiveShadow = this.enableShadows;
        });

        if (this.ground) {
            this.ground.visible = true;
        }

        if (this.shadowCatcher) {
            this.shadowCatcher.visible = this.enableShadows;
        }
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
            solidMesh.castShadow = this.enableShadows;
            solidMesh.receiveShadow = this.enableShadows;

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
        this.createOrUpdateGround(bounds);
        this.cx = (bounds.minX + bounds.maxX) / 2;
        this.cy = (bounds.minY + bounds.maxY) / 2;
        this.cz = (bounds.minZ + bounds.maxZ) / 2;
        const dx = bounds.maxX - bounds.minX;
        const dy = bounds.maxY - bounds.minY;
        const dz = bounds.maxZ - bounds.minZ;
        const radius = Math.sqrt(dx * dx + dy * dy + dz * dz) / 2 || 5;
        const fovRad = this.camera.fov * Math.PI / 180;
        this.orbitDist = radius / Math.sin(fovRad / 2) * 1.3;
        this.camera.near = Math.max(0.1, radius * 0.03);
        this.camera.far = Math.max(200, radius * 20);
        this.camera.updateProjectionMatrix();
        this.updateCamera();
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
        this.camera.lookAt(this.cx, this.cy, this.cz);
    }
}

customElements.define('horsey-viewer-app', HorseyViewerApp);
