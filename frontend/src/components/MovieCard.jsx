import { Link } from 'react-router-dom'

function MovieCard({ movie, showExplanation = false, explanation = '' }) {
  const posterUrl = movie.poster_path
    ? `https://image.tmdb.org/t/p/w500${movie.poster_path}`
    : 'https://via.placeholder.com/500x750?text=No+Poster'

  return (
    <div className="group relative">
      <Link to={`/movie/${movie.id}`} className="block">
        <div className="aspect-[2/3] rounded-lg overflow-hidden shadow-lg bg-dark-card">
          <img
            src={posterUrl}
            alt={movie.title}
            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        </div>
        <div className="mt-2">
          <h3 className="font-semibold truncate">{movie.title}</h3>
          <p className="text-sm text-gray-400">{movie.year}</p>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-yellow-400">★</span>
            <span className="text-sm">{movie.vote_average?.toFixed(1)}</span>
          </div>
        </div>
        {showExplanation && explanation && (
          <div className="mt-2 p-2 bg-dark-card rounded text-xs text-gray-300 line-clamp-2">
            {explanation}
          </div>
        )}
      </Link>
    </div>
  )
}

export default MovieCard
