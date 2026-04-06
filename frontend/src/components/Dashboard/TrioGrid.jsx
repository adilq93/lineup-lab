import TrioCard from './TrioCard'

export default function TrioGrid({ trios, activeFilters, filteredData, onCardClick }) {
  if (!trios.length) {
    return (
      <div className="text-text-secondary text-center py-16">
        No trios found.
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
      {trios.map(trio => (
        <TrioCard
          key={trio.trio_key}
          trio={trio}
          activeFilters={activeFilters}
          filteredStats={filteredData?.[trio.trio_key]}
          onClick={() => onCardClick(trio)}
        />
      ))}
    </div>
  )
}
