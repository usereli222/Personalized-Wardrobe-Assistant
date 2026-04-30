import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { signup } from '../services/auth';

function Signup({ onAuthed }) {
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!email.trim() || !password) {
      setError('Email and password are required.');
      return;
    }
    setBusy(true);
    try {
      const user = await signup({
        email: email.trim(),
        password,
        displayName: displayName.trim() || undefined,
      });
      onAuthed?.(user);
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

        <label className="login-label">Display name (optional)</label>
        <input className="login-input" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="how you'd like to be called" autoFocus />

        <label className="login-label">Email</label>
        <input className="login-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />

        <label className="login-label">Password</label>
        <input className="login-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="at least 6 characters" />

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
