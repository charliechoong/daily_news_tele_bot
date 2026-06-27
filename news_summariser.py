import os
import sys
import requests
from google import genai
from google.genai import types

def summarize_news():
    """Leverages native Google Search grounding to dynamically discover and summarize news."""
    try:
        # The SDK client automatically scans for the GEMINI_API_KEY environment variable
        client = genai.Client()

        # Enable the native Google Search tool configuration
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
        
        prompt = (
            "Perform a web search on top 5 significant events that happened around the world today.\n\n"
            "Provide an engaging, bulleted breakdown for each chosen event."
            "Use clear headings, clean spacing, and relevant emojis to make it highly readable on mobile. "
            "Avoid overly lengthy prose.\n\n"
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=config
        )
        return response.text
    except Exception as e:
        print(f"Error communicating with Gemini API: {e}")
        sys.exit(1)

def send_telegram_message(token, chat_id, text):
    """Dispatches the final summary text to the target Telegram chat with fallback handling."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    if len(text) > 4000:
        text = text[:3900] + "\n\n...[Truncated due to text limit]"
        
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    # Attempt delivery with Markdown formatting
    response = requests.post(url, json=payload)
    
    # If Telegram rejects it due to strict Markdown parsing errors,
    # strip the parse_mode and fall back to plain text delivery
    if response.status_code == 400:
        print("Telegram rejected Markdown syntax. Stripping formatting and retrying plain text transfer...")
        payload.pop("parse_mode", None)
        response = requests.post(url, json=payload)
        
    try:
        response.raise_for_status()
        print("Success! Summary dispatched to Telegram.")
    except Exception as e:
        print(f"Error sending message via Telegram Bot API: {e}")
        sys.exit(1)

def main():
    # Defensive checks for production environments
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not os.environ.get("GEMINI_API_KEY") or not telegram_token or not telegram_chat_id:
        print("Runtime Error: Missing required system environment variables.")
        sys.exit(1)
        
    print("1. Constructing contextual intelligence digest via Gemini...")
    summary = summarize_news()
    
    print("2. Executing chat message transfer pipeline...")
    send_telegram_message(telegram_token, telegram_chat_id, summary)

if __name__ == "__main__":
    main()