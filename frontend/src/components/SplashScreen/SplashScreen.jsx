import { useNavigate } from 'react-router-dom'

const TEAMS = [
  { id: 1610612743, name: 'Denver Nuggets',           abbr: 'DEN', color: '#4fa3e0' },
  { id: 1610612760, name: 'OKC Thunder',              abbr: 'OKC', color: '#007ac1' },
  { id: 1610612759, name: 'San Antonio Spurs',        abbr: 'SAS', color: '#c4ced4' },
  { id: 1610612750, name: 'Minnesota Timberwolves',   abbr: 'MIN', color: '#236192' },
  { id: 1610612745, name: 'Houston Rockets',          abbr: 'HOU', color: '#ce1141' },
]

export default function SplashScreen({ onAbout }) {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-bg flex flex-col items-center justify-center px-6">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gold tracking-tight mb-2">
          LINEUP LAB
        </h1>
        <p className="text-text-secondary text-lg">
          3-man lineup analysis for playoff preparation.
        </p>
      </div>

      <div className="flex flex-wrap justify-center gap-4 max-w-3xl">
        {TEAMS.map(team => (
          <button
            key={team.id}
            onClick={() => navigate(`/team/${team.id}`)}
            className="bg-card border border-border rounded-xl px-8 py-6 flex flex-col items-center gap-2 hover:border-gold transition-colors cursor-pointer"
            style={{ borderTopColor: team.color, borderTopWidth: 3 }}
          >
            <span className="text-2xl font-bold text-white">{team.abbr}</span>
            <span className="text-text-secondary text-sm text-center">{team.name}</span>
          </button>
        ))}
      </div>

      <button
        onClick={onAbout}
        className="mt-10 text-sm text-text-secondary hover:text-gold transition-colors"
      >
        About this project
      </button>
    </div>
  )
}
