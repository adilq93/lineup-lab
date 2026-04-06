import { useEffect, useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { getTeamTrios, getTrioDetail } from '../api/client'
import Sidebar from '../components/Layout/Sidebar'
import TopBar from '../components/Layout/TopBar'
import FilterBar from '../components/Dashboard/FilterBar'
import SearchInput from '../components/Dashboard/SearchInput'
import TrioTable from '../components/Dashboard/TrioTable'
import TrioDetailModal from '../components/TrioDetail/TrioDetailModal'

export default function TeamDashboard({ onAbout }) {
  const { teamId } = useParams()
  const teamIdNum = Number(teamId)

  const [trios, setTrios] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeFilters, setActiveFilters] = useState([])
  const [search, setSearch] = useState('')
  const [selectedTrio, setSelectedTrio] = useState(null)

  // Fetch trios when team or filters change — single request includes filtered data
  useEffect(() => {
    setLoading(true)
    setError(null)
    getTeamTrios(teamIdNum, activeFilters)
      .then(setTrios)
      .catch(() => setError('Failed to load trios. Is the Django server running?'))
      .finally(() => setLoading(false))
  }, [teamIdNum, activeFilters.join(',')])

  // Reset filters and search on team change
  useEffect(() => {
    setActiveFilters([])
    setSearch('')
    setSelectedTrio(null)
  }, [teamIdNum])

  // Client-side search filter
  const filteredTrios = useMemo(() => {
    if (!search.trim()) return trios
    const q = search.toLowerCase()
    return trios.filter(trio =>
      trio.players.some(p => p.name.toLowerCase().includes(q))
    )
  }, [trios, search])

  // Build filteredData map from inline response
  const filteredData = useMemo(() => {
    const map = {}
    for (const trio of trios) {
      if (trio.filtered) {
        map[trio.trio_key] = { filtered: trio.filtered, delta: trio.delta }
      }
    }
    return map
  }, [trios])

  return (
    <div className="flex min-h-screen bg-bg">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <TopBar onAbout={onAbout} />
        <main className="flex-1 p-6 space-y-4">
          {error ? (
            <div className="text-danger text-center py-16">{error}</div>
          ) : loading ? (
            <div className="space-y-2">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="bg-card border border-border rounded h-10 animate-pulse" />
              ))}
            </div>
          ) : (
            <>
              <SearchInput value={search} onChange={setSearch} />
              <FilterBar activeFilters={activeFilters} onChange={setActiveFilters} />
              {!filteredTrios.length ? (
                <div className="text-text-secondary text-center py-16">
                  No trios found matching your search.
                </div>
              ) : (
                <TrioTable
                  trios={filteredTrios}
                  activeFilters={activeFilters}
                  filteredData={filteredData}
                  onRowClick={setSelectedTrio}
                />
              )}
            </>
          )}
        </main>
      </div>

      {selectedTrio && (
        <TrioDetailModal
          trio={selectedTrio}
          teamId={teamIdNum}
          activeFilters={activeFilters}
          onClose={() => setSelectedTrio(null)}
        />
      )}
    </div>
  )
}
