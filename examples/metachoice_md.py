#!/usr/bin/env python3
"""
Example: Read a MetaChoice template from Markdown and generate MultiChoice
variants. The file holds the template (pool, stems, matrix, constraints);
generation parameters stay here with the exam build.

Run:
  uv run examples/metachoice_md.py
"""
from __future__ import annotations

from pathlib import Path

from questionsafe import Q, Quiz, Reader

md = Path(__file__).parent / "markdown" / "metachoice.md"
mc = Reader(md).read_metachoice()

proto = Q.MultiChoice().set_choice_layout(labels="none", shuffle=False)
group = mc.generate_multichoice(n=4, limit=2, seed=42, prototype=proto)
group.assign_idnumbers(prefix="econ-")

qz = Quiz(category="Econ Demo").add_group(group)
print(qz.to_xml().decode("utf-8"))
