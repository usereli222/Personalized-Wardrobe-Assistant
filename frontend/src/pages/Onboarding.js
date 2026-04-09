import React, { useState } from 'react';
import { createUser } from '../services/api';

const SKIN_TONE_PRESETS = [
  { name: 'Fair (Cool Winter)', season: 'cool_winter', h: 20, s: 30, l: 85 },
  { name: 'Light (Cool Summer)', season: 'cool_summer', h: 25, s: 35, l: 75 },
  { name: 'Medium (Warm Spring)', season: 'warm_spring', h: 28, s: 45, l: 65 },
  { name: 'Tan (Warm Autumn)', season: 'warm_autumn', h: 25, s: 50, l: 55 },
  { name: 'Brown (Warm Autumn)', season: 'warm_autumn', h: 22, s: 55, l: 40 },
  { name: 'Dark (Cool Winter)', season: 'cool_winter', h: 20, s: 50, l: 30 },
];

function Onboarding({ onComplete }) {
  const [name, setName] = useState('');
  const [selectedTone, setSelectedTone] = useState(null);
  const [location, setLocation] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name || selectedTone === null) return;

    setLoading(true);
    const tone = SKIN_TONE_PRESETS[selectedTone];
    try {
      const res = await createUser({
        name,
        skin_tone: { h: tone.h, s: tone.s, l: tone.l },
        season: tone.season,
        location_name: location || null,
        latitude: 40.7128,
        longitude: -74.006,
      });
      onComplete(String(res.data.id));
    } catch (err) {
      alert('Error creating profile: ' + (err.response?.data?.detail || err.message));
    }
    setLoading(false);
  };

  return (
    <div>
      <h1>Welcome to Wardrobe AI</h1>
      <p style={{ marginBottom: 24, color: '#6e6e73' }}>
        Set up your profile to get personalized outfit recommendations.
      </p>
      <form onSubmit={handleSubmit} className="card" style={{ maxWidth: 500 }}>
        <label>Your Name</label>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Enter your name" required />

        <label>Skin Tone / Color Season</label>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
          {SKIN_TONE_PRESETS.map((tone, i) => (
            <div
              key={i}
              onClick={() => setSelectedTone(i)}
              style={{
                cursor: 'pointer',
                textAlign: 'center',
                padding: 8,
                borderRadius: 8,
                border: selectedTone === i ? '2px solid #0071e3' : '2px solid transparent',
                background: selectedTone === i ? '#f0f0f5' : 'transparent',
              }}
            >
              <div
                className="color-swatch"
                style={{ background: `hsl(${tone.h}, ${tone.s}%, ${tone.l}%)`, width: 48, height: 48 }}
              />
              <div style={{ fontSize: 11, marginTop: 4 }}>{tone.name}</div>
            </div>
          ))}
        </div>

        <label>Location (optional)</label>
        <input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="e.g. New York, NY" />

        <button type="submit" className="btn-primary" disabled={loading || !name || selectedTone === null}>
          {loading ? 'Setting up...' : 'Get Started'}
        </button>
      </form>
    </div>
  );
}

export default Onboarding;
