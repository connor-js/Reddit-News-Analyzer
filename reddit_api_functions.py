import praw
from openai import OpenAI
import os
import time

# Fetch credentials from environment variables
REDDIT_CLIENT_ID = "YOUR-ID"
REDDIT_CLIENT_SECRET = "YOUR-ID"
REDDIT_USER_AGENT = "YOUR-ID"
OPENAI_API_KEY = "YOUR-ID"

# Initialize OpenAI API
client = OpenAI(api_key=OPENAI_API_KEY)

def get_top_news_post_with_comments():
    """
    Fetches the top post of the day from r/news and retrieves its title along with first-level comments up to 500.

    Returns:
    - dict: A dictionary containing the post title and a list of first-level comments.
    """
    # Initialize the Reddit instance
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )

    # Access the r/news subreddit
    subreddit = reddit.subreddit('news')

    try:
        # Get the top post of the day
        top_post = next(subreddit.top(time_filter='day', limit=1))
    except StopIteration:
        print("No posts found in r/news for the current day.")
        return None

    # Ensure all comments are loaded
    top_post.comments.replace_more(limit=0)

    # Extract first-level comments, capped at 500
    first_level_comments = [
        comment.body for comment in top_post.comments
        if isinstance(comment, praw.models.Comment)
    ][:500]  # cap the comments at 500

    return {
        'title': top_post.title,
        'comments': first_level_comments
    }

def analyze_sentiment(title, comments, batch_size=20):
    """
    Analyzes the sentiment of each comment using OpenAI's API.

    Parameters:
    - title (str): The title of the Reddit post.
    - comments (list): A list of comments to analyze.
    - batch_size (int): Number of comments to process in each batch to manage rate limits.
    - sleep_time (int): Seconds to wait between batches.

    Returns:
    - list: A list of dictionaries containing the comment and its sentiment.
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

        # Extract the response text
        response_text = response.choices[0].message.content.strip()

        # Split the response into individual sentiments
        sentiments = response_text.split('\n')

        # Clean and validate sentiments
        for comment, sentiment in zip(batch, sentiments):
            sentiment_lower = sentiment.lower()  # Convert to lowercase for case-insensitive matching
            if any(word in sentiment_lower for word in ['happy', 'neutral', 'unhappy']):
                results.append({
                    'comment': comment,
                    'sentiment': sentiment
                })

            else:
                # Handle unexpected sentiment outputs
                print("Uknown Sentiment here is chatgpt responce")
                results.append({
                    'comment': comment,
                    'sentiment': 'unknown'
                })

        print(f"Processed batch {i//batch_size + 1} / {(total_comments + batch_size -1)//batch_size}")

    return results

def get_enhanced_dataset():
    """
    Fetches the top Reddit post from r/news, analyzes the sentiment of its comments,
    and returns the dataset with sentiments attached.

    Returns:
    - dict: A dictionary containing the post title and a list of comments with sentiments.
    """
    data = get_top_news_post_with_comments()
    if not data:
        return None

    title = data['title']
    comments = data['comments']
    
    sentiments = analyze_sentiment(title, comments)

    return {
        'title': title,
        'comments_with_sentiment': sentiments
    }

if __name__ == "__main__":
    enhanced_data = get_enhanced_dataset()
    if enhanced_data:
        print("\nTitle:", enhanced_data['title'])
        print("\nComments with Sentiments:")
        for idx, item in enumerate(enhanced_data['comments_with_sentiment'], 1):
            print(f"{idx}. [{item['sentiment'].capitalize()}] {item['comment']}\n")
