import { useState } from 'react'
import { useToast } from './Toaster'
import type { RecommendationRequest } from '../types/api'

interface Props {
  onSubmit: (req: RecommendationRequest) => void
  loading: boolean
}

function validateUserId(raw: string): string | null {
  const s = raw.trim()
  if (!s) return 'User ID is required.'
  if (!/^\d+$/.test(s))
    return `"${s}" is not a valid User ID — enter a positive integer (e.g. 1, 42, 3000).`
  const n = Number(s)
  if (n === 0) return 'User ID must be greater than 0.'
  if (n > 6040) return `User ID ${n} is out of range — MovieLens-1M has users 1 to 6040.`
  return null
}

export default function WarmUserForm({ onSubmit, loading }: Props) {
  const { showToast } = useToast()
  const [userId, setUserId] = useState('')
  const [count, setCount] = useState(10)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const err = validateUserId(userId)
    if (err) {
      showToast(err, 'error')
      return
    }
    onSubmit({ user_id: userId.trim(), count })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="flex flex-col gap-2">
          <label className="text-[10px] font-black uppercase tracking-[0.15em] text-zinc-500">
            User ID
          </label>
          <input
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="e.g. 1"
            className="cinema-input"
          />
          <p className="text-[11px] text-zinc-600">Integer 1–6040 from MovieLens-1M</p>
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex justify-between items-center">
            <label className="text-[10px] font-black uppercase tracking-[0.15em] text-zinc-500">
              Count
            </label>
            <span className="text-sm font-black" style={{ color: '#e50914' }}>
              {count} films
            </span>
          </div>
          <input
            type="range"
            min={1}
            max={25}
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            className="w-full h-1 bg-zinc-800 rounded appearance-none cursor-pointer mt-3"
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full text-white font-black py-4 rounded-sm transition-all active:scale-[0.98] flex items-center justify-center gap-2 text-sm uppercase tracking-widest disabled:opacity-40 disabled:cursor-not-allowed"
        style={{ backgroundColor: '#e50914' }}
      >
        {loading ? (
          <>
            <span className="material-symbols-outlined animate-spin" style={{ fontSize: '18px' }}>
              autorenew
            </span>
            Computing…
          </>
        ) : (
          <>
            Get Recommendations
            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>
              play_arrow
            </span>
          </>
        )}
      </button>
    </form>
  )
}
