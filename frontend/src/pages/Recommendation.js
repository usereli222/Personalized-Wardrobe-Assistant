import React, { useState, useEffect } from 'react';
import { getOutfitRecommendation } from '../services/api';

const API_HOST = process.env.REACT_APP_API_HOST || 'http://localhost:8000';

function Recommendation({ userId }) {
  const [recommendation, setRecommendation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchRecommendation = async () => {
      try {
        const res = await getOutfitRecommendation(userId);
        setRecommendation(res.data);
      } catch (err) {
        setError(err.response?.data?.detail || err.message);
      }
      setLoading(false);
    };
    fetchRecommendation();
  }, [userId]);

  if (loading) return <div className="loading">Finding your outfit for today...</div>;
  if (error) return <div className="card">Error: {error}</div>;
  if (!recommendation) return null;

  const { recommended_colors, lighting_condition, weather_description, outfit } = recommendation;
  const categoryOrder = ['top', 'bottom', 'outerwear', 'shoes', 'accessory'];

  return (
    <div>
      <h1>Today's Outfit</h1>

      {/* Weather + lighting */}
      <div className="card">
        <div style={{ display: 'flex', gap: 24, alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 13, color: '#6e6e73' }}>Weather</div>
            <div style={{ fontWeight: 500, textTransform: 'capitalize' }}>{weather_description}</div>
          </div>
          <div>
            <div style={{ fontSize: 13, color: '#6e6e73' }}>Lighting</div>
            <div style={{ fontWeight: 500, textTransform: 'capitalize' }}>{lighting_condition.replace('_', ' ')}</div>
          </div>
        </div>
      </div>

      {/* Recommended color palette */}
      <div className="card">
        <h2>Recommended Colors for Today</h2>
        <div className="color-palette">
          {recommended_colors.map((c, i) => (
            <div key={i} style={{ textAlign: 'center' }}>
              <span
                className="color-swatch"
                style={{
                  background: `hsl(${c.h}, ${c.s}%, ${c.l}%)`,
                  width: 40,
                  height: 40,
                }}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Outfit recommendations by category */}
      {categoryOrder.map((cat) => {
        const items = outfit[cat];
        if (!items || items.length === 0) return null;
        return (
          <div key={cat} className="outfit-section">
            <h3>{cat === 'top' ? 'Tops' : cat === 'bottom' ? 'Bottoms' : cat + 's'}</h3>
            <div className="grid">
              {items.map((item) => (
                <div key={item.id} className="item-card">
                  <img src={`${API_HOST}/uploads/${item.image_path}`} alt={item.name || item.category} />
                  <div className="item-info">
                    <div style={{ fontWeight: 500 }}>{item.name || 'Unnamed'}</div>
                    {item.dominant_colors && (
                      <div className="color-palette">
                        {item.dominant_colors.map((c, i) => (
                          <span
                            key={i}
                            className="color-swatch"
                            style={{ background: `hsl(${c.h}, ${c.s}%, ${c.l}%)` }}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}

      {Object.keys(outfit).length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <p style={{ color: '#6e6e73' }}>No wardrobe items yet! Add some clothes to get recommendations.</p>
        </div>
      )}
    </div>
  );
}

export default Recommendation;
