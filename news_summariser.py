import os
import sys
import feedparser
import requests
from google import genai

# Configuration: Swap out the RSS URL to pull from your favorite media outlets
RSS_URL = "http://feeds.bbci.co.uk/news/world/rss.xml"

def fetch_top_news(url, limit=12):
    """Fetches the latest headlines and short summaries from an RSS feed."""
    feed = feedparser.parse(url)
    articles = []
    
    for entry in feed.entries[:limit]:
        title = entry.get("title", "No Title")
        link = entry.get("link", "")
        summary = entry.get("summary", entry.get("description", ""))
        articles.append(f"Title: {title}\nSummary: {summary}\nLink: {link}\n---")
        
    return "\n\n".join(articles)

def summarize_news(raw_news_text):
    """Generates a cohesive, structured summary using the Google GenAI SDK."""
    try:
        # The SDK client automatically scans for the GEMINI_API_KEY environment variable
        client = genai.Client()
        
        prompt = (
            "You are an expert news curator. Analyze the following raw news items from today's feed. "
            "Identify and extract the top 5 most globally impactful events.\n\n"
            "Provide an engaging, bulleted breakdown for each chosen event. "
            "Use clear headings, clean spacing, and relevant emojis to make it highly readable on mobile. "
            "Crucially, make sure to cleanly insert the original source link directly below each story's breakdown "
            "so I can tap it for deeper reading. Avoid overly lengthy prose.\n\n"
            f"RAW NEWS FEED:\n{raw_news_text}"
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
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
        
    print("1. Extracting data from RSS target...")
    raw_news = fetch_top_news(RSS_URL)
    
    if not raw_news:
        print("Aborting: Empty news payload captured.")
        return
        
    print("2. Constructing contextual intelligence digest via Gemini...")
    summary = summarize_news(raw_news)
    
    print("3. Executing chat message transfer pipeline...")
    send_telegram_message(telegram_token, telegram_chat_id, summary)

if __name__ == "__main__":
    main()