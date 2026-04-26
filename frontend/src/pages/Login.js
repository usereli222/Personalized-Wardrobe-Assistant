import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function Login({ onLogin }) {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('Please enter both a username and password.');
      return;
    }
    onLogin(username.trim());
    navigate('/wardrobe');
  };

  return (
    <div className="login-scene">
      <div className="login-glow" />
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="login-emblem">✦</div>
        <h1 className="login-title">Enter the Wardrobe</h1>
        <p className="login-sub">Sign in to your sanctuary of style</p>

        <label className="login-label">Username</label>
        <input
          className="login-input"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="your name"
          autoFocus
        />

        <label className="login-label">Password</label>
        <input
          className="login-input"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
        />

        {error && <div className="login-error">{error}</div>}

        <button type="submit" className="login-button">
          Step Inside
        </button>
      </form>
    </div>
  );
}

export default Login;
