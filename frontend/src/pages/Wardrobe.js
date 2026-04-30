import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fileUrl } from '../services/api';
import {
  listWardrobeItems,
  uploadWardrobeItem,
  deleteWardrobeItem,
  fetchSimilarItems,
} from '../services/wardrobeApi';

const SECTIONS = [
  { key: 'top', label: 'Tops' },
  { key: 'bottom', label: 'Bottoms' },
  { key: 'outerwear', label: 'Outerwear' },
  { key: 'shoes', label: 'Shoes' },
  { key: 'accessory', label: 'Accessories' },
];

function SimilarModal({ source, results, loading, error, onClose, onTryOn }) {
  if (!source) return null;

  // Result cards come from either the FAISS library (default) or the
  // user's own wardrobe (fallback). Library cards show the SAM crop +
  // a "View full outfit" link + a "Try this on" button.
  const renderCard = (it, idx) => {
    const key = it.library_item_id || it.id || idx;
    const isLibrary = it.source === 'library';
    const title = isLibrary
      ? (it.label || it.category || 'Reference item')
      : (it.name || it.subcategory || it.category || 'Wardrobe item');
    const subtitle = isLibrary
      ? `from ${it.outfit_id || 'corpus'}`
      : (it.subcategory || it.category || '');
    return (
      <div key={key} className="closet-card">
        {it.image_url ? (
          <img src={fileUrl(it.image_url)} alt={title} />
        ) : (
          <div className="empty-hint small">no image</div>
        )}
        <div className="closet-card-info">
          <div className="closet-card-cat">{title}</div>
          <div className="closet-card-name muted small">{subtitle}</div>
          <div className="muted small">
            match {Math.round((it.similarity || 0) * 100)}%
          </div>
          {isLibrary && (
            <div className="closet-card-actions">
              <button
                className="primary-btn small"
                onClick={() => onTryOn(it)}
              >
                Try this on
              </button>
              {it.outfit_image_url && (
                <a
                  className="ghost-btn small"
                  href={fileUrl(it.outfit_image_url)}
                  target="_blank"
                  rel="noreferrer"
                >
                  Full outfit
                </a>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };

  const headline = results.length > 0 && results[0].source === 'wardrobe'
    ? 'Similar items in your wardrobe'
    : 'Similar looks from the corpus';

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{headline}</h2>
          <button className="ghost-btn subtle" onClick={onClose}>Close</button>
        </div>
        <div className="modal-body">
          <div className="modal-source">
            <img src={fileUrl(source.image_url)} alt={source.name || source.category} />
            <div className="muted small">{source.subcategory || source.category}</div>
          </div>
          <div className="modal-divider" />
          <div className="modal-results">
            {loading && <div className="empty-hint">Searching…</div>}
            {error && <div className="page-error">{error}</div>}
            {!loading && !error && results.length === 0 && (
              <div className="empty-hint">
                No matches found. (If the corpus index isn't built yet,
                run <code>python scripts/build_library.py</code> and restart uvicorn.)
              </div>
            )}
            {!loading && !error && results.length > 0 && (
              <div className="closet-grid wide">
                {results.map(renderCard)}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Wardrobe() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const fileRef = useRef(null);

  const [similarSource, setSimilarSource] = useState(null);
  const [similarResults, setSimilarResults] = useState([]);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [similarError, setSimilarError] = useState('');

  const refresh = async () => {
    try {
      setItems(await listWardrobeItems());
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => { refresh(); }, []);

  const handleAdd = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError('');
    try {
      await uploadWardrobeItem({ file });
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Remove this item?')) return;
    try {
      await deleteWardrobeItem(id);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleFindSimilar = async (item) => {
    setSimilarSource(item);
    setSimilarResults([]);
    setSimilarError('');
    setSimilarLoading(true);
    try {
      const results = await fetchSimilarItems(item.id, 8);
      setSimilarResults(results);
    } catch (err) {
      setSimilarError(err.message || 'Could not find similar items.');
    } finally {
      setSimilarLoading(false);
    }
  };

  const closeSimilar = () => {
    setSimilarSource(null);
    setSimilarResults([]);
    setSimilarError('');
  };

  // User clicked "Try this on" inside the Find Similar modal. Pre-fill the
  // try-on slot for the library item's category with its image URL, leave
  // the opposite slot for them to pick from their own wardrobe.
  const handleTryOnLibrary = (libItem) => {
    const tryonState = {};
    const url = libItem.image_url || libItem.outfit_image_url;
    if (!url) return;
    if (libItem.category === 'top') {
      tryonState.topImageUrl = url;
      tryonState.topLabel = libItem.label || 'Library top';
    } else if (libItem.category === 'bottom') {
      tryonState.bottomImageUrl = url;
      tryonState.bottomLabel = libItem.label || 'Library bottom';
    } else {
      // FAISS only matches within category; for shoes/outerwear/accessory
      // we still send to try-on with a default slot, but the user will
      // need to pick the actual top/bottom from their wardrobe.
      return;
    }
    closeSimilar();
    navigate('/tryon', { state: tryonState });
  };

  return (
    <div className="page wardrobe-page">
      <div className="page-header">
        <h1>Your wardrobe</h1>
        <div className="page-actions">
          <label className="primary-btn upload-trigger">
            {busy ? 'Adding…' : '+ Add item'}
            <input type="file" accept="image/*" ref={fileRef} onChange={handleAdd} style={{ display: 'none' }} disabled={busy} />
          </label>
          <button className="ghost-btn" onClick={() => navigate('/tryon')}>To the mirror →</button>
        </div>
      </div>

      {error && <div className="page-error">{error}</div>}

      {items.length === 0 ? (
        <div className="empty-hint big">
          Your wardrobe is empty. <button className="login-link" onClick={() => navigate('/onboarding')}>Onboard now</button>
        </div>
      ) : (
        <div className="wardrobe-sections">
          {SECTIONS.map(({ key, label }) => {
            const group = items.filter((i) => i.category === key);
            if (group.length === 0) return null;
            return (
              <section key={key} className="wardrobe-section">
                <h2 className="panel-title">{label} <span className="muted small">· {group.length}</span></h2>
                <div className="closet-grid wide">
                  {group.map((it) => (
                    <div key={it.id} className="closet-card">
                      <img src={fileUrl(it.image_url)} alt={it.name || it.category} />
                      <div className="closet-card-info">
                        <div className="closet-card-cat">{it.subcategory || it.category}</div>
                        <div className="closet-card-name">{it.name || 'Unnamed'}</div>
                        <div className="closet-card-actions">
                          <button className="ghost-btn small" onClick={() => handleFindSimilar(it)}>Find similar</button>
                          <button className="ghost-btn danger small" onClick={() => handleDelete(it.id)}>Remove</button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}

      <SimilarModal
        source={similarSource}
        results={similarResults}
        loading={similarLoading}
        error={similarError}
        onClose={closeSimilar}
        onTryOn={handleTryOnLibrary}
      />
    </div>
  );
}

export default Wardrobe;