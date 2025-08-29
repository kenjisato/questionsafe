from questionsafe import Q, Text, Feedback, render_xml

q = Q.ShortAnswer(
    name="SA/Color-Spelling",
    questiontext=Text(
        "<p>Spell the British English word for 'color'</p>", format="html"
    ),
)

q.set_usecase(False)  # case-insensitive
q.add_answer("colour", fraction=100)
q.add_answer("color", fraction=50, feedback=Feedback("<p>American spelling</p>"))

print(render_xml(q).decode("utf-8"))
