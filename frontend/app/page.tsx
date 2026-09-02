"use client";

import React, { useState, useEffect, useRef } from "react";
import { supabase } from "@/lib/supabase";
import type { User } from "@supabase/supabase-js";
import {
  getGPSRoute, getChapters, sendChat, sendPhoto, getVARKProfile, getDikshaContent,
  TEST_CHAPTER_ID,
  type Chapter, type ChapterEdge, type ChaptersResponse,
  type GPSRoute, type GPSNode, type GPSEdge, type VARKProfile, type DikshaResource,
} from "@/lib/api";

// ── Constants ──────────────────────────────────────────────────────────────
const VARK_LABELS: Record<string, string> = { V: "👁️ Visual", A: "👂 Auditory", R: "📖 Read/Write", K: "🤸 Kinesthetic" };
const VARK_COLORS: Record<string, string> = { V: "bg-blue-100 text-blue-700", A: "bg-green-100 text-green-700", R: "bg-purple-100 text-purple-700", K: "bg-amber-100 text-amber-700" };

type Screen = "home" | "map" | "chat" | "progress" | "profile";
type AuthStep = "email" | "otp" | "setup";
type Message = { role: "user" | "assistant"; content: string; xp?: number };

// ── Markdown renderer ──────────────────────────────────────────────────────
function renderMessage(content: string) {
  return content.split("\n").map((line, i, arr) => {
    const parts = line.split(/\*\*(.+?)\*\*/g);
    const rendered = parts.map((part, j) =>
      j % 2 === 1 ? <strong key={j}>{part}</strong> : part
    );
    return (
      <span key={i} className={i < arr.length - 1 ? "block" : ""}>
        {rendered}
      </span>
    );
  });
}

// ── AUTH: Email screen ────────────────────────────────────────────────────
function AuthEmailScreen({ onSent }: { onSent: (email: string) => void }) {
  const [email, setEmail]   = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState("");

  async function handleSend() {
    if (!email.trim() || loading) return;
    setLoading(true);
    setError("");
    const { error } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      options: { shouldCreateUser: true },
    });
    if (error) { setError(error.message); setLoading(false); }
    else onSent(email.trim());
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-indigo-900 p-6">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <span className="text-5xl mb-3">🧭</span>
          <h1 className="text-white font-bold text-3xl"><span className="text-indigo-300">Learn</span>GPS</h1>
          <p className="text-indigo-300 text-sm mt-1">AI-powered learning for Class 8–10</p>
        </div>
        <div className="bg-white rounded-2xl p-6 shadow-xl">
          <h2 className="font-bold text-xl text-gray-900 mb-1">Welcome! 👋</h2>
          <p className="text-gray-500 text-sm mb-5">Enter your email to get started</p>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="your@email.com"
            className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm outline-none focus:border-indigo-400 mb-3"
          />
          {error && <p className="text-red-500 text-xs mb-3">{error}</p>}
          <button
            onClick={handleSend}
            disabled={loading || !email.trim()}
            className="w-full bg-indigo-600 text-white font-bold py-3 rounded-xl disabled:opacity-50 active:scale-95 transition-transform"
          >
            {loading ? "Sending..." : "Send OTP →"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── AUTH: Magic link sent screen ──────────────────────────────────────────
function AuthOTPScreen({ email, onBack }: {
  email: string;
  onVerified: (user: User) => void;
  onBack: () => void;
}) {
  const [timer, setTimer] = useState(30);
  const [resending, setResending] = useState(false);

  useEffect(() => {
    if (timer <= 0) return;
    const t = setTimeout(() => setTimer((n) => n - 1), 1000);
    return () => clearTimeout(t);
  }, [timer]);

  async function handleResend() {
    if (timer > 0) return;
    setResending(true);
    await supabase.auth.signInWithOtp({ email, options: { shouldCreateUser: true } });
    setTimer(30);
    setResending(false);
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-indigo-900 p-6">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <span className="text-6xl mb-4">📬</span>
          <h1 className="text-white font-bold text-2xl text-center">Check your email</h1>
          <p className="text-indigo-300 text-sm mt-2 text-center">We sent a sign-in link to</p>
          <p className="text-white font-semibold text-sm mt-1">{email}</p>
        </div>
        <div className="bg-white rounded-2xl p-6 shadow-xl text-center">
          <p className="text-gray-600 text-sm mb-4">
            Open your email and tap the <strong>"Sign in"</strong> link — you&apos;ll be signed in automatically.
          </p>
          <div className="bg-indigo-50 rounded-xl p-3 mb-4 text-xs text-indigo-700">
            💡 The link opens this app in your browser and logs you in instantly — no code needed!
          </div>
          <div className="flex justify-between items-center text-sm">
            <button onClick={onBack} className="text-gray-400">← Back</button>
            <button
              onClick={handleResend}
              disabled={timer > 0 || resending}
              className={timer > 0 ? "text-gray-300" : "text-indigo-600 font-semibold"}
            >
              {resending ? "Sending..." : timer > 0 ? `Resend in ${timer}s` : "Resend link"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── AUTH: Profile setup (first time only) ────────────────────────────────
function ProfileSetupScreen({ userId, onComplete }: {
  userId: string;
  onComplete: (name: string, grade: number) => void;
}) {
  const [name, setName]     = useState("");
  const [grade, setGrade]   = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSave() {
    if (!name.trim() || !grade || loading) return;
    setLoading(true);
    await supabase.from("student_profiles").upsert({
      student_id: userId,
      name: name.trim(),
      grade,
    });
    onComplete(name.trim(), grade);
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-indigo-900 p-6">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <span className="text-5xl mb-3">🎒</span>
          <h1 className="text-white font-bold text-2xl text-center">Almost there!</h1>
          <p className="text-indigo-300 text-sm mt-1 text-center">Tell us a bit about yourself</p>
        </div>
        <div className="bg-white rounded-2xl p-6 shadow-xl">
          <label className="block text-sm font-semibold text-gray-700 mb-2">What&apos;s your name?</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Dhwani"
            className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm outline-none focus:border-indigo-400 mb-5"
          />
          <label className="block text-sm font-semibold text-gray-700 mb-2">Which grade are you in?</label>
          <div className="flex gap-3 mb-6">
            {[8, 9, 10].map((g) => (
              <button
                key={g}
                onClick={() => setGrade(g)}
                className={`flex-1 py-3 rounded-xl font-bold text-lg border-2 transition-colors ${
                  grade === g ? "bg-indigo-600 border-indigo-600 text-white" : "bg-white border-gray-200 text-gray-600"
                }`}
              >
                {g}
              </button>
            ))}
          </div>
          <button
            onClick={handleSave}
            disabled={!name.trim() || !grade || loading}
            className="w-full bg-emerald-500 text-white font-bold py-3 rounded-xl disabled:opacity-50 active:scale-95 transition-transform"
          >
            {loading ? "Saving..." : "Let's Go! 🚀"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Bottom Nav ─────────────────────────────────────────────────────────────
function BottomNav({ active, setActive }: { active: Screen; setActive: (s: Screen) => void }) {
  const tabs: { id: Screen; icon: string; label: string }[] = [
    { id: "home",     icon: "🏠", label: "Home"     },
    { id: "map",      icon: "🗺️", label: "Map"      },
    { id: "chat",     icon: "🤖", label: "Gyaan"    },
    { id: "progress", icon: "📊", label: "Progress" },
    { id: "profile",  icon: "👤", label: "Profile"  },
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
function HomeScreen({ gps, studentName, totalXp, streakDays, onContinue, onStartMode, onMap }: {
  gps: GPSRoute | null;
  studentName: string;
  totalXp: number;
  streakDays: number;
  onContinue: () => void;
  onStartMode: (mode: "quiz" | "explain" | "testprep") => void;
  onMap: () => void;
}) {
  const current   = gps?.current;
  const progress  = gps?.progress_pct ?? 0;
  const completed = gps?.completed?.length ?? 0;
  const route     = gps?.route ?? [];
  const locked    = gps?.locked ?? [];

  return (
    <div className="flex flex-col gap-3 p-4 pb-24">
      <div className="flex items-center justify-between">
        <div className="w-9 h-9 rounded-full bg-indigo-600 flex items-center justify-center text-white font-bold text-sm">
          {studentName[0]?.toUpperCase() ?? "S"}
        </div>
        <span className="font-bold text-lg"><span className="text-indigo-600">Learn</span>GPS</span>
        <span className="text-xl">🔔</span>
      </div>

      <div className="rounded-2xl bg-gradient-to-br from-indigo-700 to-indigo-900 p-4 text-white">
        <p className="font-bold text-lg">Good day, {studentName} 👋</p>
        <div className="mt-2 bg-white/10 rounded-xl p-3">
          <p className="text-indigo-200 text-xs font-semibold mb-1">Gyaan says:</p>
          <p className="text-white/90 text-sm italic">
            {current
              ? `You're on "${current.name}". Let's keep the momentum going!`
              : "Ready to start your learning journey today?"}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        {[
          { label: "Day Streak", value: `🔥 ${streakDays}`, color: "text-amber-500"  },
          { label: "Total XP",   value: `${totalXp}`,       color: "text-indigo-600" },
          { label: "Mastery",    value: `${progress}%`,     color: "text-gray-700"  },
        ].map((s) => (
          <div key={s.label} className="bg-white rounded-xl p-3 text-center border border-gray-100 shadow-sm">
            <p className={`font-bold text-lg ${s.color}`}>{s.value}</p>
            <p className="text-gray-400 text-xs">{s.label}</p>
          </div>
        ))}
      </div>

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

      <div className="grid grid-cols-3 gap-2">
        {[
          { icon: "⚡", title: "Quick Quiz",   sub: "5 Qs · 5 min",  mode: "quiz"     as const },
          { icon: "📖", title: "Explain This", sub: "Ask Gyaan",      mode: "explain"  as const },
          { icon: "📝", title: "Test Prep",    sub: "12 days away",   mode: "testprep" as const },
        ].map((a) => (
          <button key={a.title} onClick={() => onStartMode(a.mode)} className="bg-white rounded-xl p-3 border border-gray-100 shadow-sm text-center active:bg-gray-50">
            <p className="text-xl">{a.icon}</p>
            <p className="text-xs font-semibold text-gray-700 mt-1">{a.title}</p>
            <p className="text-xs text-gray-400">{a.sub}</p>
          </button>
        ))}
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
        <div className="flex items-center justify-between mb-1">
          <p className="font-semibold text-gray-800">📍 Your GPS Position</p>
          <button onClick={onMap} className="text-indigo-600 text-xs font-semibold">View Map →</button>
        </div>
        <p className="text-gray-400 text-xs mb-3">Force & Pressure · Grade 8 Science</p>
        <div className="flex items-center gap-1">
          {[...Array(Math.min(completed, 2))].map((_, i) => (
            <div key={`c${i}`} className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center text-white text-xs">✓</div>
          ))}
          {current && (
            <div className="w-8 h-8 rounded-full bg-indigo-600 gps-current flex items-center justify-center text-white text-xs">📍</div>
          )}
          {route.slice(0, 2).map((n, i) => (
            <div key={`r${i}`} className="w-8 h-8 rounded-full bg-gray-100 border border-gray-300 flex items-center justify-center text-gray-400 text-xs" title={n.name}>○</div>
          ))}
          {locked.slice(0, 2).map((n, i) => (
            <div key={`g${i}`} className="w-8 h-8 rounded-full bg-amber-50 border border-dashed border-amber-300 flex items-center justify-center text-amber-400 text-xs opacity-50" title={`${n.name} (tap anytime)`}>👁</div>
          ))}
          <div className="flex-1 h-0.5 bg-gray-100 mx-1" />
        </div>
        <p className="text-xs mt-2 text-gray-600">
          <span className="text-indigo-600 font-semibold">{route.length} up next</span>
          {locked.length > 0 && <span className="text-amber-500 ml-2 opacity-70">· {locked.length} visible ahead 👁</span>}
        </p>
      </div>
    </div>
  );
}

// ── SIDEBAR — web navigation + student card ───────────────────────────────────
function Sidebar({ screen, setScreen, studentName, vark, totalXp, streakDays }: {
  screen: Screen;
  setScreen: (s: Screen) => void;
  studentName: string;
  vark: VARKProfile | null;
  totalXp: number;
  streakDays: number;
}) {
  const nav: { id: Screen; icon: string; label: string }[] = [
    { id: "home",     icon: "🏠", label: "Home"          },
    { id: "map",      icon: "🧭", label: "Knowledge Map" },
    { id: "chat",     icon: "🤖", label: "Gyaan AI"      },
    { id: "progress", icon: "📊", label: "Progress"      },
    { id: "profile",  icon: "👤", label: "Profile"       },
  ];
  return (
    <aside style={{
      width: "232px", flexShrink: 0, height: "100vh",
      background: "rgba(4,8,32,0.98)", borderRight: "1px solid rgba(255,255,255,0.06)",
      display: "flex", flexDirection: "column",
    }}>
      {/* Logo */}
      <div style={{ padding: "20px 18px 16px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "22px" }}>🧭</span>
          <div>
            <p style={{ fontWeight: 800, fontSize: "17px", color: "#fff", lineHeight: 1 }}>
              Learn<span style={{ color: "#6366f1" }}>GPS</span>
            </p>
            <p style={{ fontSize: "10px", color: "rgba(255,255,255,0.28)", marginTop: "2px" }}>AI Tutoring · Grade 8–10</p>
          </div>
        </div>
      </div>

      {/* Nav links */}
      <nav style={{ padding: "10px 8px", flex: 1 }}>
        {nav.map(item => {
          const active = screen === item.id;
          return (
            <button key={item.id} onClick={() => setScreen(item.id)}
              style={{
                width: "100%", display: "flex", alignItems: "center", gap: "10px",
                padding: "9px 12px", borderRadius: "10px", border: "none", cursor: "pointer",
                background: active ? "rgba(99,102,241,0.18)" : "transparent",
                color: active ? "#a5b4fc" : "rgba(255,255,255,0.45)",
                fontSize: "13px", fontWeight: active ? 700 : 500,
                marginBottom: "2px", fontFamily: "inherit", textAlign: "left",
                transition: "background 0.15s, color 0.15s",
              }}>
              <span style={{ fontSize: "15px", flexShrink: 0 }}>{item.icon}</span>
              <span style={{ flex: 1 }}>{item.label}</span>
              {active && <div style={{ width: "5px", height: "5px", borderRadius: "50%", background: "#6366f1", flexShrink: 0 }} />}
            </button>
          );
        })}
      </nav>

      {/* Student card */}
      <div style={{ padding: "12px 14px 18px", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "9px", marginBottom: "10px" }}>
          <div style={{
            width: "30px", height: "30px", borderRadius: "50%", background: "#4338ca",
            display: "flex", alignItems: "center", justifyContent: "center",
            color: "#fff", fontWeight: 800, fontSize: "12px", flexShrink: 0,
          }}>
            {studentName[0]?.toUpperCase() ?? "S"}
          </div>
          <div style={{ minWidth: 0 }}>
            <p style={{ fontSize: "12px", fontWeight: 700, color: "#fff", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {studentName || "Student"}
            </p>
            <p style={{ fontSize: "10px", color: "rgba(255,255,255,0.28)" }}>Grade 8 · Science</p>
          </div>
        </div>
        <div style={{ display: "flex", gap: "5px" }}>
          {[
            { val: `🔥 ${streakDays}`, label: "Streak", color: "#f59e0b" },
            { val: `${totalXp}`,        label: "XP",     color: "#6366f1" },
            ...(vark ? [{ val: vark.dominant, label: "VARK", color: "#10b981" }] : []),
          ].map(s => (
            <div key={s.label} style={{ flex: 1, background: "rgba(255,255,255,0.05)", borderRadius: "8px", padding: "5px 4px", textAlign: "center" }}>
              <p style={{ fontSize: "12px", fontWeight: 800, color: s.color }}>{s.val}</p>
              <p style={{ fontSize: "9px", color: "rgba(255,255,255,0.28)" }}>{s.label}</p>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}

// ── Hex color → rgba fill helper ─────────────────────────────────────────────
// Converts "#rrggbb" to "rgba(r,g,b,alpha)" for SVG fills.
// Handles only 6-digit hex (all colors from Neo4j are in that format).
function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

// Fallback auto-layout for chapters that don't yet have ov_x / ov_y in Neo4j.
// Arranges chapters on an ellipse centred in the 760×590 viewBox.
/**
 * Graph-based chapter positions.
 * Science → 3-col grid on the left; Maths → 4-col grid on the right.
 * Ordered by ncert_chapter_num within each subject.
 * Chapters with stored ov_x/ov_y use those instead (manual override).
 */
function getChapterGridPos(ch: Chapter, visible: Chapter[]): { x: number; y: number } {
  if (ch.ov_x > 0) return { x: ch.ov_x, y: ch.ov_y };
  const peers = [...visible]
    .filter(c => c.subject === ch.subject)
    .sort((a, b) => {
      const gd = (a.grade ?? 8) - (b.grade ?? 8);
      if (gd !== 0) return gd;
      return (a.ncert_chapter_num ?? 99) - (b.ncert_chapter_num ?? 99);
    });
  const idx   = Math.max(0, peers.findIndex(c => c.id === ch.id));
  const isSci = ch.subject === "Science";
  const COLS  = isSci ? 3 : 4;
  const CW    = 285;   // cell width
  const CH    = 195;   // cell height
  const OX    = isSci ? 145 : 1100;
  const OY    = 90;
  return { x: OX + (idx % COLS) * CW, y: OY + Math.floor(idx / COLS) * CH };
}

function getOverviewSvgHeight(visible: Chapter[]): number {
  const sciRows  = Math.ceil(visible.filter(c => c.subject === "Science").length / 3);
  const mathRows = Math.ceil(visible.filter(c => c.subject !== "Science").length / 4);
  return Math.max(1160, 90 + Math.max(sciRows, mathRows) * 195 + 150);
}

// ── MAP SCREEN — fully data-driven GPS-style 2D knowledge graph ──────────────
// Two zoom levels:
//   overview  → all chapters from /chapters API as glowing orbs + cross-chapter edges
//   chapter   → subconcept 2D graph from /gps API (positions + edges from Neo4j)
//
// Adding a new chapter = seed Neo4j (color, ov_x, ov_y, ov_radius, eta properties).
// Zero frontend changes required. Grade/subject filters work automatically.
function MapScreen({ studentId, onStart }: {
  studentId: string;
  onStart: (gps: GPSRoute) => void;
}) {
  // ── overview data (from /chapters API) ────────────────────────────────────
  const [chapters,      setChapters]      = useState<Chapter[]>([]);
  const [chapterEdges,  setChapterEdges]  = useState<ChapterEdge[]>([]);
  const [loadingChaps,  setLoadingChaps]  = useState(true);

  // ── per-chapter GPS cache (fetched on drill-in) ───────────────────────────
  const [gpsCache,   setGpsCache]   = useState<Record<string, GPSRoute>>({});
  const [loadingGps, setLoadingGps] = useState(false);

  // ── navigation ─────────────────────────────────────────────────────────────
  const [view,       setView]       = useState<"overview" | string>("overview");
  const [detailNode, setDetailNode] = useState<{ id: string; name: string; state: string; bloomTarget?: string; varkHint?: string } | null>(null);
  const [routeMode,  setRouteMode]  = useState<"focused" | "deep" | "revision">("focused");
  const [gradeFilter,   setGradeFilter]   = useState<number | null>(null);
  const [subjectFilter, setSubjectFilter] = useState<string | null>(null);

  // ── pan / zoom ──────────────────────────────────────────────────────────────
  const [pan,   setPan]   = useState({ x: 0, y: 0 });
  const [scale, setScale] = useState(1);
  const touchRef = useRef<{ x: number; y: number; dist?: number } | null>(null);
  const mouseRef = useRef<{ x: number; y: number; dragged: boolean } | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // ── Fetch all chapters on mount ────────────────────────────────────────────
  useEffect(() => {
    setLoadingChaps(true);
    getChapters({ studentId })
      .then(res => { setChapters(res.chapters); setChapterEdges(res.edges); })
      .catch(console.error)
      .finally(() => setLoadingChaps(false));
  }, [studentId]);

  // ── Drill-in: fetch GPS for selected chapter (cached after first fetch) ────
  async function drillInto(chapId: string) {
    setView(chapId);
    setPan({ x: 0, y: 0 });
    setScale(1);
    setDetailNode(null);
    if (!gpsCache[chapId]) {
      setLoadingGps(true);
      try {
        const g = await getGPSRoute(studentId, chapId);
        setGpsCache(prev => ({ ...prev, [chapId]: g }));
      } catch { /* handled by "coming soon" fallback */ }
      finally { setLoadingGps(false); }
    }
  }

  function goOverview() {
    setView("overview"); setPan({ x: 0, y: 0 }); setScale(1); setDetailNode(null);
  }

  // ── Derived state ──────────────────────────────────────────────────────────
  const isOverview   = view === "overview";
  const activeGps    = isOverview ? null : (gpsCache[view] ?? null);
  const activeChap   = isOverview ? null : chapters.find(c => c.id === view) ?? null;
  const chColor      = activeChap?.color ?? "#2979ff";

  const current    = activeGps?.current;
  const completed  = activeGps?.completed ?? [];
  const route      = activeGps?.route     ?? [];
  const locked     = activeGps?.locked    ?? [];
  const nodes      = activeGps?.nodes     ?? [];
  const edges      = activeGps?.edges     ?? [];
  const progress   = activeGps?.progress_pct ?? (activeChap?.mastery_pct ?? 0);
  const etaLabel   = current ? `~${Math.max(1, Math.round((route.length + locked.length + 1) * 0.75))}h` : "✓ Done";

  const completedIds = new Set(completed.map(n => n.id));
  const routeIds     = new Set(route.map(n => n.id));
  const posMap: Record<string, { x: number; y: number }> = {};
  for (const n of nodes) posMap[n.id] = { x: n.x, y: n.y };

  function getState(id: string): "done" | "current" | "ready" | "ghost" {
    if (completedIds.has(id))         return "done";
    if (current && current.id === id) return "current";
    if (routeIds.has(id))             return "ready";
    return "ghost";
  }

  // Grade + subject filters — derived from chapters data
  const grades    = [...new Set(chapters.map(c => c.grade))].sort((a, b) => a - b);
  const subjects  = [...new Set(chapters.map(c => c.subject))].sort();
  const visibleChapters = chapters.filter(c =>
    (!gradeFilter   || c.grade   === gradeFilter) &&
    (!subjectFilter || c.subject === subjectFilter)
  );

  // ── Touch pan / pinch-zoom ─────────────────────────────────────────────────
  function onTouchStart(e: React.TouchEvent) {
    if (e.touches.length === 1) {
      touchRef.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    } else if (e.touches.length === 2) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      touchRef.current = { x: 0, y: 0, dist: Math.sqrt(dx * dx + dy * dy) };
    }
  }
  function onTouchMove(e: React.TouchEvent) {
    e.preventDefault();
    if (!touchRef.current) return;
    if (e.touches.length === 1) {
      const dx = e.touches[0].clientX - touchRef.current.x;
      const dy = e.touches[0].clientY - touchRef.current.y;
      setPan(p => ({ x: p.x + dx, y: p.y + dy }));
      touchRef.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    } else if (e.touches.length === 2 && touchRef.current.dist) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      const nd = Math.sqrt(dx * dx + dy * dy);
      setScale(s => Math.min(4, Math.max(0.3, s * nd / touchRef.current!.dist!)));
      touchRef.current = { ...touchRef.current, dist: nd };
    }
  }
  function onTouchEnd() { touchRef.current = null; }

  // ── Node visual config ─────────────────────────────────────────────────────
  const R = 22;
  const SCFG = {
    done:    { fill: "rgba(0,40,20,0.92)",  stroke: "#00e676",               text: "#00e676",               icon: "✓", op: 1,    sw: 1.5 },
    current: { fill: "rgba(8,24,80,0.95)",  stroke: "#2979ff",               text: "#82b1ff",               icon: "●", op: 1,    sw: 2.5 },
    ready:   { fill: "rgba(40,30,0,0.88)",  stroke: "#ffd740",               text: "#ffd740",               icon: "○", op: 1,    sw: 1.5 },
    ghost:   { fill: "rgba(18,22,44,0.55)", stroke: "rgba(255,255,255,0.2)", text: "rgba(255,255,255,0.35)", icon: "·", op: 0.38, sw: 1.5 },
  };

  function edgeColor(fromId: string) {
    const s = getState(fromId);
    if (s === "done")    return "rgba(0,230,118,0.55)";
    if (s === "current") return "rgba(41,121,255,0.55)";
    return "rgba(255,255,255,0.1)";
  }
  function isRecommendedEdge(fromId: string, toId: string) {
    return routeMode === "focused" && current?.id === fromId && route.length > 0 && route[0].id === toId;
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div style={{ background: "#03061a", height: "100vh", display: "flex", flexDirection: "column", position: "relative", overflow: "hidden" }}>
      <style>{`
        @keyframes gps-pulse { 0%{r:22px;opacity:.5} 70%{r:46px;opacity:0} 100%{r:46px;opacity:0} }
        .gps-pulse-ring { animation: gps-pulse 2s ease-out infinite; }
        @keyframes dash-f { to { stroke-dashoffset: 0; } }
        .flow-edge { animation: dash-f 1.2s linear infinite; }
        @keyframes twinkle { 0%,100%{opacity:.2} 50%{opacity:.75} }
        @keyframes xpFloat { 0%{opacity:1;transform:translateY(0) scale(1)} 60%{opacity:1;transform:translateY(-40px) scale(1.1)} 100%{opacity:0;transform:translateY(-80px) scale(0.9)} }
      `}</style>

      {/* Starfield */}
      {[...Array(20)].map((_, i) => (
        <div key={i} style={{
          position: "absolute", borderRadius: "50%", pointerEvents: "none",
          width: i % 3 === 0 ? "2px" : "1px", height: i % 3 === 0 ? "2px" : "1px",
          background: "rgba(255,255,255,0.5)",
          top: `${(i * 37 + 11) % 94}%`, left: `${(i * 53 + 7) % 94}%`,
          animation: `twinkle ${2 + (i % 3)}s ease-in-out ${(i * 0.3) % 2}s infinite`,
        }} />
      ))}

      {/* ── TOP BAR ─────────────────────────────────────────────────────────── */}
      <div style={{ background: "rgba(4,8,32,0.97)", backdropFilter: "blur(14px)", borderBottom: "1px solid rgba(255,255,255,0.06)", padding: "10px 16px 8px", flexShrink: 0, zIndex: 10 }}>
        {/* Row 1: breadcrumb + mastery ring + reset */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
          <span style={{ fontSize: "15px", flexShrink: 0 }}>🧭</span>
          <button onClick={goOverview}
            style={{ fontSize: "12px", fontWeight: isOverview ? 800 : 600, color: isOverview ? "#fff" : "rgba(165,180,252,0.7)", background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", padding: 0 }}>
            All Chapters
          </button>
          {!isOverview && <>
            <span style={{ color: "rgba(255,255,255,0.25)", fontSize: "12px" }}>›</span>
            <span style={{ fontSize: "12px", fontWeight: 800, color: "#fff", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>
              {activeChap?.name ?? view}
            </span>
          </>}
          <div style={{ marginLeft: isOverview ? "auto" : undefined, display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 }}>
            <button onClick={() => { setPan({ x: 0, y: 0 }); setScale(1); }}
              style={{ fontSize: "10px", color: "rgba(255,255,255,0.35)", background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", padding: "3px 7px", cursor: "pointer", fontFamily: "inherit" }}>
              ⊹ Reset
            </button>
            {/* Mastery ring */}
            <div style={{ position: "relative", width: "36px", height: "36px", flexShrink: 0 }}>
              <svg width="36" height="36" viewBox="0 0 36 36">
                <circle cx="18" cy="18" r="13" fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="3.5" transform="rotate(-90 18 18)" />
                <circle cx="18" cy="18" r="13" fill="none" stroke={chColor} strokeWidth="3.5"
                  strokeDasharray="81.68" strokeDashoffset={81.68 * (1 - progress / 100)}
                  strokeLinecap="round" transform="rotate(-90 18 18)" />
              </svg>
              <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "8px", fontWeight: 800, color: chColor }}>{progress}%</div>
            </div>
          </div>
        </div>

        {/* Row 2: route mode tabs + grade filter (overview) / ETA (detail) */}
        <div style={{ display: "flex", alignItems: "center", gap: "5px", flexWrap: "wrap" }}>
          {(["focused", "deep", "revision"] as const).map(m => (
            <button key={m} onClick={() => setRouteMode(m)} style={{
              padding: "3px 8px", borderRadius: "10px", fontSize: "10px", fontWeight: 700, cursor: "pointer", fontFamily: "inherit",
              background: routeMode === m ? (m === "focused" ? "#4338ca" : m === "deep" ? "#00695c" : "#c62828") : "rgba(255,255,255,0.05)",
              color: routeMode === m ? "#fff" : "rgba(255,255,255,0.4)",
              border: routeMode === m ? "none" : "1px solid rgba(255,255,255,0.08)",
            }}>
              {m === "focused" ? "🎯 Focused" : m === "deep" ? "🔬 Deep" : "🔄 Revision"}
            </button>
          ))}

          {/* Subject + grade filter tabs — overview only */}
          {isOverview && (subjects.length > 1 || grades.length > 1) && (
            <div style={{ marginLeft: "auto", display: "flex", gap: "4px", flexWrap: "wrap" }}>
              {/* Subject filter */}
              {subjects.length > 1 && (
                <>
                  {["All", ...subjects].map(s => {
                    const active = s === "All" ? subjectFilter === null : subjectFilter === s;
                    return (
                      <button key={s} onClick={() => setSubjectFilter(s === "All" ? null : s)}
                        style={{ padding: "2px 8px", borderRadius: "8px", fontSize: "9px", fontWeight: 700, cursor: "pointer", fontFamily: "inherit",
                          background: active ? "rgba(255,255,255,0.18)" : "rgba(255,255,255,0.05)",
                          color: active ? "#fff" : "rgba(255,255,255,0.4)",
                          border: "1px solid rgba(255,255,255,0.1)" }}>
                        {s}
                      </button>
                    );
                  })}
                  {grades.length > 1 && <span style={{ color: "rgba(255,255,255,0.15)", fontSize: "11px", alignSelf: "center" }}>|</span>}
                </>
              )}
              {/* Grade filter */}
              {grades.length > 1 && (
                <>
                  {[null, ...grades].map(g => {
                    const active = gradeFilter === g;
                    return (
                      <button key={g ?? "all"} onClick={() => setGradeFilter(g)}
                        style={{ padding: "2px 7px", borderRadius: "8px", fontSize: "9px", fontWeight: 700, cursor: "pointer", fontFamily: "inherit",
                          background: active ? "rgba(255,255,255,0.18)" : "rgba(255,255,255,0.05)",
                          color: active ? "#fff" : "rgba(255,255,255,0.4)",
                          border: "1px solid rgba(255,255,255,0.1)" }}>
                        {g === null ? "All Grades" : `Gr ${g}`}
                      </button>
                    );
                  })}
                </>
              )}
            </div>
          )}

          {!isOverview && (
            <span style={{ marginLeft: "auto", fontSize: "10px", color: "rgba(255,255,255,0.3)" }}>ETA {etaLabel}</span>
          )}
        </div>
      </div>

      {/* ── CANVAS + PANELS ──────────────────────────────────────────────────── */}
      {isOverview ? (
        /* Overview: full-width drag canvas */
        <div
          style={{ flex: 1, overflow: "hidden", touchAction: "none", position: "relative", cursor: isDragging ? "grabbing" : "grab", userSelect: "none" }}
          onTouchStart={onTouchStart}
          onTouchMove={onTouchMove}
          onTouchEnd={onTouchEnd}
          onMouseDown={(e) => { mouseRef.current = { x: e.clientX, y: e.clientY, dragged: false }; }}
          onMouseMove={(e) => {
            if (!mouseRef.current) return;
            const dx = e.clientX - mouseRef.current.x;
            const dy = e.clientY - mouseRef.current.y;
            if (!mouseRef.current.dragged && Math.sqrt(dx * dx + dy * dy) > 4) {
              mouseRef.current.dragged = true; setIsDragging(true);
            }
            if (mouseRef.current.dragged) {
              setPan(p => ({ x: p.x + dx, y: p.y + dy }));
              mouseRef.current = { x: e.clientX, y: e.clientY, dragged: true };
            }
          }}
          onMouseUp={() => { mouseRef.current = null; setIsDragging(false); }}
          onMouseLeave={() => { mouseRef.current = null; setIsDragging(false); }}
          onWheel={(e) => { e.preventDefault(); setScale(s => Math.min(4, Math.max(0.2, s * (e.deltaY > 0 ? 0.9 : 1.11)))); }}
        >
          {loadingChaps ? (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "rgba(255,255,255,0.4)" }}>
              <div style={{ textAlign: "center" }}>
                <p style={{ fontSize: "28px", marginBottom: "10px" }}>🧭</p>
                <p style={{ fontSize: "13px" }}>Loading chapters…</p>
              </div>
            </div>
          ) : (
            <svg
              viewBox={`0 0 2000 ${getOverviewSvgHeight(visibleChapters)}`}
              width="100%" height="100%"
              preserveAspectRatio="xMidYMid meet"
              style={{ display: "block", transform: `translate(${pan.x}px,${pan.y}px) scale(${scale})`, transformOrigin: "center center", willChange: "transform" }}
            >
              <defs>
                {visibleChapters.map(ch => (
                  <radialGradient key={ch.id} id={`ogr-${ch.id}`} cx="50%" cy="40%" r="60%">
                    <stop offset="0%"   stopColor={ch.color} stopOpacity="0.4" />
                    <stop offset="100%" stopColor={ch.color} stopOpacity="0.05" />
                  </radialGradient>
                ))}
                <marker id="arr-ch" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <path d="M0,0 L0,8 L8,4 z" fill="rgba(255,255,255,0.25)" />
                </marker>
              </defs>

              {/* Section labels + divider (only when both subjects visible) */}
              {subjects.length > 1 && (<>
                <text x="572" y="44" textAnchor="middle"
                  fill="rgba(255,255,255,0.12)" fontSize="14" fontWeight="900" letterSpacing="5">SCIENCE</text>
                <text x="1527" y="44" textAnchor="middle"
                  fill="rgba(255,255,255,0.12)" fontSize="14" fontWeight="900" letterSpacing="5">MATHEMATICS</text>
                <line x1="920" y1="0" x2="920" y2="1160"
                  stroke="rgba(255,255,255,0.04)" strokeWidth="1" strokeDasharray="6 6" />
              </>)}

              {/* Cross-chapter prerequisite edges (CHAPTER_LINK from Neo4j) */}
              {chapterEdges.map((oe, i) => {
                const fm = visibleChapters.find(c => c.id === oe.from_id);
                const tm = visibleChapters.find(c => c.id === oe.to_id);
                if (!fm || !tm) return null;
                const fp  = getChapterGridPos(fm, visibleChapters);
                const tp  = getChapterGridPos(tm, visibleChapters);
                const fpx = fp.x, fpy = fp.y, tpx = tp.x, tpy = tp.y;
                const dx  = tpx - fpx, dy = tpy - fpy;
                const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                const R    = fm.subconcept_count > 0 ? (fm.ov_radius || 46) : 26;
                const TR   = tm.subconcept_count > 0 ? (tm.ov_radius || 46) : 26;
                // Trim line to orb edges
                const sx = fpx + (dx / dist) * R;
                const sy = fpy + (dy / dist) * R;
                const ex = tpx - (dx / dist) * (TR + 9);
                const ey = tpy - (dy / dist) * (TR + 9);
                const mx = (fpx + tpx) / 2, my = (fpy + tpy) / 2;
                return (
                  <g key={i}>
                    <line x1={sx} y1={sy} x2={ex} y2={ey}
                      stroke="rgba(255,255,255,0.18)" strokeWidth="1.5" strokeDasharray="6 4"
                      markerEnd="url(#arr-ch)" />
                    {oe.label && (
                      <text x={mx} y={my - 7} textAnchor="middle"
                        fill="rgba(255,255,255,0.3)" fontSize="9" fontWeight="600">{oe.label}</text>
                    )}
                  </g>
                );
              })}

              {/* Chapter orbs */}
              {visibleChapters.map((ch, idx) => {
                const pos     = getChapterGridPos(ch, visibleChapters);
                const px      = pos.x;
                const py      = pos.y;
                const hasContent = ch.subconcept_count > 0;

                /* Coming-soon: render as a small compact pill — no ring, no halo, no ETA */
                if (!hasContent) {
                  const cr = 26;
                  const nameWords = ch.name.split(" ").slice(0, 3); // max 3 words
                  const nLines  = nameWords.length;
                  const nStartY = py - ((nLines - 1) * 10) / 2;
                  return (
                    <g key={ch.id} onClick={() => drillInto(ch.id)} style={{ cursor: "pointer" }} opacity="0.55">
                      <circle cx={px} cy={py} r={cr}
                        fill={hexToRgba(ch.color, 0.06)}
                        stroke={ch.color} strokeWidth="1"
                        strokeDasharray="4 3" />
                      {nameWords.map((word, wi) => (
                        <text key={wi} x={px} y={nStartY + wi * 11}
                          textAnchor="middle" dominantBaseline="middle"
                          fill="rgba(255,255,255,0.5)" fontSize="8" fontWeight="700">
                          {word}
                        </text>
                      ))}
                      <text x={px} y={py + cr + 10} textAnchor="middle"
                        fill={ch.color} fontSize="7.5" fontWeight="600" opacity="0.7">{ch.subject}</text>
                    </g>
                  );
                }

                /* Active chapter: full orb with ring, halo, mastery % */
                const r       = ch.ov_radius > 0 ? ch.ov_radius : 46;
                const ringR   = r + 8;
                const circumf = 2 * Math.PI * ringR;
                const pct     = ch.mastery_pct;
                const words   = ch.name.split(" ");
                const startY  = py - ((words.length - 1) * 13) / 2;
                return (
                  <g key={ch.id} onClick={() => drillInto(ch.id)} style={{ cursor: "pointer" }}>
                    {/* Glow halo */}
                    <circle cx={px} cy={py} r={r + 22} fill={`url(#ogr-${ch.id})`} />
                    {/* Ring track */}
                    <circle cx={px} cy={py} r={ringR}
                      fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="3"
                      transform={`rotate(-90 ${px} ${py})`} />
                    {/* Ring progress */}
                    {pct > 0 && (
                      <circle cx={px} cy={py} r={ringR}
                        fill="none" stroke={ch.color} strokeWidth="3"
                        strokeDasharray={`${circumf}`} strokeDashoffset={circumf * (1 - pct / 100)}
                        strokeLinecap="round"
                        transform={`rotate(-90 ${px} ${py})`} />
                    )}
                    {/* Orb body */}
                    <circle cx={px} cy={py} r={r}
                      fill={hexToRgba(ch.color, 0.18)}
                      stroke={ch.color} strokeWidth="2" />
                    {/* Chapter name */}
                    {words.map((word, wi) => (
                      <text key={wi} x={px} y={startY + wi * 14}
                        textAnchor="middle" dominantBaseline="middle"
                        fill="#fff" fontSize={r > 48 ? "12" : "11"} fontWeight="800">
                        {word}
                      </text>
                    ))}
                    {/* Subject + ETA below orb */}
                    <text x={px} y={py + ringR + 13} textAnchor="middle"
                      fill={ch.color} fontSize="10" fontWeight="700">{ch.subject}</text>
                    <text x={px} y={py + ringR + 25} textAnchor="middle"
                      fill="rgba(255,255,255,0.3)" fontSize="9">{ch.eta}</text>
                    {/* Mastery % inside orb */}
                    {pct > 0 && (
                      <text x={px} y={py + r - 9} textAnchor="middle" dominantBaseline="middle"
                        fill={ch.color} fontSize="15" fontWeight="900">{pct}%</text>
                    )}
                  </g>
                );
              })}
            </svg>
          )}
        </div>
      ) : (
        /* Chapter detail: three-panel layout */
        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

          {/* ── LEFT INFO PANEL ─────────────────────────────────────────────── */}
          <div style={{
            width: "256px", flexShrink: 0,
            background: "rgba(4,8,32,0.97)", borderRight: "1px solid rgba(255,255,255,0.06)",
            padding: "16px 14px", overflowY: "auto", display: "flex", flexDirection: "column",
          }}>
            {/* Chapter header */}
            <div style={{ marginBottom: "14px" }}>
              <p style={{ fontSize: "9px", color: chColor, fontWeight: 800, letterSpacing: "1px", marginBottom: "2px" }}>
                {activeChap?.subject?.toUpperCase()}
              </p>
              <p style={{ fontSize: "15px", fontWeight: 800, color: "#fff", lineHeight: 1.25, marginBottom: "2px" }}>
                {activeChap?.name}
              </p>
              <p style={{ fontSize: "10px", color: "rgba(255,255,255,0.3)" }}>Class {activeChap?.grade} · NCERT</p>
            </div>

            {/* Overall mastery ring */}
            <div style={{ display: "flex", alignItems: "center", gap: "12px", background: "rgba(255,255,255,0.04)", borderRadius: "10px", padding: "10px 12px", marginBottom: "12px" }}>
              <div style={{ position: "relative", width: "44px", height: "44px", flexShrink: 0 }}>
                <svg width="44" height="44" viewBox="0 0 44 44">
                  <circle cx="22" cy="22" r="16" fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="3.5" />
                  <circle cx="22" cy="22" r="16" fill="none" stroke={chColor} strokeWidth="3.5"
                    strokeDasharray="100.5" strokeDashoffset={100.5 * (1 - progress / 100)}
                    strokeLinecap="round" transform="rotate(-90 22 22)" />
                </svg>
                <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "9px", fontWeight: 800, color: chColor }}>{progress}%</div>
              </div>
              <div>
                <p style={{ fontSize: "20px", fontWeight: 900, color: chColor, lineHeight: 1 }}>{progress}%</p>
                <p style={{ fontSize: "8px", color: "rgba(255,255,255,0.38)", marginTop: "1px" }}>OVERALL MASTERY</p>
                <p style={{ fontSize: "9px", color: "rgba(255,255,255,0.3)" }}>{completed.length} of {nodes.length} mastered</p>
              </div>
            </div>

            {/* Currently learning */}
            {current && (
              <div style={{ background: "rgba(41,121,255,0.09)", border: "1px solid rgba(41,121,255,0.18)", borderRadius: "10px", padding: "10px", marginBottom: "10px" }}>
                <p style={{ fontSize: "8px", fontWeight: 800, color: "#82b1ff", letterSpacing: "1px", marginBottom: "3px" }}>📍 CURRENTLY LEARNING</p>
                <p style={{ fontSize: "12px", fontWeight: 700, color: "#fff", lineHeight: 1.2 }}>{current.name}</p>
                <p style={{ fontSize: "9px", color: "rgba(255,255,255,0.35)", marginTop: "2px" }}>{activeChap?.name} · {progress}% mastery</p>
              </div>
            )}

            {/* Legend */}
            <div style={{ marginBottom: "10px" }}>
              <p style={{ fontSize: "8px", color: "rgba(255,255,255,0.28)", fontWeight: 700, letterSpacing: "1px", marginBottom: "6px" }}>LEGEND</p>
              {[
                { color: "#00e676", label: "Mastered" },
                { color: "#2979ff", label: "In Progress (you)" },
                { color: "#ffd740", label: "Ready to Learn" },
                { color: "rgba(255,255,255,0.2)", label: "Not yet reachable" },
              ].map(l => (
                <div key={l.label} style={{ display: "flex", alignItems: "center", gap: "7px", marginBottom: "4px" }}>
                  <div style={{ width: "7px", height: "7px", borderRadius: "50%", background: l.color, flexShrink: 0 }} />
                  <p style={{ fontSize: "10px", color: "rgba(255,255,255,0.5)" }}>{l.label}</p>
                </div>
              ))}
            </div>

            {/* Divider */}
            <div style={{ height: "1px", background: "rgba(255,255,255,0.05)", marginBottom: "10px" }} />

            {/* Progress stats */}
            <div style={{ marginBottom: "10px" }}>
              <p style={{ fontSize: "8px", color: "rgba(255,255,255,0.28)", fontWeight: 700, letterSpacing: "1px", marginBottom: "6px" }}>PROGRESS</p>
              {[
                { label: "Mastered",    val: String(completed.length),          color: "#00e676" },
                { label: "In Progress", val: String(current ? 1 : 0),           color: "#2979ff" },
                { label: "Ready",       val: String(route.length),               color: "#ffd740" },
                { label: "Coming up",   val: String(locked.length),              color: "rgba(255,255,255,0.3)" },
                { label: "ETA",         val: activeChap?.eta ?? "~8 sessions",   color: "rgba(255,255,255,0.5)" },
              ].map(s => (
                <div key={s.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "3px" }}>
                  <p style={{ fontSize: "10px", color: "rgba(255,255,255,0.38)" }}>{s.label}</p>
                  <p style={{ fontSize: "10px", fontWeight: 700, color: s.color }}>{s.val}</p>
                </div>
              ))}
            </div>

            {/* Recommended next */}
            {current && route.length > 0 && (
              <div style={{ background: "rgba(99,102,241,0.09)", border: "1px solid rgba(99,102,241,0.18)", borderRadius: "10px", padding: "10px", marginBottom: "10px" }}>
                <p style={{ fontSize: "8px", fontWeight: 800, color: "#a5b4fc", letterSpacing: "1px", marginBottom: "3px" }}>⚡ RECOMMENDED NEXT</p>
                <p style={{ fontSize: "10px", color: "rgba(255,255,255,0.65)", lineHeight: 1.5 }}>
                  Master <strong style={{ color: "#fff" }}>{current.name}</strong> to unlock <strong style={{ color: "#ffd740" }}>{route[0].name}</strong>
                </p>
              </div>
            )}

            {/* Continue button — pinned to bottom */}
            <div style={{ marginTop: "auto", paddingTop: "8px" }}>
              {activeGps && (
                <button onClick={() => onStart(activeGps)}
                  style={{ width: "100%", padding: "11px", borderRadius: "11px", background: "linear-gradient(135deg,#4338ca,#7c3aed)", color: "#fff", fontSize: "13px", fontWeight: 800, cursor: "pointer", border: "none", fontFamily: "inherit", boxShadow: "0 2px 14px rgba(67,56,202,0.4)" }}>
                  {current ? "▶ Continue Practice" : "✓ Chapter Complete!"}
                </button>
              )}
            </div>
          </div>

          {/* ── CENTER CANVAS ────────────────────────────────────────────────── */}
          {loadingGps && !activeGps ? (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "rgba(255,255,255,0.4)" }}>
              <div style={{ textAlign: "center" }}>
                <p style={{ fontSize: "28px", marginBottom: "10px" }}>🗺️</p>
                <p style={{ fontSize: "13px" }}>Loading chapter map…</p>
              </div>
            </div>
          ) : nodes.length === 0 ? (
            <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "12px", color: "rgba(255,255,255,0.4)", padding: "20px", textAlign: "center" }}>
              <p style={{ fontSize: "36px" }}>🔭</p>
              <p style={{ fontSize: "16px", fontWeight: 700, color: "#fff" }}>{activeChap?.name ?? view}</p>
              <p style={{ fontSize: "13px" }}>Content for this chapter is being prepared. Check back soon!</p>
              <button onClick={goOverview}
                style={{ marginTop: "8px", padding: "10px 20px", borderRadius: "12px", background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.15)", color: "#fff", fontSize: "13px", cursor: "pointer", fontFamily: "inherit" }}>
                ← All Chapters
              </button>
            </div>
          ) : (
            <div
              style={{ flex: 1, overflow: "hidden", touchAction: "none", position: "relative", cursor: isDragging ? "grabbing" : "grab", userSelect: "none" }}
              onTouchStart={onTouchStart}
              onTouchMove={onTouchMove}
              onTouchEnd={onTouchEnd}
              onMouseDown={(e) => { mouseRef.current = { x: e.clientX, y: e.clientY, dragged: false }; }}
              onMouseMove={(e) => {
                if (!mouseRef.current) return;
                const dx = e.clientX - mouseRef.current.x;
                const dy = e.clientY - mouseRef.current.y;
                if (!mouseRef.current.dragged && Math.sqrt(dx * dx + dy * dy) > 4) {
                  mouseRef.current.dragged = true; setIsDragging(true);
                }
                if (mouseRef.current.dragged) {
                  setPan(p => ({ x: p.x + dx, y: p.y + dy }));
                  mouseRef.current = { x: e.clientX, y: e.clientY, dragged: true };
                }
              }}
              onMouseUp={() => { mouseRef.current = null; setIsDragging(false); }}
              onMouseLeave={() => { mouseRef.current = null; setIsDragging(false); }}
              onWheel={(e) => { e.preventDefault(); setScale(s => Math.min(4, Math.max(0.2, s * (e.deltaY > 0 ? 0.9 : 1.11)))); }}
            >
              <svg
                viewBox="0 0 340 510"
                width="100%" height="100%"
                preserveAspectRatio="xMidYMid meet"
                style={{ display: "block", transformOrigin: "center center", transform: `translate(${pan.x}px,${pan.y}px) scale(${scale})`, willChange: "transform" }}
              >
                <defs>
                  <marker id="arr-g" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
                    <path d="M0,0 L0,7 L7,3.5 z" fill="rgba(0,230,118,0.7)" />
                  </marker>
                  <marker id="arr-b" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
                    <path d="M0,0 L0,7 L7,3.5 z" fill="rgba(41,121,255,0.6)" />
                  </marker>
                  <marker id="arr-d" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
                    <path d="M0,0 L0,7 L7,3.5 z" fill="rgba(255,255,255,0.18)" />
                  </marker>
                  <filter id="glow-g" x="-80%" y="-80%" width="260%" height="260%">
                    <feGaussianBlur stdDeviation="4" result="b" />
                    <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
                  </filter>
                  <filter id="glow-b" x="-80%" y="-80%" width="260%" height="260%">
                    <feGaussianBlur stdDeviation="5" result="b" />
                    <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
                  </filter>
                </defs>

                {/* Edges */}
                {edges.map((edge, i) => {
                  const fp = posMap[edge.from_id];
                  const tp = posMap[edge.to_id];
                  if (!fp || !tp) return null;
                  const dx   = tp.x - fp.x, dy = tp.y - fp.y;
                  const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                  const sx   = fp.x + (dx / dist) * (R + 2);
                  const sy   = fp.y + (dy / dist) * (R + 2);
                  const ex   = tp.x - (dx / dist) * (R + 9);
                  const ey   = tp.y - (dy / dist) * (R + 9);
                  const fromState = getState(edge.from_id);
                  const isRec     = isRecommendedEdge(edge.from_id, edge.to_id);
                  return (
                    <line key={i} x1={sx} y1={sy} x2={ex} y2={ey}
                      stroke={isRec ? "#2979ff" : edgeColor(edge.from_id)}
                      strokeWidth={isRec ? 2.5 : fromState === "ghost" ? 1 : 1.5}
                      strokeDasharray={isRec ? "8 4" : fromState === "ghost" ? "4 3" : undefined}
                      strokeDashoffset={isRec ? "16" : undefined}
                      className={isRec ? "flow-edge" : undefined}
                      markerEnd={fromState === "done" ? "url(#arr-g)" : fromState === "current" ? "url(#arr-b)" : "url(#arr-d)"}
                    />
                  );
                })}

                {/* Nodes */}
                {nodes.map(node => {
                  const state = getState(node.id);
                  const cfg   = SCFG[state];
                  const isCur = state === "current";
                  const isGh  = state === "ghost";
                  const filt  = state === "done" ? "url(#glow-g)" : state === "current" ? "url(#glow-b)" : undefined;
                  const words = node.name.split(" ");
                  const mid   = Math.ceil(words.length / 2);
                  const ln1   = words.slice(0, mid).join(" ");
                  const ln2   = words.slice(mid).join(" ");
                  const ly    = node.y + R + 10;
                  return (
                    <g key={node.id}
                      onClick={() => {
                        if (!mouseRef.current?.dragged) {
                          setDetailNode({ id: node.id, name: node.name, state, bloomTarget: node.bloom_target, varkHint: node.vark_hint });
                        }
                      }}
                      style={{ cursor: "pointer" }}
                    >
                      {/* Status label above node */}
                      {!isGh && (
                        <text x={node.x} y={node.y - R - 14} textAnchor="middle"
                          fill={state === "done" ? "#00e676" : state === "current" ? "#82b1ff" : "#ffd740"}
                          fontSize="7.5" fontWeight="800">
                          {state === "done" ? "✓ MASTERED" : state === "current" ? "📍 YOU ARE HERE" : "Ready ▶"}
                        </text>
                      )}
                      {isCur && (
                        <circle cx={node.x} cy={node.y} r={R}
                          fill="none" stroke="rgba(41,121,255,0.4)" strokeWidth="2"
                          className="gps-pulse-ring" />
                      )}
                      <circle cx={node.x} cy={node.y} r={R}
                        fill={cfg.fill} stroke={cfg.stroke} strokeWidth={cfg.sw}
                        strokeDasharray={isGh ? "4 3" : undefined}
                        opacity={cfg.op} filter={filt} />
                      <text x={node.x} y={node.y} textAnchor="middle" dominantBaseline="central"
                        fill={cfg.text} fontSize={isCur ? 17 : state === "done" ? 15 : 12}
                        fontWeight="800" opacity={cfg.op}>{cfg.icon}</text>
                      <text x={node.x} y={ly} textAnchor="middle" dominantBaseline="hanging"
                        fill={cfg.text} fontSize="8" fontWeight="600" opacity={cfg.op}>{ln1}</text>
                      {ln2 && (
                        <text x={node.x} y={ly + 10} textAnchor="middle" dominantBaseline="hanging"
                          fill={cfg.text} fontSize="8" fontWeight="600" opacity={cfg.op}>{ln2}</text>
                      )}
                    </g>
                  );
                })}
              </svg>
            </div>
          )}

          {/* ── RIGHT NODE DETAIL PANEL ──────────────────────────────────────── */}
          {detailNode && (
            <div style={{
              width: "296px", flexShrink: 0,
              background: "rgba(4,8,30,0.97)", borderLeft: "1px solid rgba(255,255,255,0.06)",
              padding: "16px 14px", overflowY: "auto", display: "flex", flexDirection: "column",
            }}>
              {/* Header */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
                <p style={{ fontSize: "8px", color: "rgba(255,255,255,0.28)", fontWeight: 700, letterSpacing: "0.8px", lineHeight: 1.5 }}>
                  {activeChap?.name?.toUpperCase()} · CLASS {activeChap?.grade}
                </p>
                <button onClick={() => setDetailNode(null)}
                  style={{ background: "none", border: "none", color: "rgba(255,255,255,0.35)", cursor: "pointer", fontSize: "20px", lineHeight: 1, padding: "0", fontFamily: "inherit" }}>×</button>
              </div>

              {/* Status badge */}
              <p style={{ fontSize: "8px", fontWeight: 800, textTransform: "uppercase", letterSpacing: "1.2px", marginBottom: "3px",
                color: detailNode.state === "done" ? "#00e676" : detailNode.state === "current" ? "#82b1ff" : detailNode.state === "ready" ? "#ffd740" : "rgba(255,255,255,0.4)" }}>
                {detailNode.state === "done" ? "✓ MASTERED" : detailNode.state === "current" ? "📍 YOU ARE HERE" : detailNode.state === "ready" ? "READY ▶" : "NOT YET REACHABLE"}
              </p>
              <p style={{ fontSize: "19px", fontWeight: 800, color: "#fff", marginBottom: "14px", lineHeight: 1.2 }}>{detailNode.name}</p>

              {/* Bloom's taxonomy bars */}
              {detailNode.bloomTarget && (
                <div style={{ marginBottom: "14px" }}>
                  <p style={{ fontSize: "8px", color: "rgba(255,255,255,0.28)", marginBottom: "7px", fontWeight: 700, letterSpacing: "0.8px" }}>BLOOM&apos;S TAXONOMY</p>
                  {(["Remember", "Understand", "Apply", "Analyse", "Evaluate", "Create"] as const).map((b, bi) => {
                    const targetIdx = ["Remember", "Understand", "Apply", "Analyse", "Evaluate", "Create"].indexOf(detailNode.bloomTarget ?? "Remember");
                    const pct    = bi <= targetIdx ? Math.max(8, 100 - bi * 14) : 0;
                    const active = bi <= targetIdx;
                    const barColor = bi < 2 ? "#00e676" : bi < 4 ? "#ff9100" : "#ef5350";
                    return (
                      <div key={b} style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "5px" }}>
                        <p style={{ fontSize: "10px", color: "rgba(255,255,255,0.45)", width: "68px", flexShrink: 0 }}>{b}</p>
                        <div style={{ flex: 1, height: "4px", background: "rgba(255,255,255,0.06)", borderRadius: "3px", overflow: "hidden" }}>
                          <div style={{ width: `${pct}%`, height: "100%", background: active ? barColor : "transparent", borderRadius: "3px", transition: "width 0.4s ease" }} />
                        </div>
                        <p style={{ fontSize: "9px", color: active ? "rgba(255,255,255,0.4)" : "transparent", width: "26px", textAlign: "right" }}>{active ? `${pct}%` : ""}</p>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Best learning mode */}
              {detailNode.varkHint && (
                <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "10px", padding: "10px", marginBottom: "12px" }}>
                  <p style={{ fontSize: "8px", color: "rgba(255,255,255,0.28)", marginBottom: "6px", fontWeight: 700, letterSpacing: "0.8px" }}>BEST LEARNING MODE</p>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontSize: "18px" }}>
                      {detailNode.varkHint === "V" ? "👁️" : detailNode.varkHint === "A" ? "👂" : detailNode.varkHint === "R" ? "📖" : "🤸"}
                    </span>
                    <div>
                      <p style={{ fontSize: "13px", fontWeight: 700, color: "#fff" }}>
                        {detailNode.varkHint === "V" ? "Visual" : detailNode.varkHint === "A" ? "Auditory" : detailNode.varkHint === "R" ? "Read / Write" : "Kinesthetic"}
                      </p>
                      <p style={{ fontSize: "9px", color: "rgba(255,255,255,0.35)" }}>Optimised for your VARK profile</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Description */}
              <p style={{ fontSize: "11px", color: "rgba(255,255,255,0.4)", marginBottom: "16px", lineHeight: "1.6" }}>
                {detailNode.state === "done"    ? "You've mastered this concept. Review periodically to reinforce long-term retention." :
                 detailNode.state === "current" ? "This is your GPS position. Gyaan will guide you step by step through this concept." :
                 detailNode.state === "ready"   ? "All prerequisites done! You can start this concept right now." :
                                                  "Jump here anytime — Gyaan automatically bridges any knowledge gaps for you."}
              </p>

              {/* Action button */}
              <div style={{ marginTop: "auto" }}>
                {activeGps && (
                  <button onClick={() => { setDetailNode(null); onStart(activeGps); }}
                    style={{ width: "100%", padding: "12px", borderRadius: "12px", fontFamily: "inherit", cursor: "pointer", border: "none", color: "#fff", fontSize: "13px", fontWeight: 700,
                      background: detailNode.state === "done"
                        ? "linear-gradient(135deg,#00695c,#00897b)"
                        : "linear-gradient(135deg,#4338ca,#7c3aed)",
                      boxShadow: "0 4px 16px rgba(67,56,202,0.4)" }}>
                    {detailNode.state === "done"    ? "🔄 Review & Reinforce" :
                     detailNode.state === "current" ? "▶ Continue Practice"  :
                     detailNode.state === "ready"   ? "🚀 Start Learning"    :
                                                      "▶ Jump here — Gyaan adapts"}
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── GPS ORIENTATION CARD ───────────────────────────────────────────────────
function GPSOrientationCard({ gps, onAction }: { gps: GPSRoute; onAction: (text: string) => void }) {
  const current   = gps.current;
  const completed = gps.completed ?? [];
  const nextUp    = gps.route?.[0];
  const pct       = Math.round(gps.progress_pct ?? 0);
  const chapterLabel = (gps.chapter_id ?? "").replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());

  return (
    <div style={{ background: "linear-gradient(135deg,#4338ca 0%,#6d28d9 100%)", borderRadius: 18, padding: 16, margin: "4px 0 8px", color: "white" }}>
      {/* Header */}
      <div style={{ fontSize: 10, opacity: 0.7, textTransform: "uppercase", letterSpacing: 1, marginBottom: 2 }}>📍 Your GPS Position</div>
      <div style={{ fontSize: 20, fontWeight: 800, marginBottom: 1 }}>{current?.name ?? "Starting out"}</div>
      <div style={{ fontSize: 12, opacity: 0.75, marginBottom: 10 }}>{chapterLabel}</div>

      {/* Progress bar */}
      <div style={{ background: "rgba(255,255,255,0.2)", borderRadius: 8, height: 6, marginBottom: 12 }}>
        <div style={{ background: "#fbbf24", borderRadius: 8, height: 6, width: `${pct}%`, transition: "width 1s ease" }} />
      </div>

      {/* Stats row */}
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <div style={{ flex: 1, background: "rgba(255,255,255,0.15)", borderRadius: 10, padding: "8px 10px", textAlign: "center" }}>
          <div style={{ fontSize: 20, fontWeight: 800 }}>{completed.length}</div>
          <div style={{ fontSize: 10, opacity: 0.8 }}>✅ Done</div>
        </div>
        <div style={{ flex: 1, background: "rgba(255,255,255,0.15)", borderRadius: 10, padding: "8px 10px", textAlign: "center" }}>
          <div style={{ fontSize: 20, fontWeight: 800 }}>{pct}%</div>
          <div style={{ fontSize: 10, opacity: 0.8 }}>🎯 Progress</div>
        </div>
        {nextUp && (
          <div style={{ flex: 2, background: "rgba(255,255,255,0.15)", borderRadius: 10, padding: "8px 10px" }}>
            <div style={{ fontSize: 12, fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{nextUp.name}</div>
            <div style={{ fontSize: 10, opacity: 0.8 }}>🗺️ Up next</div>
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
        <button
          onClick={() => onAction(`Let's continue learning about ${current?.name ?? "this concept"}! Give me a question to test my understanding.`)}
          style={{ flex: 1, background: "#fbbf24", color: "#78350f", border: "none", borderRadius: 12, padding: "11px 8px", fontWeight: 800, fontSize: 13, cursor: "pointer" }}>
          🔥 Continue Learning
        </button>
        <button
          onClick={() => onAction(`Give me a quick challenge question on ${current?.name ?? "this concept"} — make it interesting!`)}
          style={{ flex: 1, background: "rgba(255,255,255,0.15)", color: "white", border: "1px solid rgba(255,255,255,0.3)", borderRadius: 12, padding: "11px 8px", fontWeight: 700, fontSize: 13, cursor: "pointer" }}>
          ⚡ Challenge Me!
        </button>
      </div>

      {/* Photo upload CTA */}
      <button
        onClick={() => onAction("__OPEN_PHOTO__")}
        style={{ width: "100%", background: "rgba(255,255,255,0.12)", border: "1.5px dashed rgba(255,255,255,0.4)", borderRadius: 12, padding: "10px 12px", color: "white", fontWeight: 600, fontSize: 12, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
        📸 Upload homework question — Gyaan will guide you!
      </button>
    </div>
  );
}

// ── CHAT SCREEN ────────────────────────────────────────────────────────────
function ChatScreen({ gps, vark, studentId, studentName, messages, setMessages, bloomLevel, setBloomLevel, hintCount, setHintCount, activityShown, setActivityShown, autoPrompt, onAutoPromptSent, onXpEarned }: {
  gps: GPSRoute | null;
  vark: VARKProfile | null;
  studentId: string;
  studentName: string;
  messages: Message[];
  autoPrompt?: string | null;
  onAutoPromptSent?: () => void;
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  bloomLevel: string;
  setBloomLevel: React.Dispatch<React.SetStateAction<string>>;
  hintCount: number;
  setHintCount: React.Dispatch<React.SetStateAction<number>>;
  activityShown: boolean;
  setActivityShown: React.Dispatch<React.SetStateAction<boolean>>;
  onXpEarned: (xp: number) => void;
}) {
  const [input, setInput]           = useState("");
  const [loading, setLoading]       = useState(false);
  const [photoMode, setPhotoMode]   = useState<"guide" | "check">("guide");
  const [showPhotoPanel, setShowPhotoPanel] = useState(false);
  const [selectedFile, setSelectedFile]     = useState<File | null>(null);
  const [photoPreview, setPhotoPreview]     = useState<string | null>(null);
  const [diksha, setDiksha]         = useState<DikshaResource[]>([]);
  const [showDiksha, setShowDiksha] = useState(false);
  const [xpFloat, setXpFloat]       = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileRef   = useRef<HTMLInputElement>(null);

  const currentSC = gps?.current;
  const varkStyle = vark?.dominant ?? "K";

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Auto-fire a message when arriving from Quick Quiz / Explain This / Test Prep
  useEffect(() => {
    if (!autoPrompt) return;
    onAutoPromptSent?.();
    // Small delay so the chat screen has finished mounting
    const t = setTimeout(() => {
      setInput(autoPrompt);
      // Directly trigger send after populating input
      const doSend = async () => {
        setInput("");
        setMessages((m) => [...m, { role: "user", content: autoPrompt }]);
        setLoading(true);
        try {
          const history = messages.slice(-20).map((m) => ({ role: m.role, content: m.content }));
          const currentSCLocal = gps?.current;
          const bloomOrder = ["Remember", "Understand", "Apply", "Analyse", "Evaluate", "Create"];
          const res = await sendChat({
            studentId, studentName,
            message: autoPrompt,
            conversationHistory: history,
            subconcept_id:   currentSCLocal?.id           ?? "sc_contact_force",
            subconcept_name: currentSCLocal?.name         ?? "Contact Force",
            chapter_id:      gps?.chapter_id              ?? "",
            chapter_name:    gps?.chapter_id              ?? "Force & Pressure",
            bloom_level:     bloomLevel,
            bloom_target:    currentSCLocal?.bloom_target ?? "apply",
            vark_style:      varkStyle,
            hint_count:      hintCount,
            activity_shown:  activityShown,
            prereq_names:    gps?.locked?.map((n) => n.name) ?? [],
          });
          setHintCount(res.hint_count ?? 0);
          setActivityShown(res.activity_shown ?? false);
          if (res.bloom_advance) {
            const idx = bloomOrder.indexOf(bloomLevel);
            if (idx < bloomOrder.length - 1) setBloomLevel(bloomOrder[idx + 1]);
          }
          if ((res.xp_earned ?? 0) > 0) { onXpEarned(res.xp_earned); setXpFloat(res.xp_earned); setTimeout(() => setXpFloat(null), 2000); }
          setMessages((m) => [...m, { role: "assistant", content: res.reply, xp: res.xp_earned }]);
        } catch {
          setMessages((m) => [...m, { role: "assistant", content: "Oops! Something went wrong. Try again." }]);
        } finally {
          setLoading(false);
        }
      };
      doSend();
    }, 300);
    return () => clearTimeout(t);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoPrompt]);

  async function handleSend() {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    setMessages((m) => [...m, { role: "user", content: userMsg }]);
    setLoading(true);
    try {
      const history = messages.slice(-20).map((m) => ({ role: m.role, content: m.content }));
      const bloomOrder = ["Remember", "Understand", "Apply", "Analyse", "Evaluate", "Create"];
      const res = await sendChat({
        studentId,
        studentName,
        message: userMsg,
        conversationHistory: history,
        subconcept_id:   currentSC?.id           ?? "sc_contact_force",
        subconcept_name: currentSC?.name         ?? "Contact Force",
        chapter_id:      gps?.chapter_id         ?? "",
        chapter_name:    gps?.chapter_id         ?? "Force & Pressure",
        bloom_level:     bloomLevel,
        bloom_target:    currentSC?.bloom_target ?? "apply",
        vark_style:      varkStyle,
        hint_count:      hintCount,
        activity_shown:  activityShown,
        prereq_names:    gps?.locked?.map((n) => n.name) ?? [],
      });
      setHintCount(res.hint_count ?? 0);
      setActivityShown(res.activity_shown ?? false);
      if (res.bloom_advance) {
        const idx = bloomOrder.indexOf(bloomLevel);
        if (idx < bloomOrder.length - 1) setBloomLevel(bloomOrder[idx + 1]);
      }
      if ((res.xp_earned ?? 0) > 0) { onXpEarned(res.xp_earned); setXpFloat(res.xp_earned); setTimeout(() => setXpFloat(null), 2000); }
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
      const res = await sendPhoto(selectedFile, studentName, photoMode, "", varkStyle);
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
    } catch { setDiksha([]); }
  }

  function handleOrientationAction(text: string) {
    if (text === "__OPEN_PHOTO__") { setShowPhotoPanel(true); return; }
    setInput(text);
    setTimeout(() => {
      const btn = document.getElementById("gyaan-send-btn");
      if (btn) btn.click();
    }, 50);
  }

  const pct = Math.round(gps?.progress_pct ?? 0);

  return (
    <div className="flex flex-col h-screen max-h-screen" style={{ position: "relative" }}>
      {/* XP Float Animation */}
      {xpFloat && (
        <div style={{
          position: "absolute", top: 70, right: 20, zIndex: 100,
          background: "linear-gradient(135deg,#f59e0b,#ef4444)",
          color: "white", fontWeight: 900, fontSize: 22, padding: "8px 18px",
          borderRadius: 40, boxShadow: "0 4px 20px rgba(245,158,11,0.5)",
          animation: "xpFloat 2s ease-out forwards", pointerEvents: "none",
        }}>
          +{xpFloat} XP 🔥
        </div>
      )}

      {/* Gyaan Header */}
      <div style={{ background: "white", borderBottom: "1px solid #f0f0f0" }}>
        <div className="p-3 flex items-center gap-3">
          {/* Animated avatar */}
          <div style={{ width: 44, height: 44, borderRadius: "50%", background: "linear-gradient(135deg,#4338ca,#7c3aed)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22, boxShadow: "0 4px 12px rgba(99,102,241,0.4)", flexShrink: 0 }}>
            🧠
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ fontWeight: 800, color: "#1e1b4b", fontSize: 15, marginBottom: 1 }}>Gyaan <span style={{ fontSize: 10, fontWeight: 500, color: "#10b981", background: "#d1fae5", borderRadius: 8, padding: "1px 6px" }}>● Active</span></p>
            <p style={{ fontSize: 11, color: "#6366f1", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              📍 {currentSC?.name ?? "Force & Pressure"}
            </p>
          </div>
          <div className="flex gap-2 shrink-0">
            <span className={`text-xs px-2 py-1 rounded-full font-medium ${VARK_COLORS[varkStyle] ?? "bg-indigo-100 text-indigo-700"}`}>
              {VARK_LABELS[varkStyle] ?? "🤸 Kinesthetic"}
            </span>
            <button onClick={loadDiksha} className="text-xs px-2 py-1 bg-orange-50 text-orange-600 rounded-full font-medium">📚 NCERT</button>
          </div>
        </div>
        {/* Progress strip */}
        {gps && (
          <div style={{ height: 4, background: "#e0e7ff" }}>
            <div style={{ height: 4, background: "linear-gradient(90deg,#6366f1,#8b5cf6)", width: `${pct}%`, transition: "width 1s ease" }} />
          </div>
        )}
      </div>

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

      <div className="flex-1 overflow-y-auto no-scrollbar p-4 pb-4 bg-indigo-50/30 flex flex-col gap-3">
        {/* GPS Orientation Card — shown when chat is fresh */}
        {messages.length === 1 && gps && gps.current && (
          <GPSOrientationCard gps={gps} onAction={handleOrientationAction} />
        )}
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
                {renderMessage(msg.content)}
              </div>
              {(msg.xp ?? 0) > 0 && (
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

      {/* ── Suggestion chips — shown at start and after each Gyaan reply ── */}
      {!loading && messages.length > 0 && messages[messages.length - 1].role === "assistant" && (() => {
        const sc  = currentSC?.name ?? "this concept";
        const lvl = bloomLevel.toLowerCase();
        const chips: { label: string; action: string }[] =
          lvl === "remember"   ? [
            { label: "🤔 What is " + sc + "?", action: "What is " + sc + "? Explain simply." },
            { label: "💡 Give me a hint", action: "Give me a hint to understand " + sc },
            { label: "🎯 Quick quiz me!", action: "Give me a quick quiz question on " + sc },
          ] :
          lvl === "understand" ? [
            { label: "📖 Real-life example", action: "Give me a real-life example of " + sc },
            { label: "🤔 Why does this happen?", action: "Why does " + sc + " happen? Explain the reason." },
            { label: "⚡ Challenge me!", action: "Give me a challenging question on " + sc },
          ] :
          lvl === "apply"      ? [
            { label: "🧮 Give me a problem", action: "Give me a problem to solve on " + sc },
            { label: "🌍 Real-world use", action: "Where do we see " + sc + " in real life?" },
            { label: "🔥 Test me hard!", action: "Give me a harder question on " + sc },
          ] :
          lvl === "analyse"    ? [
            { label: "🔗 How does it connect?", action: "How does " + sc + " connect to other concepts?" },
            { label: "🤯 Harder question!", action: "Give me a much harder analytical question on " + sc },
            { label: "🎓 Explain like a teacher", action: "I want to explain " + sc + " like a teacher. Help me." },
          ] : [
            { label: "🏆 Toughest question!", action: "Give me the toughest question you can on " + sc },
            { label: "🌐 Real-world problem", action: "Give me a real-world problem involving " + sc },
            { label: "🎯 Evaluate my answer", action: "I want you to evaluate my understanding of " + sc },
          ];
        return (
          <div style={{ padding: "8px 12px 4px", background: "white", borderTop: "0.5px solid #f0f0f0" }}>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
              {chips.map((chip) => (
                <button key={chip.label}
                  onClick={() => { setInput(chip.action); setTimeout(() => document.getElementById("gyaan-send-btn")?.click(), 50); }}
                  style={{ fontSize: 12, padding: "7px 13px", borderRadius: 20, background: "#eef2ff", color: "#4338ca", border: "1px solid #c7d2fe", cursor: "pointer", whiteSpace: "nowrap", fontWeight: 600 }}>
                  {chip.label}
                </button>
              ))}
              <button
                onClick={() => setShowPhotoPanel(true)}
                style={{ fontSize: 12, padding: "7px 13px", borderRadius: 20, background: "#fef3c7", color: "#92400e", border: "1px solid #fde68a", cursor: "pointer", whiteSpace: "nowrap", fontWeight: 700 }}>
                📸 Upload Homework
              </button>
            </div>
          </div>
        );
      })()}

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

      <div className="bg-white border-t border-gray-100 p-3 pb-20 flex items-center gap-2">
        <button onClick={() => setShowPhotoPanel(!showPhotoPanel)}
          style={{ display: "flex", alignItems: "center", gap: 4, padding: "7px 12px", borderRadius: 20, background: showPhotoPanel ? "#fef3c7" : "#f5f3ff", border: "1px solid " + (showPhotoPanel ? "#fde68a" : "#ddd6fe"), cursor: "pointer", fontSize: 12, fontWeight: 700, color: showPhotoPanel ? "#92400e" : "#5b21b6", whiteSpace: "nowrap", flexShrink: 0 }}>
          📸 <span>Photo</span>
        </button>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Type your answer..."
          className="flex-1 bg-gray-50 rounded-full px-4 py-2.5 text-sm border border-gray-100 outline-none focus:border-indigo-300"
        />
        <button id="gyaan-send-btn" onClick={handleSend} disabled={loading}
          className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center text-white text-lg shrink-0 disabled:opacity-50 active:scale-95 transition-transform">
          ↑
        </button>
      </div>
    </div>
  );
}

// ── PROGRESS SCREEN ────────────────────────────────────────────────────────
function ProgressScreen({ vark, studentId, gps, streakDays }: {
  vark: VARKProfile | null;
  studentId: string;
  gps: GPSRoute | null;
  streakDays: number;
}) {
  const dominant   = vark?.dominant ?? "K";
  const confidence = vark ? Math.round(Math.max(vark.v_score, vark.a_score, vark.r_score, vark.k_score) * 100) : 25;
  const sessions   = vark?.session_count ?? 0;
  const days       = ["M", "T", "W", "T", "F", "S", "T"];

  // Real mastery from GPS data
  const completed    = gps?.completed?.length ?? 0;
  const totalNodes   = completed + (gps?.route?.length ?? 0) + (gps?.current ? 1 : 0);
  const masteryPct   = totalNodes > 0 ? Math.round((completed / totalNodes) * 100) : 0;
  const bloomLabels: Record<string, string> = {
    Remember: "Remember", Understand: "Understand", Apply: "Apply level",
    Analyse: "Analyse level", Evaluate: "Evaluate level", Create: "Create level",
  };

  return (
    <div className="flex flex-col gap-3 p-4 pb-24">
      <div>
        <h1 className="font-bold text-xl text-gray-900">Your Progress</h1>
        <p className="text-gray-400 text-sm">Grade 8 · Science</p>
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 flex items-center gap-4">
        <div className="relative w-20 h-20 shrink-0">
          <svg viewBox="0 0 80 80" className="w-20 h-20 -rotate-90">
            <circle cx="40" cy="40" r="32" fill="none" stroke="#e0e7ff" strokeWidth="8" />
            <circle cx="40" cy="40" r="32" fill="none" stroke="#4f46e5" strokeWidth="8"
              strokeDasharray={`${2 * Math.PI * 32}`}
              strokeDashoffset={`${2 * Math.PI * 32 * (1 - masteryPct / 100)}`}
              strokeLinecap="round" />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-bold text-indigo-700 text-lg">{masteryPct}%</span>
            <span className="text-gray-400 text-xs">Overall</span>
          </div>
        </div>
        <div>
          <p className="font-bold text-gray-900">Overall Mastery</p>
          <p className="text-sm text-gray-500 mt-1">Concepts: <span className="font-semibold text-gray-700">{completed} / {totalNodes}</span></p>
          <p className="text-sm text-gray-500">Bloom: <span className="font-semibold text-indigo-600">Apply level</span></p>
          <p className="text-sm text-gray-500">Sessions: <span className="font-semibold text-gray-700">{sessions}</span></p>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
        <div className="flex justify-between mb-3">
          <p className="font-semibold text-gray-800">🔥 {streakDays}-Day Streak</p>
          <p className="text-amber-500 text-sm font-semibold">{streakDays > 0 ? "Don't break it!" : "Start today!"}</p>
        </div>
        <div className="flex gap-1">
          {days.map((d, i) => (
            <div key={i} className="flex-1 flex flex-col items-center gap-1">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${i === 6 ? "bg-amber-100 ring-2 ring-amber-400" : i < streakDays ? "bg-amber-50" : "bg-gray-100"}`}>
                {i < streakDays ? "🔥" : "·"}
              </div>
              <span className="text-xs text-gray-400">{d}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
        <p className="font-semibold text-gray-800 mb-3">Chapter Mastery</p>
        <div className="mb-3">
          <div className="flex justify-between mb-1">
            <span className="text-sm text-gray-700">Force & Pressure</span>
            <span className="text-sm font-semibold text-gray-900">{masteryPct}%</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2">
            <div className="bg-indigo-500 rounded-full h-2 transition-all" style={{ width: `${masteryPct}%` }} />
          </div>
          <p className="text-xs text-gray-400 mt-1">{completed} of {totalNodes} subconcepts mastered</p>
        </div>
        <div className="py-2 text-xs text-gray-400 text-center border border-dashed border-gray-200 rounded-xl">
          🔒 More chapters unlock as you progress
        </div>
      </div>

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

      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
        <p className="font-semibold text-gray-800 mb-3">Recent Badges 🏆</p>
        <div className="grid grid-cols-4 gap-2">
          {[
            { icon: "🔥", label: "7-Day Streak", unlocked: true  },
            { icon: "⭐", label: "First Skill!", unlocked: true  },
            { icon: "🎯", label: "Apply Level",  unlocked: true  },
            { icon: "🧭", label: "Career Path",  unlocked: false },
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
function ProfileScreen({ vark, studentName, studentId, onLogout }: {
  vark: VARKProfile | null;
  studentName: string;
  studentId: string;
  onLogout: () => void;
}) {
  return (
    <div className="flex flex-col gap-3 p-4 pb-24">
      <div className="flex flex-col items-center py-4">
        <div className="w-20 h-20 rounded-full bg-indigo-600 flex items-center justify-center text-white text-3xl font-bold mb-3">
          {studentName[0]?.toUpperCase() ?? "S"}
        </div>
        <h2 className="font-bold text-xl text-gray-900">{studentName}</h2>
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
        { icon: "📚", label: "Chapters",   value: "3 in progress" },
        { icon: "🎯", label: "Bloom Level", value: "Apply"        },
        { icon: "📅", label: "Next Test",   value: "Oct 15 · 12 days" },
        { icon: "🏆", label: "Badges Earned", value: "3 / 8"     },
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
        <p className="text-xs text-gray-400 font-mono">{studentId}</p>
      </div>

      <button
        onClick={onLogout}
        className="w-full border border-red-200 text-red-500 font-semibold py-3 rounded-xl text-sm active:bg-red-50"
      >
        Sign Out
      </button>
    </div>
  );
}

// ── ROOT APP ───────────────────────────────────────────────────────────────
export default function App() {
  const [authStep, setAuthStep]         = useState<AuthStep | null>(null);
  const [authChecked, setAuthChecked]   = useState(false);
  const [pendingEmail, setPendingEmail] = useState("");

  const [studentId,   setStudentId]   = useState("");
  const [studentName, setStudentName] = useState("Student");
  const [totalXp,     setTotalXp]     = useState(0);
  const [streakDays,  setStreakDays]  = useState(0);

  const [screen, setScreen] = useState<Screen>("home");
  const [gps,  setGPS]      = useState<GPSRoute | null>(null);
  const [vark, setVARK]     = useState<VARKProfile | null>(null);

  // ── Persistent chat state (survives tab switches + page reloads) ─────────
  const [messages,   setMessages]   = useState<Message[]>(() => {
    try {
      const saved = localStorage.getItem("chat_messages");
      return saved ? JSON.parse(saved) : [];
    } catch { return []; }
  });
  const [bloomLevel, setBloomLevel] = useState(() => {
    try { return localStorage.getItem("bloom_level") ?? "Remember"; }
    catch { return "Remember"; }
  });
  const [hintCount,  setHintCount]  = useState(0);
  const [activityShown, setActivityShown] = useState(false);
  const [autoPrompt, setAutoPrompt] = useState<string | null>(null);

  // Sync messages + bloom to localStorage on every change
  useEffect(() => {
    try { localStorage.setItem("chat_messages", JSON.stringify(messages)); }
    catch { /* storage full or unavailable */ }
  }, [messages]);
  useEffect(() => {
    try { localStorage.setItem("bloom_level", bloomLevel); }
    catch { /* ignore */ }
  }, [bloomLevel]);

  // ── Check existing session on mount ─────────────────────────────────────
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        handleUserReady(session.user.id);
      } else {
        setAuthStep("email");
        setAuthChecked(true);
      }
    });

    const { data: listener } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_IN" && session?.user) {
        // Magic link clicked — user is now signed in
        handleUserReady(session.user.id);
      } else if (!session) {
        setAuthStep("email");
        setStudentId("");
        setStudentName("Student");
      }
    });
    return () => listener.subscription.unsubscribe();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleUserReady(uid: string) {
    setStudentId(uid);
    // Load profile
    const { data } = await supabase
      .from("student_profiles")
      .select("name, grade, total_xp, streak_days")
      .eq("student_id", uid)
      .single();

    if (data) {
      setStudentName(data.name);
      setTotalXp(data.total_xp ?? 0);
      setStreakDays(data.streak_days ?? 0);
      // Only show welcome message if no existing chat history in localStorage
      const savedMessages = (() => { try { const s = localStorage.getItem("chat_messages"); return s ? JSON.parse(s) : null; } catch { return null; } })();
      if (!savedMessages || savedMessages.length === 0) {
        setMessages([{ role: "assistant", content: `Welcome back, ${data.name}! 👋 I'm Gyaan, your AI tutor. What would you like to learn today?` }]);
      }
      setAuthStep(null);   // authenticated — show main app
      loadAppData(uid);
    } else {
      setAuthStep("setup"); // first time — need name/grade
    }
    setAuthChecked(true);
  }

  async function loadAppData(uid: string) {
    const [g, v] = await Promise.all([
      getGPSRoute(uid, TEST_CHAPTER_ID).catch(() => null),
      getVARKProfile(uid).catch(() => null),
    ]);
    setGPS(g);
    setVARK(v);
  }

  async function handleLogout() {
    await supabase.auth.signOut();
    setAuthStep("email");
    setStudentId("");
    setStudentName("Student");
    setGPS(null);
    setVARK(null);
    setScreen("home");
    setMessages([]);
    setBloomLevel("Remember");
    setHintCount(0);
    setActivityShown(false);
    setTotalXp(0);
    setStreakDays(0);
    try { localStorage.removeItem("chat_messages"); localStorage.removeItem("bloom_level"); } catch { /* ignore */ }
  }

  // ── Loading splash ───────────────────────────────────────────────────────
  if (!authChecked) {
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

  // ── Auth screens ─────────────────────────────────────────────────────────
  if (authStep === "email") {
    return (
      <AuthEmailScreen
        onSent={(email) => { setPendingEmail(email); setAuthStep("otp"); }}
      />
    );
  }
  if (authStep === "otp") {
    return (
      <AuthOTPScreen
        email={pendingEmail}
        onVerified={(user) => handleUserReady(user.id)}
        onBack={() => setAuthStep("email")}
      />
    );
  }
  if (authStep === "setup") {
    return (
      <ProfileSetupScreen
        userId={studentId}
        onComplete={(name, grade) => {
          setStudentName(name);
          setMessages([{ role: "assistant", content: `Hi ${name}! 👋 I'm Gyaan, your AI tutor. Ready to start your learning journey?` }]);
          void grade;      // grade stored in DB, used later for chapter filtering
          setAuthStep(null);
          loadAppData(studentId);
        }}
      />
    );
  }

  // ── Main app — web layout: sidebar + canvas ─────────────────────────────
  const handleNav = (s: Screen) => {
    if (screen === "chat" && (s === "home" || s === "map") && studentId) loadAppData(studentId);
    setScreen(s);
  };

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: "#03061a" }}>
      {/* Left sidebar */}
      <Sidebar
        screen={screen}
        setScreen={handleNav}
        studentName={studentName}
        vark={vark}
        totalXp={totalXp}
        streakDays={streakDays}
      />

      {/* Main content area */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", background: screen === "map" ? "#03061a" : "#f0f4f8" }}>
        {screen === "home" && (
          <div style={{ flex: 1, overflowY: "auto", padding: "28px 32px" }}>
            <div style={{ maxWidth: "820px", margin: "0 auto" }}>
              <HomeScreen gps={gps} studentName={studentName} totalXp={totalXp} streakDays={streakDays}
                onContinue={() => { setAutoPrompt(null); setScreen("chat"); }}
                onStartMode={(mode) => {
                  const sc = gps?.current?.name ?? "this concept";
                  setAutoPrompt(
                    mode === "quiz"     ? `Give me a 5-question quiz on ${sc}` :
                    mode === "explain"  ? `Explain ${sc} to me step by step` :
                                          `Help me prepare for my exam on ${sc} with practice questions and tips`
                  );
                  setScreen("chat");
                }}
                onMap={() => { if (studentId) loadAppData(studentId); setScreen("map"); }} />
            </div>
          </div>
        )}
        {screen === "map" && (
          <MapScreen studentId={studentId} onStart={(g) => { setGPS(g); setScreen("chat"); }} />
        )}
        {screen === "chat" && (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", maxWidth: "920px", width: "100%", margin: "0 auto" }}>
            <ChatScreen gps={gps} vark={vark} studentId={studentId} studentName={studentName}
              messages={messages} setMessages={setMessages}
              bloomLevel={bloomLevel} setBloomLevel={setBloomLevel}
              hintCount={hintCount} setHintCount={setHintCount}
              activityShown={activityShown} setActivityShown={setActivityShown}
              autoPrompt={autoPrompt} onAutoPromptSent={() => setAutoPrompt(null)}
              onXpEarned={(xp) => setTotalXp((prev) => prev + xp)} />
          </div>
        )}
        {screen === "progress" && (
          <div style={{ flex: 1, overflowY: "auto", padding: "28px 32px" }}>
            <div style={{ maxWidth: "920px", margin: "0 auto" }}>
              <ProgressScreen vark={vark} studentId={studentId} gps={gps} streakDays={streakDays} />
            </div>
          </div>
        )}
        {screen === "profile" && (
          <div style={{ flex: 1, overflowY: "auto", padding: "28px 32px" }}>
            <div style={{ maxWidth: "600px", margin: "0 auto" }}>
              <ProfileScreen vark={vark} studentName={studentName} studentId={studentId} onLogout={handleLogout} />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
