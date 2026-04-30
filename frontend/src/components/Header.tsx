export default function Header() {
  return (
    <header className="sticky top-0 z-50 bg-black/90 backdrop-blur-md border-b border-white/5">
      <div className="px-[4%] py-4 flex items-center justify-between">
        <span className="text-2xl font-black tracking-tighter" style={{ color: '#e50914' }}>
          MovieLens
        </span>
        <span className="text-xs text-zinc-600 uppercase tracking-[0.2em] hidden md:block">
          ISA · MovieLens Recommender
        </span>
      </div>
    </header>
  )
}
