# Third-party notices

## celeganssim XLSX reader

`src/hive_connectome/connectomes/xlsx.py` is adapted from `scripts/xlsx.py` in
`vdmkenny/celeganssim`.

Copyright (c) 2026 Kenny Van de Maele

MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Upstream: https://github.com/vdmkenny/celeganssim

## MaleCNS locomotor runtime data

The HIVE development/control Bee runtime downloads a pinned MaleCNS v1.0 locomotor subgraph
from DesktopFly commit `32b00011e83c3dc85fa3ea0b3934155b04f1635d`.

- Upstream extraction: https://github.com/DenisSergeevitch/desktop-fly
- MaleCNS: https://male-cns.janelia.org/
- Dataset license: CC BY 4.0
- Pinned Git blob: `2b48900d2bac49bf2b58820f29e3491fd3dd4691`

The runtime file is downloaded from its source during setup and is not embedded
in this repository.
