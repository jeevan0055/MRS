"""
TMDB Movie Enrichment Pipeline
Production-grade, scalable, resumable, fault-tolerant enrichment script
"""
import sys
import os
import time
import json
import csv
import argparse
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Thread-local storage for HTTP sessions
_thread_local = threading.local()

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models import Movie
from app.core.config import settings
from sqlalchemy.orm import load_only

# Constants
DEFAULT_BATCH_SIZE = 25
DEFAULT_CHUNK_SIZE = 100
DEFAULT_MAX_WORKERS = 5
PROGRESS_FILE = os.path.join(os.path.dirname(__file__), "tmdb_progress.json")
FAILED_FILE = os.path.join(os.path.dirname(__file__), "failed_movies.csv")
TMDB_BASE_URL = "https://api.themoviedb.org/3"


@dataclass
class ProgressState:
    """Dataclass to track progress state"""
    processed: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    last_movie_id: Optional[int] = None
    start_time: Optional[str] = None
    last_save_time: Optional[str] = None


class TokenBucketRateLimiter:
    """
    Thread-safe token bucket rate limiter with adaptive backoff for 429 responses
    """
    def __init__(
        self,
        requests_per_second: float = None,
        burst_size: int = None,
        min_rate: float = 0.5,  # 0.5 requests per second minimum
        initial_rate: float = 5.0,  # Start at 5 req/sec
        backoff_factor: float = 2.0,
        recovery_factor: float = 0.95
    ):
        # Load from environment variables if not provided
        if requests_per_second is None:
            requests_per_second = float(os.getenv("REQUESTS_PER_SECOND", str(initial_rate)))
        if burst_size is None:
            burst_size = int(os.getenv("BURST_SIZE", "10"))

        self.lock = threading.Lock()
        # Thread-safe internal state
        with self.lock:
            self.requests_per_second = requests_per_second  # Current rate (tokens/sec)
            self.base_rate = initial_rate  # Base rate to recover towards
            self.min_rate = min_rate
            self.burst_size = burst_size
            self.tokens = burst_size  # Start with full bucket
            self.last_refill_time = time.time()
            self.backoff_factor = backoff_factor
            self.recovery_factor = recovery_factor
            self.next_available_time = 0.0  # For 429 Retry-After

    def _refill_tokens(self) -> None:
        """
        Refill tokens based on elapsed time - MUST hold lock when calling this!
        """
        now = time.time()
        elapsed = now - self.last_refill_time
        new_tokens = elapsed * self.requests_per_second
        self.tokens = min(self.burst_size, self.tokens + new_tokens)
        self.last_refill_time = now

    def acquire(self) -> None:
        """
        Acquire a token from the bucket, waiting if necessary
        Does NOT hold the lock while sleeping
        """
        while True:
            with self.lock:
                # First, check if we're blocked by a Retry-After header
                now = time.time()
                if now < self.next_available_time:
                    wait_time = self.next_available_time - now
                    # Release lock, sleep outside
                    time.sleep(wait_time)
                    continue

                # Refill tokens
                self._refill_tokens()

                if self.tokens >= 1:
                    self.tokens -= 1
                    return

                # Not enough tokens, calculate wait time
                tokens_needed = 1 - self.tokens
                wait_time = tokens_needed / self.requests_per_second

            # Sleep outside the lock
            time.sleep(wait_time)

    def record_success(self) -> None:
        """
        Record a successful request - gradually increase rate towards base
        """
        with self.lock:
            self.requests_per_second = min(
                self.base_rate,
                self.requests_per_second / self.recovery_factor  # Divide by <1 to increase
            )

    def record_429(self, retry_after: Optional[int] = None) -> None:
        """
        Record a 429 response
        - Respect Retry-After header if present (in seconds)
        - Otherwise exponentially back off
        """
        with self.lock:
            if retry_after is not None and retry_after > 0:
                self.next_available_time = time.time() + retry_after
            else:
                # Exponentially reduce the rate
                self.requests_per_second = max(
                    self.min_rate,
                    self.requests_per_second / self.backoff_factor
                )
                # Also add a small delay to be safe
                self.next_available_time = time.time() + (1.0 / self.requests_per_second)


def create_retry_session() -> requests.Session:
    """Create a requests Session with retries and connection pooling"""
    session = requests.Session()
    retry = Retry(
        total=3,
        read=3,
        connect=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def get_session() -> requests.Session:
    """Get or create a thread-local requests Session"""
    if not hasattr(_thread_local, "session"):
        _thread_local.session = create_retry_session()
    return _thread_local.session


def fetch_tmdb_data(
    movie: Movie,
    rate_limiter: TokenBucketRateLimiter,
    debug: bool = False
) -> Tuple[Movie, Optional[Dict[str, Any]], Optional[str]]:
    """
    Fetch TMDB data for a single movie (runs in worker threads)
    
    Returns:
        (movie, tmdb_data_dict, error_message)
    """
    imdb_id = movie.imdb_id
    if not settings.TMDB_API_KEY or not imdb_id or not imdb_id.strip():
        return (movie, None, "Missing TMDB API key or IMDb ID")

    rate_limiter.acquire()

    try:
        url = f"{TMDB_BASE_URL}/find/tt{imdb_id}"
        params = {
            "api_key": settings.TMDB_API_KEY,
            "external_source": "imdb_id"
        }
        response = get_session().get(url, params=params, timeout=(5, 10))

        if response.status_code == 429:
            retry_after = None
            # Try to get Retry-After header (can be int or date string)
            if "Retry-After" in response.headers:
                try:
                    retry_after = int(response.headers["Retry-After"])
                except ValueError:
                    # If it's a date string, we'll just use default backoff
                    pass
            rate_limiter.record_429(retry_after)
            return (movie, None, f"429 Too Many Requests")

        response.raise_for_status()
        data = response.json()

        if data.get("movie_results"):
            rate_limiter.record_success()
            tmdb_movie = data["movie_results"][0]
            return (
                movie,
                {
                    "tmdb_id": str(tmdb_movie["id"]),
                    "poster_path": tmdb_movie.get("poster_path"),
                    "overview": tmdb_movie.get("overview"),
                    "vote_average": tmdb_movie.get("vote_average"),
                    "vote_count": tmdb_movie.get("vote_count"),
                    "popularity": tmdb_movie.get("popularity"),
                },
                None
            )

        rate_limiter.record_success()
        return (movie, None, "No movie results from TMDB")

    except requests.exceptions.RequestException as e:
        return (movie, None, str(e))


def save_progress(state: ProgressState) -> None:
    """Save progress state to JSON file"""
    state.last_save_time = datetime.now().isoformat()
    state_dict = {
        "processed": state.processed,
        "updated": state.updated,
        "skipped": state.skipped,
        "failed": state.failed,
        "last_movie_id": state.last_movie_id,
        "start_time": state.start_time,
        "last_save_time": state.last_save_time
    }
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(state_dict, f)


def load_progress() -> ProgressState:
    """Load progress state from JSON file"""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return ProgressState(
                    processed=data.get("processed", 0),
                    updated=data.get("updated", 0),
                    skipped=data.get("skipped", 0),
                    failed=data.get("failed", 0),
                    last_movie_id=data.get("last_movie_id"),
                    start_time=data.get("start_time"),
                    last_save_time=data.get("last_save_time")
                )
        except Exception:
            pass
    return ProgressState()


def log_failure(
    movie_id: int,
    imdb_id: Optional[str],
    title: Optional[str],
    error: str
) -> None:
    """Log a failed movie to failed_movies.csv"""
    file_exists = os.path.exists(FAILED_FILE)
    with open(FAILED_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "movie_id", "imdb_id", "title", "error", "timestamp"
            ])
        writer.writerow([
            movie_id,
            imdb_id or "",
            title or "",
            error,
            datetime.now().isoformat()
        ])


def print_progress(
    state: ProgressState,
    total_to_process: int,
    initial_saved_processed: int,
    start_time: datetime,
    batch_num: int,
    debug: bool = False
) -> None:
    """Print clean progress dashboard"""
    elapsed = (datetime.now() - start_time).total_seconds()
    current_run_processed = state.processed - initial_saved_processed
    remaining = total_to_process - current_run_processed
    requests_per_sec = (state.processed - state.skipped) / elapsed if elapsed > 0 else 0
    eta_seconds = remaining / requests_per_sec if requests_per_sec > 0 and remaining > 0 else 0
    eta_minutes = int(eta_seconds // 60)
    eta_secs_remaining = int(eta_seconds % 60)
    total_expected_total = total_to_process + initial_saved_processed
    percentage = (state.processed / total_expected_total * 100) if total_expected_total > 0 else 0

    # Cross-platform console clear
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")
        
    print("=" * 50)
    print("TMDB ENRICHMENT PIPELINE")
    print("=" * 50)
    print(f"Progress     : {percentage:.1f}%")
    print(f"Processed    : {state.processed} / {total_expected_total}")
    print(f"Updated      : {state.updated}")
    print(f"Skipped      : {state.skipped}")
    print(f"Failed       : {state.failed}")
    print(f"Speed        : {requests_per_sec:.1f} req/sec")
    print(f"ETA          : {eta_minutes}m {eta_secs_remaining}s")
    print(f"Current Batch: {batch_num}")
    print(f"Last Movie ID: {state.last_movie_id or 'None'}")
    print("=" * 50)
    if debug:
        print(f"\nDebug info: elapsed={elapsed:.1f}s, remaining={remaining}")


def commit_batch(db_session, bulk_updates: List[Dict], state: ProgressState, debug: bool = False) -> None:
    """Commit a batch with bulk updates, handle failures gracefully"""
    try:
        if bulk_updates:
            db_session.bulk_update_mappings(Movie, bulk_updates)
        db_session.commit()
        return True
    except Exception as e:
        if debug:
            print(f"Commit failed: {str(e)}")
        db_session.rollback()
        return False


def process_batch(
    movies: List[Movie],
    db_session,
    state: ProgressState,
    rate_limiter: TokenBucketRateLimiter,
    batch_size: int,
    max_workers: int,
    debug: bool = False
) -> None:
    """
    Process a single batch of movies:
    1. Parallel fetch TMDB data
    2. Sequentially prepare bulk updates
    3. Bulk update and commit every batch_size updates
    """
    # Map movie.id to movie for quick access to title/imdb_id
    movie_map = {movie.id: movie for movie in movies}
    
    # Step 1: Split into skipped and to-fetch
    to_fetch: List[Movie] = []
    for movie in movies:
        state.processed += 1
        if movie.tmdb_id and movie.poster_path:
            state.skipped += 1
            state.last_movie_id = movie.id
            continue
        to_fetch.append(movie)

    # Step 2: Parallel fetch
    fetched: List[Tuple[int, Optional[Dict[str, Any]], Optional[str]]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_tmdb_data, m, rate_limiter, debug): m.id
            for m in to_fetch
        }
        for future in as_completed(futures):
            movie_id = futures[future]
            # Get the movie from the map just for title/imdb_id, not to modify it
            movie = movie_map[movie_id]
            try:
                _, tmdb_data, error = future.result()
                fetched.append((movie_id, tmdb_data, error))
            except Exception as e:
                fetched.append((movie_id, None, str(e)))

    # Step3: Prepare bulk updates and commit in batches
    bulk_updates: List[Dict] = []
    
    for movie_id, tmdb_data, error in fetched:
        movie = movie_map[movie_id]
        state.last_movie_id = movie.id
        
        if error:
            state.failed += 1
            log_failure(movie_id, movie.imdb_id, movie.title, error)
        elif tmdb_data:
            # Prepare update dict - only include fields that are not None and changed
            update_dict = {"id": movie_id}
            has_changes = False
            
            if tmdb_data.get("tmdb_id") is not None and movie.tmdb_id != tmdb_data["tmdb_id"]:
                update_dict["tmdb_id"] = tmdb_data["tmdb_id"]
                has_changes = True
                
            if tmdb_data.get("poster_path") is not None and movie.poster_path != tmdb_data["poster_path"]:
                update_dict["poster_path"] = tmdb_data["poster_path"]
                has_changes = True
                
            if tmdb_data.get("overview") is not None and movie.overview != tmdb_data["overview"]:
                update_dict["overview"] = tmdb_data["overview"]
                has_changes = True
                
            if tmdb_data.get("vote_average") is not None and movie.vote_average != tmdb_data["vote_average"]:
                update_dict["vote_average"] = tmdb_data["vote_average"]
                has_changes = True
                
            if tmdb_data.get("vote_count") is not None and movie.vote_count != tmdb_data["vote_count"]:
                update_dict["vote_count"] = tmdb_data["vote_count"]
                has_changes = True
                
            if tmdb_data.get("popularity") is not None and movie.popularity != tmdb_data["popularity"]:
                update_dict["popularity"] = tmdb_data["popularity"]
                has_changes = True
                
            if has_changes:
                bulk_updates.append(update_dict)
                state.updated += 1
                
                # Commit if batch size reached
                if len(bulk_updates) >= batch_size:
                    success = commit_batch(db_session, bulk_updates, state, debug)
                    if success:
                        bulk_updates = []  # Clear batch on successful commit
                        save_progress(state)

    # Commit any remaining in this batch
    if bulk_updates:
        commit_batch(db_session, bulk_updates, state, debug)
        save_progress(state)


def retry_failed_movies(
    db_session,
    state: ProgressState,
    initial_saved_processed: int,
    rate_limiter: TokenBucketRateLimiter,
    batch_size: int,
    chunk_size: int,
    max_workers: int,
    debug: bool = False
) -> None:
    """Process only movies listed in failed_movies.csv"""
    if not os.path.exists(FAILED_FILE):
        print("No failed_movies.csv file found!")
        return

    print("Processing failed movies from failed_movies.csv")
    failed_movie_ids: List[int] = []
    with open(FAILED_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                failed_movie_ids.append(int(row["movie_id"]))
            except Exception:
                pass

    if not failed_movie_ids:
        print("No valid failed movie IDs to retry!")
        return

    # Delete existing failed file
    os.remove(FAILED_FILE)

    total_to_process = len(failed_movie_ids)
    batch_num = 0
    start_time = datetime.now()

    # Process in chunks
    for i in range(0, len(failed_movie_ids), chunk_size):
        batch_num += 1
        chunk_ids = failed_movie_ids[i:i+chunk_size]
        movies = db_session.query(Movie).options(
            load_only(
                Movie.id, Movie.imdb_id, Movie.tmdb_id,
                Movie.poster_path, Movie.overview, Movie.vote_average,
                Movie.vote_count, Movie.popularity, Movie.title
            )
        ).filter(Movie.id.in_(chunk_ids)).all()

        process_batch(
            movies,
            db_session,
            state,
            rate_limiter,
            batch_size,
            max_workers,
            debug
        )

        print_progress(state, total_to_process, initial_saved_processed, start_time, batch_num, debug)

    print("\nRetry completed!")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="TMDB Movie Enrichment Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--retry-failed", action="store_true", help="Process only failed movies from failed_movies.csv")
    parser.add_argument("--workers", type=int, default=DEFAULT_MAX_WORKERS, help="Number of parallel workers for HTTP requests")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Number of updates per DB commit")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="Number of movies per processing chunk")
    parser.add_argument("--resume", action="store_true", help="Resume from last saved progress (default behavior)")
    parser.add_argument("--fresh-start", action="store_true", help="Ignore saved progress and start fresh")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Validate TMDB API key
    if not settings.TMDB_API_KEY:
        print("ERROR: TMDB_API_KEY not found in environment variables!")
        print("Please add your TMDB API key to backend/.env")
        sys.exit(1)

    # Setup
    db = SessionLocal()
    rate_limiter = TokenBucketRateLimiter()
    start_time = datetime.now()

    # Load or reset progress
    if args.fresh_start:
        state = ProgressState(start_time=start_time.isoformat())
        initial_saved_processed = 0
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
    else:
        state = load_progress()
        initial_saved_processed = state.processed
        if not state.start_time:
            state.start_time = start_time.isoformat()

    try:
        if args.retry_failed:
            retry_failed_movies(
                db,
                state,
                initial_saved_processed,
                rate_limiter,
                args.batch_size,
                args.chunk_size,
                args.workers,
                args.debug
            )
        else:
            # Normal processing mode
            # Build query with SQL filtering and load_only
            query = db.query(Movie).options(
                load_only(
                    Movie.id, Movie.imdb_id, Movie.tmdb_id,
                    Movie.poster_path, Movie.overview, Movie.vote_average,
                    Movie.vote_count, Movie.popularity, Movie.title
                )
            ).filter(
                Movie.imdb_id.isnot(None),
                Movie.imdb_id != "",
                (Movie.tmdb_id.is_(None) | Movie.poster_path.is_(None))
            ).order_by(Movie.id)

            # Apply resume filter
            if state.last_movie_id is not None:
                query = query.filter(Movie.id > state.last_movie_id)

            total_to_process = query.count()
            if total_to_process == 0 and state.processed == 0:
                print("No movies to process! All movies are already enriched.")
                return

            batch_num = 0
            # Process using yield_per for streaming
            movies_buffer: List[Movie] = []
            for movie in query.yield_per(args.chunk_size):
                movies_buffer.append(movie)
                if len(movies_buffer) >= args.chunk_size:
                    batch_num += 1
                    process_batch(
                        movies_buffer,
                        db,
                        state,
                        rate_limiter,
                        args.batch_size,
                        args.workers,
                        args.debug
                    )
                    print_progress(state, total_to_process, initial_saved_processed, start_time, batch_num, args.debug)
                    movies_buffer = []

            # Process remaining movies in buffer
            if movies_buffer:
                batch_num += 1
                process_batch(
                    movies_buffer,
                    db,
                    state,
                    rate_limiter,
                    args.batch_size,
                    args.workers,
                    args.debug
                )
                print_progress(state, total_to_process, initial_saved_processed, start_time, batch_num, args.debug)

        # Final save and summary
        save_progress(state)
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        avg_req_sec = ((state.processed - state.skipped) / elapsed) if elapsed > 0 else 0
        avg_commits_sec = (state.updated / args.batch_size / elapsed) if elapsed > 0 else 0

        # Calculate remaining movies
        remaining_movies = db.query(Movie).filter(
            Movie.imdb_id.isnot(None),
            Movie.imdb_id != "",
            (Movie.tmdb_id.is_(None) | Movie.poster_path.is_(None))
        ).count()

        print("\n" + "=" * 50)
        print("ENRICHMENT COMPLETED!")
        print("=" * 50)
        print(f"Total movies scanned : {state.processed}")
        print(f"Successfully updated : {state.updated}")
        print(f"Skipped (already done): {state.skipped}")
        print(f"Failed               : {state.failed}")
        print(f"Total execution time : {elapsed:.2f}s")
        print(f"Average requests/sec : {avg_req_sec:.2f}")
        print(f"Average DB commits/sec: {avg_commits_sec:.2f}")
        print(f"Remaining to enrich  : {remaining_movies}")
        print("=" * 50)

    except Exception as e:
        print(f"\nFATAL ERROR: {str(e)}")
        if args.debug:
            import traceback
            traceback.print_exc()
        save_progress(state)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
