export default function ClutchNote({ baseline, clutchStats }) {
  if (!clutchStats?.stats) {
    return (
      <div className="border border-border rounded-xl p-4 mt-4">
        <div className="text-text-secondary text-xs font-bold tracking-widest mb-2">
          CLUTCH PERFORMANCE
        </div>
        <div className="text-text-secondary text-sm">
          Not enough clutch possessions to evaluate (last 5 min, score within 5).
        </div>
      </div>
    )
  }

  const stats = clutchStats.stats
  const baseNet = baseline?.net
  const clutchNet = stats.net
  const delta = baseNet != null && clutchNet != null ? clutchNet - baseNet : null
  const poss = stats.possessions
  const lowConf = poss < 50

  const deltaColor = delta <= -5 ? 'text-danger' : delta <= -2 ? 'text-warning' : delta >= 2 ? 'text-success' : 'text-text-secondary'

  return (
    <div className={`border border-border rounded-xl p-4 mt-4 ${lowConf ? 'opacity-60' : ''}`}>
      <div className="text-text-secondary text-xs font-bold tracking-widest mb-2">
        CLUTCH PERFORMANCE
        <span className="ml-2 font-normal normal-case tracking-normal">
          Last 5 min of 4Q/OT, score within 5
        </span>
      </div>
      <div className="flex items-baseline gap-4 text-sm">
        <div>
          <span className="text-text-secondary">Net Rtg: </span>
          <span className="text-white font-semibold">
            {clutchNet >= 0 ? '+' : ''}{clutchNet?.toFixed(1)}
          </span>
        </div>
        {delta != null && (
          <div>
            <span className="text-text-secondary">vs. baseline: </span>
            <span className={`font-semibold ${deltaColor}`}>
              {delta > 0 ? '+' : ''}{delta.toFixed(1)}
            </span>
          </div>
        )}
        <div className="text-text-secondary text-xs">
          {poss} poss{lowConf && ' — low sample'}
        </div>
      </div>
      {stats.ortg != null && stats.drtg != null && (
        <div className="flex gap-4 text-xs text-text-secondary mt-1">
          <span>ORtg: {stats.ortg.toFixed(1)}</span>
          <span>DRtg: {stats.drtg.toFixed(1)}</span>
        </div>
      )}
    </div>
  )
}
