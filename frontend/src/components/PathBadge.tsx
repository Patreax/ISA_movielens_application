import type { PathValue } from '../types/api'

const PATH_CONFIG: Record<PathValue, { label: string; style: React.CSSProperties }> = {
  warm: {
    label: 'SVD Model',
    style: {
      background: 'rgba(37,99,235,0.15)',
      color: '#60a5fa',
      border: '1px solid rgba(59,130,246,0.3)',
    },
  },
  cold_request_profile: {
    label: 'Cluster Model',
    style: {
      background: 'rgba(234,88,12,0.15)',
      color: '#fb923c',
      border: '1px solid rgba(249,115,22,0.3)',
    },
  },
  cold_stored_demographics: {
    label: 'Cluster Model',
    style: {
      background: 'rgba(234,88,12,0.15)',
      color: '#fb923c',
      border: '1px solid rgba(249,115,22,0.3)',
    },
  },
  cold_fallback_genre_popular: {
    label: 'Genre Popular',
    style: {
      background: 'rgba(202,138,4,0.15)',
      color: '#facc15',
      border: '1px solid rgba(234,179,8,0.3)',
    },
  },
}

interface Props {
  path: PathValue
}

export default function PathBadge({ path }: Props) {
  const { label, style } = PATH_CONFIG[path]
  return (
    <span
      className="text-[10px] font-black px-2 py-1 rounded tracking-wider uppercase"
      style={style}
    >
      {label}
    </span>
  )
}
