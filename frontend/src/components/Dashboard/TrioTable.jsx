import { useState, useMemo } from 'react'

function DeltaVal({ value }) {
  if (value === null || value === undefined || Math.abs(value) < 0.05) return null
  const color = value <= -5 ? 'text-danger' : value <= -2 ? 'text-warning' : value >= 2 ? 'text-success' : 'text-text-secondary'
  return <span className={`${color}`}>{value > 0 ? '+' : ''}{value.toFixed(1)}</span>
}

function NetVal({ value }) {
  if (value === null || value === undefined) return <span className="text-text-secondary">—</span>
  const color = value >= 0 ? 'text-success' : 'text-danger'
  return <span className={color}>{value >= 0 ? '+' : ''}{value.toFixed(1)}</span>
}

export default function TrioTable({ trios, activeFilters, filteredData, onRowClick }) {
  const [sortKey, setSortKey] = useState('net')
  const [sortDir, setSortDir] = useState('desc')
  const hasFilters = activeFilters.length > 0

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const sorted = useMemo(() => {
    return [...trios].sort((a, b) => {
      const av = _getBaseValue(a, sortKey)
      const bv = _getBaseValue(b, sortKey)
      const diff = (bv ?? -9999) - (av ?? -9999)
      return sortDir === 'desc' ? diff : -diff
    })
  }, [trios, sortKey, sortDir])

  if (!trios.length) {
    return <div className="text-text-secondary text-center py-16">No trios found.</div>
  }

  const SortHeader = ({ colKey, label, align = 'right' }) => (
    <th
      className={`px-4 py-2.5 whitespace-nowrap cursor-pointer hover:text-gold select-none ${align === 'right' ? 'text-right' : 'text-left'}`}
      onClick={() => handleSort(colKey)}
    >
      {label}
      {sortKey === colKey && (
        <span className="ml-1 text-gold text-[10px]">{sortDir === 'desc' ? '▼' : '▲'}</span>
      )}
    </th>
  )

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <table className="w-full text-sm text-white table-fixed">
        <colgroup>
          <col className="w-[280px]" />
          <col className="w-[70px]" />
          <col className="w-[70px]" />
          {hasFilters && <col className="w-[70px]" />}
          <col className="w-[70px]" />
          {hasFilters && <col className="w-[70px]" />}
          <col className="w-[80px]" />
          {hasFilters && <col className="w-[70px]" />}
        </colgroup>
        <thead>
          <tr className="bg-sidebar text-text-secondary text-xs uppercase tracking-wider border-b border-border">
            <th className="px-4 py-2.5 text-left">Trio</th>
            <SortHeader colKey="poss" label="Poss" />
            <SortHeader colKey="ortg" label="ORtg" />
            {hasFilters && <th className="px-4 py-2.5 text-right text-gold text-[10px]">Δ</th>}
            <SortHeader colKey="drtg" label="DRtg" />
            {hasFilters && <th className="px-4 py-2.5 text-right text-gold text-[10px]">Δ</th>}
            <SortHeader colKey="net" label="Net" />
            {hasFilters && <th className="px-4 py-2.5 text-right text-gold text-[10px]">Δ</th>}
          </tr>
        </thead>
        {sorted.map(trio => {
          const base = trio.baseline || {}
          const filt = filteredData?.[trio.trio_key]?.filtered || null
          const delta = filteredData?.[trio.trio_key]?.delta || null
          const lowConf = filt && filt.possessions < 50

          return (
            <tbody key={trio.trio_key}>
              <tr
                className={`border-b border-border hover:bg-card/60 cursor-pointer transition-colors ${lowConf ? 'opacity-50' : ''}`}
                onClick={() => onRowClick(trio)}
              >
                <td className="px-4 py-3 truncate">
                  <span className="font-medium">
                    {_formatTrioNames(trio.players)}
                  </span>
                </td>

                {hasFilters && !filt ? (
                  <>
                    <td className="px-4 py-3 text-right text-text-secondary" colSpan={hasFilters ? 7 : 4}>
                      0 possessions
                    </td>
                  </>
                ) : (
                  <>
                    <td className="px-4 py-3 text-right tabular-nums text-text-secondary">
                      {hasFilters && filt ? filt.possessions : base.possessions}
                    </td>

                    <td className="px-4 py-3 text-right tabular-nums">
                      {(hasFilters && filt ? filt.ortg : base.ortg)?.toFixed(1) ?? '—'}
                    </td>
                    {hasFilters && (
                      <td className="px-4 py-3 text-right tabular-nums text-xs">
                        <DeltaVal value={delta?.ortg} />
                      </td>
                    )}

                    <td className="px-4 py-3 text-right tabular-nums">
                      {(hasFilters && filt ? filt.drtg : base.drtg)?.toFixed(1) ?? '—'}
                    </td>
                    {hasFilters && (
                      <td className="px-4 py-3 text-right tabular-nums text-xs">
                        <DeltaVal value={delta?.drtg} />
                      </td>
                    )}

                    <td className="px-4 py-3 text-right tabular-nums font-semibold">
                      <NetVal value={hasFilters && filt ? filt.net : base.net} />
                    </td>
                    {hasFilters && (
                      <td className="px-4 py-3 text-right tabular-nums text-xs">
                        <DeltaVal value={delta?.net} />
                      </td>
                    )}
                  </>
                )}
              </tr>

            </tbody>
          )
        })}
      </table>
    </div>
  )
}

const SUFFIXES = new Set(['Jr.', 'Jr', 'Sr.', 'Sr', 'II', 'III', 'IV'])

function _getLastName(fullName) {
  const parts = fullName.split(' ')
  if (parts.length >= 3 && SUFFIXES.has(parts[parts.length - 1])) {
    return parts[parts.length - 2] + ' ' + parts[parts.length - 1]
  }
  return parts[parts.length - 1]
}

function _formatTrioNames(players) {
  const lastNames = players.map(p => _getLastName(p.name))
  const counts = {}
  lastNames.forEach(ln => { counts[ln] = (counts[ln] || 0) + 1 })
  return players.map(p => {
    const last = _getLastName(p.name)
    if (counts[last] > 1) {
      const first = p.name.split(' ')[0]
      return `${first[0]}. ${last}`
    }
    return last
  }).join(' / ')
}

function _getBaseValue(trio, key) {
  const base = trio.baseline || {}
  switch (key) {
    case 'poss': return base.possessions ?? 0
    case 'ortg': return base.ortg ?? 0
    case 'drtg': return base.drtg ?? 0
    case 'net':  return base.net ?? 0
    default:     return 0
  }
}
