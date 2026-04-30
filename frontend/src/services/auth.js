import { api } from './api';
import {
  fbSignIn,
  fbSignUp,
  fbSignOut,
  fbCurrentUser,
  fbOnAuthChanged,
} from './firebase';

export const signup = async ({ email, password, displayName }) => {
  const user = await fbSignUp({ email, password, displayName });
  // Fire-and-forget: tell the backend to upsert the User row + record a login.
  await api.postJson('/auth/login-event', {}).catch(() => {});
  return user;
};

export const login = async ({ email, password }) => {
  const user = await fbSignIn({ email, password });
  await api.postJson('/auth/login-event', {}).catch(() => {});
  return user;
};

export const logout = () => fbSignOut();

export const isAuthed = () => !!fbCurrentUser();

export const onAuthChanged = (cb) => fbOnAuthChanged(cb);

export const fetchMe = () => api.get('/auth/me');

export const fetchLoginHistory = () => api.get('/auth/login-history');
