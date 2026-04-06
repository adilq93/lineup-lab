export default function AboutModal({ onClose }) {
  return (
    <div
      className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-card border border-border rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="p-8 space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gold tracking-tight">LINEUP LAB</h1>
              <p className="text-text-secondary text-sm mt-1">
                A tactical scouting tool. Built for the Lakers.
              </p>
            </div>
            <button onClick={onClose} className="text-text-secondary hover:text-white text-xl">
              ✕
            </button>
          </div>

          {/* Straight talk */}
          <section>
            <p className="text-sm text-white leading-relaxed">
              I built this because I want the Software Developer role in Basketball Data Strategy.
              Not as a homework assignment — because this is the kind of tool I'd want to build
              on day one. Playoff prep starts with a question:{' '}
              <span className="text-gold italic">
                "Where does this lineup break?"
              </span>
              {' '}This answers it.
            </p>
          </section>

          {/* What it does */}
          <section>
            <h2 className="text-sm font-semibold text-gold uppercase tracking-wider mb-2">
              What It Does
            </h2>
            <p className="text-sm text-text-secondary leading-relaxed">
              Lineup Lab analyzes every 3-man combination for 5 Western Conference opponents.
              It computes offensive and defensive ratings across 200k+ play-by-play events,
              then slices those ratings by matchup context — big lineups, shooting lineups,
              small-ball, and clutch situations. The delta between baseline and filtered
              performance is the scouting insight: which trios collapse under specific pressure,
              and what archetype to deploy against them.
            </p>
          </section>

          {/* Stack — mapped to JD */}
          <section>
            <h2 className="text-sm font-semibold text-gold uppercase tracking-wider mb-2">
              How It's Built
            </h2>
            <div className="space-y-2 text-sm text-text-secondary leading-relaxed">
              <div>
                <span className="text-white font-medium">Frontend:</span> React with component-based
                architecture, Tailwind CSS, Recharts for visualization. Scalable UI patterns —
                the filter system, table, and modal are all composable and reusable.
              </div>
              <div>
                <span className="text-white font-medium">Backend:</span> Django REST Framework
                serving pre-computed stats via RESTful endpoints. PostgreSQL with JSONB lineup
                columns, GIN indexes, and boolean flag indexing for sub-second query performance
                across 200k events.
              </div>
              <div>
                <span className="text-white font-medium">Data pipeline:</span> 4-stage ingestion
                (rosters → games → play-by-play → lineup reconstruction) with raw JSON caching,
                rate limiting, and idempotent commands. Box score starters for 100% lineup
                confidence. Trio stats pre-computed and materialized for instant reads.
              </div>
              <div>
                <span className="text-white font-medium">Methodology:</span> Hollinger possession
                formula (same as Basketball Reference). Absolute lineup flags for both offensive
                and defensive filtering. 300-possession minimum to filter noise.
              </div>
            </div>
          </section>

          {/* Why me */}
          <section>
            <h2 className="text-sm font-semibold text-gold uppercase tracking-wider mb-2">
              Why This Matters
            </h2>
            <p className="text-sm text-text-secondary leading-relaxed">
              The job posting says "self-starter mentality with the ability to translate questions
              into actionable projects." This is that. I didn't wait to be asked. I saw the role,
              understood the problem space, and built the tool. The same approach I'd bring to
              Player Profiles, Scouting Reports, and whatever the coaching staff needs next.
            </p>
            <p className="text-sm text-text-secondary leading-relaxed mt-2">
              I'm not just a developer who can write code. I understand why a scout cares about
              Net Rating delta against a two-big lineup in clutch minutes. That intersection —
              basketball IQ and engineering depth — is what I bring.
            </p>
          </section>

          {/* Filters */}
          <section>
            <h2 className="text-sm font-semibold text-gold uppercase tracking-wider mb-2">
              Filter Definitions
            </h2>
            <div className="grid grid-cols-2 gap-2 text-sm">
              {[
                ['Wall', 'Opponent has 2+ players 6\'10" or taller'],
                ['Shooters', 'Opponent has 3+ players shooting 35%+ from 3 (min 82 attempts)'],
                ['Small Ball', 'No opponent player 6\'9" or taller on the floor'],
                ['Clutch', 'Last 5 min of 4Q/OT, score within 5 pts (NBA official)'],
              ].map(([name, desc]) => (
                <div key={name} className="bg-sidebar rounded-lg p-3">
                  <div className="text-white font-medium">{name}</div>
                  <div className="text-text-secondary text-xs mt-0.5">{desc}</div>
                </div>
              ))}
            </div>
          </section>

          {/* Attribution */}
          <section className="border-t border-border pt-4">
            <p className="text-sm text-white font-medium">
              Adil Qaisar
            </p>
            <div className="flex gap-4 mt-2">
              <a
                href="https://www.linkedin.com/in/adil-qaisar-751a36138/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-gold hover:underline"
              >
                LinkedIn
              </a>
              <a
                href="https://github.com/adilq93"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-gold hover:underline"
              >
                GitHub
              </a>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
