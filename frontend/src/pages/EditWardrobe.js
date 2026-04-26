import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  listItems,
  addItem,
  deleteItem,
  fileToDataUrl,
  getBodyPhoto,
  setBodyPhoto,
  clearBodyPhoto,
} from '../services/wardrobeStore';

function EditWardrobe({ username }) {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [bodyPhoto, setBodyPhotoState] = useState(null);
  const [category, setCategory] = useState('top');
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const fileRef = useRef(null);
  const bodyRef = useRef(null);

  const refresh = () => {
    setItems(listItems(username));
    setBodyPhotoState(getBodyPhoto(username));
  };

  useEffect(() => {
    refresh();
  }, [username]);

  const handleUpload = async (e) => {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setBusy(true);
    try {
      const dataUrl = await fileToDataUrl(file);
      addItem(username, { name, category, dataUrl });
      setName('');
      if (fileRef.current) fileRef.current.value = '';
      refresh();
    } finally {
      setBusy(false);
    }
  };

  const handleBodyUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const dataUrl = await fileToDataUrl(file);
    setBodyPhoto(username, dataUrl);
    setBodyPhotoState(dataUrl);
    if (bodyRef.current) bodyRef.current.value = '';
  };

  const handleClearBody = () => {
    if (!window.confirm('Remove your body photo?')) return;
    clearBodyPhoto(username);
    setBodyPhotoState(null);
  };

  const handleDelete = (id) => {
    if (!window.confirm('Remove this item from your wardrobe?')) return;
    deleteItem(username, id);
    refresh();
  };

  return (
    <div className="edit-wardrobe">
      <header className="wardrobe-header">
        <div className="wardrobe-greeting">
          <span className="wardrobe-spark">✦</span> Edit Wardrobe
        </div>
        <button className="ghost-btn" onClick={() => navigate('/wardrobe')}>
          ← Back to Mirror
        </button>
      </header>

      <section className="upload-card body-card">
        <div className="body-card-text">
          <h2 className="panel-title">Your full-body photo</h2>
          <p className="body-card-sub">
            One clear front-facing photo. The mirror will dress this image in whichever
            top &amp; bottoms you select.
          </p>
          <div className="body-card-actions">
            <label className="ghost-btn upload-trigger">
              {bodyPhoto ? 'Replace photo' : 'Upload photo'}
              <input
                type="file"
                accept="image/*"
                ref={bodyRef}
                onChange={handleBodyUpload}
                style={{ display: 'none' }}
              />
            </label>
            {bodyPhoto && (
              <button className="ghost-btn danger" onClick={handleClearBody}>
                Remove
              </button>
            )}
          </div>
        </div>
        <div className="body-preview">
          {bodyPhoto ? (
            <img src={bodyPhoto} alt="Your full-body" />
          ) : (
            <div className="body-preview-empty">No photo yet</div>
          )}
        </div>
      </section>

      <section className="upload-card">
        <h2 className="panel-title">Add a new piece</h2>
        <form onSubmit={handleUpload} className="upload-form">
          <div className="form-row">
            <label className="login-label">Name (optional)</label>
            <input
              className="login-input narrow"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Linen Oxford"
            />
          </div>
          <div className="form-row">
            <label className="login-label">Category</label>
            <select
              className="login-input narrow"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="top">Top (shirt)</option>
              <option value="bottom">Bottom (pants)</option>
            </select>
          </div>
          <div className="form-row">
            <label className="login-label">Photo</label>
            <input
              type="file"
              accept="image/*"
              ref={fileRef}
              required
              className="file-input"
            />
          </div>
          <button type="submit" className="primary-btn" disabled={busy}>
            {busy ? 'Adding…' : 'Add to Wardrobe'}
          </button>
        </form>
      </section>

      <section className="closet-section">
        <h2 className="panel-title">Your Wardrobe</h2>
        {items.length === 0 ? (
          <div className="empty-hint big">
            Your wardrobe is empty. Upload your first piece above.
          </div>
        ) : (
          <div className="closet-grid wide">
            {items.map((it) => (
              <div key={it.id} className="closet-card">
                <img src={it.dataUrl} alt={it.name || it.category} />
                <div className="closet-card-info">
                  <div className="closet-card-cat">{it.category}</div>
                  <div className="closet-card-name">{it.name || 'Unnamed'}</div>
                  <button className="ghost-btn danger" onClick={() => handleDelete(it.id)}>
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default EditWardrobe;
