import { useState } from 'react'
import Header from './components/Header'
import ModeToggle from './components/ModeToggle'
import WarmUserForm from './components/WarmUserForm'
import ColdUserForm from './components/ColdUserForm'
import RecommendationResults from './components/RecommendationResults'
import { postRecommendations } from './api/client'
import { useToast } from './components/Toaster'
import type { RecommendationResponse, RecommendationRequest } from './types/api'

type Mode = 'warm' | 'cold'

export default function App() {
  const { showToast } = useToast()
  const [mode, setMode] = useState<Mode>('warm')
  const [result, setResult] = useState<RecommendationResponse | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(req: RecommendationRequest) {
    setLoading(true)
    setResult(null)
    try {
      const data = await postRecommendations(req)
      setResult(data)
      setTimeout(() => {
        document.getElementById('results')?.scrollIntoView({ behavior: 'smooth' })
      }, 100)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      showToast(msg, 'error')
    } finally {
      setLoading(false)
    }
  }

  function handleModeChange(newMode: Mode) {
    setMode(newMode)
    setResult(null)
  }

  return (
    <div className="min-h-screen bg-black">
      <Header />
      <section className="relative min-h-[580px] flex flex-col justify-center px-[4%] py-24 overflow-hidden">
        {/* Cinematic scan-line background */}
        <div className="absolute inset-0 z-0 bg-gradient-to-b from-zinc-900/40 to-black" />
        <div
          className="absolute inset-0 z-0"
          style={{
            backgroundImage:
              'repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(255,255,255,0.012) 3px, rgba(255,255,255,0.012) 4px)',
          }}
        />

        <div className="relative z-10 max-w-3xl">
          <p
            className="text-xs font-black uppercase tracking-[0.3em] mb-4"
            style={{ color: '#e50914' }}
          >
            ISA · MovieLens-1M
          </p>
          <h1 className="text-5xl md:text-7xl font-black tracking-tight text-white mb-4 leading-none">
            Movie<br />Recommender
          </h1>
          <p className="text-lg text-zinc-400 mb-10 max-w-xl leading-relaxed">
            SVD collaborative filtering for existing users. KMeans cluster matching for new ones.
          </p>

          <ModeToggle mode={mode} onChange={handleModeChange} />

          <div className="glass-card rounded-xl p-8 max-w-2xl shadow-2xl">
            {mode === 'warm' ? (
              <WarmUserForm onSubmit={handleSubmit} loading={loading} />
            ) : (
              <ColdUserForm onSubmit={handleSubmit} loading={loading} />
            )}
          </div>
        </div>
      </section>

      {(result !== null || loading) && (
        <div id="results">
          <RecommendationResults result={result} loading={loading} />
        </div>
      )}

      <footer className="border-t border-zinc-900 py-10 px-[4%] text-center">
        <p className="text-zinc-700 text-xs tracking-widest uppercase">
           2025 ISA Project · MovieLens-1M Dataset
        </p>
      </footer>
    </div>
  )
}
