import SampleSizeWarning from './SampleSizeWarning'

const FILTER_LABELS = {
  big: 'vs. Wall', shooters: 'vs. Shooters', smallball: 'vs. Small Ball',
  clutch: 'vs. Clutch', fast: 'vs. Track Meet', slow: 'vs. Grind',
}

function DeltaCell({ delta }) {
  if (delta === null || delta === undefined) return <td className="px-4 py-2 text-text-secondary">—</td>
  const color = delta <= -5 ? 'text-danger' : delta <= -2 ? 'text-warning' : 'text-success'
  const arrow = delta > 0 ? '▲' : '▼'
  return (
    <td className={`px-4 py-2 font-semibold ${color}`}>
      {delta > 0 ? '+' : ''}{delta.toFixed(1)} {arrow}
    </td>
  )
}

function StatCell({ value, lowConf }) {
  if (value === null || value === undefined) return <td className={`px-4 py-2 ${lowConf ? 'opacity-40' : ''}`}>—</td>
  return (
    <td className={`px-4 py-2 ${lowConf ? 'opacity-40' : ''}`}>
      {value > 0 && value < 200 ? value.toFixed(1) : value}
    </td>
  )
}

export default function MetricsTable({ baseline, allFilters, activeFilters }) {
  // Show active filter columns if any, else all 6
  const filterKeys = activeFilters?.length
    ? activeFilters
    : Object.keys(allFilters || {})

  const metrics = ['ortg', 'drtg', 'net']
  const metricLabels = { ortg: 'ORtg', drtg: 'DRtg', net: 'Net Rating' }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-white border-collapse">
        <thead>
          <tr className="border-b border-border text-text-secondary">
            <th className="px-4 py-2 text-left">Metric</th>
            <th className="px-4 py-2">Baseline</th>
            {filterKeys.map(key => (
              <th key={key} className="px-4 py-2">{FILTER_LABELS[key]}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {metrics.map(metric => (
            <tr key={metric} className="border-b border-border">
              <td className="px-4 py-2 font-medium text-text-secondary">{metricLabels[metric]}</td>
              <StatCell value={baseline?.[metric]} />
              {filterKeys.map(key => {
                const fData = allFilters?.[key]
                const lowConf = fData?.stats?.low_confidence
                return (
                  <td key={key} className="px-4 py-2 text-center">
                    <div className={`inline-flex items-center ${lowConf ? 'opacity-40' : ''}`}>
                      <span>{fData?.stats ? (fData.stats[metric]?.toFixed(1) ?? '—') : '0 poss'}</span>
                      {fData?.stats && <SampleSizeWarning possessions={fData.stats.possessions} />}
                    </div>
                  </td>
                )
              })}
            </tr>
          ))}
          <tr className="border-b border-border text-text-secondary text-xs">
            <td className="px-4 py-2">Possessions</td>
            <td className="px-4 py-2 text-center">{baseline?.possessions?.toLocaleString()}</td>
            {filterKeys.map(key => (
              <td key={key} className="px-4 py-2 text-center">
                {allFilters?.[key]?.stats?.possessions?.toLocaleString() ?? '—'}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  )
}
