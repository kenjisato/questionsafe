---
type: metachoice
name: Econ/ShiftOrMove
choices:
  INCOME: A rise in consumer income
  TASTES: A shift in consumer tastes toward coffee
  SUBST: An increase in the price of tea
  TECH: An improvement in roasting technology
  INPUT: A fall in the price of raw coffee beans
  WEATHER: A frost that destroys part of the harvest
  PRICE: A change in the market price of coffee
  EXPECT:
    text: News that coffee prices will rise **sharply** next month
    format: markdown
stems:
  DEMAND_SHIFT:
    text: Which of the following shift the *demand* curve for coffee?
    format: markdown
  SUPPLY_SHIFT:
    text: Which of the following shift the *supply* curve for coffee?
    format: markdown
  MOVE_ALONG:
    text: >-
      Which of the following cause a movement *along* the demand curve
      for coffee, rather than a shift of the curve?
    format: markdown
constraints:
  # Every variant carries the movement-along-the-curve trap.
  attractor:
    members: [PRICE]
    min: 1
  # Supply-shift variants always include plausible cross-curve distractors.
  demand_side:
    members: [INCOME, TASTES, SUBST]
    min: 1
    max: 2
    apply_to: [SUPPLY_SHIFT]
  # Demand-shift variants likewise mix in supply-side distractors.
  supply_side:
    members: [TECH, INPUT, WEATHER]
    min: 1
    max: 2
    apply_to: [DEMAND_SHIFT]
---

# One pool, three stems

Three questions share one pool of eight events. A cell is `x` when the
event answers the stem, empty when it is a safe wrong answer, and `-`
when it must never be sampled into that stem.

The `-` cells are the point of this format:

- `EXPECT` shifts demand, so it is correct in `DEMAND_SHIFT`. But it also
  shifts supply (sellers withhold stock), so in `SUPPLY_SHIFT` it can be
  neither a correct answer nor a wrong one. It is simply banned there.
- `TECH`, `INPUT`, and `WEATHER` shift supply, which changes the price and
  thereby moves the market along the demand curve. Offering them as wrong
  answers in `MOVE_ALONG` would be defensibly correct, so they are banned.

`PRICE` never shifts either curve. The `attractor` constraint forces it
into every variant: as a trap in the two shift stems, and as the correct
answer in `MOVE_ALONG`.

```csv
choice,DEMAND_SHIFT,SUPPLY_SHIFT,MOVE_ALONG
INCOME,x,,
TASTES,x,,
SUBST,x,,
TECH,,x,-
INPUT,,x,-
WEATHER,,x,-
PRICE,,,x
EXPECT,x,-,
```
