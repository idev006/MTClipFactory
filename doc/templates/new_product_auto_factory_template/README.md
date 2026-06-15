# New Product Auto Factory Template

Copy this folder to create a new automation-ready product folder.

## Steps

1. Rename this folder to the product folder name you want to use.
2. Edit `contracts/product.toml`.
3. Edit `contracts/pipeline.toml`, including fill-policy defaults when needed.
4. Edit `contracts/captions.toml` when you want product-level caption pools ready.
5. Fill `contracts/prod_detail.txt` with the product facts, selling points, and operator notes.
6. Put media files into `assets/foreground`, `assets/background`, `assets/music`, and `assets/voice`.
7. Edit each `assets/*/tags.toml` file when you want automation-oriented tag metadata ready.

## Notes

- `contracts/product.toml` and `contracts/pipeline.toml` are required by the preferred folder-driven automation contract.
- `contracts/captions.toml` is included as the standard product-level caption metadata shape for automated caption resolution.
- `contracts/prod_detail.txt` is the operator-facing source for product context and offer details.
- `assets/*/tags.toml` files are included as the standard metadata shape for future automatic tag application.
- `runs/` will be created by automation to store product-local preview/final artifacts, manifests, and journal files.
- Runtime remains backward compatible with legacy root-level `product.toml`, `pipeline.toml`, `captions.toml`, and `foreground`/`background`/`music`/`voice` folders.
- Do not keep both legacy and v2 paths for the same logical item in one product folder. The runtime now fails truthfully on ambiguous layout.
- Keep automation-facing tags in `group:name` format such as `message:hook` or `scene:space`.
