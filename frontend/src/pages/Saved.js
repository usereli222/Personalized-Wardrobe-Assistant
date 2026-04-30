import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fileUrl } from '../services/api';
import { listSavedOutfits, deleteSavedOutfit } from '../services/tryon';

function Saved() {
  const navigate = useNavigate();
  const [outfits, setOutfits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState(null);

  const refresh = async () => {
    try {
      setOutfits(await listSavedOutfits());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  // Close the lightbox on Escape so it doesn't trap the user.
  useEffect(() => {
    if (!expanded) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') setExpanded(null); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [expanded]);

  const handleDelete = async (id) => {
    if (!window.confirm('Remove this saved look?')) return;
    try {
      await deleteSavedOutfit(id);
      if (expanded?.id === id) setExpanded(null);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="page saved-page">
      <div className="page-header">
        <h1>Saved looks</h1>
        <p className="muted">Outfits you've curated in the mirror.</p>
      </div>

      {error && <div className="page-error">{error}</div>}

      {loading ? (
        <div className="empty-hint">Loading…</div>
      ) : outfits.length === 0 ? (
        <div className="empty-hint big">
          You haven't saved any looks yet.{' '}
          <button className="login-link" onClick={() => navigate('/tryon')}>
            Go to the mirror
          </button>{' '}
          and tap <em>Save look</em> after generating one.
        </div>
      ) : (
        <div className="closet-grid wide">
          {outfits.map((o) => (
            <div key={o.id} className="closet-card">
              <img
                src={fileUrl(o.image_url)}
                alt={o.name || 'Saved look'}
                onClick={() => setExpanded(o)}
                style={{ cursor: 'zoom-in' }}
              />
              <div className="closet-card-info">
                <div className="closet-card-name">
                  {o.name || new Date(o.created_at).toLocaleString()}
                </div>
                {(o.top_name || o.bottom_name) && (
                  <div className="closet-card-cat muted small">
                    {[o.top_name, o.bottom_name].filter(Boolean).join(' + ')}
                  </div>
                )}
                <div className="closet-card-actions">
                  <button
                    className="ghost-btn small"
                    onClick={() => setExpanded(o)}
                  >
                    View
                  </button>
                  <button
                    className="ghost-btn danger small"
                    onClick={() => handleDelete(o.id)}
                  >
                    Remove
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {expanded && (
        <div className="modal-backdrop" onClick={() => setExpanded(null)}>
          <div
            className="modal-card saved-lightbox"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <h2>{expanded.name || new Date(expanded.created_at).toLocaleString()}</h2>
              <button className="ghost-btn subtle" onClick={() => setExpanded(null)}>
                Close
              </button>
            </div>
            <div className="modal-body" style={{ textAlign: 'center' }}>
              <img
                src={fileUrl(expanded.image_url)}
                alt={expanded.name || 'Saved look'}
                style={{ maxWidth: '100%', maxHeight: '75vh', objectFit: 'contain' }}
              />
              {(expanded.top_name || expanded.bottom_name) && (
                <div className="muted small" style={{ marginTop: '12px' }}>
                  {[expanded.top_name, expanded.bottom_name].filter(Boolean).join(' + ')}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Saved;
