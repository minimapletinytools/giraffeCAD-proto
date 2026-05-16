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
    const attemptErrors = [];

    const script = [
        'import json',
        'import os',
        'import re',
        'import site',
        'import sysconfig',
        '',
        'SKIP_DIRS = {"__pycache__", "node_modules", "dist", "build", ".git", ".hg", ".svn"}',
        '',
        'def _might_contain_patternbook(src):',
        '    if re.search(r"^\\s*patternbook\\s*=", src, flags=re.M):',
        '        return True',
        '    if re.search(r"^\\s*def\\s+create_\\w+_patternbook\\s*\\(", src, flags=re.M):',
        '        return True',
        '    return False',
        '',
        'def _might_contain_example(src):',
        '    if re.search(r"^\\s*example\\s*=", src, flags=re.M):',
        '        return True',
        '    if re.search(r"^\\s*def\\s+build_frame\\s*\\(", src, flags=re.M):',
        '        return True',
        '    return False',
        '',
        'def index_paths(folder):',
        '    if not folder or not os.path.isdir(folder):',
        '        return [], []',
        '    pattern_files = []',
        '    frame_example_files = []',
        '    for root, dirs, files in os.walk(folder):',
        '        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]',
        '        for file_name in files:',
        '            if not file_name.endswith(".py") or file_name == "__init__.py":',
        '                continue',
        '            file_path = os.path.join(root, file_name)',
        '            try:',
        '                with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:',
        '                    src = fh.read()',
        '            except Exception:',
        '                continue',
        '            if _might_contain_patternbook(src):',
        '                pattern_files.append(file_path)',
        '            if _might_contain_example(src):',
        '                frame_example_files.append(file_path)',
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
        '        if name.endswith(".dist-info") or name.endswith(".egg-info"):',
        '            continue',
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
            const wrappedError = new Error(`Python candidate '${candidate}' failed: ${error.message || error}`);
            lastError = wrappedError;
            attemptErrors.push(wrappedError.message);
        }
    }

    if (lastError) {
        throw new Error(`Dependency discovery failed after trying ${candidates.length} Python candidate(s):\n${attemptErrors.join('\n')}`);
    }
    throw new Error('No valid Python interpreter found for dependency discovery');
}

module.exports = {
    discoverDependencyContent,
};
