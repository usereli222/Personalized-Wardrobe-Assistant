import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Door from './pages/Door';
import Login from './pages/Login';
import WardrobeMain from './pages/WardrobeMain';
import EditWardrobe from './pages/EditWardrobe';

const USERNAME_KEY = 'wardrobeUsername';

function App() {
  const [username, setUsername] = useState(() => localStorage.getItem(USERNAME_KEY));

  useEffect(() => {
    if (username) {
      localStorage.setItem(USERNAME_KEY, username);
    } else {
      localStorage.removeItem(USERNAME_KEY);
    }
  }, [username]);

  const handleLogout = () => setUsername(null);

  const requireAuth = (element) =>
    username ? element : <Navigate to="/login" replace />;

  return (
    <div className="app">
      <Routes>
        <Route path="/" element={<Door />} />
        <Route path="/login" element={<Login onLogin={(u) => setUsername(u)} />} />
        <Route
          path="/wardrobe"
          element={requireAuth(
            <WardrobeMain username={username} onLogout={handleLogout} />
          )}
        />
        <Route
          path="/wardrobe/edit"
          element={requireAuth(<EditWardrobe username={username} />)}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

export default App;
