// Firebase web SDK init + thin auth helpers.
//
// Config comes from REACT_APP_FIREBASE_* env vars (set in frontend/.env).
// The values come from Firebase Console -> Project Settings ->
// "Your apps" -> Web app config.

import { initializeApp } from 'firebase/app';
import {
  getAuth,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  updateProfile,
} from 'firebase/auth';

const firebaseConfig = {
  apiKey: process.env.REACT_APP_FIREBASE_API_KEY,
  authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID,
  storageBucket: process.env.REACT_APP_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.REACT_APP_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.REACT_APP_FIREBASE_APP_ID,
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

export const fbSignUp = async ({ email, password, displayName }) => {
  const cred = await createUserWithEmailAndPassword(auth, email, password);
  if (displayName) {
    await updateProfile(cred.user, { displayName });
  }
  return cred.user;
};

export const fbSignIn = ({ email, password }) =>
  signInWithEmailAndPassword(auth, email, password).then((cred) => cred.user);

export const fbSignOut = () => signOut(auth);

export const fbOnAuthChanged = (cb) => onAuthStateChanged(auth, cb);

export const fbCurrentUser = () => auth.currentUser;

export const fbGetIdToken = (forceRefresh = false) => {
  const user = auth.currentUser;
  return user ? user.getIdToken(forceRefresh) : Promise.resolve(null);
};
