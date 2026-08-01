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

Use step products for meaningful handoffs, not every change of state. Custard,
dough, separated yolks, and prepared sauce are useful products; “warm pan” or
“stirred mixture” usually are not.

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

Julia supports this focused Markdown subset rather than arbitrary CommonMark.
