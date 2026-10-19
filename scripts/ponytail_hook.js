'use strict';

// Project adapter: load the installed skill without global mode files or network calls.
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..');
const event = process.argv[process.argv.length - 1];
const events = new Set(['SessionStart', 'UserPromptSubmit', 'SubagentStart']);
const relative = path.relative(root, process.cwd());

if (relative === '..' || relative.startsWith('..' + path.sep) || path.isAbsolute(relative)) {
  process.exit(0);
}
if (!events.has(event)) {
  process.stderr.write('Unsupported Ponytail hook event.\n');
  process.exit(1);
}

let finished = false;
function emit() {
  if (finished) return;
  finished = true;
  try {
    const skill = fs.readFileSync(path.join(root, '.agents/skills/ponytail/SKILL.md'), 'utf8')
      .replace(/^\uFEFF/, '').replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, '').trim();
    if (!skill.startsWith('# Ponytail')) throw new Error('invalid_skill');
    const preflight = [
      'Receipt Assistant project preflight:',
      '- Preserve AGENTS.md, existing user changes, OCR contracts, and Excel output compatibility.',
      '- Before edits, read the affected flow and callers and identify the smallest complete change.',
      '- For runtime or dependency changes, check the working Python, optional OCR packages, and CPU/GPU environment first.',
      '- After edits, run relevant checks and state what was not checked. Never log receipt text, secrets, or full local paths.',
      '- Respect the user\'s latest Ponytail mode/off instruction. This context does not authorize extra changes, full audits, or processing customer files.',
    ].join('\n');
    process.stdout.write(JSON.stringify({
      hookSpecificOutput: { hookEventName: event, additionalContext: skill + '\n\n' + preflight },
    }) + '\n');
    process.exit(0);
  } catch (_) {
    process.stderr.write('Project Ponytail instructions are unavailable or invalid.\n');
    process.exit(1);
  }
}

// Discard input: prompt/transcript content is neither retained nor echoed.
process.stdin.resume();
process.stdin.on('end', emit);
process.stdin.on('error', emit);
setTimeout(emit, 1000);
