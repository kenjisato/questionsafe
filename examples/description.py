from questionsafe import Q, Quiz

q = Q.Description(name="Desc/Week1", questiontext="This section covers basic topics.")

quiz = Quiz()
quiz.add(q)
print(quiz.to_xml().decode("utf-8"))
