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

Projects contain a `.julia` TOML configuration file, a `recipes/` directory, and
optionally a `guides/` directory for reference material such as temperature and
timing charts.
See [RECIPE_FORMAT.md](RECIPE_FORMAT.md) for the recipe language and `PLAN.md`
for the broader product design.

Alternate formulas for the same dish can share one collection entry through
top-level `== variant name ==` sections. Generic `@include{relative/path.md}`
directives let those variants—or any recipe source—live in smaller files without
turning the included fragments into recipe dependencies.

The generated collection is divided by content type:

```text
/               Recipes (default)
/guides/        Reference guides
/feasts/        Gatherings and menus
```

Each section has its own search and presentation. Shopping-list controls remain
on the Recipes page only.

Cookbook identity is separate from the Julia framework:

```toml
[site]
title = "My Cookbook"
unit_system = "international"
theme = "auto"

[author]
name = "Your Name"
email = "you@example.com"
website = "https://example.com"
instagram = "@yourhandle"
```

The screen theme can be changed from any generated page and is remembered on
that device. Available values are `auto`, `nordic`, `night`, and `editorial`.
`auto` follows the device's light/dark preference, choosing Nordic for light and
Night for dark. Printing always uses the Editorial treatment regardless of the
screen selection.

## Feasts

Feasts are TOML files in `feasts/` containing an ordered menu. A dish can refer
to a recipe slug or remain menu-only until its recipe is authored.

```bash
julia feast build .
julia feast serve .
```

Each feast generates an overview, printable menu, kitchen booklet, and shopping
list. Shopping-list checkboxes persist locally per feast, so completed items
remain crossed out after refreshing the page. Guest names, allergies, and private addresses belong in a private feast
repository, not a public cookbook.

Dish presentation can be customized without changing the underlying recipe:

```toml
title = "Summer Dinner"

[[dishes]]
course = "Dessert"
recipe = "sous-vide-creme-brulee"
name = "Vanilla Custard, Burnt Sugar"
description = "Silky vanilla custard with a crisp caramel top."
note = "Served with late-summer berries."
```

Dish presentation fields are scoped to that feast; they do not modify the
referenced recipe:

- `name` replaces the recipe title in the feast overview and printable menu.
- `description` replaces the recipe headnote with menu-specific descriptive text.
- `note` is appended after the effective description for feast-specific context,
  such as service or pairing details.

If an override is omitted, Julia falls back to the referenced recipe's title or
headnote. The older feast field `headnote` remains a backward-compatible alias
for `description`, but new feasts should use `description`.

A menu-only dish without a recipe can use the same presentation fields:

```toml
[[dishes]]
course = "Dessert"
name = "Seasonal Ice Cream"
description = "Tonight's market flavor."
note = "Served with crisp wafers."
```
