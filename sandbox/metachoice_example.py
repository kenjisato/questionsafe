#!/usr/bin/env python3
"""
Example: Using MetaChoice to generate MultiChoice questions from a shared pool
with global and per-stem constraints.

Run:
  uv run sandbox/metachoice_example.py
"""
from __future__ import annotations
from questionsafe.meta import MetaChoice, Constraint
from questionsafe import Q, Quiz, Text

mc = MetaChoice()

mc.set_choices({
    "T1": Text("President T1 (*long* description...)", format="markdown"),
    "T2": "President T2 (long description...)",
    "P1": "Policy P1 (long description...)",
    "P2": "Policy P2 (long description...)",
    "A1": "Attractor A1 (long description...)",
})

# The following API may look cleaner. 
mc.set_constraints({
    "term": Constraint("T1", "T2", min=1, max=1)
})

# Maybe id can be hidden (and hence optional) from user's perspective
mc.add_constraint("P1", "P2", max=1)

# Here's a user-facing API for stems that I am thinking is better
mc.add_stem(
    "TERM_Q",
    Text("Who served two terms?"), 
    correct = {"T1", "T2"},
    constraints = {}
)

mc.add_stem(
    "TERM_POLICY_Q", 
    Text("Pick a term and a policy"),
    correct=("T1", "T2"),
    constraints={
        "policy": Constraint("P1", "P2", min=1, max=1)
    }
)

# Use a prototype to set defaults like labels/shuffle
# Maybe
proto = Q.MultiChoice().set_choice_layout(labels="none", shuffle=False)

group = mc.generate_multichoice(n=3, limit=2, seed=42, prototype=proto)

# Use with Quiz.add_group
qz = Quiz(category="Demo").add_group(group)
print(qz.to_xml().decode("utf-8"))
