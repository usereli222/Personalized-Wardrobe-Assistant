import React, { useState, useEffect } from 'react';
import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import Onboarding from './pages/Onboarding';
import Wardrobe from './pages/Wardrobe';
import Recommendation from './pages/Recommendation';

function App() {
  const [userId, setUserId] = useState(() => {
    return localStorage.getItem('wardrobeUserId') || null;
  });

  useEffect(() => {
    if (userId) {
      localStorage.setItem('wardrobeUserId', userId);
    }
  }, [userId]);

  if (!userId) {
    return (
      <div className="app">
        <Onboarding onComplete={(id) => setUserId(id)} />
      </div>
    );
  }

  return (
    <div className="app">
      <nav>
        <NavLink to="/recommend" className={({ isActive }) => isActive ? 'active' : ''}>
          Today's Outfit
        </NavLink>
        <NavLink to="/wardrobe" className={({ isActive }) => isActive ? 'active' : ''}>
          My Wardrobe
        </NavLink>
        <button className="btn-secondary" onClick={() => { localStorage.removeItem('wardrobeUserId'); setUserId(null); }}>
          Reset Profile
        </button>
      </nav>
      <Routes>
        <Route path="/recommend" element={<Recommendation userId={userId} />} />
        <Route path="/wardrobe" element={<Wardrobe userId={userId} />} />
        <Route path="*" element={<Navigate to="/recommend" replace />} />
      </Routes>
    </div>
  );
}

export default App;
