---
title: Choice Fixture
yield: 1 batch
---
== step prepare yeast [choice=yeast, option=instant, default=true] ==
Mix @instant yeast{1%g} to produce =>prepared yeast{}.
== step prepare yeast [choice=yeast, option=fresh] ==
Mix @fresh yeast{3%g} to produce =>prepared yeast{}.
== step mix ==
Mix ^prepared yeast{} with @flour{100%g}.
