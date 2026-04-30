import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Door from './pages/Door';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Onboarding from './pages/Onboarding';
import Wardrobe from './pages/Wardrobe';
import Outfits from './pages/Outfits';
import TryOn from './pages/TryOn';
import AppShell, { RequireAuth } from './components/AppShell';
import { warmModels } from './services/wardrobeApi';

const USERNAME_KEY = 'wardrobeUsername';

function App() {
  const [username, setUsername] = useState(() => localStorage.getItem(USERNAME_KEY));

  // Trigger ML model load (FashionCLIP + FAISS index) once at app boot so
  // the first wardrobe upload doesn't pay the ~10-30s cold-start cost.
  // Fire-and-forget; errors are non-fatal.
  useEffect(() => { warmModels().catch(() => {}); }, []);

  const handleAuthed = (u) => {
    setUsername(u);
    localStorage.setItem(USERNAME_KEY, u);
  };

  return (
    <div className="app">
      <Routes>
        <Route path="/" element={<Door />} />
        <Route path="/login" element={<Login onAuthed={handleAuthed} />} />
        <Route path="/signup" element={<Signup onAuthed={handleAuthed} />} />

        <Route element={<RequireAuth><AppShell username={username} /></RequireAuth>}>
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/wardrobe" element={<Wardrobe />} />
          <Route path="/outfits" element={<Outfits />} />
          <Route path="/tryon" element={<TryOn />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

export default App;
