---
title: Choice Fixture
yield: 1 batch
---
== step prepare yeast [choice=yeast, option=instant, default=true] ==
Prepare @recipe{bechamel}{1%cup}, then mix @instant yeast{1%g} with
@water{65%bakers}[ratio_of=flour, options=65|70|75] to produce =>prepared yeast{}.
== step prepare yeast [choice=yeast, option=fresh] ==
Prepare @recipe{bechamel}{1%cup}, then mix @fresh yeast{3%g} with
@water{65%bakers}[ratio_of=flour, options=65|70|75] to produce =>prepared yeast{}.
== step mix ==
Mix ^prepared yeast{} with @flour{100%g}[base=true].
