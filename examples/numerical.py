from questionsafe import Q, Text, render_xml

qnum = Q.Numerical(
    name="Num/Pi-Approx", questiontext=Text("Approximate value of π (2 decimal places)")
)
qnum.add_answer(3.14, tolerance=0.005)

print(render_xml([qnum]).decode("utf-8"))
