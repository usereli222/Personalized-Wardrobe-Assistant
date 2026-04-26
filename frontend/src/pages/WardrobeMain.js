import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listItems, getBodyPhoto } from '../services/wardrobeStore';
import { generateTryOn } from '../services/tryon';

function MagicMirror({ status, bodyPhoto, resultUrl, error }) {
  // status: 'empty' | 'idle' | 'conjuring' | 'ready' | 'error'
  let body;
  if (status === 'conjuring') {
    body = (
      <>
        <img src={bodyPhoto} alt="" className="mirror-image faded" />
        <div className="mirror-overlay">
          <div className="mirror-rune" />
          <div className="mirror-loading-text">Conjuring your outfit…</div>
        </div>
      </>
    );
  } else if (status === 'ready' && resultUrl) {
    body = <img src={resultUrl} alt="Try-on result" className="mirror-image" />;
  } else if (status === 'error') {
    body = (
      <div className="mirror-empty">
        <div className="mirror-empty-glyph">⚠</div>
        <div className="mirror-empty-text">{error || 'Something went wrong.'}</div>
      </div>
    );
  } else if (status === 'empty') {
    body = (
      <div className="mirror-empty">
        <div className="mirror-empty-glyph">✦</div>
        <div className="mirror-empty-text">
          Upload a full-body photo in <em>Edit Wardrobe</em> to awaken the mirror.
        </div>
      </div>
    );
  } else {
    body = <img src={bodyPhoto} alt="You" className="mirror-image idle" />;
  }

  return (
    <div className="magic-mirror">
      <div className="mirror-frame">
        <div className="mirror-glow" />
        <div className="mirror-surface">{body}</div>
      </div>
    </div>
  );
}

function WardrobeMain({ username, onLogout }) {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [bodyPhoto, setBodyPhoto] = useState(null);
  const [selectedTopId, setSelectedTopId] = useState(null);
  const [selectedBottomId, setSelectedBottomId] = useState(null);
  const [resultUrl, setResultUrl] = useState(null);
  const [conjuring, setConjuring] = useState(false);
  const [error, setError] = useState(null);
  const lastUrlRef = useRef(null);

  useEffect(() => {
    setItems(listItems(username));
    setBodyPhoto(getBodyPhoto(username));
  }, [username]);

  // Revoke blob URLs we created so we don't leak memory
  useEffect(() => {
    return () => {
      if (lastUrlRef.current) URL.revokeObjectURL(lastUrlRef.current);
    };
  }, []);

  const tops = useMemo(() => items.filter((i) => i.category === 'top'), [items]);
  const bottoms = useMemo(() => items.filter((i) => i.category === 'bottom'), [items]);

  const selectedTop = tops.find((t) => t.id === selectedTopId);
  const selectedBottom = bottoms.find((b) => b.id === selectedBottomId);

  const canSubmit =
    !!bodyPhoto && !!selectedTop && !!selectedBottom && !conjuring;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setError(null);
    setConjuring(true);
    try {
      const url = await generateTryOn({
        bodyDataUrl: bodyPhoto,
        topDataUrl: selectedTop.dataUrl,
        bottomDataUrl: selectedBottom.dataUrl,
      });
      if (lastUrlRef.current) URL.revokeObjectURL(lastUrlRef.current);
      lastUrlRef.current = url;
      setResultUrl(url);
    } catch (err) {
      setError(err.message || 'Try-on failed.');
      setResultUrl(null);
    } finally {
      setConjuring(false);
    }
  };

  let mirrorStatus;
  if (conjuring) mirrorStatus = 'conjuring';
  else if (error) mirrorStatus = 'error';
  else if (resultUrl) mirrorStatus = 'ready';
  else if (!bodyPhoto) mirrorStatus = 'empty';
  else mirrorStatus = 'idle';

  return (
    <div className="wardrobe-main">
      <header className="wardrobe-header">
        <div className="wardrobe-greeting">
          <span className="wardrobe-spark">✦</span> Welcome, {username}
        </div>
        <div className="wardrobe-header-actions">
          <button className="ghost-btn" onClick={() => navigate('/wardrobe/edit')}>
            ✎ Edit Wardrobe
          </button>
          <button className="ghost-btn subtle" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </header>

      <div className="wardrobe-stage">
        <aside className="closet-panel">
          <h3 className="panel-title">Tops</h3>
          {tops.length === 0 ? (
            <div className="empty-hint">
              No tops yet. Add some in <em>Edit Wardrobe</em>.
            </div>
          ) : (
            <div className="closet-grid">
              {tops.map((t) => (
                <button
                  key={t.id}
                  className={`closet-tile ${selectedTopId === t.id ? 'selected' : ''}`}
                  onClick={() => setSelectedTopId(t.id)}
                  title={t.name || 'Top'}
                >
                  <img src={t.dataUrl} alt={t.name || 'top'} />
                </button>
              ))}
            </div>
          )}
        </aside>

        <div className="mannequin-stage">
          <MagicMirror
            status={mirrorStatus}
            bodyPhoto={bodyPhoto}
            resultUrl={resultUrl}
            error={error}
          />
          <div className="mannequin-caption">
            {selectedTop || selectedBottom ? (
              <>
                <span>{selectedTop?.name || (selectedTop ? 'Top' : '—')}</span>
                <span className="dot">·</span>
                <span>{selectedBottom?.name || (selectedBottom ? 'Bottoms' : '—')}</span>
              </>
            ) : (
              <span className="muted">
                {bodyPhoto
                  ? 'Pick a top and a bottom, then submit to dress the mirror.'
                  : 'Upload your full-body photo to awaken the mirror.'}
              </span>
            )}
          </div>
        </div>

        <aside className="closet-panel">
          <h3 className="panel-title">Bottoms</h3>
          {bottoms.length === 0 ? (
            <div className="empty-hint">
              No bottoms yet. Add some in <em>Edit Wardrobe</em>.
            </div>
          ) : (
            <div className="closet-grid">
              {bottoms.map((b) => (
                <button
                  key={b.id}
                  className={`closet-tile ${selectedBottomId === b.id ? 'selected' : ''}`}
                  onClick={() => setSelectedBottomId(b.id)}
                  title={b.name || 'Bottom'}
                >
                  <img src={b.dataUrl} alt={b.name || 'bottom'} />
                </button>
              ))}
            </div>
          )}
        </aside>
      </div>

      <footer className="wardrobe-footer">
        <button
          className="primary-btn"
          disabled={!canSubmit}
          onClick={handleSubmit}
        >
          {conjuring ? 'Conjuring…' : 'Try It On'}
        </button>
        {!bodyPhoto && (
          <span className="footer-hint">
            ↳ Add your photo in <em>Edit Wardrobe</em> first.
          </span>
        )}
      </footer>
    </div>
  );
}

export default WardrobeMain;
