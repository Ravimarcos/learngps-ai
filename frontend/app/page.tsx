"use client";

import { useState, useEffect, useRef } from "react";
import {
  getGPSRoute, sendChat, sendPhoto, getVARKProfile, getDikshaContent,
  TEST_STUDENT_ID, TEST_CHAPTER_ID,
  type GPSRoute, type VARKProfile, type DikshaResource,
} from "@/lib/api";

// ── Constants ──────────────────────────────────────────────────────────────
const STUDENT_NAME = "Dhwani";
const VARK_LABELS: Record<string, string> = { V: "👁️ Visual", A: "👂 Auditory", R: "📖 Read/Write", K: "🤸 Kinesthetic" };
const VARK_COLORS: Record<string, string> = { V: "bg-blue-100 text-blue-700", A: "bg-green-100 text-green-700", R: "bg-purple-100 text-purple-700", K: "bg-amber-100 text-amber-700" };

type Screen = "home" | "map" | "chat" | "progress" | "profile";
type Message = { role: "user" | "assistant"; content: string; xp?: number };

// ── Bottom Nav ─────────────────────────────────────────────────────────────
function BottomNav({ active, setActive }: { active: Screen; setActive: (s: Screen) => void }) {
  const tabs: { id: Screen; icon: string; label: string }[] = [
    { id: "home", icon: "🏠", label: "Home" },
    { id: "map", icon: "🗺️", label: "Map" },
    { id: "chat", icon: "🤖", label: "Gyaan" },
    { id: "progress", icon: "📊", label: "Progress" },
    { id: "profile", icon: "👤", label: "Profile" },
  ];
  return (
    <nav className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-sm bg-white border-t border-gray-100 flex z-50">
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => setActive(t.id)}
          className={`flex-1 flex flex-col items-center py-2 text-xs gap-0.5 transition-colors ${
            active === t.id ? "text-indigo-600 font-semibold" : "text-gray-400"
          }`}
        >
          <span className="text-xl">{t.icon}</span>
          <span>{t.label}</span>
        </button>
      ))}
    </nav>
  );
}

// ── HOME SCREEN ────────────────────────────────────────────────────────────
function HomeScreen({ gps, onContinue, onMap }: {
  gps: GPSRoute | null;
  onContinue: () => void;
  onMap: () => void;
}) {
  const current = gps?.current;
  const progress = gps?.progress_pct ?? 0;
  const completed = gps?.completed?.length ?? 0;
  const route = gps?.route ?? [];

  return (
    <div className="flex flex-col gap-3 p-4 pb-24">
      {/* Top bar */}
      <div className="flex items-center justify-between">
        <div className="w-9 h-9 rounded-full bg-indigo-600 flex items-center justify-center text-white font-bold text-sm">D</div>
        <span className="font-bold text-lg"><span className="text-indigo-600">Learn</span>GPS</span>
        <span className="text-xl">🔔</span>
      </div>

      {/* Greeting card */}
      <div className="rounded-2xl bg-gradient-to-br from-indigo-700 to-indigo-900 p-4 text-white">
        <p className="font-bold text-lg">Good evening, {STUDENT_NAME} 👋</p>
        <div className="mt-2 bg-white/10 rounded-xl p-3">
          <p className="text-indigo-200 text-xs font-semibold mb-1">Gyaan says:</p>
          <p className="text-white/90 text-sm italic">
            {current
              ? `You're currently on "${current.name}". Let's keep the momentum going!`
              : "Ready to start your learning journey today?"}
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: "Day Streak", value: "🔥 7", color: "text-amber-500" },
          { label: "Total XP", value: "340", color: "text-indigo-600" },
          { label: "Mastery", value: `${progress}%`, color: "text-gray-700" },
        ].map((s) => (
          <div key={s.label} className="bg-white rounded-xl p-3 text-center border border-gray-100 shadow-sm">
            <p className={`font-bold text-lg ${s.color}`}>{s.value}</p>
            <p className="text-gray-400 text-xs">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Continue button */}
      <button
        onClick={onContinue}
        className="w-full rounded-2xl bg-gradient-to-r from-emerald-500 to-emerald-600 p-4 flex items-center gap-3 shadow-md active:scale-95 transition-transform"
      >
        <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center text-white text-xl">▶</div>
        <div className="flex-1 text-left">
          <p className="font-bold text-white">Continue Learning</p>
          <p className="text-white/70 text-sm">{current?.name ?? "Contact Force"} · Remember level · ~10 min</p>
        </div>
        <span className="text-white text-xl">→</span>
      </button>

      {/* Quick actions */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { icon: "⚡", title: "Quick Quiz", sub: "5 Qs · 5 min" },
          { icon: "📖", title: "Explain This", sub: "Ask Gyaan" },
          { icon: "📝", title: "Test Prep", sub: "12 days away" },
        ].map((a) => (
          <button key={a.title} onClick={onContinue} className="bg-white rounded-xl p-3 border border-gray-100 shadow-sm text-center active:bg-gray-50">
            <p className="text-xl">{a.icon}</p>
            <p className="text-xs font-semibold text-gray-700 mt-1">{a.title}</p>
            <p className="text-xs text-gray-400">{a.sub}</p>
          </button>
        ))}
      </div>

      {/* GPS Position card */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
        <div className="flex items-center justify-between mb-1">
          <p className="font-semibold text-gray-800">📍 Your GPS Position</p>
          <button onClick={onMap} className="text-indigo-600 text-xs font-semibold">View Map →</button>
        </div>
        <p className="text-gray-400 text-xs mb-3">Force & Pressure · Grade 8 Science</p>

        {/* Node strip */}
        <div className="flex items-center gap-1">
          {[...Array(Math.min(completed, 2))].map((_, i) => (
            <div key={`c${i}`} className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center text-white text-xs">✓</div>
          ))}
          {current && (
            <div className="w-8 h-8 rounded-full bg-indigo-600 gps-current flex items-center justify-center text-white text-xs">📍</div>
          )}
          {route.slice(0, 2).map((_, i) => (
            <div key={`r${i}`} className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-400 text-xs">🔒</div>
          ))}
          <div className="flex-1 h-0.5 bg-gray-100 mx-1" />
        </div>

        <p className="text-xs mt-2 text-gray-600">
          <span className="text-indigo-600 font-semibold">{route.length} SubConcept{route.length !== 1 ? "s" : ""} left</span> to complete Force & Pressure
        </p>
      </div>
    </div>
  );
}

// ── MAP SCREEN ─────────────────────────────────────────────────────────────
function MapScreen({ gps, onStart }: { gps: GPSRoute | null; onStart: () => void }) {
  const current = gps?.current;
  const completed = gps?.completed ?? [];
  const route = gps?.route ?? [];
  const progress = gps?.progress_pct ?? 0;

  const allNodes = [...completed, ...(current ? [current] : []), ...route];

  return (
    <div className="flex flex-col gap-3 p-4 pb-28">
      <div>
        <h1 className="font-bold text-xl text-gray-900">Your Learning Map</h1>
        <p className="text-gray-400 text-sm">Grade 8 · Navigate your path</p>
      </div>

      {/* Progress banner */}
      <div className="rounded-xl bg-gradient-to-r from-indigo-700 to-indigo-900 p-4 text-white">
        <p className="text-sm font-semibold text-indigo-200 mb-2">⚙️ Skill: Understand Forces</p>
        <div className="w-full bg-white/20 rounded-full h-2 mb-1">
          <div className="bg-white rounded-full h-2 transition-all" style={{ width: `${progress}%` }} />
        </div>
        <p className="text-xs text-white/70">{progress}% complete · {route.length} SubConcept{route.length !== 1 ? "s" : ""} remaining</p>
      </div>

      {/* Nodes */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-3 h-3 rounded-full bg-indigo-600" />
          <p className="font-semibold text-gray-800">Force</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {allNodes.map((node) => {
            const isDone = completed.some((c) => c.id === node.id);
            const isCurrent = current?.id === node.id;
            return (
              <span
                key={node.id}
                className={`px-3 py-1.5 rounded-full text-xs font-semibold border ${
                  isDone
                    ? "bg-emerald-50 border-emerald-300 text-emerald-700"
                    : isCurrent
                    ? "bg-indigo-600 border-indigo-600 text-white gps-current"
                    : "bg-gray-50 border-gray-200 text-gray-400"
                }`}
              >
                {isDone ? "✓ " : isCurrent ? "📍 " : "🔒 "}
                {node.name}
              </span>
            );
          })}
        </div>

        {/* GPS route */}
        {current && route.length > 0 && (
          <div className="mt-3 bg-emerald-50 rounded-xl p-3 text-xs text-emerald-800">
            📍 {current.name} → {route.slice(0, 2).map((r) => r.name).join(" → ")}
            {route.length > 2 && " → ..."} →{" "}
            <span className="text-indigo-600 font-bold">Skill Complete!</span>
          </div>
        )}
      </div>

      {/* Other skills */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
        <p className="font-semibold text-gray-800 mb-2">Other Skills</p>
        {[
          { name: "Friction", status: "mastered", pct: 92 },
          { name: "Sound", status: "locked", pct: 0 },
        ].map((s) => (
          <div key={s.name} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
            <div className="flex items-center gap-2">
              <span>{s.status === "mastered" ? "✅" : "🔒"}</span>
              <span className="text-sm font-medium text-gray-700">{s.name}</span>
            </div>
            {s.status === "mastered" ? (
              <span className="text-xs text-emerald-600 font-semibold">Mastered · {s.pct}% 🏆</span>
            ) : (
              <span className="text-xs text-gray-400">Complete Forces first</span>
            )}
          </div>
        ))}
      </div>

      {/* Start button */}
      <button
        onClick={onStart}
        className="fixed bottom-20 left-1/2 -translate-x-1/2 w-[calc(100%-2rem)] max-w-sm bg-indigo-600 text-white font-bold py-4 rounded-2xl shadow-lg active:scale-95 transition-transform"
      >
        Start: {current?.name ?? "Contact Force"} →
      </button>
    </div>
  );
}

// ── CHAT SCREEN ────────────────────────────────────────────────────────────
function ChatScreen({ gps, vark }: { gps: GPSRoute | null; vark: VARKProfile | null }) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: `Welcome back, ${STUDENT_NAME}! 👋 I'm Gyaan, your AI tutor. What would you like to learn today?`,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [photoMode, setPhotoMode] = useState<"guide" | "check">("guide");
  const [showPhotoPanel, setShowPhotoPanel] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [diksha, setDiksha] = useState<DikshaResource[]>([]);
  const [showDiksha, setShowDiksha] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const currentSC = gps?.current;
  const varkStyle = vark?.dominant ?? "K";

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend() {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    setMessages((m) => [...m, { role: "user", content: userMsg }]);
    setLoading(true);

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const res = await sendChat({
        studentId: TEST_STUDENT_ID,
        studentName: STUDENT_NAME,
        message: userMsg,
        conversationHistory: history,
        subconcept_id: currentSC?.id ?? "sc_contact_force",
        subconcept_name: currentSC?.name ?? "Contact Force",
        bloom_level: "Remember",
        vark_style: varkStyle,
      });
      setMessages((m) => [...m, { role: "assistant", content: res.reply, xp: res.xp_earned }]);
    } catch {
      setMessages((m) => [...m, { role: "assistant", content: "Oops! Something went wrong. Try again." }]);
    } finally {
      setLoading(false);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    setPhotoPreview(URL.createObjectURL(file));
  }

  async function handlePhotoSend() {
    if (!selectedFile || loading) return;
    setShowPhotoPanel(false);
    setMessages((m) => [...m, { role: "user", content: `📸 [Photo uploaded — ${photoMode} mode]` }]);
    setLoading(true);

    try {
      const res = await sendPhoto(selectedFile, STUDENT_NAME, photoMode, "", varkStyle);
      setMessages((m) => [...m, { role: "assistant", content: res.reply, xp: res.xp_earned }]);
    } catch {
      setMessages((m) => [...m, { role: "assistant", content: "Couldn't read the photo. Try again with a clearer image." }]);
    } finally {
      setLoading(false);
      setSelectedFile(null);
      setPhotoPreview(null);
    }
  }

  async function loadDiksha() {
    if (!currentSC) return;
    setShowDiksha(true);
    try {
      const res = await getDikshaContent(currentSC.id);
      setDiksha(res.resources);
    } catch {
      setDiksha([]);
    }
  }

  return (
    <div className="flex flex-col h-screen max-h-screen">
      {/* Header */}
      <div className="bg-white border-b border-gray-100 p-3 flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-indigo-600 flex items-center justify-center text-xl">🤖</div>
        <div className="flex-1">
          <p className="font-bold text-gray-900 text-sm">Gyaan</p>
          <p className="text-xs text-emerald-500 font-medium">● Active · {currentSC?.name ?? "Force & Pressure"}</p>
        </div>
        <div className="flex gap-2">
          <span className={`text-xs px-2 py-1 rounded-full font-medium ${VARK_COLORS[varkStyle] ?? "bg-indigo-100 text-indigo-700"}`}>
            {VARK_LABELS[varkStyle] ?? "🤸 Kinesthetic"}
          </span>
          <button onClick={loadDiksha} className="text-xs px-2 py-1 bg-orange-50 text-orange-600 rounded-full font-medium">📚 NCERT</button>
        </div>
      </div>

      {/* DIKSHA panel */}
      {showDiksha && (
        <div className="bg-orange-50 border-b border-orange-100 p-3">
          <div className="flex justify-between mb-2">
            <p className="text-xs font-bold text-orange-700">📚 NCERT Resources for {currentSC?.name}</p>
            <button onClick={() => setShowDiksha(false)} className="text-orange-400 text-xs">✕</button>
          </div>
          {diksha.length === 0 ? (
            <p className="text-xs text-orange-500">Loading...</p>
          ) : (
            <div className="flex flex-col gap-1">
              {diksha.slice(0, 3).map((r) => (
                <a key={r.identifier} href={r.url} target="_blank" rel="noopener noreferrer"
                  className="text-xs bg-white rounded-lg p-2 border border-orange-100 text-blue-600 flex items-center gap-2">
                  <span>{r.content_type === "video" ? "🎥" : r.content_type === "activity" ? "🎮" : "📄"}</span>
                  <span className="flex-1 truncate">{r.title}</span>
                  <span>→</span>
                </a>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto no-scrollbar p-4 pb-4 bg-indigo-50/30 flex flex-col gap-3">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} fade-up`}>
            {msg.role === "assistant" && (
              <div className="w-6 h-6 rounded-full bg-indigo-600 flex items-center justify-center text-xs mr-2 mt-1 shrink-0">🤖</div>
            )}
            <div className="max-w-[80%]">
              <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white rounded-br-sm"
                  : "bg-white text-gray-800 border border-gray-100 shadow-sm rounded-bl-sm"
              }`}>
                {msg.content}
              </div>
              {msg.xp && msg.xp > 0 && (
                <div className="mt-1 text-xs text-amber-500 font-semibold px-1">+{msg.xp} XP 🔥</div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start fade-up">
            <div className="w-6 h-6 rounded-full bg-indigo-600 flex items-center justify-center text-xs mr-2">🤖</div>
            <div className="bg-white rounded-2xl rounded-bl-sm px-4 py-3 border border-gray-100 shadow-sm">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="w-2 h-2 bg-indigo-300 rounded-full animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Photo panel */}
      {showPhotoPanel && (
        <div className="bg-white border-t border-gray-100 p-3">
          <div className="flex justify-between mb-2">
            <p className="text-sm font-bold text-gray-700">📸 Send a question photo</p>
            <button onClick={() => setShowPhotoPanel(false)} className="text-gray-400 text-sm">✕</button>
          </div>
          <div className="flex gap-2 mb-3">
            {(["guide", "check"] as const).map((m) => (
              <button key={m} onClick={() => setPhotoMode(m)}
                className={`flex-1 py-2 rounded-xl text-xs font-semibold border transition-colors ${
                  photoMode === m ? "bg-indigo-600 text-white border-indigo-600" : "bg-gray-50 text-gray-600 border-gray-200"
                }`}>
                {m === "guide" ? "🧭 Guide me" : "✅ Check my answer"}
              </button>
            ))}
          </div>
          {photoPreview ? (
            <div className="flex items-center gap-2">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={photoPreview} alt="preview" className="w-16 h-16 rounded-lg object-cover border" />
              <button onClick={handlePhotoSend} className="flex-1 bg-indigo-600 text-white py-2 rounded-xl text-sm font-bold">
                Send to Gyaan →
              </button>
            </div>
          ) : (
            <button onClick={() => fileRef.current?.click()}
              className="w-full border-2 border-dashed border-indigo-200 rounded-xl py-4 text-indigo-400 text-sm font-medium">
              📷 Tap to pick a photo
            </button>
          )}
          <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={handleFileChange} />
        </div>
      )}

      {/* Input */}
      <div className="bg-white border-t border-gray-100 p-3 pb-20 flex items-center gap-2">
        <button onClick={() => setShowPhotoPanel(!showPhotoPanel)}
          className="w-10 h-10 rounded-full bg-indigo-50 flex items-center justify-center text-lg shrink-0 active:bg-indigo-100">
          📷
        </button>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Type your answer..."
          className="flex-1 bg-gray-50 rounded-full px-4 py-2.5 text-sm border border-gray-100 outline-none focus:border-indigo-300"
        />
        <button onClick={handleSend} disabled={loading}
          className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center text-white text-lg shrink-0 disabled:opacity-50 active:scale-95 transition-transform">
          ↑
        </button>
      </div>
    </div>
  );
}

// ── PROGRESS SCREEN ────────────────────────────────────────────────────────
function ProgressScreen({ vark }: { vark: VARKProfile | null }) {
  const dominant = vark?.dominant ?? "K";
  const confidence = vark ? Math.round(Math.max(vark.v_score, vark.a_score, vark.r_score, vark.k_score) * 100) : 25;
  const sessions = vark?.session_count ?? 0;

  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Today"];

  return (
    <div className="flex flex-col gap-3 p-4 pb-24">
      <div>
        <h1 className="font-bold text-xl text-gray-900">Your Progress</h1>
        <p className="text-gray-400 text-sm">Grade 8 · Science</p>
      </div>

      {/* Mastery ring */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 flex items-center gap-4">
        <div className="relative w-20 h-20 shrink-0">
          <svg viewBox="0 0 80 80" className="w-20 h-20 -rotate-90">
            <circle cx="40" cy="40" r="32" fill="none" stroke="#e0e7ff" strokeWidth="8" />
            <circle cx="40" cy="40" r="32" fill="none" stroke="#4f46e5" strokeWidth="8"
              strokeDasharray={`${2 * Math.PI * 32}`}
              strokeDashoffset={`${2 * Math.PI * 32 * (1 - 0.68)}`}
              strokeLinecap="round" />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-bold text-indigo-700 text-lg">68%</span>
            <span className="text-gray-400 text-xs">Overall</span>
          </div>
        </div>
        <div>
          <p className="font-bold text-gray-900">Overall Mastery</p>
          <p className="text-sm text-gray-500 mt-1">Concepts: <span className="font-semibold text-gray-700">8 / 12</span></p>
          <p className="text-sm text-gray-500">Bloom: <span className="font-semibold text-indigo-600">Apply level</span></p>
          <p className="text-sm text-gray-500">Sessions: <span className="font-semibold text-gray-700">{sessions || 34}</span></p>
        </div>
      </div>

      {/* Streak */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
        <div className="flex justify-between mb-3">
          <p className="font-semibold text-gray-800">🔥 7-Day Streak</p>
          <p className="text-amber-500 text-sm font-semibold">Don&apos;t break it!</p>
        </div>
        <div className="flex gap-1">
          {days.map((d, i) => (
            <div key={d} className={`flex-1 flex flex-col items-center gap-1`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${
                i === 6 ? "bg-amber-100 ring-2 ring-amber-400" : "bg-amber-50"
              }`}>🔥</div>
              <span className="text-xs text-gray-400">{d.slice(0, 1)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Chapter bars */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
        <p className="font-semibold text-gray-800 mb-3">Chapter Mastery</p>
        {[
          { name: "Force & Pressure", pct: 65, color: "bg-indigo-500" },
          { name: "Friction", pct: 92, color: "bg-emerald-500" },
          { name: "Linear Equations", pct: 78, color: "bg-indigo-400" },
        ].map((c) => (
          <div key={c.name} className="mb-3 last:mb-0">
            <div className="flex justify-between mb-1">
              <span className="text-sm text-gray-700">{c.name}</span>
              <span className="text-sm font-semibold text-gray-900">{c.pct}%</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div className={`${c.color} rounded-full h-2 transition-all`} style={{ width: `${c.pct}%` }} />
            </div>
          </div>
        ))}
      </div>

      {/* VARK card — live data */}
      <div className="bg-indigo-50 rounded-2xl border border-indigo-100 p-4">
        <p className="font-semibold text-indigo-800 mb-1">Your Learning Style</p>
        <div className="flex items-center gap-3 mt-2">
          <span className="text-3xl">{dominant === "V" ? "👁️" : dominant === "A" ? "👂" : dominant === "R" ? "📖" : "🤸"}</span>
          <div className="flex-1">
            <p className="font-bold text-indigo-700">{VARK_LABELS[dominant]} Learner</p>
            <p className="text-xs text-indigo-500">{confidence}% confidence · {sessions} sessions</p>
            <div className="w-full bg-indigo-100 rounded-full h-1.5 mt-1">
              <div className="bg-indigo-600 rounded-full h-1.5" style={{ width: `${confidence}%` }} />
            </div>
          </div>
        </div>
        {/* All 4 scores */}
        <div className="grid grid-cols-4 gap-2 mt-3">
          {(["V", "A", "R", "K"] as const).map((s) => {
            const score = vark ? Math.round((vark[`${s.toLowerCase() as "v" | "a" | "r" | "k"}_score`] ?? 0.25) * 100) : 25;
            return (
              <div key={s} className={`rounded-xl p-2 text-center ${dominant === s ? "bg-indigo-600 text-white" : "bg-white text-gray-600"}`}>
                <p className="text-xs font-bold">{s}</p>
                <p className="text-sm font-semibold">{score}%</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Badges */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
        <p className="font-semibold text-gray-800 mb-3">Recent Badges 🏆</p>
        <div className="grid grid-cols-4 gap-2">
          {[
            { icon: "🔥", label: "7-Day Streak", unlocked: true },
            { icon: "⭐", label: "First Skill!", unlocked: true },
            { icon: "🎯", label: "Apply Level", unlocked: true },
            { icon: "🧭", label: "Career Path", unlocked: false },
          ].map((b) => (
            <div key={b.label} className={`flex flex-col items-center gap-1 p-2 rounded-xl ${b.unlocked ? "" : "opacity-40"}`}>
              <span className="text-2xl">{b.icon}</span>
              <span className="text-xs text-gray-500 text-center leading-tight">{b.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── PROFILE SCREEN ─────────────────────────────────────────────────────────
function ProfileScreen({ vark }: { vark: VARKProfile | null }) {
  return (
    <div className="flex flex-col gap-3 p-4 pb-24">
      <div className="flex flex-col items-center py-4">
        <div className="w-20 h-20 rounded-full bg-indigo-600 flex items-center justify-center text-white text-3xl font-bold mb-3">D</div>
        <h2 className="font-bold text-xl text-gray-900">{STUDENT_NAME}</h2>
        <p className="text-gray-400 text-sm">Grade 8 · LearnGPS Student</p>
        <div className="flex gap-3 mt-3">
          <span className="bg-indigo-50 text-indigo-600 text-xs font-semibold px-3 py-1 rounded-full">340 XP</span>
          <span className="bg-amber-50 text-amber-600 text-xs font-semibold px-3 py-1 rounded-full">🔥 7 Streak</span>
          <span className={`text-xs font-semibold px-3 py-1 rounded-full ${VARK_COLORS[vark?.dominant ?? "K"]}`}>
            {VARK_LABELS[vark?.dominant ?? "K"]}
          </span>
        </div>
      </div>

      {[
        { icon: "📚", label: "Chapters", value: "3 in progress" },
        { icon: "🎯", label: "Bloom Level", value: "Apply" },
        { icon: "📅", label: "Next Test", value: "Oct 15 · 12 days" },
        { icon: "🏆", label: "Badges Earned", value: "3 / 8" },
      ].map((item) => (
        <div key={item.label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xl">{item.icon}</span>
            <span className="text-sm font-medium text-gray-700">{item.label}</span>
          </div>
          <span className="text-sm text-gray-500 font-semibold">{item.value}</span>
        </div>
      ))}

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
        <p className="text-sm font-semibold text-gray-700 mb-1">Student ID</p>
        <p className="text-xs text-gray-400 font-mono">{TEST_STUDENT_ID}</p>
      </div>
    </div>
  );
}

// ── ROOT APP ───────────────────────────────────────────────────────────────
export default function App() {
  const [screen, setScreen] = useState<Screen>("home");
  const [gps, setGPS] = useState<GPSRoute | null>(null);
  const [vark, setVARK] = useState<VARKProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getGPSRoute(TEST_STUDENT_ID, TEST_CHAPTER_ID).catch(() => null),
      getVARKProfile(TEST_STUDENT_ID).catch(() => null),
    ]).then(([g, v]) => {
      setGPS(g);
      setVARK(v);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-indigo-900">
        <div className="flex flex-col items-center gap-3">
          <span className="text-4xl animate-bounce">🧭</span>
          <p className="text-white font-bold text-lg">LearnGPS</p>
          <p className="text-indigo-300 text-sm">Finding your position...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-center bg-gray-100 min-h-screen">
      <div className="w-full max-w-sm min-h-screen bg-gray-50 relative overflow-hidden">
        {screen === "home" && <HomeScreen gps={gps} onContinue={() => setScreen("chat")} onMap={() => setScreen("map")} />}
        {screen === "map" && <MapScreen gps={gps} onStart={() => setScreen("chat")} />}
        {screen === "chat" && <ChatScreen gps={gps} vark={vark} />}
        {screen === "progress" && <ProgressScreen vark={vark} />}
        {screen === "profile" && <ProfileScreen vark={vark} />}
        <BottomNav active={screen} setActive={setScreen} />
      </div>
    </div>
  );
}
