# Third-party notices

## React, React DOM, and Scheduler

`frontend/offline-vendor/runtime.js` and its copy under `frontend/dist/vendor/` contain the production React 19.1.1 / React DOM 19.1.1 runtime and its Scheduler dependency. The runtime was isolated from the same packages bundled by the installed Playwright 1.57.0 distribution because npm access was unavailable. No Playwright UI/application code, fonts, icons, or other assets are included in that runtime. The small ESM wrappers are project code.

Copyright (c) Meta Platforms, Inc. and affiliates.

MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Upstream: https://github.com/facebook/react

## Bootstrap 5.3.6 CSS

`frontend/offline-vendor/bootstrap.min.css` and its copy under `frontend/dist/vendor/` are Bootstrap CSS; the original version/license header is retained. This is the standard CSS, not a paid theme.

Copyright (c) 2011–2025 The Bootstrap Authors.

MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Upstream: https://github.com/twbs/bootstrap

## Other dependencies and generated assets

Python and npm dependencies listed in the dependency manifests retain their respective upstream licenses and are installed separately. The synthetic label images and application icon were generated for this project. Sample-label generation uses an installed system font, but no font file is distributed. Government warning text is reproduced as the required federal statement. No real product labels or agency logos are included.
