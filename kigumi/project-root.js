const fs = require('fs');
const path = require('path');

function findMarkerRoot(startDir) {
    let candidate = path.resolve(startDir);

    while (true) {
        if (fs.existsSync(path.join(candidate, 'kumiki'))) {
            return { projectRoot: candidate, isLocalDev: true, marker: 'kumiki' };
        }
        if (fs.existsSync(path.join(candidate, '.kigumi.yaml'))) {
            return { projectRoot: candidate, isLocalDev: false, marker: '.kigumi.yaml' };
        }

        const parent = path.dirname(candidate);
        if (parent === candidate) {
            return null;
        }
        candidate = parent;
    }
}

function ensureKigumiYaml(projectRoot) {
    const envYamlPath = path.join(projectRoot, '.kigumi.yaml');
    if (!fs.existsSync(envYamlPath)) {
        fs.writeFileSync(envYamlPath, 'kumiki_version: latest\n', 'utf8');
    }
}

function resolveProjectEnvironment(options = {}) {
    const filePath = options.filePath ? path.resolve(options.filePath) : null;
    const workspaceRoot = options.workspaceRoot ? path.resolve(options.workspaceRoot) : null;
    const createMarkerIfMissing = options.createMarkerIfMissing !== false;

    if (filePath) {
        const fromFile = findMarkerRoot(path.dirname(filePath));
        if (fromFile) {
            return {
                ...fromFile,
                source: 'file',
            };
        }
    }

    if (workspaceRoot) {
        const fromWorkspace = findMarkerRoot(workspaceRoot);
        if (fromWorkspace) {
            return {
                ...fromWorkspace,
                source: 'workspace',
            };
        }

        if (createMarkerIfMissing) {
            ensureKigumiYaml(workspaceRoot);
        }

        return {
            projectRoot: workspaceRoot,
            isLocalDev: false,
            marker: null,
            source: 'workspace-fallback',
        };
    }

    if (filePath) {
        const fallbackRoot = path.dirname(filePath);
        if (createMarkerIfMissing) {
            ensureKigumiYaml(fallbackRoot);
        }
        return {
            projectRoot: fallbackRoot,
            isLocalDev: false,
            marker: null,
            source: 'file-fallback',
        };
    }

    return {
        projectRoot: null,
        isLocalDev: false,
        marker: null,
        source: 'none',
    };
}

module.exports = {
    ensureKigumiYaml,
    resolveProjectEnvironment,
};
