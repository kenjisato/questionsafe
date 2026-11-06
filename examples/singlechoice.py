from questionsafe import Q, Quiz

mcq = (
    Q.SingleChoice(
        name="Capital/Thailand", questiontext="What is the capital of Thailand?"
    )
    .set_choice_correct("Bangkok")
    .set_choices_wrong("Chiang Mai", "Phuket", "Pattaya")
    .set_numbering("abc")
)

quiz = Quiz([mcq])
print(quiz.to_xml().decode("utf-8"))
