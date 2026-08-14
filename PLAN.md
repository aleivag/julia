# julia

**julia** is a *cookbook static site generator*. The name comes from Julia Child,
and the recipe format is inspired by the layout of *Mastering the Art of French
Cooking* — most notably its two-column design, where ingredients sit in the left
margin aligned to the step that uses them.

> Status: **brainstorming / design**. This document is a living spec. Decisions
> we've locked in are under [Decisions](#decisions); things still open are under
> [Open questions](#open-questions).

---

## Goals

- Turn a directory of recipes (plain-text, version-controllable) into a beautiful
  static cookbook website.
- Faithfully reproduce the *Mastering the Art of French Cooking* aesthetic — the
  two-column, ingredient-beside-its-step layout is **core to julia's identity**.
- Recipes are the single source of truth. From one recipe file, julia derives:
  the two-column layout, scaled quantities, and aggregated shopping lists.
- Be a **cooking companion**, not just a publisher: an interactive **Cook Mode**
  lets you actually cook from a recipe — check off steps, scale, run timers, and
  keep notes on your experiments (see [Cook Mode](#cook-mode-headline-feature)).
- Treat every recipe as a **living lab notebook**: the notes you take while
  cooking are proto-variations that can graduate into named variations over time.
- **Zero-cost and zero-maintenance**: hostable for free on GitHub Pages (or any
  static host). No server, no database, no bill — *including* Cook Mode.

## How it works

Like most build systems / SSGs, you run:

```bash
julia build [/path/to/dir]     # defaults to cwd if the path is absent
```

The target directory must contain:

- **`.julia`** — the config file, in TOML format.
- **`recipes/`** — a directory of recipe files (markdown + julia's special syntax).

`julia build` reads the config, parses every recipe, and emits a static site
(default: `./_site` or similar) ready to be served or deployed.

---

## Decisions

### Language & distribution
- **Build engine in Python.** The format is still evolving and the hard parts are
  text parsing + templating, not raw speed. Python lets us iterate cheaply and has
  a mature ecosystem (markdown, Jinja2, TOML).
- **Distributed via `uv tool install` / `pipx`** — a one-line install, no
  virtualenv juggling for users.
- **The format spec is kept language-agnostic** so a future Rust port would be an
  engine rewrite, not a redesign.
- **Client-side interactivity in tiny vanilla JS**, *not* PyScript/Pyodide.
  Rationale: Cook Mode is used on a phone in the kitchen, on flaky wifi/cell data —
  a multi-megabyte Python-in-WASM runtime download would mean a slow "loading
  Python" spinner before anything works, and the actual logic (scaling, shopping
  lists, ratio math) is trivial arithmetic that vanilla JS runs instantly and
  offline. The engine emits structured JSON per page; JS reads it. To keep one
  source of truth, shared constants/logic can be generated from the Python model
  at build time. PyScript is reserved for a hypothetical heavy feature only.

### Recipe format — the "special syntax"

A recipe file is **frontmatter (metadata) + a sequence of steps**. Ingredients are
written **inline** in the step prose (natural to author), and julia **extracts**
them to build the left column of the two-column layout. One source of truth →
every view (layout, scaling, shopping list).

Data model:

```
recipe
├── metadata   (title, yield/servings, times, tags, relationships, ...)
└── steps[]
     ├── title         (optional: prep, brine, rub, cook, rest, ...)
     ├── prose         (instructions, with inline annotations)
     ├── ingredients[] (qty, unit, item, note, attrs) ← derived → left column
     ├── inputs[]      (intermediate products consumed from earlier steps)
     ├── outputs[]     (products created by this step for later steps)
     ├── equipment[]   (#cookware)               ← derived → margin callouts
     ├── timers[]      (~timers)                  ← derived → inline, non-scaling
     └── parameters[]  ($temp, etc.)              ← derived → inline, converts
```

Ingredients are external inputs: things the cook obtains before starting and
that belong in aggregate recipe and shopping lists. Step inputs and outputs are
internal products such as separated egg yolks, custard, dough, or a prepared
sauce. They appear in the steps that produce or consume them but never become
shopping-list entries.

Recipes can include an optional, concise headnote in frontmatter. It appears on
the cookbook index and should usually be one sentence:

```yaml
headnote: A bright make-ahead custard that turns leftover whites into pavlova.
```

Markdown between frontmatter and the first step is a short recipe-page blurb.
Blurbs support internal recipe and search links without requiring output URLs:

```markdown
Use the whites in [pavlova](recipe:orange-cranberry-mint-pavlova), or browse
[recipes using egg whites](search:egg-whites).
```

Related recipes can be grouped as named variations beneath the master recipe:

```yaml
variations: [vanilla-custard, chocolate-custard]
```

Reusable preparations are recipe dependencies, not ordinary ingredients. A
recipe reference links to its source recipe, scales the requested yield, expands
its raw ingredients into feast shopping lists, and includes its instructions in
the kitchen booklet:

```markdown
Prepare @recipe{artichoke-leche-de-tigre}{2%cups} and keep it cold.
```

The referenced recipe remains independently searchable and can use metadata such
as `family: leche-de-tigre` to group peer preparations.

On an individual recipe page, a dependency should render as a full-width,
foldable recipe step rather than as a small ingredient-row disclosure. Opening
the step reveals the dependency's normal two-column steps in place. Nested
dependencies use the same presentation recursively; all remain collapsed by
default, and each retains an optional link to its standalone recipe page. Child
steps use hierarchical display numbers (`3.1`, `3.1.1`, and so on), while Cook
Mode persistence uses stable recipe/step paths rather than those mutable display
numbers.

Inline annotation grammar (Cooklang-style — see open question on adoption):

| Syntax                             | Meaning     | Behavior                                  |
|------------------------------------|-------------|-------------------------------------------|
| `== step ==`                       | step        | begins an untitled step                   |
| `== step brine ==`                 | titled step | begins a step/component named `brine`     |
| `@item{qty%unit}`                  | ingredient  | left column + shopping list; **scales**   |
| `@brown sugar{100%g}`              | multi-word  | name ends at `{}`                         |
| `@salt{}`                          | to taste    | ingredient with no amount                 |
| `@milk{2%cups}(heated)`            | prep note   | `(note)` renders beside the ingredient    |
| `@salt{1/4%cup}[brand=diamond]`    | attributes  | variant/brand metadata for conversions    |
| `#saucepan{}`                      | equipment   | MAFC-style marginal callout               |
| `~{2%min}` / `~name{2%min}`        | timer       | rendered inline; **does not scale**       |
| `~brine{1-4%hours}`                | timer range | minimum/maximum window for Cook Mode      |
| `$temp{275%F}`                     | temperature | rendered inline; converts, does not scale |
| `=>custard{}`                      | step output | product created by this step; not shopped |
| `^custard{}`                       | step input  | product consumed from an earlier step     |

The step input/output markers make the distinction between purchased
ingredients and intermediate products explicit:

```markdown
== step separate eggs ==
Separate @large eggs{5} into =>egg yolks{5} and =>egg whites{5}.

== step make custard ==
Whisk ^egg yolks{5} with @sugar{1/3%cup} and @heavy cream{2%cups}
to produce =>custard{}.

== step fill ==
Divide ^custard{} among 6 #ramekins{}.
```

The annotation grammar is converging on one common shape:

```ebnf
annotation = marker, name, quantity, [note], [attributes] ;
marker     = "@" | "#" | "~" | "$" | "=>" | "^" ;
name       = { any character except "{" or newline } ;
quantity   = "{", [amount, ["%", unit]], "}" ;
note       = "(", text, ")" ;
attributes = "[", attribute, {",", attribute}, "]" ;
attribute  = key, ["=", value] ;
```

Names are not limited to ASCII words: punctuation, spaces, numbers, hyphens,
and Unicode are needed for names such as `St. Louis-style ribs`, `12-quart
stockpot`, and `Gruyère`. Structural delimiters (`{}`, `()`, and `[]`) currently
must open and close on the same physical line.

There are two intentional exceptions to the common shape:

- An anonymous timer may omit its name: `~{2%min}`.
- A recipe dependency has a slug block followed by a requested quantity block:
  `@recipe{mornay-sauce}{1 1/4%cups}`.

Example recipe file:

```markdown
---
title: Sauce Béchamel
yield: 2 cups
tags: [sauce, master-recipe, french]
---

== step ==
Melt the @butter{2%tbsp} in a #saucepan{} over low heat. Blend
in the @flour{3%tbsp} and cook slowly ~{2%min}, stirring, until foaming.

== step ==
Off heat, pour in the @milk{2%cups}(heated) all at once, whisking
vigorously. Return to heat and boil ~{1%min}, stirring.
```

Titled steps are optional, but recommended when the recipe has natural
components or phases:

```markdown
== step brine ==
Mix @water{3%qt}, @kosher salt{3/4%cup}[brand=diamond-crystal],
@sugar{1/3%cup}, and @liquid smoke{1/4%cup}.

== step rub ==
Mix @kosher salt{1.5%tbsp}, @black pepper{2%tbsp},
@granulated garlic{1%tbsp}, and @cayenne{1/4%tsp}.
```

The step title becomes the default component for ingredients in that step. This
lets julia render component-aware ingredient lists ("Brine", "Rub", "Glaze")
without requiring authors to repeat `component=brine` on every ingredient.

Renders (per step) as:

```
┌─────────────────┬──────────────────────────────────────┐
│ 2 tbsp butter   │  Melt the butter in a saucepan over   │
│ 3 tbsp flour    │  low heat. Blend in the flour and     │
│                 │  cook slowly (2 min), stirring, until  │
│  [saucepan]  ◀── margin: equipment callout              │
│                 │  foaming.                              │
└─────────────────┴──────────────────────────────────────┘
```

### Layout
- **Two-column, ingredient-aligned-to-step layout is non-negotiable** and drives
  the default theme and data model.
- **Responsive single-column fallback** on mobile / narrow screens.

### Quantities, scaling & ratios
- Quantities are **structured** via the inline annotation (`{qty%unit}`), giving us
  scaling, unit-aware shopping-list merging, and (later) unit conversion for free.
- Each recipe can name one practical scaling anchor. Ingredient anchors use
  `[scale=true, step=1]` (for example, racks or eggs); serving/batch-based recipes
  use `scale: yield` in frontmatter. The UI asks for the desired anchor amount and
  derives the multiplier. `[scale=false]` keeps exceptional quantities fixed.
- Portioned yields can express count and unit weight in one field, for example
  `yield: 4 dough balls [each=~250 g]` or
  `yield: 4 rolls [each=100 g +/- 2 g]`. Julia scales ingredients from the target
  total (`count × each`), while annotations marked `[scale=count]` follow the
  requested piece count. `~` means approximate; `+/-` and `±` declare a per-piece
  tolerance without changing the central scaling target.
- A compound yield can be combined with a base flour and a selectable baker's
  percentage such as `[options=65|70|75]`. The scaling panel then coordinates
  flour, hydration, portion count, and portion weight, and reports surplus dough
  when a flour-driven batch does not divide evenly.
- **Times and oven temperatures do not scale** (they aren't linear). Timers `~{}`
  are explicitly non-scaling.
- The cookbook unit system defaults to `international` in `.julia`; recipes can
  override it with `units: imperial` or `units: international` in frontmatter.
  Readers can override either default in **Scale & units**. Conversion includes
  temperatures plus structured culinary weights and volumes.
- **Ratio-aware quantities** (e.g. baker's percentages). An ingredient can be
  defined relative to a base rather than as an absolute amount:
  ```
  @flour{500%g}[base=true]
  @water{65%bakers}[ratio_of=flour] → julia computes 325 g and shows "65% hydration"
  ```
  `[base=true]` identifies the default ratio base. `ratio_of` is optional when
  there is only one base ingredient.
  Ratios recompute correctly at any batch size, so scaling stays bulletproof.
- **Deviation warnings (the mistake-catcher).** In Cook Mode you can optionally log
  what you *actually* used; if it deviates from the recipe's ratio julia warns
  (e.g. logging 250 g water on a 500 g-flour dough → "⚠ that's 50% hydration,
  recipe is 65%"). This is the pizza-dough guardrail that motivated the feature.

### Ingredient identity, variants & normalization
- Ingredient names alone are not always enough. Some ingredients are equivalent
  in purpose but not in quantity: Diamond Crystal kosher salt vs. Morton kosher
  salt vs. fine table salt; instant yeast vs. active dry yeast vs. fresh yeast.
- julia should distinguish:
  - **identity** — the culinary ingredient (`salt`, `yeast`)
  - **variant attributes** — brand, grind, type, hydration, strength, etc.
  - **display quantity** — what the author wrote
  - **canonical quantity** — normalized quantity used for math/conversion
- Attributes use bracket metadata:
  ```
  @kosher salt{3/4%cup}[brand=diamond-crystal]
  @yeast{4%g}[kind=instant]
  @St. Louis-style ribs{2%racks}[weight_each=2.5 lb]
  ```
- Ingredient normalization is opt-in. Most ingredients remain simple; sensitive
  ingredients can carry attributes so scaling, substitution, and shopping-list
  merging do not become dangerously naive.

### Process parameters: temperatures, times & ranges
- Temperatures and other process settings are not ingredients, but they should be
  structured so julia can convert them and surface them in Cook Mode.
- Proposed syntax:
  ```
  Cook at $temp{275%F} for ~first cook{2.5%hours}.
  Brine in the fridge for ~brine{1-4%hours}.
  Roast until the center reaches $temp{74%C}[role=internal].
  ```
- Temperatures **convert** (F ↔ C) but do not scale.
- Durations **convert** when useful (hours ↔ minutes) but do not scale.
- Timer ranges represent process windows: "ready after 1 hour, remove by 4 hours."

### Shopping lists & components
- Shopping lists traverse recipe dependencies and step relationships until they
  reach external `@ingredient{}` leaves. `=>outputs{}` and `^inputs{}` are
  preparation state, not purchases, and must never be aggregated.
- The recipe-level ingredient list should likewise show the external inputs
  needed to begin the recipe, including recursively expanded dependency inputs.
- A step may show both external ingredients and intermediate inputs. Intermediate
  inputs should identify their producing step (for example, "custard — from step
  2") rather than looking like another item to buy.
- julia should support two shopping-list views:
  - **Grouped by component**: ingredients are grouped under their step title
    (`Prep`, `Brine`, `Rub`, `Glaze`). This helps with mise en place and cooking
    phases.
  - **Merged by ingredient**: equivalent ingredients are combined for grocery
    shopping when safe.
- Merging must respect ingredient attributes. These should not merge blindly:
  ```
  @kosher salt{3/4%cup}[brand=diamond-crystal]
  @kosher salt{1.5%tbsp}
  ```
  If attributes differ or are missing, julia should keep lines separate or warn
  rather than assume they are interchangeable.

### Parser diagnostics
- Recipe files are meant to be hand-written drafts, so the parser should be
  friendly and specific when syntax is close but invalid.
- Diagnostics should include file path, line number, the offending marker, and a
  likely fix when possible:
  ```
  recipes/indoor_smoke_ribs.md:12: unknown step marker "== sdtep"
  Did you mean "== step =="?
  ```
- Draft tolerance is part of authoring ergonomics: julia should catch mistakes
  early without silently producing a wrong recipe.

### Cook Mode (headline feature)
"**Make this recipe**" drops you into a focused, kitchen-friendly, fully
client-side experience:
- **Pick a scale first** ("2 pizzas" / "double it") so every quantity is right
  before you start — prevents a whole class of mistakes.
- **Check off ingredients and steps** as you go; progress persists so you can set
  the phone down and come back without losing your place.
- **Live timers** — a `~{2%min}` becomes a real countdown when you reach that step.
- **Per-step notes** while cooking ("used 50% water — too dry, go 65% next time").
- **Ratio deviation warnings** as described above.
- **Cook log** — at the end, save the session (date, scale, notes, outcome:
  worked / didn't / would change).

Notes and variations are the **same feature at different maturity**: experiments
are proto-variations, and a tweak that works can graduate into a named variation.

### Notes storage & cost model
- **Everything in Cook Mode is client-side** (JS + `localStorage`). No server, no
  database → the hosted site stays **free** on GitHub Pages / Cloudflare Pages /
  Netlify. Cook Mode adds **zero hosting cost**.
- **Local-first, with optional user-owned sync:**
  - *Hosted site*: notes live in `localStorage`, with **export/import** for backup
    and moving between devices. A user can optionally sign in with Google and
    synchronize the same portable data through Drive's private `appDataFolder`.
    Julia does not operate an account server or database.
  - *Local tool* (`julia serve`/`cook` on your machine): notes can be **written
    back into the recipe files** and committed to **git** — the permanent,
    version-controlled, git-synced home for notes you want to keep.
- Google Drive is a **sync adapter**, not the runtime source of truth. Cooking
  remains functional offline and without an account. Other adapters (WebDAV,
  Dropbox, GitHub publishing) can be added later without changing the event schema.

```
hosted site (free, static)  ──cook, jot notes──►  localStorage + export
        ▲                                                   │
        │ julia build + git push (free)                     │ (import / paste back)
        │                                                   ▼
   your machine  ◄──notes graduate into recipe files (git)──┘

Optional Google Drive sync copies the local event store between a user's devices;
it is not required to build, browse, or cook.
```

### Cross-references, master recipes & variations — **in scope for v1**
- Recipes can **link to other recipes** ("see also").
- Support **master recipe + variation** relationships (a base recipe followed by
  variations that reference it), a hallmark of the MAFC format.
- Exact syntax for references/variations is an open question.

## MVP (v1) feature set

- [ ] `julia build` — parse recipes → static site.
- [ ] Two-column MAFC layout (responsive).
- [ ] **Servings / yield scaling** (interactive in the generated site).
- [ ] **Ratio-aware quantities** (baker's percentages) + deviation warnings.
- [ ] **Cook Mode** — check-off, live scaling, timers, per-step notes, cook log.
- [ ] **Notes**: `localStorage` + export on the hosted site; write-back to recipe
      files via the local tool; optional Google Drive synchronization.
- [ ] **Tags / categories + a browsable, searchable index.**
- [ ] **Shopping list / meal plan** — aggregate ingredients across selected recipes,
      with grouped-by-component and merged-by-ingredient views.
- [ ] **Cross-references + master/variation relationships.**
- [x] **Step products** — explicit `=>outputs{}` and `^inputs{}` with lineage,
      validation, and shopping-list exclusion.
- [ ] **Parser diagnostics** — friendly line-numbered errors and suggestions for
      common draft mistakes.
- [ ] **Deploy to GitHub Pages** (and any static host), $0 hosting.

> All interactivity (scaling, Cook Mode, shopping list, meal plan) is client-side
> vanilla JS over build-time JSON — no server, no cost.

---

## Open questions (still brainstorming)

- **Cooklang adoption**: use an existing Cooklang parser (Python bindings to
  `cooklang-rs`, or a pure-Python parser) as the base grammar and extend it, vs. a
  bespoke Cooklang-inspired parser. Leaning toward adopt-and-extend. *(Needs a
  check: does a chosen parser support ratio/`%bakers`-style quantities, or do we
  layer that on top?)*
- **Step delimiter**: `== step ==` vs. blank-line-separated paragraphs (Cooklang's
  default) vs. something else.
- **Ingredient attributes syntax**: bracket metadata is proposed
  (`[brand=diamond-crystal, kind=instant]`), but exact typing, quoting, and
  canonical names are still open.
- **Ingredient normalization tables**: which variants ship built in (salt brands,
  yeast types, flour protein, gelatin strength), and how users override them.
- **Process parameter syntax**: `$temp{275%F}` is proposed, but should `$...` cover
  only temperatures or become a general parameter namespace?
- **Timer ranges**: exact syntax and UI for windows like `~brine{1-4%hours}`.
- **Cook log / write-back format**: exact on-disk shape when the local tool saves
  notes into recipe files (a `## Cook Log` section? a sidecar `.log`/frontmatter?).
- **Config schema** (`.julia`): site title, author, theme, base URL, default
  units (metric/imperial), output dir, deploy settings...
- **Theming**: single built-in theme for v1, or a theming system from the start?
- **Images**: per-recipe photos, galleries, image optimization.
- **Search**: build-time index (e.g. client-side fuzzy search) vs. none for v1.
- **Cross-reference / variation syntax**: how to express "see recipe X" and
  "variation of Y" in the recipe file.
- **Step product identity**: whether names alone identify outputs within a recipe
  or whether duplicate names require explicit IDs/from-step attributes. The
  current surface syntax is `=>output{qty%unit}` and `^input{qty%unit}`.
- **Units**: conversion (metric ↔ imperial), fraction handling (½, ⅓), pluralization.
- **Shopping-list merging rules**: when similar ingredients can merge, when
  attributes prevent merging, and when julia should show a warning.
- **Output layout**: directory structure of the generated site, URL scheme.

---

## Roadmap (draft)

1. **Parser + data model** — recipe file → structured recipe object (incl. ratio
   quantities). Emit structured JSON per recipe for the client.
2. **Renderer** — data model → HTML, two-column MAFC theme (responsive).
3. **Site build** — index, tag pages, config, static assets.
4. **Interactivity** — client-side vanilla JS: scaling, shopping list / meal plan.
5. **Cook Mode** — check-off, live scaling, timers, per-step notes, ratio deviation
   warnings, cook log; `localStorage` + export.
6. **Local write-back** — `julia serve`/`cook`: notes → recipe files (git).
7. **Relationships** — cross-refs, master/variation (notes graduating to variations).
8. **Deploy** — GitHub Pages workflow, $0 hosting.
9. **Visual authoring (future)** — edit recipe source in the browser with syntax
   highlighting, live preview, parser diagnostics, and explicit save/export.
   Static hosted sites remain read-only unless connected to a writable provider;
   the local tool can write validated edits directly to recipe files.

### Deferred design: step-level variations

Small variations should not require duplicate recipe files. A future syntax will
attach additions, quantity overrides, omissions, and replacement instructions to
one step. Selecting a variation should update that step, scaling, shopping lists,
and the cooking event while leaving the base recipe intact. The exact authoring
syntax and conflict rules remain open.

Preparation choices are the implemented first slice of this design. Consecutive
steps carrying `[choice=name, option=value]` share one displayed step, and
`default=true` selects the build-time default. Mutually exclusive branches must
produce the same output contract; the selected branch controls Cook Mode and
shopping ingredients.

### Guides

Guides are implemented as Markdown files in `guides/`. They provide searchable
reference material without recipe yields, shopping data, or cooking-progress
state. Guide prose and tables support smart `$temp`, `$weight`, `$time`, and
`$thickness` annotations. Scalar and range measurements respond to the
International/Imperial control, and recipes can link to guides with `guide:`
links. More structured calculators and recipe validation against guide targets
remain future work.

The generated site separates its three primary content types: `/` is the
default Recipes collection, `/guides/` contains reference guides, and `/feasts/`
contains gathering and menu documents. Persistent navigation connects all three
sections; search remains scoped to the active section.

### Feasts

Feasts are first-class TOML documents in `feasts/`. They describe ordered menu
courses and can reference existing recipes or menu-only dishes. A build emits a
feast overview, printable guest menu, scaled kitchen booklet, and shopping list.
Private guest, allergy, and address data should live in a separate private feast
repository even when recipes are public.

Feast dishes may customize guest-facing presentation while retaining their
recipe relationship: `name` overrides the recipe title, `description` replaces
the recipe headnote with menu-specific text, and `note` appends feast-specific
context. The older feast field `headnote` remains an alias for `description`.
These fields affect the menu and feast overview, not the source recipe or kitchen
instructions.
