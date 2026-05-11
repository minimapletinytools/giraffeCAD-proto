// layers-model.js
// Pure-data model for the Kigumi viewer Layers panel.
//
// Responsibilities:
//   1. Build a hierarchical tree from the runner "get_layers_tree" payload.
//   2. Define folders as a first-class node concept (Timbers, Joints,
//      Unattached Accessories, ...).
//   3. Define stable node IDs anchored on `kumiki_id` so SelectionStore state
//      can be mapped to/from layers nodes.
//   4. Reserve in-memory hide/lock state without committing rendering changes.
//
// Node kinds:
//   folder, timber, cut, taggedCSG, feature, joint, jointEntry, accessory
//
// Node ID format:
//   folder:<key>
//   timber:<timber_kumiki_id>
//   cut:<timber_kumiki_id>/<cut_index>
//   csg:<timber_kumiki_id>/<cut_index>/<csg-path-joined-by-slash>
//   feature:<timber_kumiki_id>/<cut_index>/<csg-path>/<feature-label>
//   joint:<joint_kumiki_id>
//   joint-entry:<joint_kumiki_id>/<timber_kumiki_id>/<cut_index>
//   accessory:<accessory_kumiki_id>

(function (globalScope) {
    const FOLDER_TIMBERS = 'timbers';
    const FOLDER_JOINTS = 'joints';
    const FOLDER_UNATTACHED = 'unattached_accessories';

    const NODE_KINDS = Object.freeze({
        FOLDER: 'folder',
        TIMBER: 'timber',
        CUT: 'cut',
        TAGGED_CSG: 'taggedCSG',
        FEATURE: 'feature',
        JOINT: 'joint',
        JOINT_ENTRY: 'jointEntry',
        ACCESSORY: 'accessory',
    });

    function makeFolderId(folderKey) {
        return `folder:${folderKey}`;
    }

    function makeTimberId(timberKumikiId) {
        return `timber:${timberKumikiId}`;
    }

    function makeCutId(timberKumikiId, cutIndex) {
        return `cut:${timberKumikiId}/${cutIndex}`;
    }

    function makeCSGId(timberKumikiId, cutIndex, csgPath) {
        const path = (csgPath || []).join('/');
        return `csg:${timberKumikiId}/${cutIndex}/${path}`;
    }

    function makeFeatureId(timberKumikiId, cutIndex, csgPath, featureLabel) {
        const path = (csgPath || []).join('/');
        return `feature:${timberKumikiId}/${cutIndex}/${path}/${featureLabel}`;
    }

    function makeJointId(jointKumikiId) {
        return `joint:${jointKumikiId}`;
    }

    function makeJointEntryId(jointKumikiId, timberKumikiId, cutIndex) {
        return `joint-entry:${jointKumikiId}/${timberKumikiId}/${cutIndex}`;
    }

    function makeAccessoryId(accessoryKumikiId) {
        return `accessory:${accessoryKumikiId}`;
    }

    function emptyTree(frameName) {
        const folders = [
            {
                id: makeFolderId(FOLDER_TIMBERS),
                kind: NODE_KINDS.FOLDER,
                folderKey: FOLDER_TIMBERS,
                label: 'Timbers',
                children: [],
            },
            {
                id: makeFolderId(FOLDER_JOINTS),
                kind: NODE_KINDS.FOLDER,
                folderKey: FOLDER_JOINTS,
                label: 'Joints',
                children: [],
            },
            {
                id: makeFolderId(FOLDER_UNATTACHED),
                kind: NODE_KINDS.FOLDER,
                folderKey: FOLDER_UNATTACHED,
                label: 'Unattached Accessories',
                children: [],
            },
        ];
        return {
            frameName: frameName || null,
            folders,
            // Indices for fast lookup by SelectionStore state.
            byTimberKumikiId: new Map(),
            byMemberKey: new Map(),
            byJointKumikiId: new Map(),
            byAccessoryKumikiId: new Map(),
            byNodeId: new Map(),
            // (memberKey + cutTag) -> Set of joint-entry node ids that share
            // the same underlying tagged CSG (one tag-per-cut). Used so a CSG
            // selection from the 3D viewer highlights the matching joint row.
            jointEntriesByCutTag: new Map(),
            // Reserve hide/lock state for future use (not consumed yet by viewer).
            nodeState: new Map(),
        };
    }

    function buildLayersTree(payload) {
        const safe = payload && typeof payload === 'object' ? payload : {};
        const tree = emptyTree(safe.frameName);

        const timbersFolder = tree.folders[0];
        const jointsFolder = tree.folders[1];
        const unattachedFolder = tree.folders[2];

        const timbers = Array.isArray(safe.timbers) ? safe.timbers : [];
        const accessories = Array.isArray(safe.accessories) ? safe.accessories : [];
        const joints = Array.isArray(safe.joints) ? safe.joints : [];

        // 1. Timber nodes (with cuts as children).
        const timberNodeIndex = new Map(); // timberKumikiId -> timberNode
        for (const timber of timbers) {
            const tk = Number(timber.kumikiId);
            const memberKey = String(timber.memberKey || '');
            const cuts = Array.isArray(timber.cuts) ? timber.cuts : [];
            const cutNodes = cuts.map((cut) => ({
                id: makeCutId(tk, cut.cutIndex),
                kind: NODE_KINDS.CUT,
                label: cut.displayName || `cut ${cut.cutIndex + 1}`,
                timberKumikiId: tk,
                memberKey,
                cutIndex: Number(cut.cutIndex),
                tag: cut.tag || null,
                hasCSG: !!cut.hasCSG,
                hasEndCut: !!cut.hasEndCut,
                // CSG/feature children populated lazily after get_csg_tree response.
                children: [],
                expandable: !!cut.hasCSG || !!cut.tag,
                csgLoaded: false,
            }));
            const timberNode = {
                id: makeTimberId(tk),
                kind: NODE_KINDS.TIMBER,
                label: timber.name || memberKey,
                kumikiId: tk,
                memberKey,
                children: cutNodes,
            };
            timberNodeIndex.set(tk, timberNode);
            tree.byTimberKumikiId.set(tk, timberNode);
            if (memberKey) {
                tree.byMemberKey.set(memberKey, timberNode);
            }
            timbersFolder.children.push(timberNode);
        }

        // 2. Accessory lookup (memberKey + label).
        const accessoryIndex = new Map(); // accessoryKumikiId -> accessoryPayload
        for (const accessory of accessories) {
            accessoryIndex.set(Number(accessory.kumikiId), accessory);
        }

        // 3. Joint nodes (with joint-entry children combining timber + that
        //    joint's cutting on a single line, plus accessory children).
        const attachedAccessoryIds = new Set();
        for (const joint of joints) {
            const jk = Number(joint.kumikiId);
            const members = Array.isArray(joint.members) ? joint.members : [];
            const accessoryIds = Array.isArray(joint.accessoryKumikiIds) ? joint.accessoryKumikiIds : [];

            const entryChildren = [];
            for (const member of members) {
                const tk = Number(member.timberKumikiId);
                const cutIndices = Array.isArray(member.cutIndices) ? member.cutIndices : [];
                const timberNode = timberNodeIndex.get(tk);
                const timberLabel = timberNode ? timberNode.label : `timber#${tk}`;
                const memberKey = timberNode ? timberNode.memberKey : '';
                for (const cutIndex of cutIndices) {
                    const ci = Number(cutIndex);
                    const cutNode = timberNode
                        ? timberNode.children.find((c) => c.cutIndex === ci)
                        : null;
                    const cutLabel = cutNode ? cutNode.label : `cut ${ci + 1}`;
                    entryChildren.push({
                        id: makeJointEntryId(jk, tk, ci),
                        kind: NODE_KINDS.JOINT_ENTRY,
                        label: `${timberLabel} › ${cutLabel}`,
                        jointKumikiId: jk,
                        timberKumikiId: tk,
                        memberKey,
                        cutIndex: ci,
                        tag: cutNode ? cutNode.tag : null,
                        children: [],
                    });
                }
            }

            const accessoryChildren = [];
            for (const accId of accessoryIds) {
                const aid = Number(accId);
                attachedAccessoryIds.add(aid);
                const accessory = accessoryIndex.get(aid);
                if (!accessory) continue;
                const accessoryNode = {
                    id: makeAccessoryId(aid),
                    kind: NODE_KINDS.ACCESSORY,
                    label: accessory.name || accessory.memberKey || `accessory#${aid}`,
                    kumikiId: aid,
                    memberKey: String(accessory.memberKey || ''),
                    accessoryType: accessory.type || null,
                    jointKumikiId: jk,
                    children: [],
                };
                accessoryChildren.push(accessoryNode);
                tree.byAccessoryKumikiId.set(aid, accessoryNode);
                if (accessoryNode.memberKey) {
                    tree.byMemberKey.set(accessoryNode.memberKey, accessoryNode);
                }
            }

            const jointName = joint.name || joint.jointType || `joint#${jk}`;
            const jointNode = {
                id: makeJointId(jk),
                kind: NODE_KINDS.JOINT,
                label: jointName,
                kumikiId: jk,
                jointType: joint.jointType || null,
                children: [...entryChildren, ...accessoryChildren],
            };
            tree.byJointKumikiId.set(jk, jointNode);
            jointsFolder.children.push(jointNode);
        }

        // 4. Unattached accessories folder always exists, shows accessories
        //    not associated with any joint.
        for (const accessory of accessories) {
            const aid = Number(accessory.kumikiId);
            if (attachedAccessoryIds.has(aid)) continue;
            const memberKey = String(accessory.memberKey || '');
            const accessoryNode = {
                id: makeAccessoryId(aid),
                kind: NODE_KINDS.ACCESSORY,
                label: accessory.name || memberKey || `accessory#${aid}`,
                kumikiId: aid,
                memberKey,
                accessoryType: accessory.type || null,
                jointKumikiId: null,
                children: [],
            };
            unattachedFolder.children.push(accessoryNode);
            tree.byAccessoryKumikiId.set(aid, accessoryNode);
            if (memberKey) {
                tree.byMemberKey.set(memberKey, accessoryNode);
            }
        }

        // 5. Register every node in byNodeId, and index joint-entries by
        //    (memberKey + cutTag) so a CSG selection can highlight the
        //    matching joint row(s).
        const visit = (node) => {
            if (!node || !node.id) return;
            tree.byNodeId.set(node.id, node);
            if (node.kind === NODE_KINDS.JOINT_ENTRY && node.memberKey && node.tag) {
                const key = jointEntryCutTagKey(node.memberKey, node.tag);
                let bucket = tree.jointEntriesByCutTag.get(key);
                if (!bucket) {
                    bucket = new Set();
                    tree.jointEntriesByCutTag.set(key, bucket);
                }
                bucket.add(node.id);
            }
            if (Array.isArray(node.children)) {
                for (const child of node.children) visit(child);
            }
        };
        for (const folder of tree.folders) visit(folder);

        return tree;
    }

    function jointEntryCutTagKey(memberKey, tag) {
        return `${memberKey}\u0000${tag}`;
    }

    // Merge a loaded CSG-tree response into the matching cut node's children.
    // payload: { memberKey, cutIndex, taggedCSGs: [{ tag, path, type, features }] }
    function mergeCSGTreeIntoCut(tree, payload) {
        if (!tree || !payload) return false;
        const memberKey = payload.memberKey;
        const cutIndex = Number(payload.cutIndex);
        const timberNode = tree.byMemberKey.get(memberKey);
        if (!timberNode || timberNode.kind !== NODE_KINDS.TIMBER) return false;
        const cutNode = timberNode.children.find((c) => c.cutIndex === cutIndex);
        if (!cutNode) return false;

        const csgs = Array.isArray(payload.taggedCSGs) ? payload.taggedCSGs : [];
        const csgChildren = [];
        for (const csg of csgs) {
            const path = Array.isArray(csg.path) ? csg.path : [];
            const csgId = makeCSGId(timberNode.kumikiId, cutIndex, path);
            const featureChildren = [];
            const features = Array.isArray(csg.features) ? csg.features : [];
            for (const featureLabel of features) {
                featureChildren.push({
                    id: makeFeatureId(timberNode.kumikiId, cutIndex, path, featureLabel),
                    kind: NODE_KINDS.FEATURE,
                    label: featureLabel,
                    timberKumikiId: timberNode.kumikiId,
                    memberKey: timberNode.memberKey,
                    cutIndex,
                    csgPath: path.slice(),
                    featureLabel,
                    children: [],
                });
            }
            csgChildren.push({
                id: csgId,
                kind: NODE_KINDS.TAGGED_CSG,
                label: path.length > 0 ? path[path.length - 1] : (csg.tag || 'csg'),
                timberKumikiId: timberNode.kumikiId,
                memberKey: timberNode.memberKey,
                cutIndex,
                csgPath: path.slice(),
                csgType: csg.type || null,
                children: featureChildren,
            });
        }
        cutNode.children = csgChildren;
        cutNode.csgLoaded = true;
        // Register the freshly-built CSG/feature nodes in byNodeId so that
        // selection highlighting and click handlers can resolve them.
        if (tree.byNodeId) {
            const visit = (node) => {
                if (!node || !node.id) return;
                tree.byNodeId.set(node.id, node);
                if (Array.isArray(node.children)) {
                    for (const child of node.children) visit(child);
                }
            };
            for (const child of csgChildren) visit(child);
        }
        return true;
    }

    // Translate a SelectionStore snapshot into a Set of currently-active
    // layers node IDs. Used by the view to highlight matching rows.
    // snapshot: { selectedTimberMemberKeys: string[], csgSelection?: { timberKey, path, featureLabel } }
    function selectionSnapshotToNodeIds(tree, snapshot) {
        const ids = new Set();
        if (!tree || !snapshot) return ids;

        const memberKeys = Array.isArray(snapshot.selectedTimberMemberKeys)
            ? snapshot.selectedTimberMemberKeys
            : [];
        for (const memberKey of memberKeys) {
            const node = tree.byMemberKey.get(memberKey);
            if (node) ids.add(node.id);
        }

        const csg = snapshot.csgSelection;
        if (csg && csg.timberKey) {
            const timberNode = tree.byMemberKey.get(csg.timberKey);
            if (timberNode && timberNode.kind === NODE_KINDS.TIMBER) {
                const path = Array.isArray(csg.path) ? csg.path : [];
                const featureLabel = csg.featureLabel || null;
                if (path.length > 0) {
                    const rootTag = path[0];
                    // Highlight the timber + matching cut + tagged-CSG + feature.
                    ids.add(timberNode.id);
                    for (const cutNode of timberNode.children) {
                        if (cutNode.tag && cutNode.tag === rootTag) {
                            ids.add(cutNode.id);
                            ids.add(makeCSGId(timberNode.kumikiId, cutNode.cutIndex, path));
                            if (featureLabel) {
                                ids.add(makeFeatureId(timberNode.kumikiId, cutNode.cutIndex, path, featureLabel));
                            }
                        }
                    }
                    // Each cutting corresponds to exactly one tagged CSG, so a
                    // CSG selection on a member key + tag also lights up every
                    // joint-entry that references that cutting.
                    const bucket = tree.jointEntriesByCutTag.get(jointEntryCutTagKey(csg.timberKey, rootTag));
                    if (bucket) {
                        for (const id of bucket) ids.add(id);
                    }
                }
            }
        }

        return ids;
    }

    // Translate a layers node click into the SelectionStore action it should
    // trigger. The caller (layers-view) is responsible for invoking the
    // appropriate methods on SelectionStore.
    //
    // Returns { kind, args } where kind ∈
    //   'selectTimber' | 'selectCSG' | 'selectAccessory' |
    //   'selectJoint'   | 'clear'    | 'noop'
    function nodeIdToSelectionAction(tree, nodeId) {
        if (!tree || !nodeId || typeof nodeId !== 'string') {
            return { kind: 'noop' };
        }
        const colon = nodeId.indexOf(':');
        if (colon < 0) return { kind: 'noop' };
        const kind = nodeId.slice(0, colon);
        const rest = nodeId.slice(colon + 1);

        switch (kind) {
            case 'folder':
                return { kind: 'clear' };
            case 'timber': {
                const tk = Number(rest);
                const node = tree.byTimberKumikiId.get(tk);
                if (!node) return { kind: 'noop' };
                return { kind: 'selectTimber', memberKey: node.memberKey };
            }
            case 'cut': {
                const [tkStr] = rest.split('/');
                const tk = Number(tkStr);
                const node = tree.byTimberKumikiId.get(tk);
                if (!node) return { kind: 'noop' };
                return { kind: 'selectTimber', memberKey: node.memberKey };
            }
            case 'csg': {
                const parts = rest.split('/');
                const tk = Number(parts[0]);
                const node = tree.byTimberKumikiId.get(tk);
                if (!node) return { kind: 'noop' };
                const path = parts.slice(2);
                return {
                    kind: 'selectCSG',
                    memberKey: node.memberKey,
                    path,
                    featureLabel: null,
                };
            }
            case 'feature': {
                const parts = rest.split('/');
                const tk = Number(parts[0]);
                const node = tree.byTimberKumikiId.get(tk);
                if (!node) return { kind: 'noop' };
                const featureLabel = parts[parts.length - 1];
                const path = parts.slice(2, -1);
                return {
                    kind: 'selectCSG',
                    memberKey: node.memberKey,
                    path,
                    featureLabel,
                };
            }
            case 'joint': {
                const jk = Number(rest);
                const jointNode = tree.byJointKumikiId.get(jk);
                if (!jointNode) return { kind: 'noop' };
                const memberKeys = [];
                for (const child of jointNode.children) {
                    if (child.kind === NODE_KINDS.JOINT_ENTRY && child.memberKey) {
                        if (!memberKeys.includes(child.memberKey)) memberKeys.push(child.memberKey);
                    } else if (child.kind === NODE_KINDS.ACCESSORY && child.memberKey) {
                        if (!memberKeys.includes(child.memberKey)) memberKeys.push(child.memberKey);
                    }
                }
                return { kind: 'selectJoint', memberKeys };
            }
            case 'joint-entry': {
                // Each cutting corresponds to exactly one tagged CSG, so a
                // joint-entry click should select that tagged CSG (path=[tag])
                // when we have a tag, and fall back to a timber selection
                // otherwise (e.g. end-cut-only entries).
                const node = tree.byNodeId ? tree.byNodeId.get(nodeId) : null;
                if (!node || !node.memberKey) return { kind: 'noop' };
                if (node.tag) {
                    return {
                        kind: 'selectCSG',
                        memberKey: node.memberKey,
                        path: [node.tag],
                        featureLabel: null,
                    };
                }
                return { kind: 'selectTimber', memberKey: node.memberKey };
            }
            case 'accessory': {
                const aid = Number(rest);
                const node = tree.byAccessoryKumikiId.get(aid);
                if (!node) return { kind: 'noop' };
                return { kind: 'selectAccessory', memberKey: node.memberKey };
            }
            default:
                return { kind: 'noop' };
        }
    }

    const api = {
        NODE_KINDS,
        FOLDER_TIMBERS,
        FOLDER_JOINTS,
        FOLDER_UNATTACHED,
        emptyTree,
        buildLayersTree,
        mergeCSGTreeIntoCut,
        selectionSnapshotToNodeIds,
        nodeIdToSelectionAction,
        makeFolderId,
        makeTimberId,
        makeCutId,
        makeCSGId,
        makeFeatureId,
        makeJointId,
        makeJointEntryId,
        makeAccessoryId,
    };

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    }
    globalScope.LayersModel = api;
})(typeof window !== 'undefined' ? window : globalThis);
