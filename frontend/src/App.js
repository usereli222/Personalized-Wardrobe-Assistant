import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Door from './pages/Door';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Onboarding from './pages/Onboarding';
import Wardrobe from './pages/Wardrobe';
import Outfits from './pages/Outfits';
import TryOn from './pages/TryOn';
import Saved from './pages/Saved';
import AppShell, { RequireAuth } from './components/AppShell';
import { onAuthChanged } from './services/auth';

function App() {
  const [user, setUser] = useState(null);
  const [authReady, setAuthReady] = useState(false);

  useEffect(() => {
    const unsub = onAuthChanged((u) => {
      setUser(u);
      setAuthReady(true);
    });
    return unsub;
  }, []);

  // Pages call onAuthed(user) right after signin/signup so we don't have to
  // wait for the next onAuthStateChanged tick.
  const handleAuthed = (u) => setUser(u);

  if (!authReady) return null;

  const displayName = user?.displayName || user?.email || null;

  return (
    <div className="app">
      <Routes>
        <Route path="/" element={<Door />} />
        <Route path="/login" element={<Login onAuthed={handleAuthed} />} />
        <Route path="/signup" element={<Signup onAuthed={handleAuthed} />} />

        <Route element={<RequireAuth user={user}><AppShell username={displayName} /></RequireAuth>}>
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/wardrobe" element={<Wardrobe />} />
          <Route path="/outfits" element={<Outfits />} />
          <Route path="/tryon" element={<TryOn />} />
          <Route path="/saved" element={<Saved />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

export default App;
