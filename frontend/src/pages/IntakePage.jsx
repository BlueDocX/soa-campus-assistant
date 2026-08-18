import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mic, Square, Send, Languages, Sparkles, CheckCircle2, Loader2, ShieldCheck, EyeOff, Wand2 } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { VOICE_SAMPLES } from '../mock/mock';
import { Switch } from '../components/ui/switch';
import { toast } from 'sonner';

const PIPELINE = [
  'Detecting language',
  'Normalizing request (AI proposes)',
  'Extracting fields',
  'Retrieving policy evidence',
  'Classifying autonomy risk',
  'Executing governed plan',
];

export default function IntakePage() {
  const { submitRequest, transcribeVoice } = useApp();
  const navigate = useNavigate();
  const [text, setText] = useState('');
  const [anonymous, setAnonymous] = useState(false);
  const [voiceLang, setVoiceLang] = useState('hi');
  const [voiceState, setVoiceState] = useState('idle'); // idle | recording | transcribing | simulating
  const [transcript, setTranscript] = useState('');
  const [voiceUsed, setVoiceUsed] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [stepIdx, setStepIdx] = useState(-1);
  const timerRef = useRef([]);
  const mediaRef = useRef({ recorder: null, chunks: [], stream: null });

  useEffect(() => () => {
    timerRef.current.forEach(clearTimeout);
    if (mediaRef.current.stream) mediaRef.current.stream.getTracks().forEach((t) => t.stop());
  }, []);

  // ---- Real voice via Deepgram (EN/HI). Odia uses labeled Demo Voice. ----
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : undefined });
      mediaRef.current = { recorder, chunks: [], stream };
      recorder.ondataavailable = (e) => { if (e.data.size) mediaRef.current.chunks.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setVoiceState('transcribing');
        try {
          const blob = new Blob(mediaRef.current.chunks, { type: 'audio/webm' });
          const res = await transcribeVoice(blob, voiceLang);
          if (res.transcript) {
            setTranscript(res.transcript);
            setText(res.transcript);
            setVoiceUsed(true);
            toast('Voice transcribed', { description: `Language: ${res.language} · confidence ${(res.confidence * 100).toFixed(0)}%` });
          } else {
            toast('No speech detected', { description: 'Try again closer to the mic, or use Simulate.' });
          }
        } catch (err) {
          toast('Transcription failed', { description: 'Provider unreachable — you can use the Simulate button instead.' });
        }
        setVoiceState('idle');
      };
      recorder.start();
      setVoiceState('recording');
      setTranscript('');
    } catch (err) {
      toast('Microphone unavailable', { description: 'Permission denied — use Simulate for the demo path.' });
    }
  };

  const stopRecording = () => {
    if (mediaRef.current.recorder?.state === 'recording') mediaRef.current.recorder.stop();
  };

  const micClick = () => {
    if (processing || voiceState === 'transcribing' || voiceState === 'simulating') return;
    if (voiceState === 'recording') stopRecording();
    else if (voiceLang === 'od') simulateVoice();
    else startRecording();
  };

  // ---- Simulated Demo Voice (clearly labeled) ----
  const simulateVoice = () => {
    if (voiceState !== 'idle' || processing) return;
    setVoiceState('simulating'); setTranscript('');
    const sample = VOICE_SAMPLES[voiceLang].text;
    const words = sample.split(' ');
    words.forEach((w, i) => {
      timerRef.current.push(setTimeout(() => {
        setTranscript((t) => (t ? t + ' ' : '') + w);
        if (i === words.length - 1) {
          timerRef.current.push(setTimeout(() => { setVoiceState('idle'); setText(sample); setVoiceUsed(true); }, 400));
        }
      }, 240 * (i + 1)));
    });
  };

  // ---- Submit: pipeline animation runs while the backend orchestrates ----
  const submit = async () => {
    if (!text.trim() || processing) return;
    setProcessing(true); setStepIdx(0);
    PIPELINE.forEach((_, i) => timerRef.current.push(setTimeout(() => setStepIdx(i), 620 * i)));
    const minWait = new Promise((res) => timerRef.current.push(setTimeout(res, 620 * PIPELINE.length)));
    try {
      const [req] = await Promise.all([submitRequest(text.trim(), { anonymous, viaVoice: voiceUsed }), minWait]);
      navigate(`/requests/${req.id}`);
    } catch (e) {
      setProcessing(false); setStepIdx(-1);
      toast('Orchestration failed', { description: 'The backend could not process this request. Please retry.' });
    }
  };

  const recording = voiceState === 'recording';

  return (
    <div className="max-w-[900px] mx-auto animate-fade-up">
      <div className="mt-6 mb-8">
        <h1 className="text-5xl font-light tracking-tight">New Request</h1>
        <p className="text-[13px] text-[#8a8578] mt-3">Your voice becomes an auditable service request. English · हिन्दी · ଓଡିଆ</p>
      </div>

      {/* Voice card */}
      <div className="bg-[#151515] text-white rounded-3xl p-6 mb-4 shadow-md">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-5">
          <div className="flex items-center gap-2 flex-wrap">
            <Languages size={16} className="text-[#F5D34B]" />
            <span className="text-[13px] font-medium">Voice intake</span>
            {voiceLang === 'od' && (
              <span className="text-[10px] bg-white/10 rounded-full px-2.5 py-1 text-white/60">Odia · Demo Voice (provider fallback, labeled)</span>
            )}
          </div>
          <div className="flex gap-1 bg-white/10 rounded-full p-1">
            {Object.entries(VOICE_SAMPLES).map(([k, v]) => (
              <button key={k} onClick={() => setVoiceLang(k)} data-testid={`voice-lang-${k}`}
                className={`px-3.5 py-1.5 rounded-full text-[12px] font-medium transition-colors ${voiceLang === k ? 'bg-[#F5D34B] text-[#151515]' : 'text-white/70 hover:text-white'}`}>{v.label}</button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-5">
          <button onClick={micClick} data-testid="mic-btn" disabled={processing || voiceState === 'transcribing'}
            className={`relative rounded-full p-5 transition-all ${recording ? 'bg-[#F5D34B] text-[#151515] scale-110' : 'bg-white/10 hover:bg-[#F5D34B] hover:text-[#151515]'} disabled:opacity-50`}>
            {recording ? <Square size={22} /> : voiceState === 'transcribing' ? <Loader2 size={22} className="animate-spin" /> : <Mic size={22} />}
            {recording && <span className="absolute inset-0 rounded-full border-2 border-[#F5D34B] animate-ping" />}
          </button>
          <div className="flex-1 min-h-[52px]">
            {recording && <p className="text-[13px] text-[#F5D34B]" data-testid="voice-status">Listening… click the square to stop &amp; transcribe</p>}
            {voiceState === 'transcribing' && <p className="text-[13px] text-white/60" data-testid="voice-status">Transcribing…</p>}
            {(voiceState === 'simulating' || (transcript && voiceState === 'idle')) ? (
              <p className="text-[15px] leading-relaxed" data-testid="voice-transcript">
                {transcript}{voiceState === 'simulating' && <span className="inline-block w-0.5 h-4 bg-[#F5D34B] ml-1 animate-pulse align-middle" />}
              </p>
            ) : (!recording && voiceState === 'idle' && !transcript) ? (
              <p className="text-[13px] text-white/40">
                {voiceLang === 'od' ? 'Tap the mic to run the labeled Odia Demo Voice transcript…' : `Tap the mic and speak in ${VOICE_SAMPLES[voiceLang].label}…`}
              </p>
            ) : null}
            {transcript && voiceState === 'idle' && (
              <p className="text-[11px] text-[#F5D34B] mt-1.5 flex items-center gap-1.5"><CheckCircle2 size={12} /> Transcript moved to the request box below</p>
            )}
          </div>
          <button onClick={simulateVoice} disabled={voiceState !== 'idle' || processing} data-testid="simulate-voice-btn"
            className="hidden sm:flex items-center gap-1.5 text-[11px] font-semibold bg-white/10 rounded-full px-4 py-2.5 hover:bg-white/20 transition-colors disabled:opacity-40">
            <Wand2 size={12} /> Simulate
          </button>
        </div>
      </div>

      {/* Text intake */}
      <div className="bg-[#FBF9F4] rounded-3xl p-6 shadow-sm">
        <textarea value={text} onChange={(e) => setText(e.target.value)} data-testid="intake-textarea"
          placeholder="Type your request… e.g. 'The projector in Room 114 is not working' or 'I need a bonafide certificate for my visa'"
          className="w-full bg-white rounded-2xl p-4 text-[14px] leading-relaxed min-h-[110px] outline-none focus:ring-2 focus:ring-[#F5D34B] transition-shadow resize-none placeholder:text-[#b5b0a3]" />

        <div className="flex items-center justify-between flex-wrap gap-3 mt-4">
          <label className="flex items-center gap-2.5 cursor-pointer">
            <Switch checked={anonymous} onCheckedChange={setAnonymous} data-testid="anonymous-switch" />
            <span className="flex items-center gap-1.5 text-[13px] text-[#5a5648]"><EyeOff size={14} /> Submit anonymously (identity escrow)</span>
          </label>
          <button onClick={submit} disabled={!text.trim() || processing} data-testid="submit-request-btn"
            className="flex items-center gap-2 bg-[#151515] text-white rounded-full px-6 py-3 text-[13px] font-semibold hover:bg-[#262626] transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
            {processing ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
            {processing ? 'Orchestrating…' : 'Submit request'}
          </button>
        </div>

        {/* Sample chips */}
        {!processing && (
          <div className="mt-5 flex flex-wrap gap-2">
            {[
              'AC leaking water in Lab 201, students may slip',
              'I need a bonafide certificate for my education loan',
              'Book Physics Lab 3 tonight at 9pm, it is exam week',
              'Book Chemistry Lab 2 tomorrow at 10am',
              'Complaint: repeated ragging in Hostel Block D after 10pm',
            ].map((s) => (
              <button key={s} onClick={() => setText(s)} data-testid="sample-chip" className="text-[11px] bg-white border border-[#151515]/10 rounded-full px-3.5 py-2 text-[#5a5648] hover:border-[#F5D34B] hover:bg-[#F5D34B]/20 transition-colors">{s}</button>
            ))}
          </div>
        )}

        {/* Pipeline animation */}
        {processing && (
          <div className="mt-6 space-y-2.5" data-testid="pipeline-steps">
            {PIPELINE.map((p, i) => (
              <div key={p} className={`flex items-center gap-3 rounded-2xl px-4 py-3 transition-all ${i <= stepIdx ? 'bg-white' : 'opacity-35'}`}>
                {i < stepIdx ? <CheckCircle2 size={16} className="text-[#6a8f2f]" /> : i === stepIdx ? <Loader2 size={16} className="animate-spin text-[#151515]" /> : <Sparkles size={16} className="text-[#b5b0a3]" />}
                <span className="text-[13px] font-medium">{p}</span>
                {i === 4 && i <= stepIdx && <span className="ml-auto text-[10px] bg-[#F5D34B]/50 rounded-full px-2.5 py-0.5 font-bold">Risk Gate</span>}
              </div>
            ))}
          </div>
        )}
      </div>

      <p className="flex items-center gap-2 text-[11px] text-[#8a8578] mt-4 px-2"><ShieldCheck size={13} /> The AI layer only proposes. A deterministic orchestrator validates every action against policies, permissions and an allowlisted tool set before anything executes.</p>
    </div>
  );
}
