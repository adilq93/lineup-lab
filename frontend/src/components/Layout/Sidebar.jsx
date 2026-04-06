import { useNavigate, useParams } from 'react-router-dom'

const TEAMS = [
  { id: 1610612743, name: 'Denver Nuggets',          abbr: 'DEN' },
  { id: 1610612760, name: 'OKC Thunder',             abbr: 'OKC' },
  { id: 1610612759, name: 'San Antonio Spurs',       abbr: 'SAS' },
  { id: 1610612750, name: 'Minnesota Timberwolves',  abbr: 'MIN' },
  { id: 1610612745, name: 'Houston Rockets',         abbr: 'HOU' },
]

export default function Sidebar() {
  const navigate = useNavigate()
  const { teamId } = useParams()
  const activeId = Number(teamId)

  return (
    <aside className="w-48 min-h-screen bg-sidebar border-r border-border flex flex-col pt-6 shrink-0">
      <div className="px-4 mb-6">
        <span className="text-gold font-bold text-sm tracking-widest uppercase">
          Opponents
        </span>
      </div>
      {TEAMS.map(team => (
        <button
          key={team.id}
          onClick={() => navigate(`/team/${team.id}`)}
          className={`w-full text-left px-4 py-3 text-sm transition-colors ${
            activeId === team.id
              ? 'bg-purple text-white font-semibold'
              : 'text-text-secondary hover:text-white hover:bg-card'
          }`}
        >
          <span className="font-mono mr-2 opacity-60">{team.abbr}</span>
          {team.name}
        </button>
      ))}
    </aside>
  )
}
