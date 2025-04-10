import requests
import os
from datetime import datetime
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Fetch the API key
api_key = os.getenv("TMDB_API_KEY")

def get_movie_data(title, api_key=api_key):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={title}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check for HTTP errors
        data = response.json()
        if not data["results"]:
            return None
        movie = data["results"][0]
        # Format release date (e.g., "2010-07-16" → "July 16, 2010")
        release_date = "Unknown"
        if movie.get("release_date"):
            date_obj = datetime.strptime(movie["release_date"], "%Y-%m-%d")
            release_date = date_obj.strftime("%B %d, %Y")
        return {
            "title": movie.get("title", "N/A"),
            "rating": f"{movie.get('vote_average', 0)}/10",
            "release_date": release_date,
            "overview": movie.get("overview", "No description available.")
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

# Example usage
api_key = os.getenv("TMDB_API_KEY")  # Replace with your API key
if not api_key:
    raise ValueError("API key not found in environment variables!")

movie = get_movie_data("prison break", api_key)
if movie:
    print(f"Title: {movie['title']}")
    print(f"Rating: {movie['rating']}")
    print(f"Released: {movie['release_date']}")
    print(f"Summary: {movie['overview']}")
else:
    print("Movie not found or API error!")
