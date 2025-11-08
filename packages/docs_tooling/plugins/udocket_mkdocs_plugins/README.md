# uDocket Auto Image Scale Plugin

This directory hosts the local MkDocs plugins shipped with the docs toolbox.

## auto-image-scale

Inspects generated HTML and injects explicit `width`/`height` attributes
for images that opt in via a data attribute, a CSS class, or an optional
default scale. This keeps rendered images consistent without manually
editing every Markdown file.

Example configuration:

```yaml
plugins:
  - auto-image-scale:
      scale_attr: data-scale
      class_map:
        img--half: 0.5
      default_scale: null
```

## include-build-assets

Copies artifacts produced outside MkDocs (Mermaid renders, PDFs, hashes)
into the built site. Configure the plugin with the path to the build
directory and the prefix to use inside the site output:

```yaml
plugins:
  - include-build-assets:
      source_dir: packages/docs_tooling/build
      site_prefix: build
```

The documentation references these assets with `build/...` URLs so they
resolve correctly regardless of page depth.
