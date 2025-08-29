from questionsafe import Q, Text, Quiz

q = Q.Essay(
    name="Essay/Intro",
    questiontext=Text("Introduce yourself."),  # explicit Text, default format html
)
# Configure response using the new set_-prefixed API
q.set_response_format("editor").set_input_required(True).set_input_lines(
    8
).set_input_words(100, 500).set_attachments_count(0).set_attachments_required(
    False
).set_response_template(Text("Please include your background and interests."))

q.set_graderinfo("Look for structure and clarity.")

quiz = Quiz()
quiz.add(q)
print(quiz.to_xml().decode("utf-8"))
