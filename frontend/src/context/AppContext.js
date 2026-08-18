import React, { createContext, useContext, useEffect, useMemo, useState, useCallback, useRef } from 'react';
import axios from 'axios';
import { useAuth, ROLE_META, DEMO_ROLES } from './AuthContext';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const AppCtx = createContext(null);

const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);

export function AppProvider({ children }) {
  const { authUser, demoLogin } = useAuth();
  const [requests, setRequests] = useState([]);
  const [audit, setAudit] = useState([]);
  const [vaultLog, setVaultLog] = useState([]);
  const [identities, setIdentities] = useState({});
  const [stats, setStats] = useState(null);
  const [loaded, setLoaded] = useState(false);

  const roleId = authUser?.role || 'student';
  const role = {
    id: roleId, name: authUser?.name || 'User', first: (authUser?.name || 'User').split(' ')[0],
    title: ROLE_META[roleId]?.title || roleId, dept: '', soaId: authUser?.soaId,
  };
  const roles = DEMO_ROLES.map((r) => ({ id: r, name: cap(r), title: ROLE_META[r]?.title || r }));

  const fetchGen = useRef(0);
  const fetchAll = useCallback(async () => {
    const gen = ++fetchGen.current;
    try {
      const [rq, au, vl, st] = await Promise.all([
        axios.get(`${API}/requests`), axios.get(`${API}/audit`),
        axios.get(`${API}/vault/log`), axios.get(`${API}/stats`),
      ]);
      if (gen !== fetchGen.current) return;
      setRequests(rq.data); setAudit(au.data); setVaultLog(vl.data); setStats(st.data);
    } catch (e) { console.error('Failed to load SOA data', e); }
    finally { if (gen === fetchGen.current) setLoaded(true); }
  }, []);

  useEffect(() => { if (authUser) fetchAll(); }, [authUser, fetchAll]);

  const refreshAudit = async () => {
    try {
      const [au, st] = await Promise.all([axios.get(`${API}/audit`), axios.get(`${API}/stats`)]);
      setAudit(au.data); setStats(st.data);
    } catch (e) { console.error(e); }
  };

  // Persona switcher = real re-authentication (issues a new token), then reload data.
  const setRoleId = async (id) => { try { await demoLogin(id); await fetchAll(); } catch (e) { console.error(e); } };

  const submitRequest = async (text, opts = {}) => {
    const { data } = await axios.post(`${API}/requests`, { text, anonymous: !!opts.anonymous, via_voice: !!opts.viaVoice });
    setRequests((r) => [data, ...r]); refreshAudit();
    return data;
  };
  const decideApproval = async (reqId, decision, reason) => {
    const { data } = await axios.post(`${API}/requests/${reqId}/decision`, { decision, reason });
    setRequests((rs) => rs.map((r) => (r.id === reqId ? data : r))); refreshAudit();
    return data;
  };
  const accessVault = async (caseId, justification) => {
    const { data } = await axios.post(`${API}/vault/access`, { case_id: caseId, justification });
    setIdentities((m) => ({ ...m, [caseId]: data.identity }));
    setVaultLog((v) => [...v, data.log]); refreshAudit();
    return data;
  };
  const verifyChain = async () => (await axios.post(`${API}/audit/verify`)).data;
  const tamperEvent = async (index = 2) => { await axios.post(`${API}/audit/tamper`, { index }); refreshAudit(); };
  const rollback = async (evt) => { const { data } = await axios.post(`${API}/audit/rollback`, { event_id: evt.id }); refreshAudit(); return data; };
  const replayRequest = async (reqId) => (await axios.get(`${API}/audit/replay/${reqId}`)).data;

  const transcribeVoice = async (blob, lang) => {
    const fd = new FormData(); fd.append('audio', blob, 'clip.webm'); if (lang) fd.append('lang', lang);
    return (await axios.post(`${API}/voice/transcribe`, fd, { timeout: 60000 })).data;
  };
  const startConversation = async (anonymous) => (await axios.post(`${API}/conversation/start`, { anonymous: !!anonymous })).data;
  const conversationTurn = async (sessionId, { text, blob, speak = true } = {}) => {
    const fd = new FormData(); fd.append('sessionId', sessionId);
    if (text) fd.append('text', text); if (blob) fd.append('audio', blob, 'turn.webm');
    fd.append('speak', speak ? 'true' : 'false');
    const { data } = await axios.post(`${API}/conversation/turn`, fd, { timeout: 90000 });
    if (data.done) fetchAll();
    return data;
  };
  const sendMessage = async (reqId, text) => {
    const { data } = await axios.post(`${API}/requests/${reqId}/messages`, { text });
    setRequests((rs) => rs.map((r) => (r.id === reqId ? data : r))); refreshAudit();
    return data;
  };
  const resetDemo = async () => { try { await axios.post(`${API}/reset`); } catch (e) { console.error(e); } window.location.href = '/'; };

  const value = useMemo(() => ({
    role, roleId, setRoleId, roles, requests, audit, vaultLog, identities, stats, loaded,
    submitRequest, decideApproval, accessVault, verifyChain, tamperEvent, rollback, replayRequest,
    transcribeVoice, sendMessage, resetDemo, fetchAll, startConversation, conversationTurn,
  }), [role, roleId, requests, audit, vaultLog, identities, stats, loaded]); // eslint-disable-line react-hooks/exhaustive-deps

  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>;
}

export const useApp = () => useContext(AppCtx);
