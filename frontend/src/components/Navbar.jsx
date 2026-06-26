import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useState } from 'react'

function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')

  const handleSearch = (e) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery)}`)
    }
  }

  return (
    <nav className="bg-dark-card px-6 py-4 sticky top-0 z-50 shadow-lg">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <Link to="/" className="text-2xl font-bold text-netflix-red">
          CineMatch AI
        </Link>

        {user && (
          <div className="flex items-center gap-6 flex-1 max-w-md mx-8">
            <form onSubmit={handleSearch} className="w-full">
              <input
                type="text"
                placeholder="Search movies..."
                className="w-full px-4 py-2 rounded-lg bg-gray-800 border border-gray-700 focus:outline-none focus:border-netflix-red"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </form>
          </div>
        )}

        <div className="flex items-center gap-4">
          {user ? (
            <>
              <Link to="/" className="hover:text-netflix-red">Home</Link>
              <Link to="/profile" className="hover:text-netflix-red">Profile</Link>
              <Link to="/analytics" className="hover:text-netflix-red">Analytics</Link>
              <button
                onClick={logout}
                className="px-4 py-2 bg-netflix-red rounded hover:bg-red-700 transition"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="hover:text-netflix-red">Login</Link>
              <Link to="/register" className="px-4 py-2 bg-netflix-red rounded hover:bg-red-700 transition">
                Register
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}

export default Navbar
