import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import axios from '../api/axios'
import MovieCard from '../components/MovieCard'

function Search() {
  const [searchParams] = useSearchParams()
  const query = searchParams.get('q') || ''
  const [movies, setMovies] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const searchMovies = async () => {
      if (!query) {
        setLoading(false)
        return
      }
      setLoading(true)
      try {
        const res = await axios.get(`/search?q=${encodeURIComponent(query)}`)
        setMovies(res.data)
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    searchMovies()
  }, [query])

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <h1 className="text-3xl font-bold mb-8">Search Results for "{query}"</h1>
      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {[...Array(10)].map((_, i) => (
            <div key={i} className="aspect-[2/3] bg-gray-800 rounded-lg animate-pulse"></div>
          ))}
        </div>
      ) : movies.length > 0 ? (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {movies.map((movie) => (
            <MovieCard key={movie.id} movie={movie} />
          ))}
        </div>
      ) : (
        <p className="text-center text-gray-400 py-12">No movies found</p>
      )}
    </div>
  )
}

export default Search
