import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { fileUrl } from '../services/api';
import { listWardrobeItems, fetchBodyPhoto } from '../services/wardrobeApi';
import { generateTryOn } from '../services/tryon';

function MagicMirror({ status, bodyPhotoUrl, resultUrl, error }) {
  let body;
  if (status === 'conjuring') {
    body = (
      <>
        <img src={fileUrl(bodyPhotoUrl)} alt="" className="mirror-image faded" />
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
        <div className="mirror-empty-text">Upload a full-body photo to awaken the mirror.</div>
      </div>
    );
  } else {
    body = <img src={fileUrl(bodyPhotoUrl)} alt="You" className="mirror-image idle" />;
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

function Closet({ title, items, selectedId, onSelect, emptyHint }) {
  return (
    <aside className="closet-panel">
      <h3 className="panel-title">{title}</h3>
      {items.length === 0 ? (
        <div className="empty-hint">{emptyHint}</div>
      ) : (
        <div className="closet-grid">
          {items.map((it) => (
            <button
              key={it.id}
              className={`closet-tile ${selectedId === it.id ? 'selected' : ''}`}
              onClick={() => onSelect(it.id)}
              title={it.name || it.category}
            >
              <img src={fileUrl(it.image_url)} alt={it.name || it.category} />
            </button>
          ))}
        </div>
      )}
    </aside>
  );
}

function TryOn() {
  const navigate = useNavigate();
  const location = useLocation();
  const preselect = location.state || {};

  const [items, setItems] = useState([]);
  const [bodyPhotoUrl, setBodyPhotoUrl] = useState(null);
  const [selectedTopId, setSelectedTopId] = useState(preselect.topId || null);
  const [selectedBottomId, setSelectedBottomId] = useState(preselect.bottomId || null);
  const [resultUrl, setResultUrl] = useState(null);
  const [conjuring, setConjuring] = useState(false);
  const [error, setError] = useState(null);
  const lastUrlRef = useRef(null);

  useEffect(() => {
    (async () => {
      try {
        setItems(await listWardrobeItems());
      } catch (err) {
        setError(err.message);
      }
      try {
        const { body_photo_url } = await fetchBodyPhoto();
        setBodyPhotoUrl(body_photo_url);
      } catch {
        setBodyPhotoUrl(null);
      }
    })();
  }, []);

  useEffect(() => {
    return () => {
      if (lastUrlRef.current) URL.revokeObjectURL(lastUrlRef.current);
    };
  }, []);

  const tops = useMemo(() => items.filter((i) => i.category === 'top'), [items]);
  const bottoms = useMemo(() => items.filter((i) => i.category === 'bottom'), [items]);

  const selectedTop = tops.find((t) => t.id === selectedTopId);
  const selectedBottom = bottoms.find((b) => b.id === selectedBottomId);

  const canSubmit = !!bodyPhotoUrl && !!selectedTop && !!selectedBottom && !conjuring;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setError(null);
    setConjuring(true);
    try {
      const url = await generateTryOn({
        bodyPhotoUrl,
        topImageUrl: selectedTop.image_url,
        bottomImageUrl: selectedBottom.image_url,
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
  else if (!bodyPhotoUrl) mirrorStatus = 'empty';
  else mirrorStatus = 'idle';

  return (
    <div className="tryon-page">
      <div className="tryon-stage">
        <Closet
          title="Tops"
          items={tops}
          selectedId={selectedTopId}
          onSelect={setSelectedTopId}
          emptyHint={<>No tops. Add some in <button className="login-link" onClick={() => navigate('/wardrobe')}>Wardrobe</button>.</>}
        />
        <div className="mannequin-stage">
          <MagicMirror
            status={mirrorStatus}
            bodyPhotoUrl={bodyPhotoUrl}
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
                {bodyPhotoUrl
                  ? 'Pick a top and a bottom, then submit to dress the mirror.'
                  : 'Upload a body photo first.'}
              </span>
            )}
          </div>
        </div>
        <Closet
          title="Bottoms"
          items={bottoms}
          selectedId={selectedBottomId}
          onSelect={setSelectedBottomId}
          emptyHint={<>No bottoms. Add some in <button className="login-link" onClick={() => navigate('/wardrobe')}>Wardrobe</button>.</>}
        />
      </div>

      <footer className="tryon-footer">
        <button className="primary-btn" disabled={!canSubmit} onClick={handleSubmit}>
          {conjuring ? 'Conjuring…' : 'Try It On'}
        </button>
        {!bodyPhotoUrl && <span className="footer-hint">↳ Add your photo in <em>Wardrobe</em> first.</span>}
      </footer>
    </div>
  );
}

export default TryOn;
