import { useState, useEffect } from 'react'
import axios from '../api/axios'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'

function Analytics() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axios.get('/analytics')
        setData(res.data)
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="animate-pulse space-y-8">
          <div className="h-8 bg-gray-800 rounded w-48"></div>
          <div className="h-64 bg-gray-800 rounded"></div>
          <div className="h-64 bg-gray-800 rounded"></div>
        </div>
      </div>
    )
  }

  if (!data) return <div className="text-center py-12">No data available</div>

  const genreData = Object.entries(data.genre_distribution || {}).map(([name, count]) => ({
    name,
    count,
  }))

  const ratingData = Object.entries(data.rating_distribution || {}).map(([rating, count]) => ({
    rating: `${rating}★`,
    count,
  }))

  const COLORS = ['#E50914', '#ff7300', '#ffbb28', '#36CBCB', '#414e80', '#8884d8', '#82ca9d']

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <h1 className="text-3xl font-bold mb-8">Analytics Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <div className="bg-dark-card p-6 rounded-lg">
          <h3 className="text-gray-400 text-sm mb-2">Total Users</h3>
          <p className="text-4xl font-bold">{data.total_users}</p>
        </div>
        <div className="bg-dark-card p-6 rounded-lg">
          <h3 className="text-gray-400 text-sm mb-2">Total Movies</h3>
          <p className="text-4xl font-bold">{data.total_movies}</p>
        </div>
        <div className="bg-dark-card p-6 rounded-lg">
          <h3 className="text-gray-400 text-sm mb-2">Total Ratings</h3>
          <p className="text-4xl font-bold">{data.total_ratings}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
        <div className="bg-dark-card p-6 rounded-lg">
          <h2 className="text-xl font-semibold mb-6">Genre Distribution</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={genreData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="count"
              >
                {genreData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-dark-card p-6 rounded-lg">
          <h2 className="text-xl font-semibold mb-6">Rating Distribution</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={ratingData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="rating" stroke="#888" />
              <YAxis stroke="#888" />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f1f1f', border: '1px solid #333' }}
              />
              <Bar dataKey="count" fill="#E50914" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {data.top_rated_movies?.length > 0 && (
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-6">Top Rated Movies</h2>
          <div className="space-y-3">
            {data.top_rated_movies.map((movie, index) => (
              <div key={movie.id} className="flex items-center gap-4 p-4 bg-dark-card rounded">
                <span className="text-2xl font-bold text-netflix-red">#{index + 1}</span>
                <div className="flex-1">
                  <h3 className="font-semibold">{movie.title}</h3>
                  <p className="text-sm text-gray-400">{movie.genres}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-yellow-400">★</span>
                  <span className="font-semibold">{movie.vote_average?.toFixed(1)}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

export default Analytics
