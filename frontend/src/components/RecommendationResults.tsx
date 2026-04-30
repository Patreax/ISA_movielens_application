import type { RecommendationResponse } from '../types/api'
import MovieCard from './MovieCard'
import PathBadge from './PathBadge'
import SkeletonCard from './SkeletonCard'

interface Props {
  result: RecommendationResponse | null
  loading: boolean
}

const SKELETON_COUNT = 12

export default function RecommendationResults({ result, loading }: Props) {
  return (
    <section className="px-[4%] py-20 bg-black border-t border-white/5">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-10">
        <div className="space-y-2">
          {result && (
            <div className="flex items-center gap-3 mb-1">
              <PathBadge path={result.path} />
            </div>
          )}
          <h2 className="text-4xl font-black text-white tracking-tight">
            {loading ? 'Computing…' : 'Curated For You'}
          </h2>
          {result && (
            <p className="text-zinc-500 text-sm max-w-lg leading-relaxed">
              {result.explanation}
            </p>
          )}
          {result && result.notes.length > 0 && (
            <p className="text-zinc-700 text-xs">
              {result.notes.join(' · ')}
            </p>
          )}
        </div>
        {result && (
          <span className="text-zinc-600 text-xs uppercase tracking-widest shrink-0">
            {result.count_returned} / {result.count_requested} films
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
        {loading
          ? Array.from({ length: SKELETON_COUNT }).map((_, i) => <SkeletonCard key={i} />)
          : result?.recommendations.map((movie) => (
              <MovieCard key={movie.movie_id} movie={movie} />
            ))}
      </div>
    </section>
  )
}
