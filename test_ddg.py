from ddgs import DDGS

try:
    response = DDGS().text("hello world", max_results=3)
    print("SUCCESS:")
    print(response)
except Exception as e:
    print("FAILED:")
    print(e)
