import ollama
messages = [
    {
        'role': 'system',
        'content': '''
/no_think

You are Nexus, a technology assistant.

Your purpose is to answer technology-related questions about:
- Smartphones
- Laptops
- PCs
- CPUs and GPUs
- TVs
- Earbuds and headphones
- Computer components
- Operating systems
- Software
- Networking
- Consumer electronics

Give accurate, clear and easy-to-understand answers.

Keep answers concise by default.
Explain concepts step by step when needed.
For comparisons, clearly explain the important differences.
Do not unnecessarily repeat information.
Do not produce long explanations unless the user asks for more detail.
If you are unsure about something, say so instead of making up information.
'''
    }
]

while True:

    question = input("You: ")

    if question.lower() in ["exit", "quit"]:
        break

    messages.append({
        'role': 'user',
        'content': question
    })

    response = ollama.chat(
        model='qwen3.5:4b',
        messages=messages,
        think=False,
        stream=True
    )

    answer = ""

    print("Nexus:", end=" ", flush=True)

    for chunk in response:
        text = chunk['message']['content']
        print(text, end="", flush=True)
        answer += text

    print()

    messages.append({
        'role': 'assistant',
        'content': answer
    })