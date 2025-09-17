def sub_generator():
    yield "Hello"
    yield "World"
    return "Done!"

def delegating_generator():
    result = yield from sub_generator()
    print(f"Sub-generator returned: {result}")
    yield "Finished"

gen = delegating_generator()
print(next(gen))  # Output: Hello
print(next(gen))  # Output: World
print(next(gen))  # Output: Sub-generator returned: Done!
                  # Output: Finished
