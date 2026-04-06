export default function SearchInput({ value, onChange }) {
  return (
    <input
      type="text"
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder="Search by player name..."
      className="w-full bg-card border border-border rounded-lg px-4 py-2.5 text-sm text-white placeholder-text-secondary focus:outline-none focus:border-gold"
    />
  )
}
