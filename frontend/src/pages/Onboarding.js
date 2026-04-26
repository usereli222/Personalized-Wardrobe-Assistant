import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fileUrl } from '../services/api';
import {
  listWardrobeItems,
  uploadBodyPhoto,
  uploadWardrobeArchive,
  fetchBodyPhoto,
} from '../services/wardrobeApi';

function Onboarding() {
  const navigate = useNavigate();
  const [bodyPhotoUrl, setBodyPhotoUrl] = useState(null);
  const [items, setItems] = useState([]);
  const [bodyBusy, setBodyBusy] = useState(false);
  const [zipBusy, setZipBusy] = useState(false);
  const [error, setError] = useState('');
  const [skipped, setSkipped] = useState([]);
  const bodyRef = useRef(null);
  const zipRef = useRef(null);

  const refresh = async () => {
    try { setItems(await listWardrobeItems()); } catch { /* ignore */ }
    try {
      const { body_photo_url } = await fetchBodyPhoto();
      setBodyPhotoUrl(body_photo_url);
    } catch { setBodyPhotoUrl(null); }
  };

  useEffect(() => { refresh(); }, []);

  const handleBodyUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError('');
    setBodyBusy(true);
    try {
      const { body_photo_url } = await uploadBodyPhoto(file);
      setBodyPhotoUrl(body_photo_url);
    } catch (err) {
      setError(err.message);
    } finally {
      setBodyBusy(false);
      if (bodyRef.current) bodyRef.current.value = '';
    }
  };

  const handleZipUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError('');
    setZipBusy(true);
    setSkipped([]);
    try {
      const { created, skipped: sk } = await uploadWardrobeArchive(file);
      setSkipped(sk || []);
      await refresh();
      if ((created?.length || 0) === 0) {
        setError('No images were found in that zip.');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setZipBusy(false);
      if (zipRef.current) zipRef.current.value = '';
    }
  };

  const ready = !!bodyPhotoUrl && items.length >= 1;

  return (
    <div className="onboarding-page">
      <div className="onboarding-intro">
        <h1>Set up your wardrobe</h1>
        <p>Upload a full-body photo and a zip of clothing images. The model categorizes each item for you.</p>
      </div>

      <div className="onboarding-grid">
        <section className="onboard-card">
          <h2 className="panel-title">Step 1 — Your full-body photo</h2>
          <div className="body-preview large">
            {bodyPhotoUrl ? (
              <img src={fileUrl(bodyPhotoUrl)} alt="You" />
            ) : (
              <div className="body-preview-empty">No photo yet</div>
            )}
          </div>
          <label className={`ghost-btn upload-trigger ${bodyBusy ? 'disabled' : ''}`}>
            {bodyBusy ? 'Uploading…' : (bodyPhotoUrl ? 'Replace photo' : 'Upload photo')}
            <input
              type="file"
              accept="image/*"
              ref={bodyRef}
              onChange={handleBodyUpload}
              style={{ display: 'none' }}
              disabled={bodyBusy}
            />
          </label>
        </section>

        <section className="onboard-card">
          <h2 className="panel-title">Step 2 — Your wardrobe (.zip)</h2>
          <p className="muted small">
            One zip file containing a photo of each item. Subfolders OK; non-images are ignored.
          </p>

          <label className={`primary-btn upload-trigger ${zipBusy ? 'disabled' : ''}`}>
            {zipBusy ? 'Classifying…' : 'Upload zip'}
            <input
              type="file"
              accept=".zip,application/zip,application/x-zip-compressed"
              ref={zipRef}
              onChange={handleZipUpload}
              style={{ display: 'none' }}
              disabled={zipBusy}
            />
          </label>

          <div className="onboard-summary">
            <div className="onboard-count">{items.length} item{items.length === 1 ? '' : 's'} in your wardrobe</div>
            {items.length > 0 && (
              <div className="closet-grid small">
                {items.map((it) => (
                  <div key={it.id} className="mini-tile" title={`${it.category}${it.subcategory ? ' · ' + it.subcategory : ''}`}>
                    <img src={fileUrl(it.image_url)} alt={it.name || it.category} />
                  </div>
                ))}
              </div>
            )}
            {skipped.length > 0 && (
              <div className="muted small" style={{ marginTop: 8 }}>
                Skipped {skipped.length} non-image entr{skipped.length === 1 ? 'y' : 'ies'}.
              </div>
            )}
          </div>
        </section>
      </div>

      {error && <div className="onboard-error">{error}</div>}

      <footer className="onboard-footer">
        <button
          className="primary-btn large"
          disabled={!ready}
          onClick={() => navigate('/wardrobe')}
        >
          {ready ? 'Enter the Mirror' : 'Need a body photo and at least 1 item'}
        </button>
      </footer>
    </div>
  );
}

export default Onboarding;
