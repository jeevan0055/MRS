# CineMatch AI - AI-Powered Movie Recommendation System

A full-stack movie recommendation system with AI-powered recommendations, built with React, FastAPI, PostgreSQL, and machine learning.

## Features

- **Hybrid Recommendation Engine**: Combines content-based filtering (TF-IDF + cosine similarity) and collaborative filtering (KNN)
- **Explainable AI**: Shows why each movie was recommended
- **User Authentication**: JWT-based auth with secure password hashing
- **Movie Browsing**: Search, filter by genre, rating, popularity, and year
- **User Interaction**: Rate movies, add to favorites, write reviews, track watch history
- **Analytics Dashboard**: Visualizations for genre distribution, rating distribution, and top movies
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Dark Theme**: Modern Netflix-inspired UI

## Tech Stack

### Frontend
- React 18
- Vite
- Tailwind CSS
- React Router
- Axios
- Recharts

### Backend
- FastAPI
- SQLAlchemy ORM
- PostgreSQL
- JWT Authentication
- Pydantic
- Uvicorn

### Machine Learning
- Pandas
- NumPy
- Scikit-learn
- TF-IDF Vectorization
- Cosine Similarity
- K-Nearest Neighbors (KNN)

### Data
- MovieLens Latest Small Dataset

## Project Structure

```
tata/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── ml/
│   ├── data/
│   ├── main.py
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── context/
│   │   └── api/
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## Installation Guide

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 15+
- (Optional) TMDB API key for movie posters and details

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Copy `.env` file and configure:
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/cinematch
   SECRET_KEY=your-super-secret-key-here
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   TMDB_API_KEY=your-tmdb-api-key-here
   ```

5. Create PostgreSQL database:
   ```sql
   CREATE DATABASE cinematch;
   ```

6. Download MovieLens dataset:
   ```bash
   cd data
   python download_data.py
   cd ..
   ```

7. Load data into the database:
   ```bash
   python -m data.load_data
   ```

8. Start the backend server:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   Backend docs will be available at http://localhost:8000/docs

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

   Frontend will be available at http://localhost:3000

## Deployment Guide

### Backend Deployment (Render)

1. Push your code to GitHub
2. Create a new Web Service on Render
3. Connect your repository
4. Set environment variables in Render dashboard
5. Deploy!

### Frontend Deployment (Vercel)

1. Push your code to GitHub
2. Import project in Vercel
3. Configure build settings
4. Deploy!

## API Documentation

FastAPI automatically generates interactive API docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /register | Register new user |
| POST | /login | User login |
| GET | /movies | Get movies (with filters) |
| GET | /movies/{id} | Get movie details |
| GET | /search | Search movies |
| POST | /rate-movie | Rate a movie |
| POST | /favorite | Add/remove favorite |
| GET | /favorites | Get user favorites |
| GET | /recommend/{user_id} | Get personalized recommendations |
| GET | /similar-movies/{movie_id} | Get similar movies |
| GET | /trending | Get trending movies |
| GET | /analytics | Get analytics data |

## System Architecture

```
┌─────────────────┐
│   React Frontend│
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────┐
│  FastAPI Server │
├─────────────────┤
│  Auth Service   │
│  Movie Service  │
│Reco Engine(ML)  │
└────────┬────────┘
         │ SQLAlchemy
         ▼
┌─────────────────┐
│  PostgreSQL DB  │
└─────────────────┘
```

## ER Diagram

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    User      │       │    Movie     │       │   Rating     │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (PK)      │◄──────│ id (PK)      │──────►│ id (PK)      │
│ username     │       │ title        │       │ user_id (FK) │
│ email        │       │ genres       │       │ movie_id (FK)│
│ hashed_pw    │       │ year         │       │ rating       │
│ created_at   │       │ imdb_id      │       │ created_at   │
└──────────────┘       │ tmdb_id      │       └──────────────┘
         ▲             │ poster_path  │
         │             │ overview     │
         │             │ vote_avg     │
         │             │ popularity   │
         │             │ tags         │
         │             └──────────────┘
         │                    ▲
         │                    │
         ├────────────────────┼────────────────────┐
         │                    │                    │
┌────────┴───────┐    ┌────────┴───────┐   ┌──────────────┐
│   Favorite     │    │ Watch History   │   │    Review    │
├────────────────┤    ├────────────────┤   ├──────────────┤
│ id (PK)        │    │ id (PK)        │   │ id (PK)      │
│ user_id (FK)   │    │ user_id (FK)   │   │ user_id (FK) │
│ movie_id (FK)  │    │ movie_id (FK)  │   │ movie_id (FK)│
│ created_at     │    │ watched_at     │   │ content      │
└────────────────┘    └────────────────┘   │ created_at   │
                                           └──────────────┘
```

## Recommendation System Details

### Content-Based Filtering
- Uses TF-IDF vectorization on movie genres and tags
- Computes cosine similarity between movies
- Recommends movies similar to those the user liked

### Collaborative Filtering
- Uses user-item interaction matrix
- KNN algorithm with cosine distance
- Recommends movies liked by similar users

### Hybrid Approach
- Combines scores from content-based and collaborative methods
- Handles cold start with popularity-based recommendations for new users

## License

MIT
