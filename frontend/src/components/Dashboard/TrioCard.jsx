import { useState } from 'react'

const FILTER_LABELS = {
  big: 'Wall', shooters: 'Shooters', smallball: 'Small Ball',
  clutch: 'Clutch', fast: 'Track Meet', slow: 'Grind',
}

function Headshot({ playerId, name }) {
  const [errored, setErrored] = useState(false)
  const url = `https://cdn.nba.com/headshots/nba/latest/260x190/${playerId}.png`

  return errored ? (
    <div className="w-10 h-10 rounded-full bg-border flex items-center justify-center text-xs text-text-secondary font-bold">
      {name?.[0] ?? '?'}
    </div>
  ) : (
    <img
      src={url}
      alt={name}
      onError={() => setErrored(true)}
      className="w-10 h-10 rounded-full object-cover bg-border"
    />
  )
}

export default function TrioCard({ trio, activeFilters, filteredStats, onClick }) {
  const net = trio.baseline?.net
  const netColor = net >= 0 ? 'text-success' : 'text-danger'

  // Best delta across active filters
  const delta = filteredStats?.delta?.net
  const deltaColor = delta < -5 ? 'text-danger' : delta < -2 ? 'text-warning' : 'text-success'
  const deltaLabel = activeFilters.length === 1
    ? FILTER_LABELS[activeFilters[0]]
    : activeFilters.length > 1 ? 'Combo' : null

  return (
    <button
      onClick={onClick}
      className="bg-card border border-border rounded-xl p-4 text-left hover:border-gold transition-colors relative"
    >
      {/* Headshots */}
      <div className="flex gap-1 mb-3">
        {trio.players.map(p => (
          <Headshot key={p.player_id} playerId={p.player_id} name={p.name} />
        ))}
      </div>

      {/* Names */}
      <div className="flex gap-1 flex-wrap mb-3">
        {trio.players.map(p => (
          <span key={p.player_id} className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
            {p.name.split(' ').slice(-1)[0]}
          </span>
        ))}
      </div>

      {/* Net Rating */}
      <div className={`text-2xl font-bold ${netColor}`}>
        {net >= 0 ? '+' : ''}{net?.toFixed(1) ?? '—'}
      </div>
      <div className="text-xs text-text-secondary mt-0.5">
        {trio.baseline?.possessions?.toLocaleString()} poss
      </div>

      {/* Delta badge */}
      {delta !== undefined && delta !== null && deltaLabel && (
        <div className={`absolute bottom-3 right-3 text-xs font-bold ${deltaColor}`}>
          vs. {deltaLabel}: {delta > 0 ? '+' : ''}{delta.toFixed(1)}
        </div>
      )}
    </button>
  )
}
