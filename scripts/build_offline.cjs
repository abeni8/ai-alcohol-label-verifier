/** Offline static build of the same JSX source. Normal development uses Vite.
 * Requires TypeScript 5.8+ (npm install --no-save typescript, or TYPESCRIPT_PATH).
 * No changes to source behavior: transpile JSX and resolve vendored React 19.1.1.
 */
const fs = require('node:fs');
const path = require('node:path');
const ts = require(process.env.TYPESCRIPT_PATH || 'typescript');
const root = path.resolve(__dirname, '..');
const src = path.join(root, 'frontend/src');
const dist = path.join(root, 'frontend/dist');
fs.rmSync(dist, { recursive: true, force: true });
fs.mkdirSync(dist, { recursive: true });
fs.cpSync(path.join(root, 'frontend/offline-vendor'), path.join(dist, 'vendor'), { recursive: true });
for (const file of fs.readdirSync(src)) {
  if (file.endsWith('.jsx')) {
    let text = ts.transpileModule(fs.readFileSync(path.join(src, file), 'utf8'), {
      compilerOptions: { jsx: ts.JsxEmit.React, target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
      reportDiagnostics: true,
    });
    if (text.diagnostics?.length) throw new Error(JSON.stringify(text.diagnostics));
    text = text.outputText.replaceAll("from 'react'", "from './vendor/react.js'").replaceAll("from 'react-dom/client'", "from './vendor/react-dom.js'")
      .replaceAll('.jsx\'', '.js\'').replace(/import '[^']+\.css';\n/g, '');
    fs.writeFileSync(path.join(dist, file.replace(/\.jsx$/, '.js')), text);
  } else fs.copyFileSync(path.join(src, file), path.join(dist, file));
}
let html = fs.readFileSync(path.join(root, 'frontend/index.html'), 'utf8');
html = html.replace('/src/main.jsx', '/main.js').replace('</head>', '<link rel="stylesheet" href="/vendor/bootstrap.min.css" /><link rel="stylesheet" href="/styles.css" /></head>');
fs.writeFileSync(path.join(dist, 'index.html'), html);
fs.copyFileSync(path.join(root, 'frontend/public/favicon.svg'), path.join(dist, 'favicon.svg'));
console.log('Offline static build complete; source JSX compiled with TypeScript ' + ts.version);
