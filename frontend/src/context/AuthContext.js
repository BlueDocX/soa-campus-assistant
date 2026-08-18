import React, { createContext, useContext, useEffect, useMemo, useState, useCallback } from 'react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const AuthCtx = createContext(null);

export const ROLE_META = {
  student: { title: 'Requester \u00b7 Student' },
  approver: { title: 'Academic Approver' },
  operator: { title: 'Unit Operator' },
  auditor: { title: 'Institutional Auditor' },
  admin: { title: 'Administrator' },
};
export const DEMO_ROLES = ['student', 'approver', 'operator', 'auditor', 'admin'];

function applyToken(token) {
  if (token) axios.defaults.headers.common.Authorization = `Bearer ${token}`;
  else delete axios.defaults.headers.common.Authorization;
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => { try { return localStorage.getItem('soa_token'); } catch { return null; } });
  const [authUser, setAuthUser] = useState(null);
  const [authReady, setAuthReady] = useState(false);

  applyToken(token);

  const persist = useCallback((tok, user) => {
    try { tok ? localStorage.setItem('soa_token', tok) : localStorage.removeItem('soa_token'); } catch { /* ignore */ }
    applyToken(tok); setToken(tok); setAuthUser(user);
  }, []);

  useEffect(() => {
    let live = true;
    (async () => {
      if (!token) { setAuthReady(true); return; }
      try {
        const { data } = await axios.get(`${API}/auth/me`);
        if (live) setAuthUser(data);
      } catch { if (live) persist(null, null); }
      if (live) setAuthReady(true);
    })();
    return () => { live = false; };
  }, [token, persist]);

  const login = async (email, password) => {
    const { data } = await axios.post(`${API}/auth/login`, { email, password });
    persist(data.token, data.user);
    return data.user;
  };
  const demoLogin = async (role) => {
    const { data } = await axios.post(`${API}/auth/demo-login`, { role });
    persist(data.token, data.user);
    return data.user;
  };
  const logout = () => persist(null, null);

  const value = useMemo(() => ({ token, authUser, authReady, login, demoLogin, logout,
    isAuthed: !!token && !!authUser }), [token, authUser, authReady]); // eslint-disable-line react-hooks/exhaustive-deps

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);
