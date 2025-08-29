from questionsafe import Q, Quiz

q = Q.TrueFalse(
    name="Logic/DeMorgan",
    questiontext="True or False: Not(A and B) == (Not A) or (Not B)",
).set_correct_if_true()

quiz = Quiz([q])
print(quiz.to_xml().decode("utf-8"))
