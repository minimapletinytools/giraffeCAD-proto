(function (globalScope) {
    // LayersPanel renders a collapsible overlay tree on the left edge of the viewport.
    // It syncs bidirectionally with SelectionStore: canvas clicks highlight the
    // corresponding row, and clicking a row updates the canvas selection.
    class LayersPanel {
        constructor(selectionManager, layerStateStore) {
            this.selectionManager = selectionManager;
            this.layerStateStore = layerStateStore;
            this.hierarchy = null;
            this.collapsed = false;
            // Default: top-level sections open, individual nodes closed
            this.expandedNodes = new Set(['section:timbers', 'section:joints']);
            this.el = null;
            this.viewport = null;
            this._unsubSelection = null;
            this._unsubLayerState = null;
        }

        mount(viewport) {
            this.viewport = viewport;
            this.el = document.createElement('div');
            this.el.id = 'layers-panel';
            viewport.insertBefore(this.el, viewport.firstChild);
            this._render();

            this._unsubSelection = this.selectionManager.onSelectionChanged(() => {
                this._syncHighlight();
            });
            this._unsubLayerState = this.layerStateStore.onStateChanged(() => {
                this._updateStateIcons();
            });
        }

        setHierarchy(hierarchy) {
            this.hierarchy = hierarchy || { timbers: [], joints: [] };
            const allKeys = [
                ...this.hierarchy.timbers.map(t => t.key),
                ...(this.hierarchy.joints || []).flatMap(j => [...(j.timberKeys || []), ...(j.accessoryKeys || [])]),
            ];
            this.layerStateStore.pruneKeys(allKeys);
            this._render();
        }

        destroy() {
            if (this._unsubSelection) this._unsubSelection();
            if (this._unsubLayerState) this._unsubLayerState();
            if (this.el && this.el.parentNode) this.el.parentNode.removeChild(this.el);
            this.el = null;
        }

        // ------------------------------------------------------------------
        // Rendering
        // ------------------------------------------------------------------

        _render() {
            if (!this.el) return;
            this.el.innerHTML = '';
            this.el.className = 'lp-panel ' + (this.collapsed ? 'lp-collapsed' : 'lp-expanded');
            if (this.viewport) {
                this.viewport.classList.toggle('lp-open', !this.collapsed);
            }

            const toggleBtn = document.createElement('button');
            toggleBtn.className = 'lp-toggle-btn';
            toggleBtn.title = this.collapsed ? 'Expand layers' : 'Collapse layers';
            toggleBtn.textContent = this.collapsed ? '▷' : '◁';
            toggleBtn.addEventListener('click', () => {
                this.collapsed = !this.collapsed;
                this._render();
            });
            this.el.appendChild(toggleBtn);

            if (this.collapsed) return;

            const header = document.createElement('div');
            header.className = 'lp-header';
            header.textContent = 'Layers';
            this.el.appendChild(header);

            const tree = document.createElement('div');
            tree.className = 'lp-tree';
            this.el.appendChild(tree);

            this._renderSection(tree, 'timbers', 'Timbers', () => this._buildTimberRows());
            this._renderSection(tree, 'joints', 'Joints', () => this._buildJointRows());
            this._syncHighlight();
        }

        _renderSection(parent, sectionId, title, buildRows) {
            const nodeId = 'section:' + sectionId;
            const expanded = this.expandedNodes.has(nodeId);

            const section = document.createElement('div');
            section.className = 'lp-section';

            const sectionHeader = document.createElement('div');
            sectionHeader.className = 'lp-section-header' + (expanded ? ' lp-open' : '');
            const chevSpan = document.createElement('span');
            chevSpan.className = 'lp-chev';
            chevSpan.textContent = expanded ? '▾' : '▸';
            sectionHeader.appendChild(chevSpan);
            const titleSpan = document.createElement('span');
            titleSpan.textContent = ' ' + title;
            sectionHeader.appendChild(titleSpan);
            sectionHeader.addEventListener('click', () => {
                this._toggle(nodeId);
            });
            section.appendChild(sectionHeader);

            if (expanded) {
                const body = document.createElement('div');
                body.className = 'lp-section-body';
                for (const row of buildRows()) {
                    body.appendChild(row);
                }
                section.appendChild(body);
            }

            parent.appendChild(section);
        }

        _makeRow(opts) {
            const { nodeId, rowType, depth, label, hasChildren, selectNode, memberKey } = opts;
            const expanded = hasChildren && this.expandedNodes.has(nodeId);

            const row = document.createElement('div');
            row.className = 'lp-row lp-row-' + rowType + ' lp-depth-' + depth;
            row.dataset.nodeId = nodeId;
            if (memberKey) row.dataset.memberKey = memberKey;

            // Chevron / expand control
            const chev = document.createElement('span');
            chev.className = 'lp-chev' + (hasChildren ? ' lp-has-children' : ' lp-leaf');
            chev.textContent = hasChildren ? (expanded ? '▾' : '▸') : '';
            if (hasChildren) {
                chev.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this._toggle(nodeId);
                });
            }
            row.appendChild(chev);

            const labelEl = document.createElement('span');
            labelEl.className = 'lp-label';
            labelEl.textContent = label;
            row.appendChild(labelEl);

            // Lock / hide icon buttons (only for member-level rows)
            if (memberKey) {
                const icons = document.createElement('span');
                icons.className = 'lp-icons';

                const lockBtn = document.createElement('button');
                lockBtn.className = 'lp-icon-btn lp-btn-lock';
                lockBtn.dataset.action = 'lock';
                lockBtn.title = 'Lock';
                lockBtn.textContent = '🔒';
                lockBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.layerStateStore.toggleLocked(memberKey);
                });
                icons.appendChild(lockBtn);

                const hideBtn = document.createElement('button');
                hideBtn.className = 'lp-icon-btn lp-btn-hide';
                hideBtn.dataset.action = 'hide';
                hideBtn.title = 'Hide';
                hideBtn.textContent = '👁';
                hideBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.layerStateStore.toggleHidden(memberKey);
                });
                icons.appendChild(hideBtn);

                row.appendChild(icons);
            }

            if (selectNode) {
                row.classList.add('lp-selectable');
                row.addEventListener('click', () => {
                    this.selectionManager.selectLayerNode(selectNode);
                });
            }

            return row;
        }

        _buildTimberRows() {
            const rows = [];
            if (!this.hierarchy) return rows;

            for (const timber of this.hierarchy.timbers) {
                rows.push(this._makeRow({
                    nodeId: 'timber:' + timber.key,
                    rowType: 'timber',
                    depth: 0,
                    label: timber.name,
                    hasChildren: false,
                    memberKey: timber.key,
                    selectNode: { type: 'timber', key: timber.key },
                }));
            }
            return rows;
        }

        _buildJointRows() {
            const rows = [];
            if (!this.hierarchy) return rows;

            const nameByKey = {};
            for (const t of this.hierarchy.timbers) nameByKey[t.key] = t.name;

            for (const joint of (this.hierarchy.joints || [])) {
                const jointNodeId = 'joint:' + joint.id;
                const members = [...(joint.timberKeys || []), ...(joint.accessoryKeys || [])];
                const hasChildren = members.length > 0;

                rows.push(this._makeRow({
                    nodeId: jointNodeId,
                    rowType: 'joint',
                    depth: 0,
                    label: joint.name,
                    hasChildren,
                    selectNode: { type: 'joint', jointId: joint.id, timberKeys: joint.timberKeys || [] },
                }));

                if (!hasChildren || !this.expandedNodes.has(jointNodeId)) continue;

                for (const timberKey of (joint.timberKeys || [])) {
                    rows.push(this._makeRow({
                        nodeId: 'jm:' + joint.id + ':' + timberKey,
                        rowType: 'jointMember',
                        depth: 1,
                        label: nameByKey[timberKey] || timberKey,
                        hasChildren: false,
                        selectNode: { type: 'timber', key: timberKey },
                    }));
                }

                for (const accKey of (joint.accessoryKeys || [])) {
                    rows.push(this._makeRow({
                        nodeId: 'jm:' + joint.id + ':' + accKey,
                        rowType: 'jointMember',
                        depth: 1,
                        label: accKey.replace(/^accessory:[^:]+:/, '').replace(/^accessory:/, ''),
                        hasChildren: false,
                        selectNode: { type: 'accessory', key: accKey },
                    }));
                }
            }
            return rows;
        }

        // ------------------------------------------------------------------
        // Selection sync
        // ------------------------------------------------------------------

        _syncHighlight() {
            if (!this.el) return;

            for (const row of this.el.querySelectorAll('.lp-row.lp-selected')) {
                row.classList.remove('lp-selected');
            }

            const selectedTimbers = this.selectionManager.selectedTimbers;

            // Canvas-driven: highlight timber/accessory rows that match selected keys
            for (const key of selectedTimbers) {
                const safeKey = CSS.escape(key);
                for (const row of this.el.querySelectorAll('.lp-row[data-member-key="' + safeKey + '"]')) {
                    row.classList.add('lp-selected');
                }
                for (const row of this.el.querySelectorAll('.lp-row[data-node-id="timber:' + safeKey + '"]')) {
                    row.classList.add('lp-selected');
                }
                // Joint members referencing this key
                for (const row of this.el.querySelectorAll('.lp-row-jointMember[data-node-id$=":' + safeKey + '"]')) {
                    row.classList.add('lp-selected');
                }
            }

            // Layer-node driven: scroll to and highlight the specific node
            const layerNode = this.selectionManager.selectedLayerNode;
            if (layerNode) {
                let nodeId = null;
                if (layerNode.type === 'timber') nodeId = 'timber:' + layerNode.key;
                else if (layerNode.type === 'cutting') nodeId = 'cutting:' + layerNode.timberKey + ':' + layerNode.cuttingIdx;
                else if (layerNode.type === 'csgNode' && layerNode.path && layerNode.path[0]) {
                    // cuttingIdx is carried in the node descriptor since the row builder sets it
                    const cuttingIdx = layerNode.cuttingIdx != null ? layerNode.cuttingIdx : 0;
                    nodeId = 'csgnode:' + layerNode.timberKey + ':' + cuttingIdx + ':' + layerNode.path[0];
                }
                else if (layerNode.type === 'joint') nodeId = 'joint:' + layerNode.jointId;
                else if (layerNode.type === 'accessory') nodeId = 'timber:' + layerNode.key;

                if (nodeId) {
                    const row = this.el.querySelector('.lp-row[data-node-id="' + CSS.escape(nodeId) + '"]');
                    if (row) {
                        row.classList.add('lp-selected');
                        row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
                    }
                }
            } else if (selectedTimbers.size === 1) {
                // Scroll to selected timber row (canvas click)
                const key = Array.from(selectedTimbers)[0];
                const row = this.el.querySelector('.lp-row[data-node-id="timber:' + CSS.escape(key) + '"]');
                if (row) row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            }
        }

        _updateStateIcons() {
            if (!this.el) return;
            for (const row of this.el.querySelectorAll('.lp-row[data-member-key]')) {
                const key = row.dataset.memberKey;
                const state = this.layerStateStore.getState(key);
                const lockBtn = row.querySelector('[data-action="lock"]');
                const hideBtn = row.querySelector('[data-action="hide"]');
                if (lockBtn) {
                    lockBtn.classList.toggle('lp-active', state.locked);
                    lockBtn.title = state.locked ? 'Unlock' : 'Lock';
                }
                if (hideBtn) {
                    hideBtn.classList.toggle('lp-active', state.hidden);
                    hideBtn.title = state.hidden ? 'Show' : 'Hide';
                }
            }
        }

        // ------------------------------------------------------------------
        // Helpers
        // ------------------------------------------------------------------

        _toggle(nodeId) {
            if (this.expandedNodes.has(nodeId)) {
                this.expandedNodes.delete(nodeId);
            } else {
                this.expandedNodes.add(nodeId);
            }
            this._render();
        }
    }

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = { LayersPanel };
    }
    globalScope.LayersPanel = LayersPanel;
})(typeof window !== 'undefined' ? window : globalThis);
