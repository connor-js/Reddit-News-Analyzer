import praw
from openai import OpenAI
import os
import time
import sqlite3

# Fetch credentials from environment variables
REDDIT_CLIENT_ID = "YOUR-ID"
REDDIT_CLIENT_SECRET = "YOUR-ID"
REDDIT_USER_AGENT = "YOUR-ID"
OPENAI_API_KEY = "YOUR-ID"

# Initialize OpenAI API
client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize SQL database connection
conn = sqlite3.connect("reddit_posts.db")
cursor = conn.cursor()

# Create a table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        comment TEXT,
        sentiment TEXT
    )
""")
conn.commit()

def get_top_news_posts_with_comments(limit=100):
    """
    Fetches the top posts of the day from r/news and retrieves titles and first-level comments.
    
    Parameters:
    - limit (int): Number of posts to retrieve.

    Returns:
    - list: A list of dictionaries containing post titles and lists of first-level comments.
    """
    # Initialize the Reddit instance
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )

    # Access the r/news subreddit
    subreddit = reddit.subreddit('news')

    posts_data = []

    # Get the top posts of the day
    for post in subreddit.top(time_filter='year', limit=limit):
        post.comments.replace_more(limit=0)
        first_level_comments = [
            comment.body for comment in post.comments
            if isinstance(comment, praw.models.Comment)
        ][:100]  # cap the comments at 100
        
        posts_data.append({
            'title': post.title,
            'comments': first_level_comments
        })

    return posts_data

def analyze_sentiment(title, comments, batch_size=20):
    """
    Analyzes the sentiment of each comment using OpenAI's API.
    """
    results = []
    total_comments = len(comments)
    print(f"Analyzing sentiment for {total_comments} comments...")

    for i in range(0, total_comments, batch_size):
        batch = comments[i:i+batch_size]
        prompts = [
            f"Title: {title}\nComment: {comment}\n-> Pick the sentiment of the comment responding only with 'happy', 'neutral', or 'unhappy'"
            for comment in batch
        ]

        # Combine prompts for batch processing
        combined_prompt = "\n\n".join(prompts)

        messages = [
            {"role": "system", "content": "You are an assistant that analyzes the sentiment of comments. Respond with only 'happy', 'neutral', or 'unhappy' for each comment under no circumstances is there anything else"},
            {"role": "user", "content": combined_prompt}
        ]

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )

        response_text = response.choices[0].message.content.strip()
        sentiments = response_text.split('\n')

        for comment, sentiment in zip(batch, sentiments):
            sentiment_lower = sentiment.lower()
            if any(word in sentiment_lower for word in ['happy', 'neutral', 'unhappy']):
                results.append({
                    'comment': comment,
                    'sentiment': sentiment
                })
            else:
                results.append({
                    'comment': comment,
                    'sentiment': 'unknown'
                })

        print(f"Processed batch {i//batch_size + 1} / {(total_comments + batch_size -1)//batch_size}")

    return results

def save_to_database(title, comments_with_sentiment):
    """
    Saves post title, comments, and sentiment data to the SQL database.
    """
    for entry in comments_with_sentiment:
        comment = entry['comment']
        sentiment = entry['sentiment']
        cursor.execute("INSERT INTO posts (title, comment, sentiment) VALUES (?, ?, ?)", (title, comment, sentiment))
    conn.commit()

def process_and_store_posts():
    """
    Fetches multiple top Reddit posts, analyzes sentiment for each comment,
    and stores results in the SQL database.
    """
    posts_data = get_top_news_posts_with_comments()
    for post_data in posts_data:
        title = post_data['title']
        comments = post_data['comments']
        
        sentiments = analyze_sentiment(title, comments)
        save_to_database(title, sentiments)
        print(f"Data for post '{title}' saved to database.")

if __name__ == "__main__":
    process_and_store_posts()
    conn.close()
