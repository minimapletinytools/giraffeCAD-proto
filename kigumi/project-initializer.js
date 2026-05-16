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
        '"""Starter Kigumi frame: a simple H-shaped frame made of four 90x90mm timbers.',
        '',
        'Two side timbers run in the +Y direction. Two cross timbers join them with',
        'mortise-and-tenon joints (with 15mm draw-bore pegs), inset from the ends so',
        'the mortises sit safely away from the timber ends.',
        '"""',
        '',
        'from kumiki import *',
        '',
        '',
        '# --- Dimensions -------------------------------------------------------------',
        '',
        'timber_size = Matrix([mm(90), mm(90)])  # 90x90mm cross section',
        '',
        'side_length = mm(600)            # length of each side timber (along Y)',
        'side_spacing = mm(500)           # center-to-center spacing of side timbers (along X)',
        'end_inset = mm(100)              # cross-timber inset from the side-timber ends',
        '',
        '# Tenon cross-section is (width_axis, height_axis) in the cross-timber local frame.',
        '# Cross timbers run in +X with width_direction=FRONT, so local height axis = global Z.',
        '# 80mm in global Y, 40mm in global Z (the shorter dimension).',
        'tenon_size = Matrix([mm(80), mm(40)])',
        'tenon_length = mm(75)',
        'mortise_depth = tenon_length + mm(6)',
        '',
        '# 15mm round draw-bore peg, slightly offset so the joint draws tight.',
        'peg_diameter = mm(15)',
        'peg_draw_bore_offset = mm(2)',
        '',
        '',
        'def build_frame() -> Frame:',
        '    # Side timbers run in +Y, at x = +/- side_spacing/2.',
        '    left_side = create_axis_aligned_timber(',
        '        bottom_position=create_v3(-side_spacing / 2, -side_length / 2, Rational(0)),',
        '        length=side_length,',
        '        size=timber_size,',
        '        length_direction=TimberFace.FRONT,',
        '        width_direction=TimberFace.RIGHT,',
        '        ticket="Left Side",',
        '    )',
        '    right_side = create_axis_aligned_timber(',
        '        bottom_position=create_v3(side_spacing / 2, -side_length / 2, Rational(0)),',
        '        length=side_length,',
        '        size=timber_size,',
        '        length_direction=TimberFace.FRONT,',
        '        width_direction=TimberFace.RIGHT,',
        '        ticket="Right Side",',
        '    )',
        '',
        '    # Cross timbers run in +X, inset from the ends of the side timbers.',
        '    # Their length spans center-to-center so the tenons land inside the sides.',
        '    cross_length = side_spacing',
        '    cross_y_front = side_length / 2 - end_inset',
        '    cross_y_back = -cross_y_front',
        '',
        '    back_cross = create_axis_aligned_timber(',
        '        bottom_position=create_v3(-cross_length / 2, cross_y_back, Rational(0)),',
        '        length=cross_length,',
        '        size=timber_size,',
        '        length_direction=TimberFace.RIGHT,',
        '        width_direction=TimberFace.FRONT,',
        '        ticket="Back Cross",',
        '    )',
        '    front_cross = create_axis_aligned_timber(',
        '        bottom_position=create_v3(-cross_length / 2, cross_y_front, Rational(0)),',
        '        length=cross_length,',
        '        size=timber_size,',
        '        length_direction=TimberFace.RIGHT,',
        '        width_direction=TimberFace.FRONT,',
        '        ticket="Front Cross",',
        '    )',
        '',
        '    # Round draw-bore peg, one per joint, centered on the tenon.',
        '    # Peg axis is perpendicular to the cross timber\'s FRONT face (i.e. through',
        '    # the side timber from the front, in global +Y on the back cross and -Y on the front cross).',
        '    peg_params = SimplePegParameters(',
        '        shape=PegShape.ROUND,',
        '        peg_positions=[(tenon_length / 2, Rational(0))],',
        '        size=peg_diameter,',
        '        depth=None,                                # through peg',
        '        tenon_hole_offset=peg_draw_bore_offset,    # draw-bore offset pulls the joint tight',
        '    )',
        '',
        '    def mortise_into_side(cross, cross_end, side):',
        '        return cut_mortise_and_tenon_joint_on_FAT(',
        '            arrangement=ButtJointTimberArrangement(',
        '                receiving_timber=side,',
        '                butt_timber=cross,',
        '                butt_timber_end=cross_end,',
        '                front_face_on_butt_timber=TimberLongFace.FRONT,',
        '            ),',
        '            tenon_size=tenon_size,',
        '            tenon_length=tenon_length,',
        '            mortise_depth=mortise_depth,',
        '            peg_parameters=peg_params,',
        '        )',
        '',
        '    joints = [',
        '        mortise_into_side(back_cross, TimberReferenceEnd.BOTTOM, left_side),',
        '        mortise_into_side(back_cross, TimberReferenceEnd.TOP, right_side),',
        '        mortise_into_side(front_cross, TimberReferenceEnd.BOTTOM, left_side),',
        '        mortise_into_side(front_cross, TimberReferenceEnd.TOP, right_side),',
        '    ]',
        '',
        '    return Frame.from_joints(joints, name="My Cute Frame")',
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
        'required = ["sympy", "numpy", "trimesh", "manifold3d", "networkx"]',
        'missing = [name for name in required if importlib.util.find_spec(name) is None]',
        'print("\\n".join(missing))',
    ].join('; ');

    const { stdout } = await runCommand(pythonPath, ['-c', snippet], workspaceRoot);
    return stdout
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.length > 0);
}

async function ensurePipAvailable(workspaceRoot, pythonPath) {
    try {
        await runCommand(pythonPath, ['-m', 'pip', '--version'], workspaceRoot);
        return;
    } catch (_error) {
        // Fall through to ensurepip repair path.
    }

    await runCommand(pythonPath, ['-m', 'ensurepip', '--upgrade'], workspaceRoot);
    await runCommand(pythonPath, ['-m', 'pip', '--version'], workspaceRoot);
}

async function installBasePackages(workspaceRoot, pythonPath, isLocalDev) {
    const missingBefore = await getMissingViewerDependencies(workspaceRoot, pythonPath);
    if (missingBefore.length === 0) {
        return {
            installedViewerDeps: false,
            missingBefore,
        };
    }

    await ensurePipAvailable(workspaceRoot, pythonPath);
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

let _initializationInProgress = false;

function isInitializationInProgress() {
    return _initializationInProgress;
}

async function initializeWorkspaceProject(workspaceRoot, filePath) {
    if (_initializationInProgress) {
        const err = new Error('Initialization is already in progress.');
        err.code = 'INITIALIZATION_IN_PROGRESS';
        throw err;
    }
    _initializationInProgress = true;
    try {
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
    } finally {
        _initializationInProgress = false;
    }
}

module.exports = {
    getInitializationStatus,
    initializeWorkspaceProject,
    isInitializationInProgress,
};
