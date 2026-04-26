import { api, setToken, clearToken, getToken } from './api';

export const signup = async ({ username, email, password }) => {
  const { token } = await api.postJson('/auth/signup', { username, email, password });
  setToken(token);
  return token;
};

export const login = async ({ username, password }) => {
  const { token } = await api.postJson('/auth/login', { username, password });
  setToken(token);
  return token;
};

export const logout = () => clearToken();

export const isAuthed = () => !!getToken();

export const fetchMe = () => api.get('/auth/me');

export const fetchLoginHistory = () => api.get('/auth/login-history');
