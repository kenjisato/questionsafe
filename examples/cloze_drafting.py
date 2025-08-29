from questionsafe import Q

scq = (
    Q.SingleChoice("a")
    .ask("What is the capital of Tokyo.")
    .set_choice_correct("<div style='color:red;size:20px;'>Tokyo</div>")
    .set_choices_wrong("Osaka", "Kyoto")
)

mcq = (
    Q.MultiChoice("b")
    .ask("Choose cities in Japan")
    .set_choices_correct("Osaka", "Kyoto")
    .set_choices_wrong("New York", "Taipei")
)

sa = (
    Q.ShortAnswer("c")
    .ask("What is the capital of Canada?")
    .add_answer("Ottawa", fraction=100)
)

num = (
    Q.Numerical("d")
    .ask("1 + 3")
    .add_answer(4)
)

print(scq.cloze(orientation='h'))
print(num.cloze())
