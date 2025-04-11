import requests
import os
from datetime import datetime
from dotenv import load_dotenv
from textblob import TextBlob
import pandas as pd

# Load variables from .env file
load_dotenv()

# Fetch the API key
api_key = os.getenv("TMDB_API_KEY")

def get_movie_data(title, api_key=api_key):
    """Fetch basic movie details from TMDb API."""
    url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={title}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check for HTTP errors
        data = response.json()
        if not data["results"]:
            return None
        movie = data["results"][0]
        # Format release date (e.g., "2025-06-25" → "June 25, 2025")
        release_date = "Unknown"
        if movie.get("release_date"):
            date_obj = datetime.strptime(movie["release_date"], "%Y-%m-%d")
            release_date = date_obj.strftime("%B %d, %Y")
        return {
            "id": movie.get("id"),  # Added movie ID for reviews endpoint
            "title": movie.get("title", "N/A"),
            "rating": f"{movie.get('vote_average', 0)}/10",
            "release_date": release_date,
            "overview": movie.get("overview", "No description available.")
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def get_movie_reviews(movie_id, api_key=api_key):
    """Fetch movie reviews from TMDb API."""
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/reviews?api_key={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        reviews = data.get("results", [])
        return [review["content"] for review in reviews]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching reviews: {e}")
        return []

def analyze_sentiment(text):
    """Analyze sentiment of a given text using TextBlob."""
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity > 0:
        return "Positive"
    elif polarity < 0:
        return "Negative"
    else:
        return "Neutral"

def summarize_sentiment(reviews):
    """Summarize sentiment across all reviews."""
    if not reviews:
        return {"Positive": 0, "Negative": 0, "Neutral": 0}
    
    sentiments = [analyze_sentiment(review) for review in reviews]
    total = len(sentiments)
    if total == 0:
        return {"Positive": 0, "Negative": 0, "Neutral": 0}
    
    sentiment_counts = {
        "Positive": sentiments.count("Positive") / total * 100,
        "Negative": sentiments.count("Negative") / total * 100,
        "Neutral": sentiments.count("Neutral") / total * 100
    }
    return sentiment_counts

# Main execution
if __name__ == "__main__":
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        raise ValueError("API key not found in environment variables!")

    # Search for the movie
    movie_title = "Oppenheimer"
    movie = get_movie_data(movie_title, api_key)
    
    if movie:
        print(f"Title: {movie['title']}")
        print(f"Rating: {movie['rating']}")
        print(f"Released: {movie['release_date']}")
        print(f"Summary: {movie['overview']}")
        
        # Fetch and analyze reviews
        reviews = get_movie_reviews(movie["id"], api_key)
        if reviews:
            print("\nReviews found:", len(reviews))
            sentiment_summary = summarize_sentiment(reviews)
            print("\nSentiment Analysis Summary:")
            print(f"Positive: {sentiment_summary['Positive']:.2f}%")
            print(f"Negative: {sentiment_summary['Negative']:.2f}%")
            print(f"Neutral: {sentiment_summary['Neutral']:.2f}%")
            
            # Print a sample review with its sentiment
            print("\nSample Review:")
            sample_review = reviews[0][:200] + "..." if len(reviews[0]) > 200 else reviews[0]
            print(f"Review: {sample_review}")
            print(f"Sentiment: {analyze_sentiment(reviews[0])}")
        else:
            print("\nNo reviews found for this movie.")
    else:
        print("Movie not found or API error!")
