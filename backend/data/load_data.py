import sys
import os
import pandas as pd
import re
import argparse

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, engine, Base
from app.models import Movie, Rating, Favorite, WatchHistory, Review, User


def extract_year(title):
    match = re.search(r"\((\d{4})\)", title)
    return int(match.group(1)) if match else None


def reset_database(db):
    print("Resetting database: deleting all existing data...")
    db.query(Review).delete()
    db.query(WatchHistory).delete()
    db.query(Favorite).delete()
    db.query(Rating).delete()
    db.query(Movie).delete()
    db.query(User).delete()
    db.commit()
    print("Database reset complete!")


def load_data(reset=False):
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    if reset:
        reset_database(db)
    else:
        # Check if data already exists
        if db.query(Movie).count() > 0:
            print("Data already loaded! Use --reset to clear and reload.")
            db.close()
            return

    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml-latest-small")
    print(f"Loading data from {DATA_DIR}...")

    print("Reading movies.csv...")
    movies_df = pd.read_csv(os.path.join(DATA_DIR, "movies.csv"))
    print("Reading links.csv...")
    links_df = pd.read_csv(os.path.join(DATA_DIR, "links.csv"))
    print("Reading tags.csv...")
    tags_df = pd.read_csv(os.path.join(DATA_DIR, "tags.csv"))
    print("Reading ratings.csv...")
    ratings_df = pd.read_csv(os.path.join(DATA_DIR, "ratings.csv"))

    # Process tags
    print("Processing tags...")
    tag_agg = tags_df.groupby("movieId")["tag"].apply(lambda x: " ".join(x.astype(str))).reset_index()
    tag_agg.columns = ["movieId", "tags"]

    # Merge dataframes
    print("Merging data...")
    movies_df = movies_df.merge(links_df, on="movieId", how="left")
    movies_df = movies_df.merge(tag_agg, on="movieId", how="left")
    movies_df["tags"] = movies_df["tags"].fillna("")

    total_movies = len(movies_df)
    print(f"Importing {total_movies} movies...")
    movies_to_insert = []
    for idx, row in movies_df.iterrows():
        clean_title = re.sub(r"\s*\(\d{4}\)", "", row["title"])
        year = extract_year(row["title"])
        imdb_id = str(int(row["imdbId"])).zfill(7) if pd.notna(row["imdbId"]) else None
        
        movie = Movie(
            id=row["movieId"],
            title=clean_title,
            genres=row["genres"],
            year=year,
            imdb_id=imdb_id,
            tmdb_id=None,
            poster_path=None,
            overview=None,
            vote_average=0.0,
            vote_count=0,
            popularity=0.0,
            tags=row["tags"],
        )
        movies_to_insert.append(movie)
        
        # Log progress every 100 movies
        if (idx + 1) % 100 == 0 or (idx + 1) == total_movies:
            print(f"  Imported {idx + 1}/{total_movies} movies...")

    print("Inserting movies into database...")
    db.bulk_save_objects(movies_to_insert)
    db.commit()
    print(f"Successfully inserted {len(movies_to_insert)} movies!")

    total_ratings = len(ratings_df)
    print(f"Importing {total_ratings} ratings...")
    ratings_to_insert = []
    for idx, row in ratings_df.iterrows():
        rating = Rating(
            user_id=int(row["userId"]),
            movie_id=int(row["movieId"]),
            rating=float(row["rating"]),
        )
        ratings_to_insert.append(rating)
        
        if (idx + 1) % 1000 == 0 or (idx + 1) == total_ratings:
            print(f"  Imported {idx + 1}/{total_ratings} ratings...")
            db.bulk_save_objects(ratings_to_insert)
            db.commit()
            ratings_to_insert = []
    
    if ratings_to_insert:
        db.bulk_save_objects(ratings_to_insert)
        db.commit()
    print(f"Successfully imported {total_ratings} ratings!")

    # Verify insertion
    movie_count = db.query(Movie).count()
    rating_count = db.query(Rating).count()
    print(f"Verification: Found {movie_count} movies and {rating_count} ratings in the database!")

    db.close()
    print("Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load MovieLens data into the database (offline)")
    parser.add_argument("--reset", action="store_true", help="Clear existing data before loading")
    args = parser.parse_args()
    load_data(reset=args.reset)
