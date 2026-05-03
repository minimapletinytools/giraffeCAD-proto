const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const SKIP_FOLDER_NAMES = new Set([
    '__pycache__',
    '.git',
    '.venv',
    'venv',
    'node_modules',
    'dist',
    'build',
]);

function dedupeAndSortPaths(pathsList) {
    return Array.from(new Set(pathsList || [])).sort((a, b) => a.localeCompare(b));
}

async function listPythonFiles(rootDir) {
    const results = [];
    const queue = [rootDir];

    while (queue.length > 0) {
        const current = queue.shift();
        let entries = [];
        try {
            entries = await fs.promises.readdir(current, { withFileTypes: true });
        } catch (_error) {
            continue;
        }

        for (const entry of entries) {
            const fullPath = path.join(current, entry.name);
            if (entry.isDirectory()) {
                if (SKIP_FOLDER_NAMES.has(entry.name) || entry.name.endsWith('.dist-info') || entry.name.endsWith('.egg-info')) {
                    continue;
                }
                queue.push(fullPath);
                continue;
            }
            if (entry.isFile() && entry.name.endsWith('.py') && entry.name !== '__init__.py') {
                results.push(fullPath);
            }
        }
    }

    return dedupeAndSortPaths(results);
}

function getPythonCandidates(workspaceRoot) {
    if (process.platform === 'win32') {
        return [
            path.join(workspaceRoot, '.venv', 'Scripts', 'python.exe'),
            path.join(workspaceRoot, 'venv', 'Scripts', 'python.exe'),
            'python',
            'py',
        ];
    }

    return [
        path.join(workspaceRoot, '.venv', 'bin', 'python3'),
        path.join(workspaceRoot, '.venv', 'bin', 'python'),
        path.join(workspaceRoot, 'venv', 'bin', 'python3'),
        path.join(workspaceRoot, 'venv', 'bin', 'python'),
        'python3',
        'python',
    ];
}

function runPythonJson(pythonCommand, script, workspaceRoot, timeoutMs) {
    return new Promise((resolve, reject) => {
        const child = spawn(pythonCommand, ['-c', script], {
            cwd: workspaceRoot,
            stdio: ['ignore', 'pipe', 'pipe'],
        });

        let stdout = '';
        let stderr = '';
        let finished = false;

        const timer = setTimeout(() => {
            if (finished) {
                return;
            }
            finished = true;
            child.kill('SIGKILL');
            reject(new Error(`Python discovery timed out after ${timeoutMs}ms`));
        }, timeoutMs);

        child.stdout.on('data', (chunk) => {
            stdout += chunk.toString();
        });

        child.stderr.on('data', (chunk) => {
            stderr += chunk.toString();
        });

        child.on('error', (error) => {
            if (finished) {
                return;
            }
            finished = true;
            clearTimeout(timer);
            reject(error);
        });

        child.on('close', (code) => {
            if (finished) {
                return;
            }
            finished = true;
            clearTimeout(timer);

            if (code !== 0) {
                reject(new Error(`Python discovery failed with exit code ${code}: ${stderr.trim()}`));
                return;
            }

            let parsed = null;
            try {
                parsed = JSON.parse(stdout.trim() || '{}');
            } catch (error) {
                reject(new Error(`Invalid JSON from python discovery: ${error.message}; stderr=${stderr.trim()}`));
                return;
            }

            resolve(parsed);
        });
    });
}

async function discoverDependencyContent(workspaceRoot, options = {}) {
    const timeoutMs = Number.isFinite(options.timeoutMs) ? options.timeoutMs : 10000;
    const candidates = options.pythonCommand ? [options.pythonCommand] : getPythonCandidates(workspaceRoot);

    const script = [
        'import json',
        'import os',
        'import site',
        'import sysconfig',
        'import contextlib',
        'from kumiki.librarian import scan_library_index',
        '',
        'def index_paths(folder):',
        '    if not folder or not os.path.isdir(folder):',
        '        return [], []',
        '    with contextlib.redirect_stdout(__import__("sys").stderr):',
        '        idx = scan_library_index(folder)',
        '    pattern_files = [entry.get("file_path") for entry in idx.get("patternbooks", []) if entry.get("file_path")]',
        '    frame_example_files = [entry.get("file_path") for entry in idx.get("frame_examples", []) if entry.get("file_path")]',
        '    return pattern_files, frame_example_files',
        '',
        'site_roots = set()',
        "for key in ('purelib', 'platlib'):",
        '    path = sysconfig.get_paths().get(key)',
        '    if path:',
        '        site_roots.add(path)',
        'try:',
        '    for candidate in site.getsitepackages():',
        '        site_roots.add(candidate)',
        'except Exception:',
        '    pass',
        'try:',
        '    usersite = site.getusersitepackages()',
        '    if usersite:',
        '        site_roots.add(usersite)',
        'except Exception:',
        '    pass',
        '',
        'kumiki_patterns = set()',
        'kumiki_examples = set()',
        'dependency_patterns = set()',
        'dependency_examples = set()',
        '',
        'for site_root in list(site_roots):',
        '    if not os.path.isdir(site_root):',
        '        continue',
        '    try:',
        '        entries = list(os.scandir(site_root))',
        '    except Exception:',
        '        continue',
        '    for entry in entries:',
        '        if not entry.is_dir():',
        '            continue',
        '        name = entry.name',
        '        if name == "kumiki":',
        '            kp, ke = index_paths(os.path.join(entry.path, "patterns"))',
        '            kumiki_patterns.update(kp)',
        '            kumiki_examples.update(ke)',
        '            kp, ke = index_paths(os.path.join(entry.path, "examples"))',
        '            kumiki_patterns.update(kp)',
        '            kumiki_examples.update(ke)',
        '            kp, ke = index_paths(os.path.join(entry.path, "patterns", "examples"))',
        '            kumiki_patterns.update(kp)',
        '            kumiki_examples.update(ke)',
        '            kp, ke = index_paths(os.path.join(entry.path, "patternbooks", "examples"))',
        '            kumiki_patterns.update(kp)',
        '            kumiki_examples.update(ke)',
        '            continue',
        '        if name.startswith("_"):',
        '            continue',
        '        kp, ke = index_paths(os.path.join(entry.path, "patterns"))',
        '        dependency_patterns.update(kp)',
        '        dependency_examples.update(ke)',
        '        kp, ke = index_paths(os.path.join(entry.path, "examples"))',
        '        dependency_patterns.update(kp)',
        '        dependency_examples.update(ke)',
        '',
        'print(json.dumps({',
        '    "kumikiPatterns": sorted(kumiki_patterns),',
        '    "kumikiExamples": sorted(kumiki_examples),',
        '    "dependencyPatterns": sorted(dependency_patterns),',
        '    "dependencyExamples": sorted(dependency_examples),',
        '}))',
    ].join('\n');

    let lastError = null;
    for (const candidate of candidates) {
        try {
            if (candidate.includes(path.sep) && !fs.existsSync(candidate)) {
                continue;
            }
            const raw = await runPythonJson(candidate, script, workspaceRoot, timeoutMs);

            return {
                kumikiPatterns: dedupeAndSortPaths(raw.kumikiPatterns || []),
                kumikiExamples: dedupeAndSortPaths(raw.kumikiExamples || []),
                dependencyPatterns: dedupeAndSortPaths(raw.dependencyPatterns || []),
                dependencyExamples: dedupeAndSortPaths(raw.dependencyExamples || []),
            };
        } catch (error) {
            lastError = error;
        }
    }

    throw lastError || new Error('No valid Python interpreter found for dependency discovery');
}

module.exports = {
    discoverDependencyContent,
};
