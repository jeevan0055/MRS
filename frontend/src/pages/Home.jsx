import { useState, useEffect } from 'react'
import MovieCard from '../components/MovieCard'
import axios from '../api/axios'
import { useAuth } from '../context/AuthContext'

function Home() {
  const [trending, setTrending] = useState([])
  const [topRated, setTopRated] = useState([])
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(true)
  const { user } = useAuth()

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [trendingRes, recRes] = await Promise.all([
          axios.get('/trending'),
          axios.get(`/recommend/${user?.id || 1}`),
        ])
        setTrending(trendingRes.data)
        setRecommendations(recRes.data)

        const moviesRes = await axios.get('/movies?sort_by=rating&limit=10')
        setTopRated(moviesRes.data)
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [user?.id])

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="animate-pulse space-y-8">
          <div className="h-8 bg-gray-800 rounded w-48"></div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="aspect-[2/3] bg-gray-800 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {recommendations.length > 0 && (
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-6">For You</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {recommendations.map((rec) => (
              <MovieCard
                key={rec.movie.id}
                movie={rec.movie}
                showExplanation
                explanation={rec.explanation}
              />
            ))}
          </div>
        </section>
      )}

      <section className="mb-12">
        <h2 className="text-2xl font-bold mb-6">Trending Now</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {trending.map((movie) => (
            <MovieCard key={movie.id} movie={movie} />
          ))}
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold mb-6">Top Rated</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {topRated.map((movie) => (
            <MovieCard key={movie.id} movie={movie} />
          ))}
        </div>
      </section>
    </div>
  )
}

export default Home
