
import anthropic
import os
from dotenv import load_dotenv

def main():
    # load .env file into environment variables
    load_dotenv()

    # set the api key from environment variable
    api_key = os.getenv("ANTHROPIC_API_KEY")

    # initialize the client with the api key
    client = anthropic.Anthropic(api_key=api_key)

    # create a message with web search tool enabled
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": "Find the latest 3 news about Matheus Kunzler Maldaner"
            }
        ],
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            #"max_uses": 5
        }]
    )
    print(message.content)



if __name__ == "__main__":
    main()