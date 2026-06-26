
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List
import pandas as pd
import os

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
)
from app.models import User, Movie, Rating, Favorite, WatchHistory, Review
from app.schemas import (
    UserCreate,
    UserResponse,
    Token,
    MovieResponse,
    RatingCreate,
    RatingResponse,
    FavoriteCreate,
    FavoriteResponse,
    WatchHistoryCreate,
    WatchHistoryResponse,
    ReviewCreate,
    ReviewResponse,
    RecommendationResponse,
    AnalyticsResponse,
)
from app.ml.recommender import MovieRecommender

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Global recommender instance
recommender = None


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


def init_recommender(db: Session):
    global recommender
    if recommender is not None:
        return recommender

    # Load data from DB
    movies_query = db.query(Movie).all()
    movies_data = [
        {
            "movieId": m.id,
            "title": m.title,
            "genres": m.genres,
            "tags": m.tags or "",
        }
        for m in movies_query
    ]
    movies_df = pd.DataFrame(movies_data)

    ratings_query = db.query(Rating).all()
    ratings_data = [
        {"userId": r.user_id, "movieId": r.movie_id, "rating": r.rating}
        for r in ratings_query
    ]
    ratings_df = pd.DataFrame(ratings_data)

    recommender = MovieRecommender(movies_df, ratings_df)
    return recommender


# Auth endpoints
@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# Movie endpoints
@router.get("/movies", response_model=List[MovieResponse])
def get_movies(
    skip: int = 0,
    limit: int = 20,
    genre: str = None,
    year: int = None,
    sort_by: str = "popularity",
    db: Session = Depends(get_db),
):
    query = db.query(Movie)
    if genre:
        query = query.filter(Movie.genres.contains(genre))
    if year:
        query = query.filter(Movie.year == year)
    if sort_by == "popularity":
        query = query.order_by(Movie.popularity.desc())
    elif sort_by == "rating":
        query = query.order_by(Movie.vote_average.desc())
    elif sort_by == "year":
        query = query.order_by(Movie.year.desc())
    movies = query.offset(skip).limit(limit).all()
    return movies


@router.get("/movies/{movie_id}", response_model=MovieResponse)
def get_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@router.get("/search", response_model=List[MovieResponse])
def search_movies(q: str, db: Session = Depends(get_db)):
    movies = db.query(Movie).filter(
        or_(Movie.title.ilike(f"%{q}%"), Movie.genres.ilike(f"%{q}%"))
    ).limit(20).all()
    return movies


# Rating endpoints
@router.post("/rate-movie", response_model=RatingResponse)
def rate_movie(
    rating: RatingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing_rating = db.query(Rating).filter(
        Rating.user_id == current_user.id,
        Rating.movie_id == rating.movie_id
    ).first()
    if existing_rating:
        existing_rating.rating = rating.rating
    else:
        existing_rating = Rating(
            user_id=current_user.id,
            movie_id=rating.movie_id,
            rating=rating.rating
        )
        db.add(existing_rating)
    db.commit()
    db.refresh(existing_rating)
    return existing_rating


# Favorite endpoints
@router.post("/favorite")
def toggle_favorite(
    favorite: FavoriteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.movie_id == favorite.movie_id
    ).first()
    if existing:
        db.delete(existing)
        db.commit()
        return {"status": "removed", "movie_id": favorite.movie_id}
    new_favorite = Favorite(user_id=current_user.id, movie_id=favorite.movie_id)
    db.add(new_favorite)
    db.commit()
    db.refresh(new_favorite)
    movie = db.query(Movie).filter(Movie.id == new_favorite.movie_id).first()
    return FavoriteResponse(
        id=new_favorite.id,
        movie_id=new_favorite.movie_id,
        user_id=new_favorite.user_id,
        created_at=new_favorite.created_at,
        movie=MovieResponse.model_validate(movie)
    )


@router.get("/favorites", response_model=List[FavoriteResponse])
def get_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    favorites = db.query(Favorite).filter(Favorite.user_id == current_user.id).all()
    result = []
    for fav in favorites:
        movie = db.query(Movie).filter(Movie.id == fav.movie_id).first()
        result.append(FavoriteResponse(
            id=fav.id,
            movie_id=fav.movie_id,
            user_id=fav.user_id,
            created_at=fav.created_at,
            movie=MovieResponse.model_validate(movie)
        ))
    return result


# Watch history endpoints
@router.post("/watch-history", response_model=WatchHistoryResponse)
def add_to_watch_history(
    history: WatchHistoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(WatchHistory).filter(
        WatchHistory.user_id == current_user.id,
        WatchHistory.movie_id == history.movie_id
    ).first()
    if existing:
        existing.watched_at = func.now()
    else:
        existing = WatchHistory(user_id=current_user.id, movie_id=history.movie_id)
        db.add(existing)
    db.commit()
    db.refresh(existing)
    movie = db.query(Movie).filter(Movie.id == existing.movie_id).first()
    return WatchHistoryResponse(
        id=existing.id,
        movie_id=existing.movie_id,
        user_id=existing.user_id,
        watched_at=existing.watched_at,
        movie=MovieResponse.model_validate(movie)
    )


@router.get("/watch-history", response_model=List[WatchHistoryResponse])
def get_watch_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    history = db.query(WatchHistory).filter(
        WatchHistory.user_id == current_user.id
    ).order_by(WatchHistory.watched_at.desc()).limit(20).all()
    result = []
    for h in history:
        movie = db.query(Movie).filter(Movie.id == h.movie_id).first()
        result.append(WatchHistoryResponse(
            id=h.id,
            movie_id=h.movie_id,
            user_id=h.user_id,
            watched_at=h.watched_at,
            movie=MovieResponse.model_validate(movie)
        ))
    return result


# Review endpoints
@router.post("/reviews", response_model=ReviewResponse)
def add_review(
    review: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_review = Review(
        user_id=current_user.id,
        movie_id=review.movie_id,
        content=review.content
    )
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    user = db.query(User).filter(User.id == new_review.user_id).first()
    return ReviewResponse(
        id=new_review.id,
        movie_id=new_review.movie_id,
        user_id=new_review.user_id,
        content=new_review.content,
        created_at=new_review.created_at,
        user=UserResponse.model_validate(user)
    )


@router.get("/movies/{movie_id}/reviews", response_model=List[ReviewResponse])
def get_movie_reviews(movie_id: int, db: Session = Depends(get_db)):
    reviews = db.query(Review).filter(Review.movie_id == movie_id).all()
    result = []
    for r in reviews:
        user = db.query(User).filter(User.id == r.user_id).first()
        result.append(ReviewResponse(
            id=r.id,
            movie_id=r.movie_id,
            user_id=r.user_id,
            content=r.content,
            created_at=r.created_at,
            user=UserResponse.model_validate(user)
        ))
    return result


# Recommendation endpoints
@router.get("/recommend/{user_id}", response_model=List[RecommendationResponse])
def get_recommendations(user_id: int, db: Session = Depends(get_db)):
    rec = init_recommender(db)
    recs = rec.get_hybrid_recommendations(user_id, top_n=10)
    result = []
    for movie_id, score, explanation in recs:
        movie = db.query(Movie).filter(Movie.id == movie_id).first()
        if movie:
            result.append(RecommendationResponse(
                movie=MovieResponse.model_validate(movie),
                score=score,
                explanation=explanation
            ))
    return result


@router.get("/similar-movies/{movie_id}", response_model=List[RecommendationResponse])
def get_similar_movies(movie_id: int, db: Session = Depends(get_db)):
    rec = init_recommender(db)
    recs = rec.get_similar_movies(movie_id, top_n=10)
    result = []
    for m_id, score, explanation in recs:
        movie = db.query(Movie).filter(Movie.id == m_id).first()
        if movie:
            result.append(RecommendationResponse(
                movie=MovieResponse.model_validate(movie),
                score=score,
                explanation=explanation
            ))
    return result


@router.get("/trending", response_model=List[MovieResponse])
def get_trending(db: Session = Depends(get_db)):
    rec = init_recommender(db)
    recs = rec.get_popularity_based_recommendations(top_n=10)
    movie_ids = [m_id for m_id, _, _ in recs]
    movies = db.query(Movie).filter(Movie.id.in_(movie_ids)).all()
    # Preserve order
    movie_dict = {m.id: m for m in movies}
    return [MovieResponse.model_validate(movie_dict[m_id]) for m_id in movie_ids if m_id in movie_dict]


# Analytics endpoint
@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics(db: Session = Depends(get_db)):
    total_users = db.query(func.count(User.id)).scalar()
    total_movies = db.query(func.count(Movie.id)).scalar()
    total_ratings = db.query(func.count(Rating.id)).scalar()

    # Genre distribution
    all_movies = db.query(Movie.genres).all()
    genre_counts = {}
    for (genres,) in all_movies:
        for g in genres.split("|"):
            genre_counts[g] = genre_counts.get(g, 0) + 1

    # Rating distribution
    ratings = db.query(Rating.rating).all()
    rating_counts = {}
    for (r,) in ratings:
        key = str(round(r, 1))
        rating_counts[key] = rating_counts.get(key, 0) + 1

    # Top rated
    top_rated = db.query(Movie).order_by(Movie.vote_average.desc()).limit(10).all()
    # Most popular
    most_popular = db.query(Movie).order_by(Movie.popularity.desc()).limit(10).all()

    return AnalyticsResponse(
        total_users=total_users,
        total_movies=total_movies,
        total_ratings=total_ratings,
        genre_distribution=genre_counts,
        rating_distribution=rating_counts,
        top_rated_movies=[MovieResponse.model_validate(m) for m in top_rated],
        most_popular_movies=[MovieResponse.model_validate(m) for m in most_popular],
    )
