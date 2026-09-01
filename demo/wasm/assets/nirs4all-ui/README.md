# Vendored nirs4all-ui assets

These files are unmodified snapshots of canonical assets maintained in
[`nirs4all-ui`](https://github.com/GBeurier/nirs4all-ui):

- `assets/styles/nirs4all-default.css`
- `assets/viz.css`
- `assets/brands/nirs4all-methods/horizontal.svg`
- `assets/brands/nirs4all-formats/icon.svg`

They are vendored so the paper companion remains self-contained and works
without a CDN. Run `../../sync_ui_assets.sh` from this directory, or
`./sync_ui_assets.sh` from `demo/wasm`, to refresh them from a sibling checkout.
No demo-specific logo, icon or chart asset is maintained outside
`nirs4all-ui`.
