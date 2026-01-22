import ollama

model = 'mistral:7b-instruct-v0.2-q4_0'
messages = [{'role': 'system', 'content': 'You are a helpful AI assistant.'}]

print("채팅 시작 (quit 입력으로 종료)")

while True:
    user_input = input("You: ")
    if user_input.lower() == 'quit':
        break
    
    messages.append({'role': 'user', 'content': user_input})
    response = ollama.chat(model=model, messages=messages)
    answer = response['message']['content']
    print("Bot:", answer)
    messages.append({'role': 'assistant', 'content': answer})
