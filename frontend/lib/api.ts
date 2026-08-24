/**
 * LearnGPS API Client
 * Calls our FastAPI backend running on port 8000 (dev) or Railway (prod)
 */

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// Test student — replace with real auth on Day 10
export const TEST_STUDENT_ID = "00000000-0000-0000-0000-000000000000";
export const TEST_CHAPTER_ID = "ch_force_pressure";

// ── Types ──────────────────────────────────────────────────────────────────

export interface GPSRoute {
  student_id: string;
  chapter_id: string;
  current: { id: string; name: string } | null;
  route: { id: string; name: string }[];
  completed: { id: string; name: string }[];
  locked_count: number;
  progress_pct: number;
}

export interface ChatResponse {
  reply: string;
  xp_earned: number;
  bloom_advance: boolean;
  model_used: string;
  vark_updated?: string;
  hint_count: number;
  activity_shown: boolean;
  guardrail_rule?: string | null;
  distress_count?: number;
}

export interface PhotoResponse {
  reply: string;
  xp_earned: number;
  mode: string;
  model_used: string;
}

export interface VARKProfile {
  student_id: string;
  v_score: number;
  a_score: number;
  r_score: number;
  k_score: number;
  session_count: number;
  dominant: string;
}

export interface DikshaResource {
  title: string;
  description: string;
  content_type: string;
  url: string;
  identifier: string;
  source: string;
}

// ── API functions ──────────────────────────────────────────────────────────

export async function getGPSRoute(
  studentId: string,
  chapterId: string
): Promise<GPSRoute> {
  const res = await fetch(`${API}/gps/${studentId}/${chapterId}`);
  if (!res.ok) throw new Error("GPS fetch failed");
  return res.json();
}

export async function sendChat(params: {
  studentId: string;
  studentName: string;
  message: string;
  conversationHistory: { role: string; content: string }[];
  subconcept_id: string;
  subconcept_name: string;
  bloom_level: string;
  vark_style: string;
  hint_count?: number;
  mode?: string;
  activity_shown?: boolean;
  distress_count?: number;
}): Promise<ChatResponse> {
  const res = await fetch(`${API}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      student_id:           params.studentId,
      student_name:         params.studentName,
      message:              params.message,
      conversation_history: params.conversationHistory,
      subconcept_id:        params.subconcept_id,
      subconcept_name:      params.subconcept_name,
      chapter_name:         "Force & Pressure",
      bloom_level:          params.bloom_level,
      vark_style:           params.vark_style,
      hint_count:           params.hint_count ?? 0,
      mode:                 params.mode ?? "learning",
      activity_shown:       params.activity_shown ?? false,
      distress_count:       params.distress_count ?? 0,
    }),
  });
  if (!res.ok) throw new Error("Chat failed");
  return res.json();
}

export async function sendPhoto(
  imageFile: File,
  studentName: string,
  mode: "guide" | "check",
  studentAnswer: string,
  varkStyle: string
): Promise<PhotoResponse> {
  const form = new FormData();
  form.append("image", imageFile);
  form.append("student_name", studentName);
  form.append("mode", mode);
  form.append("student_answer", studentAnswer);
  form.append("vark_style", varkStyle);

  const res = await fetch(`${API}/photo`, { method: "POST", body: form });
  if (!res.ok) throw new Error("Photo upload failed");
  return res.json();
}

export async function getVARKProfile(studentId: string): Promise<VARKProfile> {
  const res = await fetch(`${API}/vark/${studentId}`);
  if (!res.ok) throw new Error("VARK fetch failed");
  return res.json();
}

export async function getDikshaContent(
  subconceptId: string
): Promise<{ resources: DikshaResource[]; count: number }> {
  const res = await fetch(`${API}/diksha/${subconceptId}`);
  if (!res.ok) throw new Error("DIKSHA fetch failed");
  return res.json();
}
