/** Start the complete local application. Ctrl+C stops both owned processes. */
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const python = join(root, 'Backend/.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const vite = join(root, 'frontend/node_modules/vite/bin/vite.js');
for (const file of [python, vite]) {
  if (!existsSync(file)) throw new Error('Faltan dependencias. Sigue la instalación del README antes de iniciar.');
}
const processes = [];
let stopping = false;
function stop(code = 0) {
  if (stopping) return;
  stopping = true; process.exitCode = code;
  for (const child of processes) if (child.exitCode === null) child.kill();
}
function start(command, args, cwd, name) {
  const child = spawn(command, args, { cwd, windowsHide: true, stdio: 'inherit' });
  processes.push(child);
  child.on('error', error => { console.error(`${name}: ${error.message}`); stop(1); });
  child.on('exit', code => { if (!stopping) { console.error(`${name} terminó (${code}).`); stop(code || 0); } });
}
process.on('SIGINT', () => stop());
process.on('SIGTERM', () => stop());
start(python, ['-m', 'uvicorn', 'main:app', '--app-dir', 'Backend/src', '--host', '127.0.0.1', '--port', '8000'], root, 'Backend');
start(process.execPath, [vite, '--host', '127.0.0.1'], join(root, 'frontend'), 'Frontend');
console.log('Macromicetos: http://127.0.0.1:5173/Macromicetos/ · API: http://127.0.0.1:8000/docs');
