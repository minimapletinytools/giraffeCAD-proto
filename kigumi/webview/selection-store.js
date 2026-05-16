(function (globalScope) {
    // Layer node descriptor shapes:
    //   { type: 'timber',    key }
    //   { type: 'cutting',   timberKey, cuttingIdx }
    //   { type: 'csgNode',   timberKey, path }
    //   { type: 'joint',     jointId, timberKeys }
    //   { type: 'accessory', key }

    class SelectionStore {
        constructor() {
            this.selectedTimbers = new Set();
            this.selectedFeatures = [];
            this.csgSelection = null;
            this.selectedLayerNode = null;
            this.listeners = new Set();
        }

        selectTimber(name, addToSelection = false) {
            this.clearLayerSelection();
            if (!addToSelection) {
                this.selectedTimbers.clear();
            }
            this.selectedTimbers.add(name);
            this.emit({ type: 'timber-selected', timberName: name });
        }

        deselectTimber(name) {
            this.selectedTimbers.delete(name);
            this.emit({ type: 'timber-deselected', timberName: name });
        }

        toggleTimber(name) {
            if (this.selectedTimbers.has(name)) {
                this.deselectTimber(name);
                return;
            }
            this.selectTimber(name, true);
        }

        clearTimberSelection() {
            this.clearLayerSelection();
            if (this.selectedTimbers.size === 0) {
                return;
            }
            this.selectedTimbers.clear();
            this.emit({ type: 'clear-timbers' });
        }

        isTimberSelected(name) {
            return this.selectedTimbers.has(name);
        }

        getSelectedTimbers() {
            return Array.from(this.selectedTimbers);
        }

        selectFeature(timberName, featureId, addToSelection = false) {
            if (!addToSelection) {
                this.selectedFeatures = [];
            }
            this.addFeature(timberName, featureId);
        }

        addFeature(timberName, featureId) {
            const alreadySelected = this.selectedFeatures.some((feature) => (
                feature.timberName === timberName && feature.featureId === featureId
            ));
            if (alreadySelected) {
                return;
            }
            this.selectedFeatures.push({ timberName, featureId });
            this.emit({ type: 'feature-selected', timberName, featureId });
        }

        clearFeatureSelection() {
            if (this.selectedFeatures.length === 0) {
                return;
            }
            this.selectedFeatures = [];
            this.emit({ type: 'clear-features' });
        }

        selectCSG(timberKey, path, featureLabel) {
            this.csgSelection = { timberKey, path: path || [], featureLabel: featureLabel || null };
            this.emit({ type: 'csg-selected', csgSelection: this.csgSelection });
        }

        clearCSGSelection() {
            if (!this.csgSelection) {
                return;
            }
            this.csgSelection = null;
            this.emit({ type: 'clear-csg' });
        }

        // --- Layer node selection ---

        selectLayerNode(node, addToSelection = false) {
            if (addToSelection) {
                this.clearCSGSelection();
                this.clearFeatureSelection();
                this.clearLayerSelection();

                if (node.type === 'timber') {
                    this.toggleTimber(node.key);
                } else if (node.type === 'cutting') {
                    this.toggleTimber(node.timberKey);
                } else if (node.type === 'accessory') {
                    this.toggleTimber(node.key);
                } else if (node.type === 'joint') {
                    for (const key of (node.timberKeys || [])) {
                        this.selectedTimbers.add(key);
                    }
                    this.emit({ type: 'joint-selected', jointId: node.jointId, timberKeys: node.timberKeys || [] });
                } else {
                    // CSG nodes don't support additive selection; fall back to single-select.
                    addToSelection = false;
                }

                if (addToSelection) {
                    return;
                }
            }

            this.selectedLayerNode = node;

            if (node.type === 'timber') {
                this.clearCSGSelection();
                this.clearFeatureSelection();
                this.selectedTimbers.clear();
                this.selectedTimbers.add(node.key);
                this.emit({ type: 'timber-selected', timberName: node.key });
            } else if (node.type === 'cutting') {
                this.clearCSGSelection();
                this.clearFeatureSelection();
                this.selectedTimbers.clear();
                this.selectedTimbers.add(node.timberKey);
                this.emit({ type: 'timber-selected', timberName: node.timberKey });
            } else if (node.type === 'csgNode') {
                this.selectedTimbers.clear();
                this.selectedTimbers.add(node.timberKey);
                this.csgSelection = { timberKey: node.timberKey, path: node.path || [], featureLabel: null };
                this.emit({ type: 'csg-selected', csgSelection: this.csgSelection });
            } else if (node.type === 'joint') {
                this.clearCSGSelection();
                this.clearFeatureSelection();
                this.selectedTimbers.clear();
                for (const key of (node.timberKeys || [])) {
                    this.selectedTimbers.add(key);
                }
                this.emit({ type: 'joint-selected', jointId: node.jointId, timberKeys: node.timberKeys || [] });
            } else if (node.type === 'accessory') {
                this.clearCSGSelection();
                this.clearFeatureSelection();
                this.selectedTimbers.clear();
                this.selectedTimbers.add(node.key);
                this.emit({ type: 'timber-selected', timberName: node.key });
            }

            this.emit({ type: 'layer-node-selected', node });
        }

        clearLayerSelection() {
            if (!this.selectedLayerNode) return;
            this.selectedLayerNode = null;
            this.emit({ type: 'clear-layer-node' });
        }

        hasSelection() {
            return this.selectedTimbers.size > 0 || this.selectedFeatures.length > 0 || this.csgSelection !== null || this.selectedLayerNode !== null;
        }

        onSelectionChanged(callback) {
            this.listeners.add(callback);
            return () => {
                this.listeners.delete(callback);
            };
        }

        emit(event) {
            for (const listener of this.listeners) {
                listener(event);
            }
        }
    }

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = { SelectionStore };
    }
    globalScope.SelectionStore = SelectionStore;
})(typeof window !== 'undefined' ? window : globalThis);
