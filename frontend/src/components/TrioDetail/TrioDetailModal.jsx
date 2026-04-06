import { useEffect, useState } from 'react'
import { getTrioDetail } from '../../api/client'
import DeltaBarChart from './DeltaBarChart'
import CounterLineup from './CounterLineup'
import ClutchNote from './ClutchNote'

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

export default function TrioDetailModal({ trio, teamId, activeFilters, onClose }) {
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!trio) return
    setLoading(true)
    getTrioDetail(trio.trio_key, teamId, activeFilters)
      .then(setDetail)
      .finally(() => setLoading(false))
  }, [trio?.trio_key])

  if (!trio) return null

  const trioName = _formatTrioNames(trio.players)

  return (
    <div
      className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-card border border-border rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-border">
          <div>
            <h2 className="text-lg font-bold text-white">{trioName}</h2>
            <p className="text-xs text-text-secondary mt-0.5">
              {trio.players.map(p => p.name).join(', ')}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-text-secondary hover:text-white text-xl leading-none ml-4"
          >
            ✕
          </button>
        </div>

        <div className="p-6 space-y-6">
          {loading ? (
            <div className="text-text-secondary text-center py-8">Loading...</div>
          ) : detail ? (
            <>
              <DeltaBarChart
                baseline={detail.baseline}
                allFilters={detail.all_filters}
              />
              <CounterLineup counter={detail.counter} />
              <ClutchNote baseline={detail.baseline} clutchStats={detail.all_filters?.clutch} />
            </>
          ) : (
            <div className="text-text-secondary text-center py-8">No data available.</div>
          )}
        </div>
      </div>
    </div>
  )
}
