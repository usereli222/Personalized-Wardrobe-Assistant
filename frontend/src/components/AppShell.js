import React from 'react';
import { NavLink, useNavigate, Outlet, Navigate } from 'react-router-dom';
import { logout } from '../services/auth';

export function RequireAuth({ user, children }) {
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function AppShell({ username }) {
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  const tab = ({ isActive }) => `nav-tab ${isActive ? 'active' : ''}`;

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-brand">
          <span className="wardrobe-spark">✦</span> Wardrobe
        </div>
        <nav className="app-nav">
          <NavLink to="/wardrobe" className={tab}>Wardrobe</NavLink>
          <NavLink to="/outfits" className={tab}>Outfits</NavLink>
          <NavLink to="/tryon" className={tab}>Try-On</NavLink>
          <NavLink to="/saved" className={tab}>Saved</NavLink>
        </nav>
        <div className="app-header-right">
          {username && <span className="app-user">{username}</span>}
          <button className="ghost-btn subtle" onClick={handleLogout}>Sign out</button>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}

export default AppShell;
