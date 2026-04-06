export default function SampleSizeWarning({ possessions }) {
  if (!possessions || possessions >= 50) return null
  return (
    <span className="text-warning text-xs ml-2">
      ⚠ Low confidence ({possessions} poss)
    </span>
  )
}
