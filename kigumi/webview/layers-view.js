// layers-view.js
// LitElement webview component for the Layers panel.
//
// Connects:
//   - LayersModel (from layers-model.js): tree data + selection mapping.
//   - SelectionStore: shared selection state with the 3D viewer.
//   - vscode.postMessage: requests lazy CSG-tree loads through the extension
//     host (handled by frame-view-session.js).

import { LitElement, html } from 'https://unpkg.com/lit@3.2.0/index.js?module';

const LayersModel = window.LayersModel;

const COLLAPSE_LABEL = '«';
const EXPAND_LABEL = '»';

class KigumiLayersView extends LitElement {
    static properties = {
        collapsed: { type: Boolean },
    };

    constructor() {
        super();
        this.collapsed = false;
        this.tree = null;
        this.expanded = new Set();
        this.highlightedNodeIds = new Set();
        this.requestedCSGTrees = new Set();
        this.selectionStore = null;
        this.vscode = null;
        this._unsubscribe = null;
        // Always expand the three top-level folders by default.
        if (LayersModel) {
            this.expanded.add(LayersModel.makeFolderId(LayersModel.FOLDER_TIMBERS));
            this.expanded.add(LayersModel.makeFolderId(LayersModel.FOLDER_JOINTS));
            this.expanded.add(LayersModel.makeFolderId(LayersModel.FOLDER_UNATTACHED));
        }
    }

    // Render into light DOM so the existing global stylesheet (viewer.css)
    // applies, matching the rest of the viewer panels.
    createRenderRoot() {
        return this;
    }

    attach(selectionStore, vscode) {
        this.selectionStore = selectionStore;
        this.vscode = vscode;
        if (selectionStore && typeof selectionStore.onSelectionChanged === 'function') {
            this._unsubscribe = selectionStore.onSelectionChanged(() => {
                this._refreshHighlights();
            });
        }
        this._refreshHighlights();
    }

    detach() {
        if (typeof this._unsubscribe === 'function') {
            this._unsubscribe();
            this._unsubscribe = null;
        }
    }

    setLayersPayload(payload) {
        if (!LayersModel) return;
        this.tree = LayersModel.buildLayersTree(payload || {});
        this.requestedCSGTrees.clear();
        this._refreshHighlights();
        this.requestUpdate();
    }

    mergeCSGTreePayload(payload) {
        if (!LayersModel || !this.tree) return;
        const merged = LayersModel.mergeCSGTreeIntoCut(this.tree, payload);
        if (merged) {
            this.requestUpdate();
        }
    }

    toggleCollapsed() {
        this.collapsed = !this.collapsed;
    }

    _refreshHighlights() {
        if (!LayersModel || !this.tree || !this.selectionStore) {
            this.highlightedNodeIds = new Set();
            this.requestUpdate();
            return;
        }
        const memberKeys = typeof this.selectionStore.getSelectedTimbers === 'function'
            ? this.selectionStore.getSelectedTimbers()
            : [];
        const csgSelection = this.selectionStore.csgSelection || null;
        this.highlightedNodeIds = LayersModel.selectionSnapshotToNodeIds(this.tree, {
            selectedTimberMemberKeys: memberKeys,
            csgSelection,
        });
        this.requestUpdate();
    }

    _onNodeClick(node, event) {
        if (event && event.target && event.target.classList && event.target.classList.contains('layers-disclosure')) {
            return;
        }
        if (!LayersModel || !this.tree || !this.selectionStore) return;
        const action = LayersModel.nodeIdToSelectionAction(this.tree, node.id);
        const additive = !!(event && (event.shiftKey || event.metaKey || event.ctrlKey));
        switch (action.kind) {
            case 'selectTimber':
                if (action.memberKey) {
                    this.selectionStore.clearCSGSelection();
                    this.selectionStore.selectTimber(action.memberKey, additive);
                }
                break;
            case 'selectAccessory':
                if (action.memberKey) {
                    this.selectionStore.clearCSGSelection();
                    this.selectionStore.selectTimber(action.memberKey, additive);
                }
                break;
            case 'selectCSG':
                if (action.memberKey) {
                    // Set CSG selection first, then select the timber for
                    // opacity purposes. The viewer's listener won't clear CSG
                    // if one is already set.
                    this.selectionStore.selectCSG(
                        action.memberKey,
                        action.path || [],
                        action.featureLabel || null,
                    );
                    this.selectionStore.selectTimber(action.memberKey, false);
                    // Request the highlight mesh from the runner so the 3D
                    // viewer can show the CSG geometry.
                    if (this.vscode && action.path && action.path.length > 0) {
                        this.vscode.postMessage({
                            type: 'requestCSGByPath',
                            memberKey: action.memberKey,
                            path: action.path,
                            featureLabel: action.featureLabel || null,
                        });
                    }
                }
                break;
            case 'selectJoint': {
                this.selectionStore.clearCSGSelection();
                const memberKeys = Array.isArray(action.memberKeys) ? action.memberKeys : [];
                if (memberKeys.length === 0) {
                    this.selectionStore.clearTimberSelection();
                    break;
                }
                this.selectionStore.clearTimberSelection();
                memberKeys.forEach((memberKey, idx) => {
                    this.selectionStore.selectTimber(memberKey, idx > 0);
                });
                break;
            }
            case 'clear':
                this.selectionStore.clearTimberSelection();
                this.selectionStore.clearCSGSelection();
                break;
            default:
                break;
        }
    }

    _onDisclosureClick(node, event) {
        if (event) {
            event.stopPropagation();
            event.preventDefault();
        }
        if (this.expanded.has(node.id)) {
            this.expanded.delete(node.id);
        } else {
            this.expanded.add(node.id);
            this._maybeRequestCSGTree(node);
        }
        this.requestUpdate();
    }

    _maybeRequestCSGTree(node) {
        if (!node || node.kind !== (LayersModel ? LayersModel.NODE_KINDS.CUT : null)) return;
        if (!node.expandable || node.csgLoaded) return;
        if (!node.memberKey) return;
        const requestKey = `${node.memberKey}#${node.cutIndex}`;
        if (this.requestedCSGTrees.has(requestKey)) return;
        this.requestedCSGTrees.add(requestKey);
        if (this.vscode) {
            this.vscode.postMessage({
                type: 'requestCSGTree',
                memberKey: node.memberKey,
                cutIndex: node.cutIndex,
            });
        }
    }

    _isExpandable(node) {
        if (!node) return false;
        if (node.kind === (LayersModel ? LayersModel.NODE_KINDS.CUT : null)) {
            return !!node.expandable;
        }
        return Array.isArray(node.children) && node.children.length > 0;
    }

    _renderNode(node, depth) {
        if (!node) return null;
        const expandable = this._isExpandable(node);
        const expanded = this.expanded.has(node.id);
        const highlighted = this.highlightedNodeIds.has(node.id);
        const classes = [
            'layers-row',
            `layers-kind-${node.kind}`,
            highlighted ? 'is-highlighted' : '',
        ].filter(Boolean).join(' ');

        const children = expanded && Array.isArray(node.children)
            ? node.children
            : null;

        const pl = `${depth * 16 + 6}px`;
        return html`
            <div class=${classes}
                 style="padding-left: ${pl}"
                 @click=${(event) => this._onNodeClick(node, event)}>
                <span
                    class="layers-disclosure ${expandable ? 'is-toggle' : 'is-leaf'}"
                    @click=${expandable ? (event) => this._onDisclosureClick(node, event) : undefined}>
                    ${expandable ? (expanded ? '▾' : '▸') : '·'}
                </span>
                <span class="layers-label">${node.label}</span>
            </div>
            ${children
                ? children.map((child) => this._renderNode(child, depth + 1))
                : null}
        `;
    }

    render() {
        const collapsed = this.collapsed;
        const folders = this.tree && Array.isArray(this.tree.folders) ? this.tree.folders : [];
        return html`
            <aside class="layers-panel ${collapsed ? 'is-collapsed' : ''}" aria-label="Layers">
                <div class="layers-header">
                    <button class="layers-collapse-btn"
                            type="button"
                            title=${collapsed ? 'Expand layers panel' : 'Collapse layers panel'}
                            @click=${() => this.toggleCollapsed()}>
                        ${collapsed ? EXPAND_LABEL : COLLAPSE_LABEL}
                    </button>
                    <span class="layers-title">layers</span>
                </div>
                <div class="layers-body" ?hidden=${collapsed}>
                    ${folders.length === 0
                        ? html`<div class="layers-empty">no frame loaded</div>`
                        : folders.map((folder) => this._renderNode(folder, 0))}
                </div>
            </aside>
        `;
    }
}

customElements.define('kigumi-layers-view', KigumiLayersView);

if (typeof window !== 'undefined') {
    window.KigumiLayersView = KigumiLayersView;
}
