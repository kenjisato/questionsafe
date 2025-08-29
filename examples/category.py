from questionsafe import Q, Quiz

# Build a quiz under a parent category, grouping variants into subcategories
quiz = Quiz(category="SampleCourse/Week1", subcategory_id="123")
quiz.add_category("Subcategory")

quiz.add(Q.ShortAnswer("SA1", "What is the capital of Japan?").add_answer("Tokyo"))
quiz.add(Q.Numerical("Num1", "1+1=?").add_answer(2))

quiz.to_xml("build/category.xml")
