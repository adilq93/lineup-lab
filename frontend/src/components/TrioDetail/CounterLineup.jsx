export default function CounterLineup({ counter }) {
  if (!counter) {
    return (
      <div className="border border-border rounded-xl p-4 mt-4">
        <div className="text-text-secondary text-xs font-bold tracking-widest mb-2">
          SCOUTING NOTE
        </div>
        <div className="text-text-secondary text-sm">
          No obvious lineup mismatch for this trio. Performance is stable across all matchup contexts.
        </div>
      </div>
    )
  }

  return (
    <div className="border border-gold rounded-xl p-4 mt-4">
      <div className="text-gold text-xs font-bold tracking-widest mb-2">
        RECOMMENDED DEPLOYMENT
      </div>
      <div className="text-white font-semibold">
        Run a <span className="text-gold">{counter.archetype}</span> against this trio.
      </div>
      <div className="text-text-secondary text-sm mt-1">
        Net Rating drops from baseline to{' '}
        <span className="text-danger font-semibold">
          {counter.filtered_net > 0 ? '+' : ''}{counter.filtered_net?.toFixed(1)}
        </span>
        &nbsp;·&nbsp; Delta:{' '}
        <span className="text-danger font-semibold">{counter.delta.toFixed(1)}</span>
        &nbsp;·&nbsp; {counter.possessions} possessions
      </div>
    </div>
  )
}
