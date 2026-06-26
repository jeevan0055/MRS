from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ratings = relationship("Rating", back_populates="user")
    favorites = relationship("Favorite", back_populates="user")
    watch_history = relationship("WatchHistory", back_populates="user")
    reviews = relationship("Review", back_populates="user")


class Movie(Base):
    __tablename__ = "movies"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    genres = Column(String, nullable=False)
    year = Column(Integer)
    imdb_id = Column(String)
    tmdb_id = Column(String)
    poster_path = Column(String)
    overview = Column(Text)
    vote_average = Column(Float, default=0.0)
    vote_count = Column(Integer, default=0)
    popularity = Column(Float, default=0.0)
    tags = Column(Text)

    ratings = relationship("Rating", back_populates="movie")
    favorites = relationship("Favorite", back_populates="movie")
    watch_history = relationship("WatchHistory", back_populates="movie")
    reviews = relationship("Review", back_populates="movie")


class Rating(Base):
    __tablename__ = "ratings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    rating = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="ratings")
    movie = relationship("Movie", back_populates="ratings")

    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="_user_movie_uc"),)


class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="favorites")
    movie = relationship("Movie", back_populates="favorites")

    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="_user_favorite_uc"),)


class WatchHistory(Base):
    __tablename__ = "watch_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    watched_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="watch_history")
    movie = relationship("Movie", back_populates="watch_history")


class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="reviews")
    movie = relationship("Movie", back_populates="reviews")
