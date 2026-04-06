import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ReferenceLine,
  ResponsiveContainer, Cell,
} from 'recharts'

const FILTER_LABELS = {
  baseline: 'Baseline',
  big: 'Wall', shooters: 'Shooters', smallball: 'Small Ball',
}

function barColor(net, baseline) {
  if (net === null || net === undefined) return '#2A2A3E'
  const delta = net - baseline
  if (delta <= -5) return '#E53935'
  if (delta <= -2) return '#FFB300'
  return '#43A047'
}

export default function DeltaBarChart({ baseline, allFilters }) {
  if (!baseline?.net) return null

  const data = [
    { key: 'baseline', label: 'Baseline', net: baseline.net },
    ...Object.entries(allFilters || {})
      .filter(([key]) => key in FILTER_LABELS)
      .map(([key, val]) => ({
        key,
        label: FILTER_LABELS[key],
        net: val?.stats?.net ?? null,
      })),
  ]

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 80, right: 20 }}>
          <XAxis type="number" tick={{ fill: '#A0A0B0', fontSize: 11 }} />
          <YAxis
            type="category"
            dataKey="label"
            tick={{ fill: '#A0A0B0', fontSize: 11 }}
            width={80}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const d = payload[0].payload
              const poss = allFilters?.[d.key]?.stats?.possessions ?? baseline.possessions
              return (
                <div className="bg-sidebar border border-border rounded-lg px-3 py-2 text-sm">
                  <div className="text-text-secondary font-medium">{d.label}</div>
                  <div className="text-white mt-1">Net Rtg: <span className="font-bold">{d.net?.toFixed(1) ?? '—'}</span></div>
                  <div className="text-text-secondary text-xs mt-0.5">{poss} possessions</div>
                </div>
              )
            }}
          />
          <ReferenceLine x={baseline.net} stroke="#FDB927" strokeDasharray="4 2" />
          <Bar dataKey="net" radius={[0, 4, 4, 0]}>
            {data.map(entry => (
              <Cell key={entry.key} fill={barColor(entry.net, baseline.net)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
