import { useState, useEffect, useRef } from 'react'
import { getReferenceData } from '../api/client'
import { useToast } from './Toaster'
import type { RecommendationRequest, ReferenceDataResponse, AgeCode, Gender } from '../types/api'

interface Props {
  onSubmit: (req: RecommendationRequest) => void
  loading: boolean
}

export default function ColdUserForm({ onSubmit, loading }: Props) {
  const { showToast } = useToast()
  const [refData, setRefData] = useState<ReferenceDataResponse | null>(null)
  const [refFailed, setRefFailed] = useState(false)
  const [ageCode, setAgeCode] = useState<AgeCode>(18)
  const [gender, setGender] = useState<Gender>('M')
  const [occupationCode, setOccupationCode] = useState(4)
  const [selectedGenres, setSelectedGenres] = useState<string[]>([])
  const [count, setCount] = useState(10)
  const userIdRef = useRef(crypto.randomUUID())

  useEffect(() => {
    getReferenceData()
      .then(setRefData)
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : 'Failed to load reference data'
        showToast(`Could not load form data — is the backend running? (${msg})`, 'error')
        setRefFailed(true)
      })
  }, [showToast])

  function toggleGenre(genre: string) {
    setSelectedGenres((prev) =>
      prev.includes(genre) ? prev.filter((g) => g !== genre) : [...prev, genre],
    )
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onSubmit({
      user_id: userIdRef.current,
      count,
      profile: { age_code: ageCode, gender, occupation_code: occupationCode, preferred_genres: selectedGenres },
    })
  }

  if (refFailed) {
    return (
      <div className="py-6 text-sm text-zinc-500 flex items-center gap-2">
        <span className="material-symbols-outlined" style={{ color: '#e50914', fontSize: '18px' }}>
          signal_disconnected
        </span>
        Backend is not reachable — start the backend and reload.
      </div>
    )
  }

  if (!refData) {
    return (
      <div className="py-8 flex items-center gap-2 text-zinc-500 text-sm">
        <span className="material-symbols-outlined animate-spin" style={{ fontSize: '18px' }}>
          autorenew
        </span>
        Loading reference data…
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="flex flex-col gap-2">
          <label className="text-[10px] font-black uppercase tracking-[0.15em] text-zinc-500">
            Age Range
          </label>
          <select
            value={ageCode}
            onChange={(e) => setAgeCode(Number(e.target.value) as AgeCode)}
            className="cinema-select"
          >
            {refData.age_codes.map((ac) => (
              <option key={ac.code} value={ac.code}>
                {ac.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-[10px] font-black uppercase tracking-[0.15em] text-zinc-500">
            Occupation
          </label>
          <select
            value={occupationCode}
            onChange={(e) => setOccupationCode(Number(e.target.value))}
            className="cinema-select"
          >
            {refData.occupation_codes.map((oc) => (
              <option key={oc.code} value={oc.code}>
                {oc.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <label className="text-[10px] font-black uppercase tracking-[0.15em] text-zinc-500">
          Gender
        </label>
        <div className="flex gap-6">
          {(['M', 'F'] as Gender[]).map((g) => (
            <label key={g} className="flex items-center gap-2 cursor-pointer group">
              <input
                type="radio"
                name="gender"
                value={g}
                checked={gender === g}
                onChange={() => setGender(g)}
                style={{ accentColor: '#e50914' }}
              />
              <span
                className="text-sm transition-colors"
                style={{ color: gender === g ? '#fff' : '#a1a1aa' }}
              >
                {g === 'M' ? 'Male' : 'Female'}
              </span>
            </label>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <label className="text-[10px] font-black uppercase tracking-[0.15em] text-zinc-500">
          Preferred Genres{' '}
          <span className="normal-case text-zinc-600 tracking-normal font-normal">(optional)</span>
        </label>
        <div className="flex flex-wrap gap-2">
          {refData.genres.map((genre) => {
            const selected = selectedGenres.includes(genre)
            return (
              <button
                key={genre}
                type="button"
                onClick={() => toggleGenre(genre)}
                className="px-3 py-1.5 text-xs font-bold rounded-sm transition-all duration-150"
                style={
                  selected
                    ? { backgroundColor: '#e50914', color: '#fff' }
                    : { backgroundColor: '#27272a', color: '#a1a1aa' }
                }
              >
                {genre}
              </button>
            )
          })}
        </div>
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
          className="w-full h-1 bg-zinc-800 rounded appearance-none cursor-pointer"
        />
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
