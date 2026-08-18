import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mic, Square, Send, Volume2, VolumeX, EyeOff, Loader2, Sparkles, FileText, MessageSquare, ShieldCheck, Bot, User } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Switch } from '../components/ui/switch';
import { toast } from 'sonner';

export default function AssistantPage() {
  const { startConversation, conversationTurn } = useApp();
  const navigate = useNavigate();

  const [anonymous, setAnonymous] = useState(false);
  const [started, setStarted] = useState(false);
  const [starting, setStarting] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [speakOn, setSpeakOn] = useState(true);
  const [done, setDone] = useState(false);
  const [requestId, setRequestId] = useState(null);

  const speakOnRef = useRef(true);
  const scrollRef = useRef(null);
  const audioRef = useRef(null);
  const mediaRef = useRef({ recorder: null, chunks: [], stream: null });

  useEffect(() => { speakOnRef.current = speakOn; }, [speakOn]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, busy]);

  useEffect(() => () => {
    if (mediaRef.current.stream) mediaRef.current.stream.getTracks().forEach((t) => t.stop());
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
  }, []);

  const playAudio = (b64) => {
    if (!b64 || !speakOnRef.current) return;
    try {
      if (audioRef.current) audioRef.current.pause();
      const a = new Audio(`data:audio/wav;base64,${b64}`);
      audioRef.current = a;
      a.play().catch(() => {});
    } catch { /* ignore */ }
  };

  const begin = async () => {
    if (starting) return;
    setStarting(true);
    try {
      const data = await startConversation(anonymous);
      setSessionId(data.id);
      setMessages(data.messages || []);
      setStarted(true);
      playAudio(data.audioBase64);
    } catch (e) {
      toast('Could not start the assistant', { description: 'Please try again in a moment.' });
    } finally {
      setStarting(false);
    }
  };

  const applyTurn = (data) => {
    setMessages(data.messages || []);
    playAudio(data.audioBase64);
    if (data.done) { setDone(true); setRequestId(data.requestId); }
  };

  const sendText = async () => {
    const text = input.trim();
    if (!text || busy || done) return;
    setInput('');
    setMessages((m) => [...m, { role: 'user', content: text }]);
    setBusy(true);
    try {
      const data = await conversationTurn(sessionId, { text, speak: speakOn });
      applyTurn(data);
    } catch (e) {
      toast('The assistant could not respond', { description: 'Please try again.' });
    } finally {
      setBusy(false);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendText(); }
  };

  // ---- Voice turn (record -> stop -> send audio) ----
  const startRecording = async () => {
    if (busy || done) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      const recorder = new MediaRecorder(stream, { mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : undefined });
      mediaRef.current = { recorder, chunks: [], stream };
      recorder.ondataavailable = (e) => { if (e.data.size) mediaRef.current.chunks.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        const blob = new Blob(mediaRef.current.chunks, { type: 'audio/webm' });
        if (!blob.size) return;
        setBusy(true);
        try {
          const data = await conversationTurn(sessionId, { blob, speak: speakOn });
          applyTurn(data);
        } catch (e) {
          toast('Voice turn failed', { description: 'Please try again or type your message.' });
        } finally {
          setBusy(false);
        }
      };
      recorder.start();
      setRecording(true);
    } catch (e) {
      toast('Microphone unavailable', { description: 'Permission denied — you can type instead.' });
    }
  };

  const stopRecording = () => {
    if (mediaRef.current.recorder?.state === 'recording') mediaRef.current.recorder.stop();
  };

  const micClick = () => {
    if (busy || done) return;
    if (recording) stopRecording(); else startRecording();
  };

  const startOver = () => {
    setStarted(false); setSessionId(null); setMessages([]); setInput('');
    setDone(false); setRequestId(null); setBusy(false);
  };

  // ---------- Pre-start screen ----------
  if (!started) {
    return (
      <div className="max-w-[720px] mx-auto animate-fade-up">
        <div className="mt-6 mb-8">
          <h1 className="text-5xl font-light tracking-tight">SOA Assistant</h1>
          <p className="text-[13px] text-[#8a8578] mt-3">Have a real conversation — type or talk. I understand English · हिन्दी · ଓଡ଼ିଆ and reply in your language.</p>
        </div>

        <div className="bg-[#151515] text-white rounded-3xl p-8 shadow-md">
          <div className="flex items-center gap-3 mb-5">
            <span className="rounded-full bg-[#F5D34B] text-[#151515] p-3"><Bot size={22} /></span>
            <div>
              <p className="text-[15px] font-semibold">Start a service conversation</p>
              <p className="text-[12px] text-white/60">Tell me what you need. I classify it, assign the right desk, and file an auditable request.</p>
            </div>
          </div>

          <label className="flex items-center justify-between gap-3 bg-white/5 rounded-2xl px-4 py-3.5 mb-5 cursor-pointer">
            <span className="flex items-center gap-2 text-[13px]"><EyeOff size={15} className="text-[#F5D34B]" /> Anonymous mode <span className="text-white/50">· no SOA ID asked, identity escrowed</span></span>
            <Switch checked={anonymous} onCheckedChange={setAnonymous} data-testid="assistant-anonymous-switch" />
          </label>

          <button onClick={begin} disabled={starting} data-testid="assistant-start-btn"
            className="w-full flex items-center justify-center gap-2 bg-[#F5D34B] text-[#151515] rounded-full py-4 text-[14px] font-semibold hover:brightness-95 transition-all disabled:opacity-50">
            {starting ? <Loader2 size={16} className="animate-spin" /> : <MessageSquare size={16} />}
            {starting ? 'Starting…' : 'Start conversation'}
          </button>
        </div>

        <p className="flex items-center gap-2 text-[11px] text-[#8a8578] mt-4 px-2"><ShieldCheck size={13} /> The assistant only gathers details. A deterministic orchestrator validates every action against policies, permissions and evidence before anything executes.</p>
      </div>
    );
  }

  // ---------- Conversation screen ----------
  return (
    <div className="max-w-[820px] mx-auto animate-fade-up">
      <div className="mt-6 mb-4 flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-light tracking-tight flex items-center gap-3">
            SOA Assistant
            {anonymous && <span className="text-[10px] bg-[#151515] text-white rounded-full px-3 py-1 font-medium flex items-center gap-1"><EyeOff size={11} /> Anonymous</span>}
          </h1>
          <p className="text-[12px] text-[#8a8578] mt-1">Session {sessionId}</p>
        </div>
        <button onClick={() => setSpeakOn((s) => !s)} data-testid="assistant-speaker-toggle"
          className="flex items-center gap-1.5 bg-white rounded-full px-4 py-2.5 text-[12px] font-medium shadow-sm hover:bg-[#e9e4d8] transition-colors">
          {speakOn ? <Volume2 size={15} /> : <VolumeX size={15} />} {speakOn ? 'Voice on' : 'Voice off'}
        </button>
      </div>

      {/* Chat transcript */}
      <div ref={scrollRef} data-testid="assistant-chat" className="bg-[#FBF9F4] rounded-3xl p-5 md:p-6 shadow-sm h-[52vh] min-h-[360px] overflow-y-auto">
        <div className="space-y-4">
          {messages.map((m, i) => {
            const agent = m.role === 'agent';
            return (
              <div key={i} className={`flex gap-2.5 ${agent ? '' : 'flex-row-reverse'}`} data-testid={`chat-msg-${m.role}`}>
                <span className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${agent ? 'bg-[#151515] text-[#F5D34B]' : 'bg-[#F5D34B] text-[#151515]'}`}>
                  {agent ? <Bot size={16} /> : <User size={16} />}
                </span>
                <div className={`max-w-[78%] rounded-2xl px-4 py-2.5 text-[13.5px] leading-relaxed ${agent ? 'bg-white text-[#151515]' : 'bg-[#151515] text-white'}`}>
                  {m.content}
                </div>
              </div>
            );
          })}
          {busy && (
            <div className="flex gap-2.5" data-testid="assistant-thinking">
              <span className="shrink-0 w-8 h-8 rounded-full bg-[#151515] text-[#F5D34B] flex items-center justify-center"><Bot size={16} /></span>
              <div className="bg-white rounded-2xl px-4 py-3 flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-[#b5b0a3] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-[#b5b0a3] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-[#b5b0a3] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Done banner */}
      {done && requestId && (
        <div className="mt-4 bg-[#151515] text-white rounded-3xl p-5 flex items-center justify-between flex-wrap gap-3 animate-fade-up" data-testid="assistant-done-banner">
          <div className="flex items-center gap-3">
            <span className="rounded-full bg-[#F5D34B] text-[#151515] p-2.5"><Sparkles size={18} /></span>
            <div>
              <p className="text-[14px] font-semibold">Request filed · {requestId}</p>
              <p className="text-[12px] text-white/60">Your governed request is on record with a full audit trail.</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => navigate(`/requests/${requestId}/report`)} data-testid="assistant-view-report-btn"
              className="flex items-center gap-1.5 bg-[#F5D34B] text-[#151515] rounded-full px-5 py-2.5 text-[12px] font-semibold hover:brightness-95 transition-all">
              <FileText size={14} /> View report
            </button>
            <button onClick={() => navigate(`/requests/${requestId}`)}
              className="flex items-center gap-1.5 bg-white/10 rounded-full px-4 py-2.5 text-[12px] font-medium hover:bg-white/20 transition-colors">
              Open request
            </button>
            <button onClick={startOver} data-testid="assistant-new-btn"
              className="flex items-center gap-1.5 bg-white/10 rounded-full px-4 py-2.5 text-[12px] font-medium hover:bg-white/20 transition-colors">
              New
            </button>
          </div>
        </div>
      )}

      {/* Input bar */}
      {!done && (
        <div className="mt-4 bg-white rounded-full p-2 pl-5 shadow-sm flex items-center gap-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={busy || recording}
            data-testid="assistant-input"
            placeholder={recording ? 'Listening… tap the square to send' : 'Type your message, or tap the mic to talk…'}
            className="flex-1 bg-transparent outline-none text-[14px] placeholder:text-[#b5b0a3] disabled:opacity-60"
          />
          <button onClick={micClick} disabled={busy} data-testid="assistant-mic-btn"
            className={`shrink-0 rounded-full p-3 transition-all ${recording ? 'bg-[#F5D34B] text-[#151515]' : 'bg-[#F1EDE3] text-[#151515] hover:bg-[#e9e4d8]'} disabled:opacity-40`}>
            {recording ? <Square size={17} /> : <Mic size={17} />}
          </button>
          <button onClick={sendText} disabled={!input.trim() || busy || recording} data-testid="assistant-send-btn"
            className="shrink-0 rounded-full p-3 bg-[#151515] text-white hover:bg-[#262626] transition-colors disabled:opacity-30">
            {busy ? <Loader2 size={17} className="animate-spin" /> : <Send size={17} />}
          </button>
        </div>
      )}

      <p className="flex items-center gap-2 text-[11px] text-[#8a8578] mt-3 px-2">
        <ShieldCheck size={13} /> Speak in any language — replies are in English. {anonymous ? 'Anonymous: no SOA ID is requested.' : 'Your SOA ID is confirmed before filing.'}
      </p>
    </div>
  );
}
