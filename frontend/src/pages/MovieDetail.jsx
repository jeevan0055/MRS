import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import axios from '../api/axios'
import MovieCard from '../components/MovieCard'

function MovieDetail() {
  const { id } = useParams()
  const [movie, setMovie] = useState(null)
  const [similar, setSimilar] = useState([])
  const [reviews, setReviews] = useState([])
  const [rating, setRating] = useState(0)
  const [reviewText, setReviewText] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchMovie = async () => {
      try {
        const [movieRes, similarRes, reviewsRes] = await Promise.all([
          axios.get(`/movies/${id}`),
          axios.get(`/similar-movies/${id}`),
          axios.get(`/movies/${id}/reviews`),
        ])
        setMovie(movieRes.data)
        setSimilar(similarRes.data)
        setReviews(reviewsRes.data)
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchMovie()
  }, [id])

  const handleRate = async () => {
    try {
      await axios.post('/rate-movie', { movie_id: parseInt(id), rating })
      alert('Rating submitted!')
    } catch (err) {
      console.error(err)
    }
  }

  const handleFavorite = async () => {
    try {
      await axios.post('/favorite', { movie_id: parseInt(id) })
      alert('Added to favorites!')
    } catch (err) {
      console.error(err)
    }
  }

  const handleAddReview = async (e) => {
    e.preventDefault()
    try {
      await axios.post('/reviews', { movie_id: parseInt(id), content: reviewText })
      setReviewText('')
      const reviewsRes = await axios.get(`/movies/${id}/reviews`)
      setReviews(reviewsRes.data)
    } catch (err) {
      console.error(err)
    }
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="animate-pulse">
          <div className="h-96 bg-gray-800 rounded-lg mb-8"></div>
          <div className="h-8 bg-gray-800 rounded w-1/2 mb-4"></div>
          <div className="h-4 bg-gray-800 rounded w-3/4 mb-2"></div>
          <div className="h-4 bg-gray-800 rounded w-2/3"></div>
        </div>
      </div>
    )
  }

  if (!movie) return <div className="text-center py-12">Movie not found</div>

  const posterUrl = movie.poster_path
    ? `https://image.tmdb.org/t/p/w500${movie.poster_path}`
    : 'https://via.placeholder.com/500x750?text=No+Poster'

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="flex flex-col md:flex-row gap-8 mb-12">
        <div className="md:w-1/3">
          <img src={posterUrl} alt={movie.title} className="w-full rounded-lg shadow-2xl" />
        </div>
        <div className="md:w-2/3">
          <h1 className="text-4xl font-bold mb-2">{movie.title}</h1>
          <p className="text-gray-400 mb-4">{movie.year} • {movie.genres}</p>
          <div className="flex items-center gap-4 mb-6">
            <div className="flex items-center gap-2">
              <span className="text-yellow-400 text-2xl">★</span>
              <span className="text-xl font-semibold">{movie.vote_average?.toFixed(1)}</span>
            </div>
            <button
              onClick={handleFavorite}
              className="px-6 py-2 bg-netflix-red rounded hover:bg-red-700 transition"
            >
              Add to Favorites
            </button>
          </div>
          <p className="text-gray-300 mb-8">{movie.overview}</p>

          <div className="mb-8">
            <h3 className="text-xl font-semibold mb-4">Rate this movie</h3>
            <div className="flex items-center gap-4 mb-4">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  onClick={() => setRating(star)}
                  className={`text-3xl ${star <= rating ? 'text-yellow-400' : 'text-gray-600'}`}
                >
                  ★
                </button>
              ))}
            </div>
            <button
              onClick={handleRate}
              className="px-6 py-2 bg-gray-700 rounded hover:bg-gray-600 transition"
            >
              Submit Rating
            </button>
          </div>

          <div>
            <h3 className="text-xl font-semibold mb-4">Write a review</h3>
            <form onSubmit={handleAddReview} className="space-y-4">
              <textarea
                className="w-full px-4 py-2 rounded bg-gray-800 border border-gray-700 focus:outline-none focus:border-netflix-red"
                rows="4"
                value={reviewText}
                onChange={(e) => setReviewText(e.target.value)}
                placeholder="Share your thoughts..."
              ></textarea>
              <button
                type="submit"
                className="px-6 py-2 bg-netflix-red rounded hover:bg-red-700 transition"
              >
                Post Review
              </button>
            </form>
          </div>
        </div>
      </div>

      {reviews.length > 0 && (
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-6">Reviews</h2>
          <div className="space-y-4">
            {reviews.map((review) => (
              <div key={review.id} className="bg-dark-card p-4 rounded-lg">
                <p className="font-semibold mb-2">{review.user?.username}</p>
                <p className="text-gray-300">{review.content}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {similar.length > 0 && (
        <section>
          <h2 className="text-2xl font-bold mb-6">Similar Movies</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {similar.map((rec) => (
              <MovieCard key={rec.movie.id} movie={rec.movie} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

export default MovieDetail
