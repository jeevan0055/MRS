import { useState, useEffect } from 'react'
import axios from '../api/axios'
import MovieCard from '../components/MovieCard'
import { useAuth } from '../context/AuthContext'

function Profile() {
  const [favorites, setFavorites] = useState([])
  const [watchHistory, setWatchHistory] = useState([])
  const { user } = useAuth()

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [favRes, histRes] = await Promise.all([
          axios.get('/favorites'),
          axios.get('/watch-history'),
        ])
        setFavorites(favRes.data)
        setWatchHistory(histRes.data)
      } catch (err) {
        console.error(err)
      }
    }
    fetchData()
  }, [])

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <h1 className="text-3xl font-bold mb-8">Your Profile</h1>
      <div className="mb-8 p-6 bg-dark-card rounded-lg">
        <h2 className="text-xl font-semibold mb-2">{user?.username}</h2>
        <p className="text-gray-400">{user?.email}</p>
      </div>

      {favorites.length > 0 && (
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-6">Your Favorites</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {favorites.map((fav) => (
              <MovieCard key={fav.id} movie={fav.movie} />
            ))}
          </div>
        </section>
      )}

      {watchHistory.length > 0 && (
        <section>
          <h2 className="text-2xl font-bold mb-6">Watch History</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {watchHistory.map((item) => (
              <MovieCard key={item.id} movie={item.movie} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

export default Profile
