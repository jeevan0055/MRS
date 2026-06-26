from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class MovieBase(BaseModel):
    title: str
    genres: str
    year: Optional[int] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    poster_path: Optional[str] = None
    overview: Optional[str] = None
    vote_average: Optional[float] = 0.0
    vote_count: Optional[int] = 0
    popularity: Optional[float] = 0.0
    tags: Optional[str] = None


class MovieCreate(MovieBase):
    pass


class MovieResponse(MovieBase):
    id: int

    class Config:
        from_attributes = True


class RatingBase(BaseModel):
    movie_id: int
    rating: float


class RatingCreate(RatingBase):
    pass


class RatingResponse(RatingBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class FavoriteBase(BaseModel):
    movie_id: int


class FavoriteCreate(FavoriteBase):
    pass


class FavoriteResponse(FavoriteBase):
    id: int
    user_id: int
    created_at: datetime
    movie: MovieResponse

    class Config:
        from_attributes = True


class WatchHistoryBase(BaseModel):
    movie_id: int


class WatchHistoryCreate(WatchHistoryBase):
    pass


class WatchHistoryResponse(WatchHistoryBase):
    id: int
    user_id: int
    watched_at: datetime
    movie: MovieResponse

    class Config:
        from_attributes = True


class ReviewBase(BaseModel):
    movie_id: int
    content: str


class ReviewCreate(ReviewBase):
    pass


class ReviewResponse(ReviewBase):
    id: int
    user_id: int
    created_at: datetime
    user: UserResponse

    class Config:
        from_attributes = True


class RecommendationResponse(BaseModel):
    movie: MovieResponse
    score: float
    explanation: str


class AnalyticsResponse(BaseModel):
    total_users: int
    total_movies: int
    total_ratings: int
    genre_distribution: dict
    rating_distribution: dict
    top_rated_movies: List[MovieResponse]
    most_popular_movies: List[MovieResponse]
