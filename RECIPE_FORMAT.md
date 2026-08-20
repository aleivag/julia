# Julia recipe format

Julia recipes are Markdown-like text files containing frontmatter, prose, steps,
and inline annotations. The annotations let Julia derive ingredient lists,
shopping data, scaling controls, equipment, timers, temperatures, intermediate
products, and recipe dependencies from one source.

## Minimal recipe

```markdown
---
title: Sauce Béchamel
yield: 1 cup
scale: yield
tags: [sauce, french]
---

A basic white sauce for gratins and other sauces.

== step make roux ==
Melt @butter{2%tbsp} in a #saucepan{} and whisk in @flour{2%tbsp}.
Cook for ~roux{1%minute}.

== step finish ==
Whisk in @whole milk{1%cup}(warm) and cook at $temp{180%F} until smooth.
```

## File structure

Frontmatter is enclosed by `---`. `title` is required. Common metadata includes:

```yaml
---
title: Croque Monsieur
yield: 4 servings
scale: yield
headnote: A French ham and cheese sandwich with Mornay sauce.
source: America's Test Kitchen
source_url: https://example.com/recipe
family: sandwich
tags: [sandwich, ham, french]
units: imperial
variations: [vegetarian-croque]
---
```

Text between frontmatter and the first step is introductory prose. Steps begin
with either an untitled or titled marker:

```markdown
== step ==
Do something.

== step make sauce ==
Do something with a descriptive component name.
```

The filename becomes the recipe slug: `croque_monsieur.md` becomes
`croque-monsieur`.

## Recipe variants and source includes

Use top-level variant sections when multiple formulas are alternate versions of
the same dish rather than independent cookbook entries:

```markdown
---
title: Japanese Fluffy Pancakes
tags: [breakfast, pancakes, japanese]
---

== variant buttermilk [default=true] ==
@include{_variants/fluffy_pancakes/buttermilk.md}

== variant jiggly ==
@include{_variants/fluffy_pancakes/jiggly.md}
```

Steps following a variant marker belong to that variant until the next variant
marker. One variant may use `[default=true]`; otherwise the first variant is the
default. Julia produces one collection card and a style switcher on the recipe
page. Each variant keeps its own yield, source, steps, scaling state, shopping
ingredients, and Cook Mode history. Feasts and recipe dependencies use the
default variant.

`@include{path}` is a generic build-time source include and must appear on its
own line. Paths resolve relative to the file containing the include. The
included body is parsed at that location, so it inherits the active recipe or
variant scope. Optional included frontmatter fills metadata that is not already
defined in that scope:

```markdown
---
title: Jiggly Soufflé
yield: 1 serving
source: Example source
source_url: https://example.com/pancakes
---

== step make meringue ==
Whip @egg whites{2} with @sugar{26%g}.
```

Includes may be nested; missing files and circular include chains are build
errors. Put non-public fragments in a nested directory such as
`recipes/_variants/`. Julia discovers public recipes from top-level
`recipes/*.md` files, so nested fragments do not create collection cards.

`@include` and `@recipe` have deliberately different meanings:

- `@include` organizes source files and becomes part of the current recipe.
- `@recipe` is a culinary dependency with its own recipe identity, shopping
  expansion, and collapsible preparation steps.

### Compound yields

Portioned recipes can describe count and unit weight in the single `yield`
field:

```yaml
yield: 4 dough balls [each=250 g]
yield: 4 dough balls [each=~250 g]
yield: 4 dough balls [each=250 g +/- 2 g]
yield: 4 dough balls [each=250 g ± 2 g]
```

The plain value is a target, `~` marks an approximate target, and `+/-` or `±`
declares a per-piece tolerance. Scaling uses `count × each` as the target batch
mass. Mark count-bound outputs and later references with `[scale=count]` so their
displayed quantity follows the requested piece count rather than batch mass:

```markdown
Divide the dough to produce =>dough balls{4%balls}[scale=count].
Refrigerate ^dough balls{4%balls}[scale=count] overnight.
```

### Baker's formulas with portioned yields

A compound yield, a base flour, and one selectable baker's-percentage ingredient
create a formula-aware scaling panel:

```markdown
---
yield: 4 dough balls [each=~250 g]
---

Measure @water{65%bakers}[ratio_of=tipo 00 flour, options=65|70|75].
Mix with @tipo 00 flour{600%g}[base=true, scale=true] and @salt{17%g}.
```

The panel coordinates total flour, hydration, portion count, and portion weight.
Changing flour or hydration keeps the portion weight and reports the number of
full portions plus any extra dough. Changing count or portion weight keeps those
two yield targets and calculates the required flour. Other same-unit ingredients
and baker's percentages are included in the total dough calculation.

## Common annotation grammar

Most inline annotations use this shape:

```text
<marker><name>{<quantity>%<unit>}(<optional note>)[<optional attributes>]
```

The quantity block is always required, even when empty. Notes and attributes are
optional:

```markdown
@salt{}
@whole milk{2%cups}(heated)
@kosher salt{3/4%cup}[brand=diamond-crystal]
@butter{2%tbsp}(melted)[scale=false]
```

Names may contain spaces, numbers, punctuation, hyphens, and Unicode. A name
ends at its first `{`. Each annotation's `{}`, optional `()`, and optional `[]`
must currently open and close on the same physical line.

### Unit conversion

The International/Imperial control converts temperatures and structured
culinary quantities. Supported ingredient conversions include `oz`/`lb` ↔
`g`/`kg` and `tsp`/`tbsp`/`cups`/`fl oz`/`qt` ↔ `ml`/`L`. Unknown units and
free-form compound quantities remain as authored. Teaspoons, tablespoons, and
cups remain the primary display when using International units, with the metric
volume shown as a convenience: `2 tbsp (30 ml)`, `1 tsp (5 ml)`, or
`1 cup (240 ml)`.

## Guides

Files in `guides/` are searchable reference pages rather than recipes. They do
not have yields, shopping ingredients, scaling, or cooking-progress state.

```markdown
---
title: Turkey Temperature and Timing
headnote: Compare roasting and sous vide targets.
product: turkey
format: time-temperature
tags: [turkey, temperature, sous-vide]
source: USDA Turkey Roasting Charts
source_url: https://example.com/turkey
---

## Whole turkey

| Weight | Oven | Time |
|---|---|---|
| $weight{8-12%lb} | $temp{325%F} | $time{2.75-3%hours} |
```

Guide tables and prose support smart parameters:

```markdown
$temp{145%F}
$weight{8-12%lb}
$time{3-4%hours}
$thickness{2%in}
```

Temperature, weight, and thickness values—including ranges—respond to the
guide's International/Imperial control. Time remains unit-aware but is not
converted. Link to a guide from a recipe or another guide with:

```markdown
See [Turkey temperatures](guide:turkey-temperature-and-timing).
```

## Markers

### External ingredients: `@`

```markdown
Whisk @large eggs{5} with @sugar{1/3%cup} and @salt{}(a pinch).
```

External ingredients appear beside their step, scale with the recipe, and enter
recipe and shopping lists. `[scale=false]` keeps an exceptional quantity fixed.
`[scale=true, step=1]` makes an ingredient a practical scaling anchor.

### Equipment: `#`

```markdown
Transfer to a #small saucepan{} and whisk with a #balloon whisk{}.
```

Equipment is displayed with the step but never enters ingredient or shopping
lists.

### Timers: `~`

```markdown
Cook for ~{10%minutes}.
Brine for ~brine{1-4%hours}.
```

Timers are interactive and do not scale. A timer may be anonymous or named.

### Process parameters: `$`

```markdown
Heat the oven to $temp{375%F}.
```

Temperatures do not scale and can be converted between Fahrenheit and Celsius.

### Step outputs: `=>`

```markdown
Separate @large eggs{5} into =>egg yolks{5} and =>egg whites{5}.
```

A step output is produced during cooking. It is shown as the result of its step
but is not an item to buy and never enters a shopping list.

### Intermediate step inputs: `^`

```markdown
Whisk ^egg yolks{5} with @heavy cream{2%cups} to produce =>custard{}.

Divide ^custard{} among the #ramekins{}.
```

An intermediate input must match an output from an earlier step in the same
recipe. Julia rejects missing inputs and duplicate output names. Intermediate
inputs display the step that produced them and never enter shopping lists.

Leave an intermediate product's quantity block empty when a useful amount cannot
or need not be stated:

```markdown
Chop ^cooked shrimp tails{} to produce =>chopped shrimp tails{}.
```

Unlike an empty external ingredient, which displays as “as needed,” an empty
step-product quantity displays no measure.

Use step products for meaningful handoffs, not every change of state. Custard,
dough, separated yolks, and prepared sauce are useful products; “warm pan” or
“stirred mixture” usually are not.

## Alternative preparation steps

Consecutive steps with the same `choice` attribute occupy one displayed step.
Each branch needs a unique `option`; one branch may be marked as the default:

```markdown
== step prepare yeast [choice=yeast, option=instant, default=true] ==
Mix @instant yeast{0.4%g} with @water{390%g} to produce
=>yeast water{390%g}.

== step prepare yeast [choice=yeast, option=active-dry] ==
Bloom @active dry yeast{0.5%g} in @warm water{30%g} for
~bloom{5-10%minutes}. Add @cool water{360%g} to produce
=>yeast water{390%g}.
```

All options must produce the same named outputs so later common steps have one
stable contract. Julia displays an option selector and includes only the active
branch's ingredients, instructions, timers, and parameters in Cook Mode and
shopping views. Feast documents use the default branch.

### Recipe dependencies: `@recipe`

```markdown
Prepare @recipe{mornay-sauce}{1 1/4%cups} and keep it warm.
```

Recipe dependencies are the exception to the common one-block form. They have a
recipe slug block followed by the requested quantity block:

```text
@recipe{<recipe-slug>}{<quantity>%<unit>}
```

Dependencies scale recursively. Their external ingredients enter shopping
lists, while their instructions can be expanded in the parent recipe. Missing
dependencies and circular dependency chains are build errors.

A step containing one recipe dependency and no external ingredients or inputs
becomes a collapsible dependency step. Its recipe steps inherit hierarchical
numbers from the parent:

```text
Step 3       Prepare 1 1/4 cups Mornay Sauce
  Step 3.1     Prepare 1 cup Béchamel Sauce
    Step 3.1.1   Make roux
    Step 3.1.2   Add milk
  Step 3.2     Finish Mornay sauce
```

Keep a dependency in its own step when this presentation is desired. Checking a
dependency step marks its child steps complete; completing all children marks
the parent complete. Ingredients and intermediate inputs remain independently
checkable inside every expanded child step.

## Complete step-product example

```markdown
---
title: Simple Custard
yield: 6 servings
scale: yield
---

== step separate ==
Separate @large eggs{5}[scale=true, step=1] into =>egg yolks{5} and
=>egg whites{5}.

== step mix ==
Whisk ^egg yolks{5} with @sugar{1/3%cup}, @heavy cream{2%cups}, and
@vanilla extract{1%tsp} to produce =>custard{}.

== step portion ==
Divide ^custard{} among 6 #ramekins{}.
```

The shopping list contains large eggs, sugar, heavy cream, and vanilla. Egg
yolks, egg whites, and custard remain step products and are not aggregated as
purchases.

## Links and emphasis

```markdown
See [Mornay sauce](recipe:mornay-sauce).
Browse [custard recipes](search:custard).
Read an [external source](https://example.com).
This word is *emphasized*.
```

Ordered and unordered lists are also supported in recipe introductions and
steps. Wrapped continuation lines remain part of the preceding item:

```markdown
1. First reason.
2. Second reason wraps
   onto another line.

- One note.
- Another note.
```

Julia supports this focused Markdown subset rather than arbitrary CommonMark.

## YouTube videos

Embed a responsive YouTube video in introductory prose or a recipe step with its
11-character video ID:

```markdown
!youtube{LysF3BGtXt4}
```

Video annotations accept optional attributes:

```markdown
!youtube{LysF3BGtXt4}[start=1m30s, end=3m, title=Prime rib technique]
!youtube{LysF3BGtXt4}[autoplay=false, mute=true, loop=true, controls=false, captions=true]
```

`start` and `end` accept seconds or durations such as `1m30s`. Boolean options
accept `true` or `false`. Embeds use YouTube's privacy-enhanced domain and load
lazily. Raw HTML, including manually written iframes, remains escaped.
