const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

function resolvePython(projectRoot) {
  if (process.env.HORSEY_VIEWER_PYTHON) {
    return process.env.HORSEY_VIEWER_PYTHON;
  }

  const candidates = [
    '.venv/bin/python3',
    '.venv/bin/python',
    'venv/bin/python3',
    'venv/bin/python',
  ];

  for (const rel of candidates) {
    const candidate = path.join(projectRoot, rel);
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  return 'python3';
}

function createRunnerClient() {
  const extensionRoot = path.resolve(__dirname, '..');
  const projectRoot = path.resolve(extensionRoot, '..');
  const runnerPath = path.join(extensionRoot, 'runner.py');
  const examplePath = path.join(extensionRoot, 'test-fixtures', 'minimal_frame.py');
  const pythonCmd = resolvePython(projectRoot);

  const child = spawn(pythonCmd, [runnerPath, examplePath], {
    cwd: projectRoot,
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  let buffer = '';
  const waiters = [];
  const stderr = [];

  child.stdout.on('data', (chunk) => {
    buffer += chunk.toString();
    let newlineIndex = buffer.indexOf('\n');

    while (newlineIndex >= 0) {
      const line = buffer.slice(0, newlineIndex).trim();
      buffer = buffer.slice(newlineIndex + 1);

      if (line) {
        let parsed;
        try {
          parsed = JSON.parse(line);
        } catch (error) {
          parsed = { __parseError: error.message, raw: line };
        }
        const waiter = waiters.shift();
        if (waiter) {
          waiter.resolve(parsed);
        }
      }

      newlineIndex = buffer.indexOf('\n');
    }
  });

  child.stderr.on('data', (chunk) => {
    stderr.push(chunk.toString());
  });

  function readMessage(timeoutMs = 15000) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error(`Timed out waiting for runner message. stderr:\n${stderr.join('')}`));
      }, timeoutMs);

      waiters.push({
        resolve: (message) => {
          clearTimeout(timer);
          resolve(message);
        },
      });
    });
  }

  let requestId = 0;
  async function request(command, payload = {}) {
    requestId += 1;
    const id = requestId;
    child.stdin.write(`${JSON.stringify({ id, command, payload })}\n`);
    const message = await readMessage();
    return message;
  }

  async function shutdown() {
    if (!child.killed && child.exitCode === null) {
      try {
        await request('shutdown');
      } catch (error) {
        // Ignore shutdown race conditions.
      }
    }
    if (!child.killed && child.exitCode === null) {
      child.kill();
    }
  }

  return { child, readMessage, request, shutdown, stderr };
}

describe('runner protocol', () => {
  jest.setTimeout(60000);

  test('ready + command flow returns frame and geometry payloads', async () => {
    const client = createRunnerClient();

    try {
      const ready = await client.readMessage();
      expect(ready.type).toBe('ready');
      expect(Array.isArray(ready.commands)).toBe(true);
      expect(ready.commands).toContain('get_frame');
      expect(ready.commands).toContain('get_geometry');

      const ping = await client.request('ping');
      expect(ping.ok).toBe(true);
      expect(ping.result).toEqual({ pong: true });

      const frame = await client.request('get_frame');
      expect(frame.ok).toBe(true);
      expect(frame.result.timber_count).toBeGreaterThan(0);

      const geometry1 = await client.request('get_geometry');
      expect(geometry1.ok).toBe(true);
      expect(geometry1.result.kind).toBe('triangle-geometry');
      expect(Array.isArray(geometry1.result.meshes)).toBe(true);
      expect(geometry1.result.meshes.length).toBeGreaterThan(0);
      expect(geometry1.result.changedKeys.length).toBe(geometry1.result.meshes.length);
      expect(Array.isArray(geometry1.result.remeshMetrics)).toBe(true);
      expect(geometry1.result.remeshMetrics.length).toBe(geometry1.result.changedKeys.length);
      expect(geometry1.result.counts.totalTimbers).toBe(geometry1.result.meshes.length);
      expect(geometry1.result.counts.changedTimbers).toBe(geometry1.result.changedKeys.length);
      expect(geometry1.result.counts.removedTimbers).toBe(geometry1.result.removedKeys.length);
      if (geometry1.result.remeshMetrics.length > 0) {
        const metric = geometry1.result.remeshMetrics[0];
        expect(typeof metric.timberKey).toBe('string');
        expect(typeof metric.remesh_s).toBe('number');
        expect(metric.remesh_s).toBeGreaterThanOrEqual(0);
        expect(typeof metric.csg_depth).toBe('number');
        expect(metric.csg_depth).toBeGreaterThanOrEqual(1);
        expect(typeof metric.triangle_count).toBe('number');
        expect(metric.triangle_count).toBeGreaterThanOrEqual(0);
      }

      const geometry2 = await client.request('get_geometry');
      expect(geometry2.ok).toBe(true);
      expect(geometry2.result.kind).toBe('triangle-geometry');
      expect(Array.isArray(geometry2.result.changedKeys)).toBe(true);
      expect(geometry2.result.changedKeys).toHaveLength(0);
      expect(Array.isArray(geometry2.result.remeshMetrics)).toBe(true);
      expect(geometry2.result.remeshMetrics).toHaveLength(0);
      expect(geometry2.result.counts.totalTimbers).toBe(geometry2.result.meshes.length);
    } finally {
      await client.shutdown();
    }
  });
});
