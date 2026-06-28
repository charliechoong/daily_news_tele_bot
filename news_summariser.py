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
            "Perform a web search on top 5 significant events that happened around the world in the past 12 hours.\n\n"
            "Provide an engaging, bulleted breakdown for each chosen event."
            "Also, provide any significant updates on COIN, META, NOW, UNH, DUOL, SPCX, LULU and BABA"
            "Use clear headings, clean spacing, and relevant emojis to make it highly readable on mobile. "
            "Avoid overly lengthy prose.\n\n"
        )
        
        response = client.models.generate_content(
            model='gemini-3.5-flash',
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
    MAX_CHUNK_SIZE = 4000  # Leave a conservative safety margin under 4096
    
    # 1. Chunking Buffer Logic Architecture
    if len(text) <= MAX_CHUNK_SIZE:
        chunks = [text]
    else:
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""
        for paragraph in paragraphs:
            # Edge case mitigation: if a single paragraph itself is somehow over 4000 chars
            if len(paragraph) > MAX_CHUNK_SIZE:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                # Force slice the anomaly raw
                for i in range(0, len(paragraph), MAX_CHUNK_SIZE):
                    chunks.append(paragraph[i:i+MAX_CHUNK_SIZE].strip())
            # If combining this paragraph breaks the max limit, flush the active chunk
            elif len(current_chunk) + len(paragraph) + 2 > MAX_CHUNK_SIZE:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            # Otherwise, compound the paragraph into the operational buffer
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        if current_chunk:
            chunks.append(current_chunk.strip())
    
    # 2. Sequential Dispatch Pipeline execution
    print(f"Message payload mapped and separated into {len(chunks)} sequential packet(s).")
    for index, chunk in enumerate(chunks):
        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, json=payload)
        
        # Structural fallback: if strict Markdown constraints break inside the packet
        if response.status_code == 400:
            print(f"Formatting validation error on package {index+1}. Retrying via plain text transfer...")
            payload.pop("parse_mode", None)
            response = requests.post(url, json=payload)
            
        try:
            response.raise_for_status()
            print(f"Packet {index+1}/{len(chunks)} transferred cleanly to Telegram.")
        except Exception as e:
            print(f"Fatal transfer exception on network package {index+1}: {e}")
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