from questionsafe import Q, Quiz

# Multi-choice example with combined feedback
q1 = (
    Q.MultiChoice(
        name="Capitals/EU",
    )
    .ask("Pick EU capitals")
    .set_choices_correct("Paris", "Berlin")  # -> 50 each
    .set_choices_wrong("Zurich", "Madrid", fraction=0.0)
    .set_shuffle(True)
)
# Set combined feedback fields explicitly (optional)
q1.set_feedback_combined(
    correct="Nice.", partiallycorrect="Close.", incorrect="Review capitals."
)

quiz = Quiz([q1])
print(quiz.to_xml().decode("utf-8"))
