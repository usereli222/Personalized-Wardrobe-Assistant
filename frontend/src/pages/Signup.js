import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { signup } from '../services/auth';

function Signup({ onAuthed }) {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!username.trim() || !email.trim() || !password) {
      setError('All fields are required.');
      return;
    }
    setBusy(true);
    try {
      await signup({ username: username.trim(), email: email.trim(), password });
      onAuthed?.(username.trim());
      navigate('/onboarding', { replace: true });
    } catch (err) {
      setError(err.message || 'Signup failed.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-scene">
      <div className="login-glow" />
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="login-emblem">✦</div>
        <h1 className="login-title">Forge a Wardrobe</h1>
        <p className="login-sub">Make an account to begin</p>

        <label className="login-label">Username</label>
        <input className="login-input" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="your name" autoFocus />

        <label className="login-label">Email</label>
        <input className="login-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />

        <label className="login-label">Password</label>
        <input className="login-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />

        {error && <div className="login-error">{error}</div>}

        <button type="submit" className="login-button" disabled={busy}>
          {busy ? 'Creating…' : 'Create Account'}
        </button>

        <div className="login-footer">
          Already have one? <Link to="/login" className="login-link">Sign in</Link>
        </div>
      </form>
    </div>
  );
}

export default Signup;
