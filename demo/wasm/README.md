# AOM-PLS WebAssembly demonstration

This static page calls the `nirs4all-methods` (`n4m`) AOM-PLS selector compiled
to WebAssembly. It fits a reproducible synthetic NIR calibration in the browser,
reports the globally selected strict-linear operator and predicts a held-out set
from original-wavelength coefficients.

The committed bundle is the public `@nirs4all/methods` **1.0.13** release. Refresh
it reproducibly from npm (the version is pinned in the staging script):

```bash
./stage_bundle.sh
```

Run locally from the repository root (WASM must be served over HTTP):

```bash
python -m http.server 8765
# open http://localhost:8765/demo/wasm/
```

The GitHub Pages workflow publishes this directory. The demonstration contains
no remote analytics and does not upload spectra.
