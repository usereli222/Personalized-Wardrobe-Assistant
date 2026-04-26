import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fileUrl } from '../services/api';
import { fetchOutfitSuggestions } from '../services/outfitsApi';

function Outfits() {
  const navigate = useNavigate();
  const [outfits, setOutfits] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchOutfitSuggestions();
        if (!cancelled) setOutfits(data);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const handleTryOn = (outfit) => {
    navigate('/tryon', {
      state: { topId: outfit.top.id, bottomId: outfit.bottom.id },
    });
  };

  return (
    <div className="page outfits-page">
      <div className="page-header">
        <h1>Suggested outfits</h1>
        <p className="muted">Curated combinations from your wardrobe.</p>
      </div>

      {error && <div className="page-error">{error}</div>}

      {loading ? (
        <div className="empty-hint">Conjuring outfits…</div>
      ) : outfits.length === 0 ? (
        <div className="empty-hint big">
          No outfits to suggest yet — add at least one top and one bottom in your wardrobe.
        </div>
      ) : (
        <div className="outfits-grid">
          {outfits.map((o, idx) => (
            <article key={idx} className="outfit-card">
              <div className="outfit-pair">
                <div className="outfit-thumb">
                  <img src={fileUrl(o.top.image_url)} alt={o.top.name || 'top'} />
                  <div className="outfit-thumb-label">{o.top.name || o.top.subcategory || 'Top'}</div>
                </div>
                <div className="outfit-thumb">
                  <img src={fileUrl(o.bottom.image_url)} alt={o.bottom.name || 'bottom'} />
                  <div className="outfit-thumb-label">{o.bottom.name || o.bottom.subcategory || 'Bottom'}</div>
                </div>
              </div>
              <div className="outfit-meta">
                <div className="outfit-score">match {Math.round((o.score || 0) * 100)}%</div>
                <button className="primary-btn small" onClick={() => handleTryOn(o)}>Try this on</button>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

export default Outfits;
