#!/usr/bin/env python3
"""
Example: Using MetaChoice to generate MultiChoice questions from a shared pool
with global and per-stem constraints.

Run:
  uv run sandbox/metachoice_example.py
"""
from __future__ import annotations
from questionsafe.meta import MetaChoice, Stem, Constraint


def main() -> None:
    mc = (
        MetaChoice()
        # Use keyed choices so long texts can have short keys
        .set_choices({
            "T1": "President T1 (long description...)",
            "T2": "President T2 (long description...)",
            "P1": "Policy P1 (long description...)",
            "P2": "Policy P2 (long description...)",
            "A1": "Attractor A1 (long description...)",
        })
        .add_constraint(Constraint("term", choices={"T1", "T2"}, min=1, max=1))   # exactly one term
        .add_constraint(Constraint("policy", choices={"P1", "P2"}, min=0, max=1)) # at most one policy
    )

    # Stem 1: correct items are the terms; pick 3 options overall
    mc.add_stem(
        Stem("TERM_Q", "Who served two terms?").set_choices_correct({"T1", "T2"})
    )

    # Stem 2: also require at least one policy locally, with deterministic sampling
    stem2 = (
        Stem("TERM_POLICY_Q", "Pick a term and a policy")
        .set_choices_correct({"T1", "T2"})
        .add_constraint(Constraint("policy", choices={"P1", "P2"}, min=1, max=1))
    )
    mc.add_stem(stem2)

# Use a prototype to set defaults like labels/shuffle
from questionsafe.questions.multichoice import MultiChoice as _MC
proto = _MC(name="TEMPLATE").set_choice_layout(labels="abc", shuffle=False)

group = mc.generate_multichoice(n=3, limit=2, seed=42, prototype=proto)

    # Use with Quiz.add_group
    from questionsafe.quiz import Quiz
    qz = Quiz(category="Demo").add_group(group)
    print(qz.to_xml().decode("utf-8"))

if __name__ == "__main__":
    main()

