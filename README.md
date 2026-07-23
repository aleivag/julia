# julia

Julia is a static cookbook generator and local-first cooking companion. Julia is
the framework; each generated cookbook has its own configurable identity.

```bash
python3 -m julia_cookbook build .
python3 -m julia_cookbook serve .
```

Projects contain a `.julia` TOML configuration file and a `recipes/` directory.
See `PLAN.md` for the recipe language and product design.

Cookbook identity is separate from the Julia framework:

```toml
[site]
title = "My Cookbook"
unit_system = "international"

[author]
name = "Your Name"
email = "you@example.com"
website = "https://example.com"
instagram = "@yourhandle"
```
