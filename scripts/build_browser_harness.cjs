/** Compile the unmodified React source for in-memory browser testing when browser URL navigation is disabled. */
const fs=require('node:fs'),path=require('node:path');
const ts=require(process.env.TYPESCRIPT_PATH||'typescript');
const root=path.resolve(__dirname,'..');
const src=path.join(root,'frontend/src');
const runtime=fs.readFileSync(path.join(root,'frontend/offline-vendor/runtime.js'),'utf8').replace('export const React = Bh();','globalThis.React = Bh();').replace('export const ReactDOM = F1();','globalThis.ReactDOM = F1();');
let code='(function(){\n'+runtime+'\n})();\n(function(){\nconst modules={},cache={};\n';
for(const file of fs.readdirSync(src)) {
 if(!/\.(jsx|mjs)$/.test(file))continue;
 const output=ts.transpileModule(fs.readFileSync(path.join(src,file),'utf8'),{fileName:'source.tsx',compilerOptions:{jsx:ts.JsxEmit.React,target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}).outputText;
 code+='modules['+JSON.stringify('./'+file)+']=function(require,module,exports){\n'+output+'\n};\n';
}
code+=`function require(name){if(name==='react')return globalThis.React;if(name==='react-dom/client')return globalThis.ReactDOM;if(name.endsWith('.css'))return {};if(cache[name])return cache[name].exports;if(!modules[name])throw new Error('Unknown module '+name);const m={exports:{}};cache[name]=m;modules[name](require,m,m.exports);return m.exports;}require('./main.jsx');})();`;
fs.writeFileSync(path.join(root,'evidence/browser-harness.js'),code);
console.log('Browser test harness compiled from current source.');
