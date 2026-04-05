import React, { useState } from 'react';

/* ========== Squad Tab ========== */
export function SquadTab({ data, loading, onPlayerClick }) {
  const [view, setView] = useState('cards'); // 'cards' or 'table'
  const [sortKey, setSortKey] = useState('projected_points');
  const [sortAsc, setSortAsc] = useState(false);

  if (loading) return <div className="loading-text">Loading squad...</div>;
  if (!data) return <div className="empty-state">Enter your team ID and click "Load Data" to see your squad.</div>;

  const { squad, squad_by_position, bank, points, rank, current_gw } = data;

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
    return <span style={{color: '#f59e0b'}}> {sortAsc ? '\u2191' : '\u2193'}</span>;
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
                  </div>
                  <div className="player-team">{player.team_name} &middot; {player.position}</div>
                  <div className="player-points">Projected: {player.projected_points} pts</div>
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
                <th onClick={() => handleSort('projected_points')}>Proj<SortIcon col="projected_points" /></th>
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

/* ========== Recommendations Tab ========== */
export function RecommendationsTab({ data, loading, onPlayerClick }) {
  if (loading) return <div className="loading-text">Calculating recommendations...</div>;
  if (!data) return <div className="empty-state">Load your team data to see transfer recommendations.</div>;

  const { current_squad_rating, optimized_squad_rating, recommendations } = data;
  const improvement = optimized_squad_rating - current_squad_rating;

  return (
    <div className="fade-in">
      {/* Rating Comparison */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{current_squad_rating?.toFixed(1)}</div>
          <div className="stat-label">Current Rating</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{optimized_squad_rating?.toFixed(1)}</div>
          <div className="stat-label">Optimized Rating</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{color: improvement > 0 ? '#22c55e' : improvement < 0 ? '#ef4444' : '#94a3b8'}}>
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
              <div style={{color: '#ef4444', fontSize: '0.75rem', fontWeight: 600, marginBottom: '0.25rem'}}>OUT</div>
              <div className="player-name player-link">{rec.transfer_out.name}</div>
              <div className="player-team">{rec.transfer_out.team_name} &middot; {rec.transfer_out.position}</div>
              <div className="player-points">&pound;{rec.transfer_out.price?.toFixed(1)}m &middot; {rec.transfer_out.projected_points} pts</div>
            </div>

            {/* Arrow */}
            <div className="transfer-arrow">&rarr;</div>

            {/* Player In */}
            <div style={{flex: 1, cursor: 'pointer'}} onClick={() => onPlayerClick?.({player_id: rec.transfer_in.player_id, ...rec.transfer_in})}>
              <div style={{color: '#22c55e', fontSize: '0.75rem', fontWeight: 600, marginBottom: '0.25rem'}}>IN</div>
              <div className="player-name player-link">{rec.transfer_in.name}</div>
              <div className="player-team">{rec.transfer_in.team_name} &middot; {rec.transfer_in.position}</div>
              <div className="player-points">&pound;{rec.transfer_in.price?.toFixed(1)}m &middot; {rec.transfer_in.projected_points} pts &middot; {rec.transfer_in.ownership}% owned</div>
            </div>

            {/* Delta */}
            <div style={{textAlign: 'right', minWidth: '80px'}}>
              <div className={`transfer-delta ${rec.net_points_delta > 0 ? 'delta-positive' : 'delta-negative'}`}>
                {rec.net_points_delta > 0 ? '+' : ''}{rec.net_points_delta?.toFixed(1)} pts
              </div>
              <div className="player-points">
                {rec.price_delta > 0 ? '+' : ''}&pound;{rec.price_delta?.toFixed(1)}m
              </div>
              {rec.penalty < 0 && <div style={{color: '#ef4444', fontSize: '0.75rem'}}>{rec.penalty} pt hit</div>}
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
      <h2 style={{fontSize: '1.25rem', fontWeight: 600, marginBottom: '1rem'}}>Captain Picks for Next Gameweek</h2>
      {captains.map(captain => (
        <div key={captain.player_id} className="captain-card clickable" onClick={() => onPlayerClick?.(captain)}>
          <div className="captain-rank">#{captain.rank}</div>
          <div style={{flex: 1}}>
            <div className="player-name">{captain.name}</div>
            <div className="player-team">{captain.team_name} &middot; {captain.position}</div>
          </div>
          {captain.fixture && (
            <div style={{textAlign: 'center'}}>
              <div style={{fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.25rem'}}>
                {captain.fixture.is_home ? 'HOME' : 'AWAY'}
              </div>
              <span className={`fixture-badge diff-${captain.fixture.difficulty}`}>
                vs {captain.fixture.opponent}
              </span>
            </div>
          )}
          <div style={{textAlign: 'right', minWidth: '80px'}}>
            <div style={{color: '#f59e0b', fontWeight: 700, fontSize: '1.1rem'}}>{captain.projected_points?.toFixed(1)} pts</div>
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
            <span style={{fontSize: '0.9rem', color: '#94a3b8'}}>{gw.total_projected?.toFixed(1)} pts</span>
          </div>

          {/* Starting XI */}
          <div className="card" style={{marginBottom: '0.5rem'}}>
            <div style={{fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.5rem', fontWeight: 600}}>STARTING XI</div>
            <div style={{display: 'flex', flexWrap: 'wrap'}}>
              {gw.starting_xi?.map(p => (
                <span key={p.player_id} className="player-badge clickable" onClick={() => onPlayerClick?.(p)} style={{
                  borderColor: p.is_captain ? '#f59e0b' : undefined,
                  borderWidth: p.is_captain ? '2px' : undefined,
                }}>
                  <PositionDot position={p.position} />
                  {p.name}
                  {p.is_captain && <span className="captain-badge">C</span>}
                  <span style={{color: '#94a3b8', fontSize: '0.75rem'}}>{p.projected_points}</span>
                </span>
              ))}
            </div>
          </div>

          {/* Bench */}
          <div className="card" style={{opacity: 0.7}}>
            <div style={{fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.5rem', fontWeight: 600}}>BENCH</div>
            <div style={{display: 'flex', flexWrap: 'wrap'}}>
              {gw.bench?.map(p => (
                <span key={p.player_id} className="player-badge clickable" onClick={() => onPlayerClick?.(p)}>
                  <PositionDot position={p.position} />
                  {p.name}
                  <span style={{color: '#94a3b8', fontSize: '0.75rem'}}>{p.projected_points}</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ========== Settings Tab ========== */
export function SettingsTab({ settings, onChange }) {
  return (
    <div className="fade-in">
      <h2 style={{fontSize: '1.25rem', fontWeight: 600, marginBottom: '1.5rem'}}>Settings</h2>

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
        <div style={{display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '0.75rem'}}>
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
        <div style={{display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '0.75rem'}}>
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
        <p style={{color: '#94a3b8', marginBottom: '0.75rem'}}>
          The recommendation engine uses a weighted scoring model:
        </p>
        <p style={{marginBottom: '0.5rem'}}>
          <code>projected_points = (form &times; 0.6) + (fixture_adj &times; 0.4)</code>
        </p>
        <ul style={{color: '#94a3b8', fontSize: '0.9rem', paddingLeft: '1.25rem', lineHeight: 1.8}}>
          <li><strong style={{color: '#f1f5f9'}}>Form (60%)</strong> &mdash; Points per game from FPL API</li>
          <li><strong style={{color: '#f1f5f9'}}>Fixture Difficulty (40%)</strong> &mdash; Adjusted by opponent difficulty (1-5 scale)</li>
          <li><strong style={{color: '#f1f5f9'}}>Status</strong> &mdash; Unavailable players &times;0.5, doubtful &times;0.7</li>
          <li><strong style={{color: '#f1f5f9'}}>Transfers</strong> &mdash; -4 pt penalty for transfers beyond 2 free</li>
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
              {p.status === 'a' && <span style={{color: '#22c55e', fontSize: '0.8rem', fontWeight: 600}}>Available</span>}
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
            <div className="modal-stat-lbl">Projected Pts</div>
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
