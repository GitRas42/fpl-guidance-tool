import React, { useState, useCallback } from 'react';
import { SquadTab, RecommendationsTab, CaptainTab, RotationTab, SettingsTab, PlayerDetailModal } from './components/index';

// In production, frontend is served by Flask — use relative URLs.
// In development, proxy is configured in package.json.
const API_BASE = '/api';

const TABS = ['Squad', 'Transfers', 'Captain', 'Rotation', 'Settings'];

function App() {
  const [activeTab, setActiveTab] = useState('Squad');
  const [teamId, setTeamId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState({});
  const [settings, setSettings] = useState({
    max_transfers: 2,
    lookahead_gw: 5,
    optimization_criteria: 'projected_points',
  });

  const fetchData = useCallback(async (endpoint, params = {}) => {
    if (!teamId) return null;
    const queryParams = new URLSearchParams({ team_id: teamId, ...params });
    const res = await fetch(`${API_BASE}/${endpoint}?${queryParams}`);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  }, [teamId]);

  const loadAll = useCallback(async (refresh = false) => {
    if (!teamId) {
      setError('Please enter a team ID');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const params = refresh ? { refresh: 'true' } : {};
      const [squad, recommendations, captains, rotation] = await Promise.all([
        fetchData('squad', params),
        fetchData('recommendations', {
          max_transfers: settings.max_transfers,
          lookahead_gw: settings.lookahead_gw,
        }),
        fetchData('captains'),
        fetchData('rotation', { num_gw: settings.lookahead_gw }),
      ]);
      setData({ squad, recommendations, captains, rotation });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [teamId, settings, fetchData]);

  const handleSubmit = (e) => {
    e.preventDefault();
    loadAll(true);
  };

  // Player detail modal state
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [playerDetail, setPlayerDetail] = useState(null);
  const [playerLoading, setPlayerLoading] = useState(false);

  const openPlayerDetail = useCallback(async (player) => {
    setSelectedPlayer(player);
    setPlayerDetail(null);
    if (teamId && player.player_id) {
      setPlayerLoading(true);
      try {
        const detail = await fetchData(`player/${player.player_id}/stats`);
        setPlayerDetail(detail);
      } catch {
        // Fall back to the data we already have
        setPlayerDetail(null);
      } finally {
        setPlayerLoading(false);
      }
    }
  }, [teamId, fetchData]);

  const closePlayerDetail = () => {
    setSelectedPlayer(null);
    setPlayerDetail(null);
  };

  const handleSettingsChange = (newSettings) => {
    setSettings(prev => ({ ...prev, ...newSettings }));
  };

  const renderTab = () => {
    switch (activeTab) {
      case 'Squad':
        return <SquadTab data={data.squad} loading={loading} onPlayerClick={openPlayerDetail} />;
      case 'Transfers':
        return <RecommendationsTab data={data.recommendations} loading={loading} onPlayerClick={openPlayerDetail} />;
      case 'Captain':
        return <CaptainTab data={data.captains} loading={loading} onPlayerClick={openPlayerDetail} />;
      case 'Rotation':
        return <RotationTab data={data.rotation} loading={loading} onPlayerClick={openPlayerDetail} />;
      case 'Settings':
        return <SettingsTab settings={settings} onChange={handleSettingsChange} />;
      default:
        return null;
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <h1 className="app-title">
            <span className="title-icon">&#9917;</span> FPL Guidance Tool
          </h1>
          <form onSubmit={handleSubmit} className="header-form">
            <input
              type="number"
              value={teamId}
              onChange={(e) => setTeamId(e.target.value)}
              placeholder="Team ID"
              className="team-input"
            />
            <button type="submit" className="refresh-btn" disabled={loading}>
              {loading ? 'Loading...' : 'Load Data'}
            </button>
          </form>
        </div>
      </header>

      {/* Error banner */}
      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="error-close">&times;</button>
        </div>
      )}

      {/* Tab Navigation */}
      <nav className="tab-nav">
        {TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`tab-btn ${activeTab === tab ? 'tab-active' : ''}`}
          >
            {tab}
          </button>
        ))}
      </nav>

      {/* Tab Content */}
      <main className="tab-content fade-in">
        {renderTab()}
      </main>

      {/* Player Detail Modal */}
      {selectedPlayer && (
        <PlayerDetailModal
          player={selectedPlayer}
          detail={playerDetail}
          loading={playerLoading}
          onClose={closePlayerDetail}
        />
      )}

      {/* Footer */}
      <footer className="app-footer">
        <p>FPL Guidance Tool &mdash; Built with React + Flask + FPL API</p>
      </footer>
    </div>
  );
}

export default App;
