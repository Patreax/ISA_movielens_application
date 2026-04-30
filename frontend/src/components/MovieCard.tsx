import { useState } from 'react'
import type { MovieRecommendation } from '../types/api'

interface Props {
  movie: MovieRecommendation
}

export default function MovieCard({ movie }: Props) {
  const [imgError, setImgError] = useState(false)
  const matchPct = Math.min(Math.round((movie.score / 5) * 100), 100)
  const imgSrc = `https://picsum.photos/seed/${movie.movie_id}/300/450`

  return (
    <div className="group relative cursor-pointer overflow-hidden rounded-sm" style={{ aspectRatio: '2/3' }}>
      {/* Poster image */}
      {!imgError ? (
        <img
          src={imgSrc}
          alt={movie.title}
          onError={() => setImgError(true)}
          className="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
        />
      ) : (
        <div className="absolute inset-0 transition-transform duration-500 group-hover:scale-105 bg-zinc-800" />
      )}

      {/* Rank badge */}
      <div
        className="absolute top-2 left-2 z-20 w-8 h-8 bg-black/80 flex items-center justify-center border border-white/20 font-black text-base italic"
        style={{ color: '#e50914' }}
      >
        {movie.rank}
      </div>

      {/* Always-visible title (fades on hover) */}
      <div className="absolute bottom-0 left-0 right-0 z-10 p-3 bg-gradient-to-t from-black/90 to-transparent transition-opacity duration-300 group-hover:opacity-0">
        <h3 className="text-white font-bold text-xs leading-tight line-clamp-2">
          {movie.title}
        </h3>
      </div>

      {/* Hover overlay */}
      <div className="absolute inset-0 z-20 flex flex-col justify-end p-4 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-t from-black via-black/70 to-transparent">
        <h3 className="text-white font-bold text-sm leading-tight mb-2 line-clamp-3">
          {movie.title}
        </h3>
        <div className="flex flex-wrap gap-1 mb-3">
          {movie.genres.slice(0, 2).map((genre) => (
            <span
              key={genre}
              className="text-[8px] px-1.5 py-0.5 text-zinc-300 uppercase font-black tracking-wider"
              style={{ background: 'rgba(255,255,255,0.1)' }}
            >
              {genre}
            </span>
          ))}
        </div>
        <div className="w-full bg-zinc-800 h-0.5 rounded-full overflow-hidden">
          <div
            className="h-full transition-all duration-700"
            style={{ width: `${matchPct}%`, backgroundColor: '#e50914' }}
          />
        </div>
        <span className="text-[10px] font-black mt-1" style={{ color: '#e50914' }}>
          {matchPct}% match
        </span>
      </div>
    </div>
  )
}
