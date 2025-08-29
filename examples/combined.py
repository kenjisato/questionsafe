from questionsafe import Q, Quiz, Hint, Text, Unit

# Build a quiz under a parent category, grouping variants into subcategories
quiz = Quiz(category="Exam/Week1", subcategory_id="123")

# Multichoice variants (fluent, ergonomic chaining)
mcq1 = (
    Q.MultiChoice(
        name="Capital/Thailand", questiontext="What is the capital of Thailand?"
    )
    .set_choices_correct("Bangkok", feedback="Right!")
    .set_choices_wrong("Chiang Mai", "Phuket", "Pattaya")
    .set_hints(
        Hint("Consider the most populous city.", shownumcorrect=True),
        Hint("Eliminate coastal resort options.", clearwrong=True),
        penalty=0.25,
    )
)
mcq2 = (
    Q.MultiChoice(
        name="Capital/Thailand",
        questiontext=Text(
            "Pick EU capitals:\n\n- Paris\n- Berlin\n- Madrid", format="markdown"
        ),
    )
    .set_choices_correct("Bangkok", feedback="Yes!")
    .set_choices_wrong("Ayutthaya", "Nonthaburi", "Pattaya")
)
quiz.add_group([mcq1, mcq2], idnumber_prefix="mcq-", idnumber_offset=10)


# Single Choice
sc = (
    Q.SingleChoice(
        name="Capital/Japan", questiontext=Text("<p>What is the capital of Japan?</p>")
    )
    .set_choice_correct("Tokyo")
    .set_choices_wrong("Osaka", "Kyoto", "Nagoya")
    .set_choices_correct()
)


# True/False variants
_tf1 = (
    Q.TrueFalse(
        name="Logic/DeMorgan", questiontext="Not(A and B) == (Not A) or (Not B)"
    )
    .set_choice_correct("true")
    .set_choice_wrong("false")
)
_tf2 = (
    Q.TrueFalse(
        name="Logic/DeMorgan", questiontext="Not(A and B) == (Not A) or (Not B)"
    )
    .set_choice_correct("true")
    .set_choice_wrong("false")
)
quiz.add_group([_tf1, _tf2], idnumber_prefix="tf-", idnumber_offset=0)

# Short answer variants
sa1 = (
    Q.ShortAnswer(
        name="SA/Color-Spelling",
        questiontext="Spell the British English word for 'color'",
    )
    .add_answer("colour", fraction=100)
    .set_penalty(0.5)
    .add_hint("It's not 'color'. Think UK spelling.")
)
sa2 = Q.ShortAnswer(
    name="SA/Color-Spelling", questiontext="Spell the British English word for 'color'"
).add_answer("colour", fraction=100)
quiz.add_group([sa1, sa2], idnumber_prefix="sa-", idnumber_offset=0)

# Numerical variants
num1 = (
    Q.Numerical(
        name="Num/Pi-Approx", questiontext="Approximate value of π (2 decimal places)"
    )
    .add_answer(3.14, tolerance=0.005)
    .set_penalty(0.2)
    .add_hint("Use 22/7 as a rough fraction.")
    .add_hint("Round to two decimal places.")
)
num2 = (
    Q.Numerical(
        name="Num/Pi-Approx-Units",
        questiontext="Give π with two decimals and unit m/s. Alternative unit km/h allowed.",
    )
    .add_answer(3.14, tolerance=0.005)
    .set_units(
        Unit(unit_name="m/s", multiplier=1.0, fraction=100),
        Unit(unit_name="km/h", multiplier=0.2777778, fraction=0),
        showunits=1,
        unitgradingtype=1,
        unitpenalty=0.1,
        unitsleft=False,
    )
)
# Attach UnitSpec: primary unit m/s, alternative km/h with no credit, units required with fractional penalty
quiz.add_group([num1, num2], idnumber_prefix="num-", idnumber_offset=100)

# Essay variants
es1 = Q.Essay(name="Essay/Intro", questiontext=Text("<p>Introduce yourself.</p>"))
es2 = Q.Essay(name="Essay/Intro", questiontext=Text("<p>Introduce yourself.</p>"))
quiz.add_group([es1, es2], idnumber_prefix="essay-", idnumber_offset=1)

# Description variants (treated like any normal question for grouping)
d1 = Q.Description(
    name="Desc/Week1", questiontext=Text("<p>This section covers basic topics.</p>")
)
d2 = Q.Description(
    name="Desc/Week1", questiontext=Text("<p>This section covers basic topics.</p>")
)
quiz.add_group([d1, d2], idnumber_prefix="desc-", idnumber_offset=0)

# Write outputs (preferred typical usage)
quiz.to_xml("build/combined.xml")
quiz.title = "Combined Preview"
quiz.to_html("build/combined.html")

quiz.info()
