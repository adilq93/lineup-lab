import { useEffect, useState } from 'react'
import { getFreshness } from '../../api/client'

export default function TopBar({ onAbout }) {
  const [freshness, setFreshness] = useState(null)

  useEffect(() => {
    getFreshness().then(setFreshness).catch(() => {})
  }, [])

  const staleness = freshness?.ingested_at
    ? Math.floor((Date.now() - new Date(freshness.ingested_at)) / 3600000)
    : null

  const isStale = staleness !== null && staleness > 48
  const dotColor = isStale ? 'bg-warning' : 'bg-success'

  return (
    <header className="h-14 bg-sidebar border-b border-border flex items-center justify-between px-6 shrink-0">
      <span className="text-gold font-bold tracking-widest text-sm uppercase">
        Lineup Lab
      </span>
      <div className="flex items-center gap-4">
        {freshness && (
          <div className="flex items-center gap-2 text-xs text-text-secondary">
            <span className={`w-2 h-2 rounded-full ${dotColor}`} />
            {freshness.last_game_date
              ? `Data through ${freshness.last_game_date}`
              : 'No data yet'}
            {staleness !== null && ` · Updated ${staleness}h ago`}
          </div>
        )}
        <button
          onClick={onAbout}
          className="text-xs text-text-secondary hover:text-gold transition-colors"
        >
          About
        </button>
      </div>
    </header>
  )
}
