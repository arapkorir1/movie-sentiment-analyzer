import requests
import os
from datetime import datetime
from dotenv import load_dotenv
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import sqlite3
import matplotlib.pyplot as plt
import logging

# Configure  logging
logging.basicConfig(filename="sentiment.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load environment variables
load_dotenv()
api_key = os.getenv("TMDB_API_KEY")

def init_db():
    try:
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
        logging.info("Database initialized successfully")
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database initialization failed: {e}")
        raise

def get_movie_data(title, api_key=api_key):
    # Try movie search first
    url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={title}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data["results"]:
            movie = data["results"][0]
            release_date = "Unknown"
            if movie.get("release_date"):
                date_obj = datetime.strptime(movie["release_date"], "%Y-%m-%d")
                release_date = date_obj.strftime("%B %d, %Y")
            logging.info(f"Fetched movie data for {title}")
            return {
                "id": movie.get("id"),
                "title": movie.get("title", "N/A"),
                "rating": f"{movie.get('vote_average', 0)}/10",
                "release_date": release_date,
                "overview": movie.get("overview", "No description available."),
                "type": "movie"
            }
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching movie data for {title}: {e}")
    
    # Try TV show search if no movie found
    url = f"https://api.themoviedb.org/3/search/tv?api_key={api_key}&query={title}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data["results"]:
            show = data["results"][0]
            release_date = "Unknown"
            if show.get("first_air_date"):
                date_obj = datetime.strptime(show["first_air_date"], "%Y-%m-%d")
                release_date = date_obj.strftime("%B %d, %Y")
            logging.info(f"Fetched TV show data for {title}")
            return {
                "id": show.get("id"),
                "title": show.get("name", "N/A"),
                "rating": f"{show.get('vote_average', 0)}/10",
                "release_date": release_date,
                "overview": show.get("overview", "No description available."),
                "type": "tv"
            }
        logging.warning(f"No results found for {title}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching TV data for {title}: {e}")
        return None

def get_movie_reviews(item_id, item_type, api_key=api_key):
    endpoint = "movie" if item_type == "movie" else "tv"
    url = f"https://api.themoviedb.org/3/{endpoint}/{item_id}/reviews?api_key={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        reviews = [review["content"] for review in data.get("results", [])]
        logging.info(f"Fetched {len(reviews)} reviews for ID {item_id}")
        return reviews
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching reviews for ID {item_id}: {e}")
        return []

def analyze_sentiment(text):
    try:
        sid = SentimentIntensityAnalyzer()
        scores = sid.polarity_scores(text)
        compound = scores["compound"]
        if compound >= 0.1:
            return "Positive"
        elif compound <= -0.1:
            return "Negative"
        else:
            return "Neutral"
    except Exception as e:
        logging.error(f"Sentiment analysis failed: {e}")
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
    try:
        labels = sentiment_summary.keys()
        sizes = sentiment_summary.values()
        plt.pie(sizes, labels=labels, autopct="%1.2f%%", startangle=140)
        plt.title(f"Sentiment Distribution for {title}")
        plt.show()
        logging.info(f"Plotted sentiment for {title}")
    except Exception as e:
        logging.error(f"Plotting failed: {e}")
        print("Unable to display plot. Check log for details.")

def save_results(item, sentiment_summary, conn):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO movies (title, rating, release_date, positive, negative, neutral)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (item["title"], item["rating"], item["release_date"],
              sentiment_summary["Positive"], sentiment_summary["Negative"], sentiment_summary["Neutral"]))
        conn.commit()
        logging.info(f"Saved results for {item['title']}")
    except sqlite3.Error as e:
        logging.error(f"Database save failed for {item['title']}: {e}")

def display_menu():
    print("\nMovie Sentiment Analyzer Menu:")
    print("[S]earch Movie or TV Show")
    print("[Q]uit")
    return input("Enter option (S/Q): ").lower()

def main():
    if not api_key:
        raise ValueError("API key not found in .env file!")
    conn = init_db()
    while True:
        choice = display_menu()
        if choice == 's':
            title = input("Enter movie or TV show title: ").strip()
            if not title:
                print("Please enter a valid title.")
                logging.warning("Empty title input")
                continue
            item = get_movie_data(title, api_key)
            if item:
                print(f"\nTitle: {item['title']} ({'Movie' if item['type'] == 'movie' else 'TV Show'})")
                print(f"Rating: {item['rating']}")
                print(f"Released: {item['release_date']}")
                print(f"Summary: {item['overview']}")
                reviews = get_movie_reviews(item["id"], item["type"], api_key)
                if reviews:
                    print(f"\nFound {len(reviews)} reviews")
                    sentiment_summary = summarize_sentiment(reviews)
                    print("\nSentiment Analysis Summary:")
                    print(f"Positive: {sentiment_summary['Positive']:.2f}%")
                    print(f"Negative: {sentiment_summary['Negative']:.2f}%")
                    print(f"Neutral: {sentiment_summary['Neutral']:.2f}%")
                    if reviews:
                        sample_review = reviews[0][:200] + "..." if len(reviews[0]) > 200 else reviews[0]
                        print("\nSample Review:")
                        print(f"Review: {sample_review}")
                        print(f"Sentiment: {analyze_sentiment(reviews[0])}")
                    plot_sentiment(sentiment_summary, item["title"])
                    save_results(item, sentiment_summary, conn)
                else:
                    print("\nNo reviews found for this title.")
            else:
                print(f"\n'{title}' not found. Try a different spelling or title.")
        elif choice == 'q':
            print("Thanks for using the Movie Sentiment Analyzer! Goodbye!")
            conn.close()
            break
        else:
            print("Invalid choice. Please select S or Q.")
            logging.warning(f"Invalid menu choice: {choice}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
        logging.info("Program terminated by user")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        logging.error(f"Unexpected error: {e}")
