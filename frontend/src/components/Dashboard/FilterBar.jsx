const FILTERS = [
  { key: 'big',       label: 'Wall',       desc: 'Opp. has 2+ players 6\'10" or taller' },
  { key: 'shooters',  label: 'Shooters',   desc: 'Opp. has 3+ players shooting 35%+ from 3' },
  { key: 'smallball', label: 'Small Ball', desc: 'No opp. player 6\'9" or taller' },
]

export default function FilterBar({ activeFilters, onChange }) {
  const toggle = (key) => {
    if (activeFilters.includes(key)) {
      onChange(activeFilters.filter(f => f !== key))
    } else {
      onChange([...activeFilters, key])
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => onChange([])}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            activeFilters.length === 0
              ? 'bg-gold text-black'
              : 'bg-chip-inactive text-text-secondary hover:text-white'
          }`}
        >
          Baseline
        </button>
        {FILTERS.map(f => (
          <button
            key={f.key}
            onClick={() => toggle(f.key)}
            title={f.desc}
            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
              activeFilters.includes(f.key)
                ? 'bg-gold text-black'
                : 'bg-chip-inactive text-text-secondary hover:text-white'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>
      {activeFilters.length > 0 && (
        <div className="text-xs text-text-secondary">
          {activeFilters.map(k => FILTERS.find(f => f.key === k)?.desc).filter(Boolean).join(' + ')}
        </div>
      )}
    </div>
  )
}
