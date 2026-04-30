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

function SimilarModal({ source, results, loading, error, onClose }) {
  if (!source) return null;
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Items like this</h2>
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
              <div className="empty-hint">No similar items in your wardrobe yet.</div>
            )}
            {!loading && !error && results.length > 0 && (
              <div className="closet-grid wide">
                {results.map((it) => (
                  <div key={it.id} className="closet-card">
                    <img src={fileUrl(it.image_url)} alt={it.name || it.category} />
                    <div className="closet-card-info">
                      <div className="closet-card-cat">{it.subcategory || it.category}</div>
                      <div className="closet-card-name">{it.name || 'Unnamed'}</div>
                      <div className="muted small">
                        match {Math.round((it.similarity || 0) * 100)}%
                      </div>
                    </div>
                  </div>
                ))}
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
      />
    </div>
  );
}

export default Wardrobe;
