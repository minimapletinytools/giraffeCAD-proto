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

function normalizePatternbookRecords(records, fallbackPaths) {
    const normalized = [];
    const seen = new Set();

    for (const record of Array.isArray(records) ? records : []) {
        const sourceFile = record && (record.sourceFile || record.filePath || record.file_path);
        if (!sourceFile || seen.has(sourceFile)) {
            continue;
        }
        seen.add(sourceFile);

        const fallbackName = path.basename(sourceFile, '.py');
        const patternNames = Array.isArray(record.patternNames)
            ? record.patternNames
            : (Array.isArray(record.pattern_names) ? record.pattern_names : []);
        const groupNames = Array.isArray(record.groupNames)
            ? record.groupNames
            : (Array.isArray(record.group_names) ? record.group_names : []);

        normalized.push({
            sourceFile,
            patternbookName: record.patternbookName || fallbackName,
            patternNames: Array.from(new Set(patternNames)).sort((a, b) => a.localeCompare(b)),
            groupNames: Array.from(new Set(groupNames)).sort((a, b) => a.localeCompare(b)),
        });
    }

    for (const sourceFile of dedupeAndSortPaths(fallbackPaths || [])) {
        if (seen.has(sourceFile)) {
            continue;
        }
        const fallbackName = path.basename(sourceFile, '.py');
        normalized.push({
            sourceFile,
            patternbookName: fallbackName,
            patternNames: [fallbackName],
            groupNames: [],
        });
    }

    normalized.sort((a, b) => a.sourceFile.localeCompare(b.sourceFile));
    return normalized;
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
        'def _fallback_patternbook_records(file_paths):',
        '    rows = []',
        '    for fp in sorted(set(file_paths)):',
        '        base = os.path.splitext(os.path.basename(fp))[0]',
        '        rows.append({',
        '            "sourceFile": fp,',
        '            "patternbookName": base,',
        '            "patternNames": [base],',
        '            "groupNames": [],',
        '        })',
        '    return rows',
        '',
        'def _scan_patternbook_records(file_paths):',
        '    if not file_paths:',
        '        return []',
        '    files = sorted(set(file_paths))',
        '    try:',
        '        from kumiki.librarian import scan_specific_files_index',
        '    except Exception:',
        '        return _fallback_patternbook_records(files)',
        '',
        '    try:',
        '        root = os.path.commonpath(files)',
        '    except Exception:',
        '        root = os.path.dirname(files[0])',
        '    if not root:',
        '        root = os.path.dirname(files[0])',
        '    if not os.path.isdir(root):',
        '        root = os.path.dirname(root)',
        '',
        '    try:',
        '        index = scan_specific_files_index(files, root)',
        '    except Exception:',
        '        return _fallback_patternbook_records(files)',
        '',
        '    rows = []',
        '    seen = set()',
        '    for rec in index.get("patternbooks", []):',
        '        fp = rec.get("file_path")',
        '        if not fp or fp in seen:',
        '            continue',
        '        seen.add(fp)',
        '        base = os.path.splitext(os.path.basename(fp))[0]',
        '        pattern_names = sorted(set(rec.get("pattern_names") or []))',
        '        rows.append({',
        '            "sourceFile": fp,',
        '            "patternbookName": base,',
        '            "patternNames": pattern_names if pattern_names else [base],',
        '            "groupNames": sorted(set(rec.get("group_names") or [])),',
        '        })',
        '',
        '    # Keep files that static scan flagged but librarian could not load.',
        '    for fp in files:',
        '        if fp in seen:',
        '            continue',
        '        base = os.path.splitext(os.path.basename(fp))[0]',
        '        rows.append({',
        '            "sourceFile": fp,',
        '            "patternbookName": base,',
        '            "patternNames": [base],',
        '            "groupNames": [],',
        '        })',
        '',
        '    rows.sort(key=lambda r: r["sourceFile"])',
        '    return rows',
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
        'kumiki_patternbooks = _scan_patternbook_records(kumiki_patterns)',
        'dependency_patternbooks = _scan_patternbook_records(dependency_patterns)',
        '',
        'print(json.dumps({',
        '    "kumikiPatterns": sorted(kumiki_patterns),',
        '    "kumikiPatternbooks": kumiki_patternbooks,',
        '    "kumikiExamples": sorted(kumiki_examples),',
        '    "dependencyPatterns": sorted(dependency_patterns),',
        '    "dependencyPatternbooks": dependency_patternbooks,',
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

            const kumikiPatternPaths = dedupeAndSortPaths(raw.kumikiPatterns || []);
            const dependencyPatternPaths = dedupeAndSortPaths(raw.dependencyPatterns || []);

            return {
                kumikiPatterns: kumikiPatternPaths,
                kumikiPatternbooks: normalizePatternbookRecords(raw.kumikiPatternbooks, kumikiPatternPaths),
                kumikiExamples: dedupeAndSortPaths(raw.kumikiExamples || []),
                dependencyPatterns: dependencyPatternPaths,
                dependencyPatternbooks: normalizePatternbookRecords(raw.dependencyPatternbooks, dependencyPatternPaths),
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
