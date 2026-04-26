import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { login, signup } from '../services/auth';
import { listWardrobeItems } from '../services/wardrobeApi';

const DEMO = { username: 'demo', email: 'demo@demo.com', password: 'demo' };

function Login({ onAuthed }) {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const goAfterAuth = async (u) => {
    onAuthed?.(u);
    try {
      const items = await listWardrobeItems();
      navigate(items.length === 0 ? '/onboarding' : '/wardrobe', { replace: true });
    } catch {
      navigate('/wardrobe', { replace: true });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!username.trim() || !password) {
      setError('Please enter both a username and password.');
      return;
    }
    setBusy(true);
    try {
      await login({ username: username.trim(), password });
      await goAfterAuth(username.trim());
    } catch (err) {
      setError(err.message || 'Login failed.');
    } finally {
      setBusy(false);
    }
  };

  // One-click demo: try login, fall back to signup if the in-memory store
  // was cleared on backend restart.
  const handleDemo = async () => {
    setError('');
    setBusy(true);
    try {
      try {
        await login(DEMO);
      } catch {
        await signup(DEMO);
      }
      await goAfterAuth(DEMO.username);
    } catch (err) {
      setError(err.message || 'Demo login failed.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-scene">
      <div className="login-glow" />
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="login-emblem">✦</div>
        <h1 className="login-title">Enter the Wardrobe</h1>
        <p className="login-sub">Sign in to your sanctuary of style</p>

        <label className="login-label">Username</label>
        <input className="login-input" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="your name" autoFocus />

        <label className="login-label">Password</label>
        <input className="login-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />

        {error && <div className="login-error">{error}</div>}

        <button type="submit" className="login-button" disabled={busy}>
          {busy ? 'Signing in…' : 'Step Inside'}
        </button>

        <button type="button" className="ghost-btn demo-button" onClick={handleDemo} disabled={busy}>
          ✦ Use demo account
        </button>

        <div className="login-footer">
          New here? <Link to="/signup" className="login-link">Create an account</Link>
        </div>
      </form>
    </div>
  );
}

export default Login;
