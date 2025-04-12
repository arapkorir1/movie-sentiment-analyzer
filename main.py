import requests
import os
from datetime import datetime
from dotenv import load_dotenv
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import sqlite3
import matplotlib.pyplot as plt
import pandas as pd

# Load environment variables
load_dotenv()
api_key = os.getenv("TMDB_API_KEY")

def init_db():
    conn = sqlite3.connect("movies.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            title TEXT PRIMARY KEY,
            rating TEXT,
            release_date TEXT,
            positive REAL,
            negative REAL,
            neutral REAL
        )
    """)
    conn.commit()
    return conn

def get_movie_data(title, api_key=api_key):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={title}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if not data["results"]:
            return None
        movie = data["results"][0]
        release_date = "Unknown"
        if movie.get("release_date"):
            date_obj = datetime.strptime(movie["release_date"], "%Y-%m-%d")
            release_date = date_obj.strftime("%B %d, %Y")
        return {
            "id": movie.get("id"),
            "title": movie.get("title", "N/A"),
            "rating": f"{movie.get('vote_average', 0)}/10",
            "release_date": release_date,
            "overview": movie.get("overview", "No description available.")
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def get_movie_reviews(movie_id, api_key=api_key):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/reviews?api_key={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return [review["content"] for review in data.get("results", [])]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching reviews: {e}")
        return []

def analyze_sentiment(text):
    sid = SentimentIntensityAnalyzer()
    scores = sid.polarity_scores(text)
    compound = scores["compound"]
    if compound >= 0.1:
        return "Positive"
    elif compound <= -0.1:
        return "Negative"
    else:
        return "Neutral"

def summarize_sentiment(reviews):
    if not reviews:
        return {"Positive": 0, "Negative": 0, "Neutral": 0}
    sentiments = [analyze_sentiment(review) for review in reviews]
    total = len(sentiments)
    if total == 0:
        return {"Positive": 0, "Negative": 0, "Neutral": 0}
    return {
        "Positive": sentiments.count("Positive") / total * 100,
        "Negative": sentiments.count("Negative") / total * 100,
        "Neutral": sentiments.count("Neutral") / total * 100
    }

def plot_sentiment(sentiment_summary, title):
    labels = sentiment_summary.keys()
    sizes = sentiment_summary.values()
    plt.pie(sizes, labels=labels, autopct="%1.2f%%", startangle=140)
    plt.title(f"Sentiment Distribution for {title}")
    plt.show()

def save_results(movie, sentiment_summary, conn):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO movies (title, rating, release_date, positive, negative, neutral)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (movie["title"], movie["rating"], movie["release_date"],
          sentiment_summary["Positive"], sentiment_summary["Negative"], sentiment_summary["Neutral"]))
    conn.commit()

def display_menu():
    print("\nMenu:\n[S]earch Movie, [Q]uit")
    return input("Enter option (S/Q): ").lower()

def main():
    if not api_key:
        raise ValueError("API key not found!")
    conn = init_db()
    while True:
        choice = display_menu()
        if choice == 's':
            movie_title = input("Enter movie title: ")
            movie = get_movie_data(movie_title, api_key)
            if movie:
                print(f"Title: {movie['title']}")
                print(f"Rating: {movie['rating']}")
                print(f"Released: {movie['release_date']}")
                print(f"Summary: {movie['overview']}")
                reviews = get_movie_reviews(movie["id"], api_key)
                if reviews:
                    print("\nReviews found:", len(reviews))
                    sentiment_summary = summarize_sentiment(reviews)
                    print("\nSentiment Analysis Summary:")
                    print(f"Positive: {sentiment_summary['Positive']:.2f}%")
                    print(f"Negative: {sentiment_summary['Negative']:.2f}%")
                    print(f"Neutral: {sentiment_summary['Neutral']:.2f}%")
                    sample_review = reviews[0][:200] + "..." if len(reviews[0]) > 200 else reviews[0]
                    print("\nSample Review:")
                    print(f"Review: {sample_review}")
                    print(f"Sentiment: {analyze_sentiment(reviews[0])}")
                    plot_sentiment(sentiment_summary, movie["title"])
                    save_results(movie, sentiment_summary, conn)
                else:
                    print("\nNo reviews found.")
            else:
                print("Movie not found!")
        elif choice == 'q':
            print("Goodbye!")
            conn.close()
            break
        else:
            print("Invalid choice, try again.")

if __name__ == "__main__":
    main()
