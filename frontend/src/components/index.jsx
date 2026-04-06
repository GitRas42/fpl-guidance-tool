import React, { useState, useEffect, useCallback } from 'react';

/* ========== Squad Tab ========== */
export function SquadTab({ data, loading, onPlayerClick }) {
  const [view, setView] = useState('cards'); // 'cards' or 'table'
  const [sortKey, setSortKey] = useState('projected_points');
  const [sortAsc, setSortAsc] = useState(false);

  if (loading) return <div className="loading-text">Loading squad...</div>;
  if (!data) return <div className="empty-state">Enter your team ID and click "Load Data" to see your squad.</div>;

  const { squad, squad_by_position, bank, points, rank, current_gw, lookahead_gw } = data;
  const gwLabel = `next ${lookahead_gw || 5} GWs`;

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  const sortedSquad = [...(squad || [])].sort((a, b) => {
    let aVal = a[sortKey], bVal = b[sortKey];
    if (typeof aVal === 'string') aVal = aVal.toLowerCase();
    if (typeof bVal === 'string') bVal = bVal.toLowerCase();
    if (aVal < bVal) return sortAsc ? -1 : 1;
    if (aVal > bVal) return sortAsc ? 1 : -1;
    return 0;
  });

  const SortIcon = ({ col }) => {
    if (sortKey !== col) return <span style={{opacity: 0.3}}> &uarr;&darr;</span>;
    return <span style={{color: 'var(--gold)'}}> {sortAsc ? '\u2191' : '\u2193'}</span>;
  };

  return (
    <div className="fade-in">
      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">GW {current_gw}</div>
          <div className="stat-label">Current Gameweek</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{points?.toLocaleString() || 0}</div>
          <div className="stat-label">Overall Points</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{rank?.toLocaleString() || '-'}</div>
          <div className="stat-label">Global Rank</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">&pound;{bank?.toFixed(1) || '0.0'}m</div>
          <div className="stat-label">In the Bank</div>
        </div>
      </div>

      {/* View Toggle */}
      <div className="view-toggle">
        <button className={`view-btn ${view === 'cards' ? 'view-active' : ''}`} onClick={() => setView('cards')}>Cards</button>
        <button className={`view-btn ${view === 'table' ? 'view-active' : ''}`} onClick={() => setView('table')}>Table</button>
      </div>

      {/* Card View */}
      {view === 'cards' && ['GK', 'DEF', 'MID', 'FWD'].map(pos => (
        <div key={pos} className="position-group">
          <h3 className="position-title">{pos === 'GK' ? 'Goalkeepers' : pos === 'DEF' ? 'Defenders' : pos === 'MID' ? 'Midfielders' : 'Forwards'}</h3>
          <div className="player-grid">
            {(squad_by_position?.[pos] || []).map(player => (
              <div key={player.player_id} className="player-card clickable" onClick={() => onPlayerClick?.(player)}>
                <div>
                  <div className="player-name">
                    {player.name}
                    {player.is_captain && <span className="captain-badge">C</span>}
                    {player.is_vice_captain && <span className="captain-badge" style={{background: '#64748b'}}>V</span>}
                    {player.squad_position > 11 && <span className="bench-badge">Bench</span>}
                  </div>
                  <div className="player-team">{player.team_name} &middot; {player.position}</div>
                  <div className="player-points">Projected: {player.projected_points} pts ({gwLabel})</div>
                </div>
                <div style={{textAlign: 'right'}}>
                  <div className="player-price">&pound;{player.price?.toFixed(1)}m</div>
                  <div className="player-points">{player.ownership}% owned</div>
                  <StatusBadge status={player.status} />
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Table View */}
      {view === 'table' && (
        <div className="table-wrapper">
          <table className="player-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('name')}>Player<SortIcon col="name" /></th>
                <th onClick={() => handleSort('position')}>Pos<SortIcon col="position" /></th>
                <th onClick={() => handleSort('team_name')}>Team<SortIcon col="team_name" /></th>
                <th onClick={() => handleSort('price')}>Price<SortIcon col="price" /></th>
                <th onClick={() => handleSort('total_points')}>Pts<SortIcon col="total_points" /></th>
                <th onClick={() => handleSort('form')}>Form<SortIcon col="form" /></th>
                <th onClick={() => handleSort('projected_points')}>Proj ({lookahead_gw || 5} GWs)<SortIcon col="projected_points" /></th>
                <th onClick={() => handleSort('ownership')}>Own%<SortIcon col="ownership" /></th>
                <th onClick={() => handleSort('minutes')}>Min<SortIcon col="minutes" /></th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {sortedSquad.map(player => (
                <tr key={player.player_id} className="table-row clickable" onClick={() => onPlayerClick?.(player)}>
                  <td className="table-player-name">
                    {player.name}
                    {player.is_captain && <span className="captain-badge">C</span>}
                    {player.is_vice_captain && <span className="captain-badge" style={{background: '#64748b'}}>V</span>}
                    {player.squad_position > 11 && <span className="bench-badge">Bench</span>}
                  </td>
                  <td><PositionBadge position={player.position} /></td>
                  <td>{player.team_name}</td>
                  <td className="table-price">&pound;{player.price?.toFixed(1)}m</td>
                  <td>{player.total_points}</td>
                  <td>{player.form}</td>
                  <td className="table-projected">{player.projected_points}</td>
                  <td>{player.ownership}%</td>
                  <td>{player.minutes}</td>
                  <td><StatusBadge status={player.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ========== Transfer Recommendations Tab ========== */
export function RecommendationsTab({ data, loading, onPlayerClick }) {
  if (loading) return <div className="loading-text">Calculating recommendations...</div>;
  if (!data) return <div className="empty-state">Load your team data to see transfer recommendations.</div>;

  const { current_squad_rating, optimized_squad_rating, recommendations, lookahead_gw } = data;
  const improvement = optimized_squad_rating - current_squad_rating;
  const gwLabel = `over ${lookahead_gw || 5} GWs`;

  return (
    <div className="fade-in">
      <h2 style={{fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem', fontFamily: "'Playfair Display', Georgia, serif", color: 'var(--accent)'}}>
        Transfer Recommendations
      </h2>
      <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem'}}>
        Projected points are calculated {gwLabel} based on form and fixture difficulty.
      </p>

      {/* Rating Comparison */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{current_squad_rating?.toFixed(1)}</div>
          <div className="stat-label">Current Rating ({gwLabel})</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{optimized_squad_rating?.toFixed(1)}</div>
          <div className="stat-label">Optimized Rating</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{color: improvement > 0 ? 'var(--success)' : improvement < 0 ? 'var(--danger)' : 'var(--text-secondary)'}}>
            {improvement > 0 ? '+' : ''}{improvement?.toFixed(1)}
          </div>
          <div className="stat-label">Improvement</div>
        </div>
      </div>

      {/* Transfer Recommendations */}
      {recommendations?.length === 0 && (
        <div className="empty-state">No beneficial transfers found. Your squad looks strong!</div>
      )}
      {recommendations?.map((rec, i) => (
        <div key={i} className="transfer-card">
          <div className="transfer-row">
            {/* Player Out */}
            <div style={{flex: 1, cursor: 'pointer'}} onClick={() => onPlayerClick?.({player_id: rec.transfer_out.player_id, ...rec.transfer_out})}>
              <div style={{color: 'var(--danger)', fontSize: '0.75rem', fontWeight: 600, marginBottom: '0.25rem'}}>
                OUT {!rec.transfer_out.is_starter && <span className="bench-badge" style={{marginLeft: '0.25rem'}}>Bench</span>}
              </div>
              <div className="player-name player-link">{rec.transfer_out.name}</div>
              <div className="player-team">{rec.transfer_out.team_name} &middot; {rec.transfer_out.position}</div>
              <div className="player-points">&pound;{rec.transfer_out.price?.toFixed(1)}m &middot; {rec.transfer_out.projected_points} pts ({gwLabel})</div>
            </div>

            {/* Arrow */}
            <div className="transfer-arrow">&rarr;</div>

            {/* Player In */}
            <div style={{flex: 1, cursor: 'pointer'}} onClick={() => onPlayerClick?.({player_id: rec.transfer_in.player_id, ...rec.transfer_in})}>
              <div style={{color: 'var(--success)', fontSize: '0.75rem', fontWeight: 600, marginBottom: '0.25rem'}}>IN</div>
              <div className="player-name player-link">{rec.transfer_in.name}</div>
              <div className="player-team">{rec.transfer_in.team_name} &middot; {rec.transfer_in.position}</div>
              <div className="player-points">&pound;{rec.transfer_in.price?.toFixed(1)}m &middot; {rec.transfer_in.projected_points} pts ({gwLabel}) &middot; {rec.transfer_in.ownership}% owned</div>
            </div>

            {/* Delta */}
            <div style={{textAlign: 'right', minWidth: '80px'}}>
              <div className={`transfer-delta ${rec.net_points_delta > 0 ? 'delta-positive' : 'delta-negative'}`}>
                {rec.net_points_delta > 0 ? '+' : ''}{rec.net_points_delta?.toFixed(1)} pts
              </div>
              <div className="player-points">
                {rec.price_delta > 0 ? '+' : ''}&pound;{rec.price_delta?.toFixed(1)}m
              </div>
              {rec.penalty < 0 && <div style={{color: 'var(--danger)', fontSize: '0.75rem'}}>{rec.penalty} pt hit</div>}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ========== Captain Tab ========== */
export function CaptainTab({ data, loading, onPlayerClick }) {
  if (loading) return <div className="loading-text">Finding best captains...</div>;
  if (!data) return <div className="empty-state">Load your team data to see captain recommendations.</div>;

  const captains = data.captains || [];

  return (
    <div className="fade-in">
      <h2 style={{fontSize: '1.25rem', fontWeight: 600, marginBottom: '1rem', fontFamily: "'Playfair Display', Georgia, serif", color: 'var(--accent)'}}>Captain Picks for Next Gameweek</h2>
      {captains.map(captain => (
        <div key={captain.player_id} className="captain-card clickable" onClick={() => onPlayerClick?.(captain)}>
          <div className="captain-rank">#{captain.rank}</div>
          <div style={{flex: 1}}>
            <div className="player-name">{captain.name}</div>
            <div className="player-team">{captain.team_name} &middot; {captain.position}</div>
          </div>
          {captain.fixture && (
            <div style={{textAlign: 'center'}}>
              <div style={{fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem'}}>
                {captain.fixture.is_home ? 'HOME' : 'AWAY'}
              </div>
              <span className={`fixture-badge diff-${captain.fixture.difficulty}`}>
                vs {captain.fixture.opponent}
              </span>
            </div>
          )}
          <div style={{textAlign: 'right', minWidth: '80px'}}>
            <div style={{color: 'var(--gold)', fontWeight: 700, fontSize: '1.1rem'}}>{captain.projected_points?.toFixed(1)} pts</div>
            <div className="player-points">{captain.ownership}% owned</div>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ========== Rotation Tab ========== */
export function RotationTab({ data, loading, onPlayerClick }) {
  if (loading) return <div className="loading-text">Planning rotation...</div>;
  if (!data) return <div className="empty-state">Load your team data to see rotation strategy.</div>;

  const { strategy, total_projected_points } = data;

  return (
    <div className="fade-in">
      <div className="stats-grid" style={{marginBottom: '2rem'}}>
        <div className="stat-card">
          <div className="stat-value">{strategy?.length || 0}</div>
          <div className="stat-label">Gameweeks Planned</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{total_projected_points?.toFixed(1)}</div>
          <div className="stat-label">Total Projected Points</div>
        </div>
      </div>

      {strategy?.map(gw => (
        <div key={gw.gw} className="gw-section">
          <div className="gw-header">
            <span>Gameweek {gw.gw}</span>
            <span style={{fontSize: '0.9rem', color: 'var(--text-secondary)'}}>{gw.total_projected?.toFixed(1)} pts</span>
          </div>

          {/* Starting XI */}
          <div className="card" style={{marginBottom: '0.5rem'}}>
            <div style={{fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', fontWeight: 600}}>STARTING XI</div>
            <div style={{display: 'flex', flexWrap: 'wrap'}}>
              {gw.starting_xi?.map(p => (
                <span key={p.player_id} className="player-badge clickable" onClick={() => onPlayerClick?.(p)} style={{
                  borderColor: p.is_captain ? 'var(--gold)' : undefined,
                  borderWidth: p.is_captain ? '2px' : undefined,
                }}>
                  <PositionDot position={p.position} />
                  {p.name}
                  {p.is_captain && <span className="captain-badge">C</span>}
                  <span style={{color: 'var(--text-secondary)', fontSize: '0.75rem'}}>{p.projected_points}</span>
                </span>
              ))}
            </div>
          </div>

          {/* Bench */}
          <div className="card" style={{opacity: 0.7}}>
            <div style={{fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', fontWeight: 600}}>BENCH</div>
            <div style={{display: 'flex', flexWrap: 'wrap'}}>
              {gw.bench?.map(p => (
                <span key={p.player_id} className="player-badge clickable" onClick={() => onPlayerClick?.(p)}>
                  <PositionDot position={p.position} />
                  {p.name}
                  <span style={{color: 'var(--text-secondary)', fontSize: '0.75rem'}}>{p.projected_points}</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ========== Leagues Tab ========== */
export function LeaguesTab({ data, loading, teamId, fetchData, onPlayerClick }) {
  const [selectedLeague, setSelectedLeague] = useState(null);
  const [standings, setStandings] = useState(null);
  const [standingsLoading, setStandingsLoading] = useState(false);
  const [rivalAnalysis, setRivalAnalysis] = useState(null);
  const [rivalLoading, setRivalLoading] = useState(false);
  const [rivals, setRivals] = useState([]);

  if (loading) return <div className="loading-text">Loading leagues...</div>;
  if (!data) return <div className="empty-state">Load your team data to see your leagues.</div>;

  const allLeagues = [...(data.classic || []), ...(data.h2h || [])];

  const openLeague = async (league) => {
    setSelectedLeague(league);
    setStandings(null);
    setRivalAnalysis(null);
    setStandingsLoading(true);
    try {
      const res = await fetch(`/api/leagues/${league.id}/standings?team_id=${teamId}`);
      const d = await res.json();
      setStandings(d);
    } catch {
      setStandings(null);
    } finally {
      setStandingsLoading(false);
    }
  };

  const analyzeRival = async (rivalTeamId) => {
    setRivalLoading(true);
    setRivalAnalysis(null);
    try {
      const res = await fetch(`/api/rivals/${rivalTeamId}/analysis?team_id=${teamId}`);
      const d = await res.json();
      setRivalAnalysis(d);
    } catch {
      setRivalAnalysis(null);
    } finally {
      setRivalLoading(false);
    }
  };

  const toggleRival = (entry) => {
    const id = entry.entry;
    setRivals(prev => {
      const next = prev.includes(id) ? prev.filter(r => r !== id) : [...prev, id];
      // Save to backend
      fetch('/api/rivals', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({rival_ids: next}),
      });
      return next;
    });
  };

  // League list view
  if (!selectedLeague) {
    return (
      <div className="fade-in">
        <h2 style={{fontSize: '1.25rem', fontWeight: 600, marginBottom: '1.25rem', fontFamily: "'Playfair Display', Georgia, serif", color: 'var(--accent)'}}>
          Your Leagues
        </h2>
        {allLeagues.length === 0 && <div className="empty-state">No leagues found.</div>}
        <div className="player-grid">
          {allLeagues.map(league => (
            <div key={league.id} className="player-card clickable" onClick={() => openLeague(league)}>
              <div style={{flex: 1}}>
                <div className="player-name">{league.name}</div>
                <div className="player-team">Your rank: #{league.rank || '?'}</div>
              </div>
              <div style={{color: 'var(--gold)', fontWeight: 700, fontSize: '1.1rem'}}>
                &rarr;
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // League standings view
  const standingsList = standings?.standings?.results || [];
  const leagueInfo = standings?.league || {};

  return (
    <div className="fade-in">
      <button className="view-btn" onClick={() => { setSelectedLeague(null); setRivalAnalysis(null); }} style={{marginBottom: '1rem'}}>
        &larr; Back to Leagues
      </button>

      <h2 style={{fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem', fontFamily: "'Playfair Display', Georgia, serif", color: 'var(--accent)'}}>
        {leagueInfo.name || selectedLeague.name}
      </h2>

      {standingsLoading && <div className="loading-text">Loading standings...</div>}

      {standingsList.length > 0 && (
        <div className="table-wrapper" style={{marginBottom: '1.5rem'}}>
          <table className="player-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Manager</th>
                <th>Team</th>
                <th>GW</th>
                <th>Total</th>
                <th>Rival</th>
              </tr>
            </thead>
            <tbody>
              {standingsList.map(entry => {
                const isUser = entry.entry === parseInt(teamId);
                const isRival = rivals.includes(entry.entry);
                return (
                  <tr key={entry.entry} className="table-row" style={{
                    background: isUser ? 'rgba(139, 26, 43, 0.08)' : isRival ? 'rgba(200, 169, 110, 0.12)' : undefined,
                    fontWeight: isUser ? 700 : undefined,
                  }}>
                    <td style={{fontWeight: 700}}>{entry.rank}</td>
                    <td>{entry.player_name} {isUser && <span style={{color: 'var(--accent)', fontSize: '0.75rem'}}>(You)</span>}</td>
                    <td>{entry.entry_name}</td>
                    <td>{entry.event_total}</td>
                    <td style={{fontWeight: 700}}>{entry.total}</td>
                    <td>
                      {!isUser && (
                        <div style={{display: 'flex', gap: '0.25rem'}}>
                          <button
                            className={`view-btn ${isRival ? 'view-active' : ''}`}
                            style={{padding: '0.2rem 0.5rem', fontSize: '0.7rem'}}
                            onClick={() => toggleRival(entry)}
                          >
                            {isRival ? 'Rival' : 'Mark'}
                          </button>
                          <button
                            className="view-btn"
                            style={{padding: '0.2rem 0.5rem', fontSize: '0.7rem'}}
                            onClick={() => analyzeRival(entry.entry)}
                          >
                            Compare
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Rival Analysis */}
      {rivalLoading && <div className="loading-text">Analyzing rival squad...</div>}
      {rivalAnalysis && (
        <div style={{marginTop: '1rem'}}>
          <h3 style={{fontSize: '1.1rem', fontWeight: 700, color: 'var(--accent)', marginBottom: '0.75rem', fontFamily: "'Playfair Display', Georgia, serif"}}>
            Squad Comparison vs {rivalAnalysis.rival_info?.name}
          </h3>

          <div className="stats-grid" style={{marginBottom: '1rem'}}>
            <div className="stat-card">
              <div className="stat-value">{rivalAnalysis.shared_count}</div>
              <div className="stat-label">Shared Players</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{rivalAnalysis.differential_count}</div>
              <div className="stat-label">Differentials</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{rivalAnalysis.differential_score}%</div>
              <div className="stat-label">Squad Difference</div>
            </div>
          </div>

          {/* Your differentials */}
          <div className="card" style={{marginBottom: '0.75rem'}}>
            <div style={{fontSize: '0.8rem', color: 'var(--success)', marginBottom: '0.5rem', fontWeight: 700}}>
              YOUR DIFFERENTIALS ({rivalAnalysis.user_only?.length || 0})
            </div>
            <div style={{display: 'flex', flexWrap: 'wrap'}}>
              {rivalAnalysis.user_only?.map(p => (
                <span key={p.player_id} className="player-badge clickable" onClick={() => onPlayerClick?.(p)}>
                  <PositionDot position={p.position} />
                  {p.name}
                  <span style={{color: 'var(--text-secondary)', fontSize: '0.75rem'}}>{p.projected_points?.toFixed(1)}</span>
                </span>
              ))}
            </div>
          </div>

          {/* Rival differentials */}
          <div className="card" style={{marginBottom: '0.75rem'}}>
            <div style={{fontSize: '0.8rem', color: 'var(--danger)', marginBottom: '0.5rem', fontWeight: 700}}>
              RIVAL DIFFERENTIALS ({rivalAnalysis.rival_only?.length || 0})
            </div>
            <div style={{display: 'flex', flexWrap: 'wrap'}}>
              {rivalAnalysis.rival_only?.map(p => (
                <span key={p.player_id} className="player-badge clickable" onClick={() => onPlayerClick?.(p)}>
                  <PositionDot position={p.position} />
                  {p.name}
                  <span style={{color: 'var(--text-secondary)', fontSize: '0.75rem'}}>{p.projected_points?.toFixed(1)}</span>
                </span>
              ))}
            </div>
          </div>

          {/* Shared players */}
          <div className="card" style={{opacity: 0.7}}>
            <div style={{fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', fontWeight: 700}}>
              SHARED PLAYERS ({rivalAnalysis.shared?.length || 0})
            </div>
            <div style={{display: 'flex', flexWrap: 'wrap'}}>
              {rivalAnalysis.shared?.map(p => (
                <span key={p.player_id} className="player-badge clickable" onClick={() => onPlayerClick?.(p)}>
                  <PositionDot position={p.position} />
                  {p.name}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ========== Chips Tab ========== */
export function ChipsTab({ data, loading }) {
  if (loading) return <div className="loading-text">Analyzing chip strategy...</div>;
  if (!data) return <div className="empty-state">Load your team data to see chip recommendations.</div>;

  const { available_chips, used_chips, recommendations } = data;

  const chipIcons = {
    bboost: '\u2B06',     // ⬆
    '3xc': '\u00D73',    // ×3
    freehit: '\u26A1',    // ⚡
    wildcard: '\u2606',   // ☆
  };

  return (
    <div className="fade-in">
      <h2 style={{fontSize: '1.25rem', fontWeight: 600, marginBottom: '1.25rem', fontFamily: "'Playfair Display', Georgia, serif", color: 'var(--accent)'}}>
        Chip Strategy
      </h2>

      {/* Chip Status */}
      <div className="stats-grid" style={{marginBottom: '1.5rem'}}>
        {['bboost', '3xc', 'freehit', 'wildcard'].map(chip => {
          const isAvailable = available_chips?.some(c => c.chip === chip);
          const usedChip = used_chips?.find(c => c.chip === chip);
          const label = {bboost: 'Bench Boost', '3xc': 'Triple Captain', freehit: 'Free Hit', wildcard: 'Wildcard'}[chip];
          return (
            <div key={chip} className="stat-card" style={{
              opacity: isAvailable ? 1 : 0.5,
              borderColor: isAvailable ? 'var(--gold)' : 'var(--border)',
            }}>
              <div className="stat-value" style={{fontSize: '1.25rem'}}>
                {chipIcons[chip] || '?'}
              </div>
              <div className="stat-label">{label}</div>
              <div style={{fontSize: '0.7rem', color: isAvailable ? 'var(--success)' : 'var(--text-secondary)', marginTop: '0.25rem', fontWeight: 600}}>
                {isAvailable ? 'Available' : `Used GW${usedChip?.gw || '?'}`}
              </div>
            </div>
          );
        })}
      </div>

      {/* Recommendations */}
      <h3 style={{fontSize: '1rem', fontWeight: 700, color: 'var(--accent)', marginBottom: '0.75rem', fontFamily: "'Playfair Display', Georgia, serif"}}>
        Recommendations
      </h3>

      {recommendations?.length === 0 && (
        <div className="empty-state">All chips have been used!</div>
      )}

      {recommendations?.map((rec, i) => (
        <div key={rec.chip} className="card" style={{marginBottom: '0.75rem'}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem'}}>
            <div>
              <div style={{fontWeight: 700, fontSize: '1.05rem', color: 'var(--text-primary)'}}>
                {chipIcons[rec.chip]} {rec.label}
              </div>
              <div style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.25rem'}}>
                {rec.reason}
              </div>
            </div>
            <div style={{textAlign: 'right'}}>
              <div style={{fontWeight: 700, fontSize: '1.1rem', color: 'var(--accent)', fontFamily: "'Playfair Display', Georgia, serif"}}>
                GW {rec.best_gw}
              </div>
              <div style={{fontSize: '0.75rem', color: 'var(--text-secondary)'}}>Recommended</div>
            </div>
          </div>

          {/* GW value bars */}
          {rec.gw_values && rec.gw_values.length > 0 && (
            <div style={{display: 'flex', gap: '0.25rem', alignItems: 'flex-end', height: '60px'}}>
              {rec.gw_values.map(gv => {
                const maxVal = Math.max(...rec.gw_values.map(v => v.value));
                const height = maxVal > 0 ? (gv.value / maxVal) * 100 : 0;
                const isBest = gv.gw === rec.best_gw;
                return (
                  <div key={gv.gw} style={{flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
                    <div style={{
                      width: '100%',
                      height: `${Math.max(height, 5)}%`,
                      background: isBest ? 'var(--accent)' : 'var(--border)',
                      borderRadius: '0.25rem 0.25rem 0 0',
                      minHeight: '3px',
                    }} />
                    <div style={{fontSize: '0.6rem', color: isBest ? 'var(--accent)' : 'var(--text-secondary)', marginTop: '0.15rem', fontWeight: isBest ? 700 : 400}}>
                      {gv.gw}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ))}

      {/* Used chips history */}
      {used_chips?.length > 0 && (
        <div style={{marginTop: '1.5rem'}}>
          <h3 style={{fontSize: '1rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.5rem'}}>
            Chips Used This Season
          </h3>
          <div style={{display: 'flex', gap: '0.5rem', flexWrap: 'wrap'}}>
            {used_chips.map((c, i) => (
              <span key={i} className="player-badge" style={{opacity: 0.6}}>
                {c.chip} &middot; GW{c.gw}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ========== Settings Tab ========== */
export function SettingsTab({ settings, onChange }) {
  return (
    <div className="fade-in">
      <h2 style={{fontSize: '1.25rem', fontWeight: 600, marginBottom: '1.5rem', fontFamily: "'Playfair Display', Georgia, serif", color: 'var(--accent)'}}>Settings</h2>

      <div className="settings-group">
        <label className="settings-label">
          Max Transfers: {settings.max_transfers}
        </label>
        <input
          type="range"
          min="1" max="5" step="1"
          value={settings.max_transfers}
          onChange={(e) => onChange({ max_transfers: parseInt(e.target.value) })}
          className="settings-slider"
        />
        <div style={{display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '0.75rem'}}>
          <span>1</span><span>2</span><span>3</span><span>4</span><span>5</span>
        </div>
      </div>

      <div className="settings-group">
        <label className="settings-label">
          Lookahead Period: {settings.lookahead_gw} gameweeks
        </label>
        <input
          type="range"
          min="1" max="10" step="1"
          value={settings.lookahead_gw}
          onChange={(e) => onChange({ lookahead_gw: parseInt(e.target.value) })}
          className="settings-slider"
        />
        <div style={{display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '0.75rem'}}>
          {[...Array(10)].map((_, i) => <span key={i}>{i + 1}</span>)}
        </div>
      </div>

      <div className="settings-group">
        <label className="settings-label">Optimization Criteria</label>
        <select
          value={settings.optimization_criteria}
          onChange={(e) => onChange({ optimization_criteria: e.target.value })}
          className="settings-select"
        >
          <option value="projected_points">Projected Points</option>
          <option value="form">Recent Form</option>
          <option value="fixture_difficulty">Fixture Difficulty</option>
        </select>
      </div>

      {/* Algorithm Explanation */}
      <div className="algorithm-box">
        <h3>How the Algorithm Works</h3>
        <p style={{color: 'var(--text-secondary)', marginBottom: '0.75rem'}}>
          The recommendation engine uses a weighted scoring model:
        </p>
        <p style={{marginBottom: '0.5rem'}}>
          <code>projected_points = (form &times; 0.6) + (fixture_adj &times; 0.4)</code>
        </p>
        <ul style={{color: 'var(--text-secondary)', fontSize: '0.9rem', paddingLeft: '1.25rem', lineHeight: 1.8}}>
          <li><strong style={{color: 'var(--text-primary)'}}>Form (60%)</strong> &mdash; Points per game from FPL API</li>
          <li><strong style={{color: 'var(--text-primary)'}}>Fixture Difficulty (40%)</strong> &mdash; Adjusted by opponent difficulty (1-5 scale)</li>
          <li><strong style={{color: 'var(--text-primary)'}}>Status</strong> &mdash; Unavailable players &times;0.5, doubtful &times;0.7</li>
          <li><strong style={{color: 'var(--text-primary)'}}>Bench</strong> &mdash; Bench players weighted at 20% (auto-sub probability)</li>
          <li><strong style={{color: 'var(--text-primary)'}}>Transfers</strong> &mdash; -4 pt penalty for transfers beyond free</li>
        </ul>
      </div>
    </div>
  );
}

/* ========== Player Detail Modal ========== */
export function PlayerDetailModal({ player, detail, loading, onClose }) {
  // Merge base player info with API detail (detail may be null if API call failed)
  const p = detail || player;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div>
            <h2 className="modal-player-name">{p.full_name || p.name}</h2>
            <div className="modal-player-sub">
              {p.team_name} &middot; {p.position} &middot; <StatusBadge status={p.status} inline />
              {p.status === 'a' && <span style={{color: 'var(--success)', fontSize: '0.8rem', fontWeight: 600}}>Available</span>}
            </div>
          </div>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        {loading && <div className="loading-text" style={{padding: '1rem'}}>Loading player details...</div>}

        {/* Stats Table */}
        <div className="modal-stats-grid">
          <div className="modal-stat">
            <div className="modal-stat-val">&pound;{p.price?.toFixed(1)}m</div>
            <div className="modal-stat-lbl">Price</div>
          </div>
          <div className="modal-stat">
            <div className="modal-stat-val">{p.total_points ?? '-'}</div>
            <div className="modal-stat-lbl">Total Points</div>
          </div>
          <div className="modal-stat">
            <div className="modal-stat-val">{p.form ?? '-'}</div>
            <div className="modal-stat-lbl">Form (PPG)</div>
          </div>
          <div className="modal-stat">
            <div className="modal-stat-val">{p.projected_points ?? '-'}</div>
            <div className="modal-stat-lbl">Projected (5 GWs)</div>
          </div>
          <div className="modal-stat">
            <div className="modal-stat-val">{p.ownership ?? '-'}%</div>
            <div className="modal-stat-lbl">Ownership</div>
          </div>
          <div className="modal-stat">
            <div className="modal-stat-val">{p.minutes ?? '-'}</div>
            <div className="modal-stat-lbl">Minutes</div>
          </div>
        </div>

        {/* Detailed stats from API */}
        {detail && (
          <div className="modal-detail-section">
            <h3>Season Stats</h3>
            <table className="detail-table">
              <tbody>
                <tr><td>Goals</td><td>{detail.goals_scored}</td></tr>
                <tr><td>Assists</td><td>{detail.assists}</td></tr>
                <tr><td>Clean Sheets</td><td>{detail.clean_sheets}</td></tr>
                <tr><td>Minutes Played</td><td>{detail.minutes}</td></tr>
                <tr><td>Total Points</td><td>{detail.total_points}</td></tr>
              </tbody>
            </table>
          </div>
        )}

        {/* News */}
        {detail?.news && (
          <div className="modal-news">
            <strong>News:</strong> {detail.news}
          </div>
        )}

        {/* Upcoming Fixtures */}
        {p.fixtures && p.fixtures.length > 0 && (
          <div className="modal-detail-section">
            <h3>Upcoming Fixtures</h3>
            <table className="detail-table fixture-table">
              <thead>
                <tr>
                  <th>GW</th>
                  <th>Opponent</th>
                  <th>Venue</th>
                  <th>Difficulty</th>
                </tr>
              </thead>
              <tbody>
                {p.fixtures.map((fix) => (
                  <tr key={`${fix.gw}-${fix.opponent_team}`}>
                    <td>{fix.gw}</td>
                    <td>{fix.opponent_name || `Team ${fix.opponent_team}`}</td>
                    <td>{fix.is_home ? 'Home' : 'Away'}</td>
                    <td>
                      <span className={`fixture-badge diff-${fix.difficulty}`}>
                        {fix.difficulty}/5
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

/* ========== Helpers ========== */
function StatusBadge({ status, inline }) {
  if (status === 'a') return null;
  const styles = {
    d: { bg: '#854d0e', color: '#fef08a', label: 'Doubtful' },
    u: { bg: '#991b1b', color: '#fecaca', label: 'Unavailable' },
    i: { bg: '#991b1b', color: '#fecaca', label: 'Injured' },
    s: { bg: '#7f1d1d', color: '#fca5a5', label: 'Suspended' },
  };
  const s = styles[status] || styles.u;
  return (
    <span style={{
      background: s.bg, color: s.color, fontSize: '0.7rem', fontWeight: 600,
      padding: '0.1rem 0.4rem', borderRadius: '0.25rem',
      marginTop: inline ? 0 : '0.25rem',
      marginRight: inline ? '0.4rem' : 0,
      display: 'inline-block',
    }}>
      {s.label}
    </span>
  );
}

function PositionDot({ position }) {
  const colors = { GK: '#f59e0b', DEF: '#22c55e', MID: '#3b82f6', FWD: '#ef4444' };
  return (
    <span style={{
      width: '8px', height: '8px', borderRadius: '50%', display: 'inline-block',
      background: colors[position] || '#94a3b8',
    }} />
  );
}

function PositionBadge({ position }) {
  const colors = { GK: '#f59e0b', DEF: '#22c55e', MID: '#3b82f6', FWD: '#ef4444' };
  return (
    <span style={{
      background: colors[position] || '#94a3b8', color: '#000',
      fontSize: '0.7rem', fontWeight: 700, padding: '0.15rem 0.4rem',
      borderRadius: '0.25rem', display: 'inline-block',
    }}>
      {position}
    </span>
  );
}
