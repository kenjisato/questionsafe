from questionsafe import Q, write_xml

# Using the new, concise API with sensible defaults
qnum_unit = (
    Q.Numerical(name="Weight", questiontext="100g + 1kg = ?")
    .add_answer_unit(1100, "g")  # establishes base unit 'g' and base answer 1100
    .add_answer_unit(1.1, "kg")  # registers kg with inferred multiplier 1000
)

# print(render_xml([qnum_unit]).decode("utf-8"))
write_xml([qnum_unit], path="build/numerical_with_unit.xml")
