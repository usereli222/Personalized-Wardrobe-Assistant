import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fileUrl } from '../services/api';
import {
  listWardrobeItems,
  uploadWardrobeItem,
  deleteWardrobeItem,
} from '../services/wardrobeApi';

const SECTIONS = [
  { key: 'top', label: 'Tops' },
  { key: 'bottom', label: 'Bottoms' },
  { key: 'outerwear', label: 'Outerwear' },
  { key: 'shoes', label: 'Shoes' },
  { key: 'accessory', label: 'Accessories' },
];

function Wardrobe() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const fileRef = useRef(null);

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
                        <button className="ghost-btn danger" onClick={() => handleDelete(it.id)}>Remove</button>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default Wardrobe;
