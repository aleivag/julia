# julia

Julia is a static cookbook generator and local-first cooking companion. Julia is
the framework; each generated cookbook has its own configurable identity.

```bash
python3 -m julia_cookbook build .
python3 -m julia_cookbook serve .
```

During authoring, watch the cookbook and reload open browser pages automatically:

```bash
julia serve . --watch
julia feast serve . --watch
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

## Feasts

Feasts are TOML files in `feasts/` containing an ordered menu. A dish can refer
to a recipe slug or remain menu-only until its recipe is authored.

```bash
julia feast build .
julia feast serve .
```

Each feast generates an overview, printable menu, kitchen booklet, and shopping
list. Guest names, allergies, and private addresses belong in a private feast
repository, not a public cookbook.
