
import anthropic
import env

def main():
    print("Welcome to Sentinel Searcher!")


    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": "What's the weather in NYC?"
            }
        ],
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 5
        }]
    )
    print(response)



if __name__ == "__main__":
    main()