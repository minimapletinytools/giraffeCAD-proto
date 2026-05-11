const LayersModel = require('../webview/layers-model');

describe('LayersModel.buildLayersTree', () => {
    const samplePayload = {
        frameName: 'demo',
        timbers: [
            {
                kumikiId: 1,
                memberKey: 'beam#0',
                name: 'beam',
                cuts: [
                    { cutIndex: 0, tag: 'mortise', hasCSG: true, hasEndCut: false, displayName: 'mortise' },
                    { cutIndex: 1, tag: null, hasCSG: false, hasEndCut: true, displayName: 'end cut' },
                ],
            },
            {
                kumikiId: 2,
                memberKey: 'post#0',
                name: 'post',
                cuts: [
                    { cutIndex: 0, tag: 'tenon', hasCSG: true, hasEndCut: false, displayName: 'tenon' },
                ],
            },
        ],
        accessories: [
            {
                kumikiId: 10,
                memberKey: 'accessory:Peg#0',
                name: 'peg',
                type: 'Peg',
                jointKumikiId: 100,
            },
            {
                kumikiId: 11,
                memberKey: 'accessory:Peg#1',
                name: 'peg-loose',
                type: 'Peg',
                jointKumikiId: null,
            },
        ],
        joints: [
            {
                kumikiId: 100,
                name: 'mortise-and-tenon',
                jointType: 'MortiseAndTenon',
                members: [
                    { timberKumikiId: 1, cutIndices: [0] },
                    { timberKumikiId: 2, cutIndices: [0] },
                ],
                accessoryKumikiIds: [10],
            },
        ],
    };

    test('emptyTree exposes the three folders', () => {
        const tree = LayersModel.emptyTree('demo');
        expect(tree.folders.map((f) => f.folderKey)).toEqual([
            LayersModel.FOLDER_TIMBERS,
            LayersModel.FOLDER_JOINTS,
            LayersModel.FOLDER_UNATTACHED,
        ]);
    });

    test('builds timber nodes with cut children', () => {
        const tree = LayersModel.buildLayersTree(samplePayload);
        const timbers = tree.folders[0].children;
        expect(timbers).toHaveLength(2);
        expect(timbers[0].label).toBe('beam');
        expect(timbers[0].children.map((c) => c.cutIndex)).toEqual([0, 1]);
        expect(timbers[0].children[0].expandable).toBe(true);
        expect(timbers[0].children[1].expandable).toBe(false);
    });

    test('joint folder has joint-entry rows combining timber + cut', () => {
        const tree = LayersModel.buildLayersTree(samplePayload);
        const joints = tree.folders[1].children;
        expect(joints).toHaveLength(1);
        const entries = joints[0].children.filter((c) => c.kind === LayersModel.NODE_KINDS.JOINT_ENTRY);
        expect(entries).toHaveLength(2);
        expect(entries[0].label).toContain('beam');
        expect(entries[0].label).toContain('mortise');
    });

    test('attached accessory appears under joint, unattached lives in unattached folder', () => {
        const tree = LayersModel.buildLayersTree(samplePayload);
        const joints = tree.folders[1].children;
        const acc = joints[0].children.filter((c) => c.kind === LayersModel.NODE_KINDS.ACCESSORY);
        expect(acc).toHaveLength(1);
        expect(acc[0].kumikiId).toBe(10);

        const unattached = tree.folders[2].children;
        expect(unattached).toHaveLength(1);
        expect(unattached[0].kumikiId).toBe(11);
    });

    test('mergeCSGTreeIntoCut populates tagged CSGs and features', () => {
        const tree = LayersModel.buildLayersTree(samplePayload);
        const merged = LayersModel.mergeCSGTreeIntoCut(tree, {
            memberKey: 'beam#0',
            cutIndex: 0,
            taggedCSGs: [
                { tag: 'mortise', path: ['mortise'], type: 'Difference', features: ['cheek-near'] },
            ],
        });
        expect(merged).toBe(true);
        const cutNode = tree.folders[0].children[0].children[0];
        expect(cutNode.csgLoaded).toBe(true);
        expect(cutNode.children).toHaveLength(1);
        expect(cutNode.children[0].kind).toBe(LayersModel.NODE_KINDS.TAGGED_CSG);
        expect(cutNode.children[0].children[0].featureLabel).toBe('cheek-near');
    });

    test('nodeIdToSelectionAction maps each node kind to a SelectionStore intent', () => {
        const tree = LayersModel.buildLayersTree(samplePayload);
        const timberId = LayersModel.makeTimberId(1);
        expect(LayersModel.nodeIdToSelectionAction(tree, timberId)).toEqual({
            kind: 'selectTimber',
            memberKey: 'beam#0',
        });

        const cutId = LayersModel.makeCutId(1, 0);
        expect(LayersModel.nodeIdToSelectionAction(tree, cutId).kind).toBe('selectTimber');

        const csgId = LayersModel.makeCSGId(1, 0, ['mortise']);
        const csgAction = LayersModel.nodeIdToSelectionAction(tree, csgId);
        expect(csgAction.kind).toBe('selectCSG');
        expect(csgAction.memberKey).toBe('beam#0');
        expect(csgAction.path).toEqual(['mortise']);

        const featureId = LayersModel.makeFeatureId(1, 0, ['mortise'], 'cheek-near');
        const featureAction = LayersModel.nodeIdToSelectionAction(tree, featureId);
        expect(featureAction.kind).toBe('selectCSG');
        expect(featureAction.featureLabel).toBe('cheek-near');
        expect(featureAction.path).toEqual(['mortise']);

        // Joint-entry nodes act as a tagged-CSG selection (1 cutting == 1 tag).
        const jointEntryId = LayersModel.makeJointEntryId(100, 1, 0);
        const jointEntryAction = LayersModel.nodeIdToSelectionAction(tree, jointEntryId);
        expect(jointEntryAction.kind).toBe('selectCSG');
        expect(jointEntryAction.memberKey).toBe('beam#0');
        expect(jointEntryAction.path).toEqual(['mortise']);
        expect(jointEntryAction.featureLabel).toBeNull();

        const jointId = LayersModel.makeJointId(100);
        const jointAction = LayersModel.nodeIdToSelectionAction(tree, jointId);
        expect(jointAction.kind).toBe('selectJoint');
        expect(new Set(jointAction.memberKeys)).toEqual(
            new Set(['beam#0', 'post#0', 'accessory:Peg#0']),
        );

        const accessoryId = LayersModel.makeAccessoryId(11);
        expect(LayersModel.nodeIdToSelectionAction(tree, accessoryId)).toEqual({
            kind: 'selectAccessory',
            memberKey: 'accessory:Peg#1',
        });

        const folderId = LayersModel.makeFolderId(LayersModel.FOLDER_TIMBERS);
        expect(LayersModel.nodeIdToSelectionAction(tree, folderId).kind).toBe('clear');
    });

    test('selectionSnapshotToNodeIds includes selected timbers + matching CSG + joint-entry', () => {
        const tree = LayersModel.buildLayersTree(samplePayload);
        LayersModel.mergeCSGTreeIntoCut(tree, {
            memberKey: 'beam#0',
            cutIndex: 0,
            taggedCSGs: [
                { tag: 'mortise', path: ['mortise'], type: 'Difference', features: ['cheek-near'] },
            ],
        });
        const ids = LayersModel.selectionSnapshotToNodeIds(tree, {
            selectedTimberMemberKeys: ['beam#0'],
            csgSelection: { timberKey: 'beam#0', path: ['mortise'], featureLabel: 'cheek-near' },
        });
        expect(ids.has(LayersModel.makeTimberId(1))).toBe(true);
        expect(ids.has(LayersModel.makeCutId(1, 0))).toBe(true);
        expect(ids.has(LayersModel.makeCSGId(1, 0, ['mortise']))).toBe(true);
        expect(ids.has(LayersModel.makeFeatureId(1, 0, ['mortise'], 'cheek-near'))).toBe(true);
        // The matching joint-entry is also highlighted.
        expect(ids.has(LayersModel.makeJointEntryId(100, 1, 0))).toBe(true);
    });
});
