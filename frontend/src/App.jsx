import React, { useState, useCallback, useEffect, useRef } from 'react';
import { SquadTab, RecommendationsTab, CaptainTab, RotationTab, LeaguesTab, ChipsTab, SettingsTab, PlayerDetailModal, ManagerIdInput, loadManagerHistory, saveManagerToHistory, PlanningTab, appendRecHistory } from './components/index';

// In production, frontend is served by Flask — use relative URLs.
// In development, proxy is configured in package.json.
const API_BASE = '/api';

const TABS = ['Squad', 'Transfer Recs', 'Captain', 'Rotation', 'Leagues', 'Chips', 'Planning', 'Settings'];

function App() {
  const [activeTab, setActiveTab] = useState('Squad');
  // Persist manager ID across sessions (Feature 2): seed from the most-recent
  // entry in localStorage so the user never has to retype it.
  const [teamId, setTeamId] = useState(() => {
    const hist = loadManagerHistory();
    return hist[0]?.id || '';
  });
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
      const [squad, recommendations, captains, rotation, leagues, chips] = await Promise.all([
        fetchData('squad', params),
        fetchData('recommendations', {
          max_transfers: settings.max_transfers,
          lookahead_gw: settings.lookahead_gw,
        }),
        fetchData('captains'),
        fetchData('rotation', { num_gw: settings.lookahead_gw }),
        fetchData('leagues'),
        fetchData('chips'),
      ]);
      setData({ squad, recommendations, captains, rotation, leagues, chips });
      // Persist this manager ID + team name to localStorage history
      if (squad) {
        saveManagerToHistory(teamId, squad.team_name || '');
        window.dispatchEvent(new Event('fpl-history-updated'));
      }
      // Append the recommendation set to the per-manager history log
      if (recommendations?.recommendations?.length) {
        appendRecHistory(teamId, squad?.current_gw, recommendations.recommendations);
        window.dispatchEvent(new Event('fpl-rec-history-updated'));
      }
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
    // Mark transfer count as user-overridden so the auto-sync effect won't
    // clobber it on the next squad refresh.
    if ('max_transfers' in newSettings) {
      transferOverrideRef.current = true;
    }
    setSettings(prev => ({ ...prev, ...newSettings }));
  };

  // Feature 5: sync free transfers from the live API on every squad load.
  // The synced value pre-populates max_transfers unless the user has manually
  // overridden it via the Settings slider during this session.
  const transferOverrideRef = useRef(false);
  const lastSyncedGwRef = useRef(null);
  useEffect(() => {
    const ft = data.squad?.free_transfers;
    const gw = data.squad?.current_gw;
    if (typeof ft !== 'number') return;
    // Re-sync (overriding any manual change) when the gameweek rolls over.
    if (gw !== lastSyncedGwRef.current) {
      transferOverrideRef.current = false;
      lastSyncedGwRef.current = gw;
    }
    if (transferOverrideRef.current) return;
    const clamped = Math.max(0, Math.min(5, ft));
    setSettings(prev => prev.max_transfers === clamped ? prev : { ...prev, max_transfers: clamped });
  }, [data.squad]);

  const renderTab = () => {
    switch (activeTab) {
      case 'Squad':
        return <SquadTab data={data.squad} recommendations={data.recommendations} loading={loading} onPlayerClick={openPlayerDetail} />;
      case 'Transfer Recs':
        return <RecommendationsTab data={data.recommendations} loading={loading} onPlayerClick={openPlayerDetail} />;
      case 'Captain':
        return <CaptainTab data={data.captains} loading={loading} onPlayerClick={openPlayerDetail} />;
      case 'Rotation':
        return <RotationTab data={data.rotation} loading={loading} onPlayerClick={openPlayerDetail} />;
      case 'Leagues':
        return <LeaguesTab data={data.leagues} loading={loading} teamId={teamId} fetchData={fetchData} onPlayerClick={openPlayerDetail} />;
      case 'Chips':
        return <ChipsTab data={data.chips} loading={loading} />;
      case 'Planning':
        return <PlanningTab teamId={teamId} currentGw={data.squad?.current_gw} />;
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
            <ManagerIdInput
              value={teamId}
              onChange={setTeamId}
              onSubmit={() => loadAll(true)}
              loading={loading}
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
