const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { ensureKigumiYaml, resolveProjectEnvironment } = require('./project-root');

function getVenvPython(workspaceRoot) {
    if (process.platform === 'win32') {
        return path.join(workspaceRoot, '.venv', 'Scripts', 'python.exe');
    }
    return path.join(workspaceRoot, '.venv', 'bin', 'python3');
}

function runCommand(command, args, cwd) {
    return new Promise((resolve, reject) => {
        const child = spawn(command, args, {
            cwd,
            stdio: ['ignore', 'pipe', 'pipe'],
        });

        let stdout = '';
        let stderr = '';

        child.stdout.on('data', (chunk) => {
            stdout += chunk.toString();
        });

        child.stderr.on('data', (chunk) => {
            stderr += chunk.toString();
        });

        child.on('error', (error) => {
            reject(error);
        });

        child.on('close', (code) => {
            if (code === 0) {
                resolve({ stdout, stderr });
                return;
            }
            reject(new Error(`${command} ${args.join(' ')} failed with exit code ${code}: ${stderr.trim()}`));
        });
    });
}

function yamlQuote(value) {
    return `'${String(value).replace(/'/g, "''")}'`;
}

function writeProjectYaml(workspaceRoot, pythonPath, metadata) {
    const folder = path.join(workspaceRoot, '.kigumi');
    fs.mkdirSync(folder, { recursive: true });

    const lines = [
        'schema_version: 1',
        `project_root: ${yamlQuote(workspaceRoot)}`,
        `python_path: ${yamlQuote(pythonPath)}`,
        `venv_path: ${yamlQuote(path.join(workspaceRoot, '.venv'))}`,
        `local_dev: ${metadata.isLocalDev ? 'true' : 'false'}`,
        `last_setup_at: ${yamlQuote(new Date().toISOString())}`,
        `created_venv: ${metadata.createdVenv ? 'true' : 'false'}`,
        `installed_viewer_deps: ${metadata.installedViewerDeps ? 'true' : 'false'}`,
    ];

    if (metadata.missingBefore.length > 0) {
        lines.push('missing_before_setup:');
        for (const pkg of metadata.missingBefore) {
            lines.push(`  - ${pkg}`);
        }
    }

    fs.writeFileSync(path.join(folder, 'project.yaml'), `${lines.join('\n')}\n`, 'utf8');
}

function ensureExampleFrame(workspaceRoot) {
    const filePath = path.join(workspaceRoot, 'my_cute_frame.py');
    if (fs.existsSync(filePath)) {
        return { filePath, created: false };
    }

    const content = [
        '"""Starter Kigumi frame example."""',
        '',
        'from kumiki.construction import build_cube_frame',
        '',
        '',
        'def build_frame():',
        '    # Keep this example tiny and quick to render.',
        '    return build_cube_frame(120, 80, 100, 12)',
        '',
        '',
        'example = build_frame',
        '',
    ].join('\n');

    fs.writeFileSync(filePath, content, 'utf8');
    return { filePath, created: true };
}

async function createVenv(workspaceRoot) {
    const venvPython = getVenvPython(workspaceRoot);
    if (fs.existsSync(venvPython)) {
        return { createdVenv: false, pythonPath: venvPython };
    }

    const launchers = process.platform === 'win32'
        ? [
            { command: 'py', args: ['-3', '-m', 'venv', '.venv'] },
            { command: 'python', args: ['-m', 'venv', '.venv'] },
        ]
        : [
            { command: 'python3', args: ['-m', 'venv', '.venv'] },
            { command: 'python', args: ['-m', 'venv', '.venv'] },
        ];

    let lastError = null;
    for (const launcher of launchers) {
        try {
            await runCommand(launcher.command, launcher.args, workspaceRoot);
            return { createdVenv: true, pythonPath: venvPython };
        } catch (error) {
            lastError = error;
        }
    }

    throw lastError || new Error('Unable to create virtual environment');
}

async function getMissingViewerDependencies(workspaceRoot, pythonPath) {
    const snippet = [
        'import importlib.util',
        'required = ["sympy", "numpy", "trimesh", "manifold3d"]',
        'missing = [name for name in required if importlib.util.find_spec(name) is None]',
        'print("\\n".join(missing))',
    ].join('; ');

    const { stdout } = await runCommand(pythonPath, ['-c', snippet], workspaceRoot);
    return stdout
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.length > 0);
}

async function installBasePackages(workspaceRoot, pythonPath, isLocalDev) {
    const missingBefore = await getMissingViewerDependencies(workspaceRoot, pythonPath);
    if (missingBefore.length === 0) {
        return {
            installedViewerDeps: false,
            missingBefore,
        };
    }

    await runCommand(pythonPath, ['-m', 'pip', 'install', '--upgrade', 'pip'], workspaceRoot);

    if (isLocalDev && fs.existsSync(path.join(workspaceRoot, 'pyproject.toml'))) {
        await runCommand(pythonPath, ['-m', 'pip', 'install', '-e', workspaceRoot], workspaceRoot);
    } else {
        await runCommand(pythonPath, ['-m', 'pip', 'install', 'kumiki'], workspaceRoot);
    }

    return {
        installedViewerDeps: true,
        missingBefore,
    };
}

function getInitializationStatus(workspaceRoot, filePath) {
    const env = resolveProjectEnvironment({
        workspaceRoot,
        filePath,
        createMarkerIfMissing: false,
    });
    const resolvedRoot = env.projectRoot || workspaceRoot;
    const isLocalDev = !!env.isLocalDev;
    const hasKigumiYaml = fs.existsSync(path.join(resolvedRoot, '.kigumi.yaml'));
    const hasProjectYaml = fs.existsSync(path.join(resolvedRoot, '.kigumi', 'project.yaml'));
    const hasVenvPython = fs.existsSync(getVenvPython(resolvedRoot));
    const hasExampleFile = fs.existsSync(path.join(resolvedRoot, 'my_cute_frame.py'));
    const hasExistingProject = hasKigumiYaml || hasProjectYaml || hasVenvPython || hasExampleFile;

    let projectStatus = 'no-project';
    if (isLocalDev) {
        projectStatus = 'local-dev';
    } else if (hasExistingProject) {
        projectStatus = 'existing-project';
    }

    return {
        projectRoot: resolvedRoot,
        projectStatus,
        isLocalDev,
        hasExistingProject,
        hasKigumiYaml,
        hasProjectYaml,
        hasVenvPython,
        hasExampleFile,
        isInitialized: projectStatus === 'existing-project' && hasKigumiYaml && hasProjectYaml && hasVenvPython && hasExampleFile,
    };
}

async function initializeWorkspaceProject(workspaceRoot, filePath) {
    const env = resolveProjectEnvironment({
        workspaceRoot,
        filePath,
        createMarkerIfMissing: true,
    });
    const resolvedRoot = env.projectRoot || workspaceRoot;

    ensureKigumiYaml(resolvedRoot);
    const envResult = await createVenv(resolvedRoot);
    const installResult = await installBasePackages(resolvedRoot, envResult.pythonPath, env.isLocalDev);

    writeProjectYaml(resolvedRoot, envResult.pythonPath, {
        createdVenv: envResult.createdVenv,
        installedViewerDeps: installResult.installedViewerDeps,
        missingBefore: installResult.missingBefore,
        isLocalDev: env.isLocalDev,
    });

    const exampleResult = ensureExampleFrame(resolvedRoot);

    return {
        projectRoot: resolvedRoot,
        isLocalDev: env.isLocalDev,
        pythonPath: envResult.pythonPath,
        createdVenv: envResult.createdVenv,
        installedViewerDeps: installResult.installedViewerDeps,
        missingBefore: installResult.missingBefore,
        exampleFilePath: exampleResult.filePath,
        createdExampleFile: exampleResult.created,
    };
}

module.exports = {
    getInitializationStatus,
    initializeWorkspaceProject,
};
