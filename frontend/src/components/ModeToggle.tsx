type Mode = 'warm' | 'cold'

interface Props {
  mode: Mode
  onChange: (mode: Mode) => void
}

export default function ModeToggle({ mode, onChange }: Props) {
  return (
    <div className="inline-flex bg-zinc-900 border border-white/10 rounded p-1 mb-6">
      <button
        onClick={() => onChange('warm')}
        className="px-6 py-2.5 text-sm font-bold rounded-sm transition-all duration-200"
        style={mode === 'warm' ? { backgroundColor: '#e50914', color: '#fff' } : { color: '#a1a1aa' }}
      >
        Existing User
      </button>
      <button
        onClick={() => onChange('cold')}
        className="px-6 py-2.5 text-sm font-bold rounded-sm transition-all duration-200"
        style={mode === 'cold' ? { backgroundColor: '#e50914', color: '#fff' } : { color: '#a1a1aa' }}
      >
        New User
      </button>
    </div>
  )
}
