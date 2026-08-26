# Evolution5 Cambrian League

Evolution5 replaces the single-family Evolution4 search with eight semi-independent islands, a constrained behavior-graph genotype, coordinated strategy bundles, module mutations, 20–40% graph rewrites, random immigrants, a MAP-Elites niche archive and a multi-member champion league.

A generation uses isolated seed streams: breeding/training, rotating evaluation, fresh holdout, promotion/league, and never-used final validation. Stage 1 keeps three organisms per island; Stage 2 keeps an elite per island; fresh Stage 3 can change the league but is not used to choose breeding survivors.

Plateau response escalates mutation temperature, architecture mutation rate, island reseeding and finally a Cambrian extinction that preserves league/archive/elites while replacing most non-elites.

Durable control branch: `evolution5/cambrian-league`. STOP marker: `evolution5/STOP`.
