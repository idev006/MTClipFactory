# New Product Auto Factory Template

Copy this folder to create a new automation-ready product folder.

## Steps

1. Rename this folder to the product folder name you want to use.
2. Edit `product.toml`.
3. Edit `pipeline.toml`, including fill-policy defaults when needed.
4. Edit `captions.toml` when you want product-level caption pools ready.
5. Put media files into `foreground`, `background`, `music`, and `voice`.
6. Edit each `tags.toml` file when you want automation-oriented tag metadata ready.

## Notes

- `product.toml` and `pipeline.toml` are required by the current folder-driven automation contract.
- `captions.toml` is included as the standard product-level caption metadata shape for future automated caption resolution.
- `tags.toml` files are included as the standard metadata shape for future automatic tag application.
- `runs/` will be created by automation to store product-local preview/final artifacts, manifests, and journal files.
- Keep automation-facing tags in `group:name` format such as `message:hook` or `scene:space`.
