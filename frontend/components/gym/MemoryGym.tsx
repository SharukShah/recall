"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Brain, Hash, Calculator, Shapes, Users,
  ArrowLeft, Play, RotateCcw, Check, X, Volume2, Trophy,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  Per-exercise accent classes (theme-independent, work in dark mode) */
/* ------------------------------------------------------------------ */
type Accent = "primary" | "amber" | "emerald" | "rose";
const A: Record<Accent, { text: string; bg: string; soft: string; ring: string }> = {
  primary: { text: "text-primary", bg: "bg-primary", soft: "bg-primary/10", ring: "border-primary" },
  amber: { text: "text-amber-500", bg: "bg-amber-500", soft: "bg-amber-500/10", ring: "border-amber-500" },
  emerald: { text: "text-emerald-600 dark:text-emerald-500", bg: "bg-emerald-600", soft: "bg-emerald-600/10", ring: "border-emerald-600" },
  rose: { text: "text-rose-500", bg: "bg-rose-500", soft: "bg-rose-500/10", ring: "border-rose-500" },
};

/* ------------------------------- utils ---------------------------- */
const rint = (n: number) => Math.floor(Math.random() * n);
const pick = <T,>(a: T[]): T => a[rint(a.length)];
const shuffle = <T,>(a: T[]): T[] => {
  const x = [...a];
  for (let i = x.length - 1; i > 0; i--) { const j = rint(i + 1); [x[i], x[j]] = [x[j], x[i]]; }
  return x;
};
const seeded = (seed: number) => {
  let s = (seed * 2654435761) % 2147483647;
  return () => (s = (s * 48271) % 2147483647) / 2147483647;
};

/* --------------------------- shared UI ---------------------------- */
function Btn({ children, onClick, kind = "primary", accent = "primary", disabled, full }: {
  children: React.ReactNode; onClick?: () => void; kind?: "primary" | "ghost"; accent?: Accent; disabled?: boolean; full?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold transition active:scale-95 disabled:opacity-40 disabled:active:scale-100",
        kind === "primary" ? cn(A[accent].bg, "text-primary-foreground") : "border border-border text-foreground hover:bg-accent",
        full && "w-full",
      )}
    >
      {children}
    </button>
  );
}

function Stat({ label, value, accent }: { label: string; value: React.ReactNode; accent?: Accent }) {
  return (
    <div className="flex flex-col">
      <span className={cn("font-mono text-2xl font-semibold tabular-nums", accent ? A[accent].text : "text-foreground")}>{value}</span>
      <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</span>
    </div>
  );
}

function Stage({ children, ring }: { children: React.ReactNode; ring?: string }) {
  return (
    <div className={cn("relative flex aspect-square w-full max-w-sm items-center justify-center rounded-3xl border bg-card shadow-sm", ring || "border-border")}>
      {children}
    </div>
  );
}

function ExerciseShell({ title, subtitle, onBack, children }: { title: string; subtitle: string; onBack: () => void; children: React.ReactNode }) {
  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-5">
      <div className="flex items-center gap-3">
        <button onClick={onBack} className="rounded-full border border-border bg-card p-2 text-foreground transition active:scale-90 hover:bg-accent" aria-label="Back to gym">
          <ArrowLeft size={18} />
        </button>
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-foreground">{title}</h2>
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        </div>
      </div>
      {children}
    </div>
  );
}

function ResultCard({ headline, metric, metricLabel, lines = [], onAgain, onBack, accent = "primary" }: {
  headline: string; metric: React.ReactNode; metricLabel: string;
  lines?: { label: string; value: React.ReactNode; accent?: Accent }[];
  onAgain: () => void; onBack: () => void; accent?: Accent;
}) {
  return (
    <div className="flex flex-col items-center gap-5 rounded-3xl border border-border bg-card p-7 text-center">
      <div className={cn("flex h-12 w-12 items-center justify-center rounded-full", A[accent].soft, A[accent].text)}>
        <Trophy size={22} />
      </div>
      <div>
        <div className={cn("font-mono text-5xl font-bold tabular-nums", A[accent].text)}>{metric}</div>
        <div className="mt-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">{metricLabel}</div>
      </div>
      <p className="text-sm font-medium text-foreground">{headline}</p>
      {lines.length > 0 && (
        <div className="flex w-full justify-around border-t border-border pt-4">
          {lines.map((l, i) => <Stat key={i} {...l} />)}
        </div>
      )}
      <div className="flex w-full gap-3 pt-1">
        <Btn kind="ghost" onClick={onBack} full>Gym</Btn>
        <Btn accent={accent} onClick={onAgain} full><RotateCcw size={16} /> Train again</Btn>
      </div>
    </div>
  );
}

/* ============================ 1. DUAL N-BACK ====================== */
const NB_LETTERS = ["C", "H", "K", "L", "Q", "R", "S", "T"];
type Beat = { pos: number; letter: string };
function makeNBackSeq(n: number, beats: number): Beat[] {
  const seq: Beat[] = [];
  for (let i = 0; i < beats; i++) {
    let pos = rint(9), let_ = pick(NB_LETTERS);
    if (i >= n) {
      if (Math.random() < 0.3) pos = seq[i - n].pos;
      if (Math.random() < 0.3) let_ = seq[i - n].letter;
    }
    seq.push({ pos, letter: let_ });
  }
  return seq;
}
function DualNBack({ onBack }: { onBack: () => void }) {
  const [n, setN] = useState(2);
  const [phase, setPhase] = useState<"idle" | "run" | "done">("idle");
  const [step, setStep] = useState(-1);
  const [result, setResult] = useState<any>(null);
  const seqRef = useRef<Beat[]>([]);
  const respRef = useRef<{ pos?: boolean; let?: boolean }[]>([]);
  const stepRef = useRef(-1);
  const [, setTick] = useState(0);
  const beats = 20 + n;

  const speak = (ch: string) => {
    try {
      const u = new SpeechSynthesisUtterance(ch);
      u.rate = 0.9; u.volume = 1;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(u);
    } catch {}
  };

  const finish = useCallback(() => {
    const seq = seqRef.current, resp = respRef.current;
    let pHit = 0, pFa = 0, lHit = 0, lFa = 0, pT = 0, lT = 0;
    for (let i = 0; i < seq.length; i++) {
      const r = resp[i] || {};
      if (i >= n) {
        const pm = seq[i].pos === seq[i - n].pos;
        const lm = seq[i].letter === seq[i - n].letter;
        if (pm) { pT++; if (r.pos) pHit++; } else if (r.pos) pFa++;
        if (lm) { lT++; if (r.let) lHit++; } else if (r.let) lFa++;
      }
    }
    const raw = Math.round(((pHit + lHit) / Math.max(1, pT + lT)) * 100) - Math.round(((pFa + lFa) / Math.max(1, seq.length)) * 60);
    const accuracy = Math.max(0, Math.min(100, raw));
    let next = n;
    if (accuracy >= 80 && pFa + lFa <= 3) next = n + 1;
    else if (accuracy < 50) next = Math.max(1, n - 1);
    setResult({ accuracy, pHit, lHit, fa: pFa + lFa, next, prevN: n });
    setN(next);
    setPhase("done");
  }, [n]);

  const start = () => {
    seqRef.current = makeNBackSeq(n, beats);
    respRef.current = Array.from({ length: beats }, () => ({}));
    setResult(null); setPhase("run"); stepRef.current = -1; setStep(-1);
  };

  useEffect(() => {
    if (phase !== "run") return;
    const id = setInterval(() => {
      const next = stepRef.current + 1;
      if (next >= seqRef.current.length) { clearInterval(id); finish(); return; }
      stepRef.current = next; setStep(next);
      speak(seqRef.current[next].letter);
    }, 2600);
    return () => clearInterval(id);
  }, [phase, finish]);

  const flag = (kind: "pos" | "let") => {
    const i = stepRef.current;
    if (phase !== "run" || i < 0) return;
    respRef.current[i] = { ...respRef.current[i], [kind]: true };
    setTick((t) => t + 1);
  };

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === "a" || e.key === "A") flag("pos");
      if (e.key === "l" || e.key === "L") flag("let");
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [phase]);

  const cur = step >= 0 ? seqRef.current[step] : null;
  const curResp = step >= 0 ? respRef.current[step] : {};

  return (
    <ExerciseShell title="Dual N-Back" subtitle={`Match what came ${n} step${n > 1 ? "s" : ""} back`} onBack={onBack}>
      {phase === "done" ? (
        <ResultCard
          accent="primary" metric={`${result.accuracy}%`} metricLabel="accuracy"
          headline={result.accuracy >= 80 ? `Strong round — moving up to ${result.next}-back.` : `Keep going. Next round: ${result.next}-back.`}
          lines={[
            { label: "pos hit", value: result.pHit, accent: "emerald" },
            { label: "snd hit", value: result.lHit, accent: "emerald" },
            { label: "false", value: result.fa, accent: "rose" },
          ]}
          onAgain={start} onBack={onBack}
        />
      ) : (
        <div className="flex flex-col items-center gap-5">
          <Stage>
            {phase === "idle" ? (
              <div className="flex flex-col items-center gap-3 px-8 text-center">
                <Brain size={30} className="text-primary" />
                <p className="text-sm text-muted-foreground">
                  Watch the square and listen to the letter. Tap a panel when the current one matches the one from <b className="text-foreground">{n}</b> step{n > 1 ? "s" : ""} ago.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-2.5 p-5">
                {Array.from({ length: 9 }).map((_, i) => (
                  <div key={i} className={cn("h-20 w-20 rounded-2xl transition-all duration-200", cur && cur.pos === i ? "bg-primary scale-105" : "bg-primary/10")} />
                ))}
              </div>
            )}
            {phase === "run" && (
              <div className="absolute right-4 top-4 flex items-center gap-1.5 rounded-full bg-muted px-3 py-1.5 text-muted-foreground">
                <Volume2 size={14} /><span className="font-mono text-sm font-bold text-foreground">{cur?.letter}</span>
              </div>
            )}
            {phase === "run" && <div className="absolute left-4 top-4 font-mono text-xs text-muted-foreground">{step + 1}/{beats}</div>}
          </Stage>

          {phase === "idle" ? (
            <Btn onClick={start} full><Play size={16} /> Start {n}-back</Btn>
          ) : (
            <div className="grid w-full max-w-sm grid-cols-2 gap-3">
              <button onClick={() => flag("pos")} className={cn("rounded-2xl border py-4 text-sm font-semibold transition active:scale-95", curResp?.pos ? "border-primary bg-primary text-primary-foreground" : "border-border bg-card text-foreground")}>
                Position <span className={curResp?.pos ? "opacity-80" : "text-muted-foreground"}>(A)</span>
              </button>
              <button onClick={() => flag("let")} className={cn("rounded-2xl border py-4 text-sm font-semibold transition active:scale-95", curResp?.let ? "border-primary bg-primary text-primary-foreground" : "border-border bg-card text-foreground")}>
                Sound <span className={curResp?.let ? "opacity-80" : "text-muted-foreground"}>(L)</span>
              </button>
            </div>
          )}
        </div>
      )}
    </ExerciseShell>
  );
}

/* ============================ 2. SPAN DRILL ======================= */
function SpanDrill({ onBack }: { onBack: () => void }) {
  const [reverse, setReverse] = useState(false);
  const [phase, setPhase] = useState<"idle" | "show" | "recall" | "done">("idle");
  const [len, setLen] = useState(3);
  const [seq, setSeq] = useState<number[]>([]);
  const [showIdx, setShowIdx] = useState(-1);
  const [entry, setEntry] = useState<number[]>([]);
  const [lives, setLives] = useState(2);
  const [best, setBest] = useState(0);

  const begin = (l = 3) => {
    setSeq(Array.from({ length: l }, () => rint(10))); setLen(l); setEntry([]); setShowIdx(0); setPhase("show");
  };
  const startGame = () => { setLives(2); setBest(0); begin(3); };

  useEffect(() => {
    if (phase !== "show") return;
    if (showIdx >= seq.length) { const t = setTimeout(() => setPhase("recall"), 350); return () => clearTimeout(t); }
    const t = setTimeout(() => setShowIdx((i) => i + 1), 850);
    return () => clearTimeout(t);
  }, [phase, showIdx, seq.length]);

  const submit = () => {
    const target = reverse ? [...seq].reverse() : seq;
    const ok = entry.length === target.length && entry.every((d, i) => d === target[i]);
    if (ok) { setBest(len); begin(len + 1); }
    else if (lives > 1) { setLives((v) => v - 1); begin(len); }
    else setPhase("done");
  };
  const press = (d: number) => { if (entry.length < len) setEntry((e) => [...e, d]); };

  return (
    <ExerciseShell title="Span Drill" subtitle={reverse ? "Repeat the digits in reverse" : "Repeat the digits in order"} onBack={onBack}>
      {phase === "done" ? (
        <ResultCard accent="amber" metric={best} metricLabel="digit span"
          headline={`Your ${reverse ? "reverse " : ""}span this session was ${best} digits.`}
          onAgain={startGame} onBack={onBack} />
      ) : (
        <div className="flex flex-col items-center gap-5">
          <Stage>
            {phase === "idle" && (
              <div className="flex flex-col items-center gap-4 px-8 text-center">
                <Hash size={30} className="text-amber-500" />
                <p className="text-sm text-muted-foreground">Memorize the digit sequence, then key it back. It grows by one each time you nail it.</p>
                <button onClick={() => setReverse((r) => !r)} className={cn("rounded-full px-3 py-1.5 text-xs font-semibold", reverse ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground")}>
                  {reverse ? "Reverse mode: on" : "Reverse mode: off"}
                </button>
              </div>
            )}
            {phase === "show" && <div className="font-mono text-7xl font-bold tabular-nums text-foreground">{showIdx < seq.length ? seq[showIdx] : ""}</div>}
            {phase === "recall" && (
              <div className="flex flex-wrap items-center justify-center gap-2 px-6">
                {Array.from({ length: len }).map((_, i) => (
                  <div key={i} className={cn("flex h-12 w-9 items-center justify-center rounded-lg border bg-muted font-mono text-2xl font-bold tabular-nums text-foreground", entry[i] != null ? "border-primary" : "border-border")}>
                    {entry[i] != null ? entry[i] : ""}
                  </div>
                ))}
              </div>
            )}
            <div className="absolute left-4 top-4 flex gap-1">
              {Array.from({ length: 2 }).map((_, i) => <div key={i} className={cn("h-2 w-2 rounded-full", i < lives ? "bg-amber-500" : "bg-border")} />)}
            </div>
          </Stage>

          {phase === "idle" && <Btn accent="amber" onClick={startGame} full><Play size={16} /> Start</Btn>}
          {phase === "recall" && (
            <div className="w-full max-w-xs">
              <div className="grid grid-cols-3 gap-2">
                {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((d) => (
                  <button key={d} onClick={() => press(d)} className="rounded-xl border border-border bg-card py-3 font-mono text-xl font-semibold text-foreground transition active:scale-90">{d}</button>
                ))}
                <button onClick={() => setEntry((e) => e.slice(0, -1))} className="rounded-xl bg-muted py-3 text-sm font-semibold text-muted-foreground">⌫</button>
                <button onClick={() => press(0)} className="rounded-xl border border-border bg-card py-3 font-mono text-xl font-semibold text-foreground transition active:scale-90">0</button>
                <button onClick={submit} disabled={entry.length !== len} className="rounded-xl bg-primary py-3 text-primary-foreground transition active:scale-90 disabled:opacity-40"><Check size={18} className="mx-auto" /></button>
              </div>
            </div>
          )}
        </div>
      )}
    </ExerciseShell>
  );
}

/* ============================ 3. MATH LADDER ===================== */
function genMath(level: number) {
  const ops = level < 2 ? ["+", "-"] : level < 4 ? ["+", "-", "×"] : ["+", "-", "×", "×"];
  const op = pick(ops);
  let a: number, b: number;
  if (op === "×") { a = rint(level < 4 ? 9 : 13) + 2; b = rint(level < 4 ? 9 : 13) + 2; }
  else { const max = 10 + level * 12; a = rint(max) + 1; b = rint(max) + 1; if (op === "-" && b > a) [a, b] = [b, a]; }
  const ans = op === "+" ? a + b : op === "-" ? a - b : a * b;
  return { text: `${a} ${op} ${b}`, ans };
}
function MathLadder({ onBack }: { onBack: () => void }) {
  const [phase, setPhase] = useState<"idle" | "run" | "done">("idle");
  const [time, setTime] = useState(60);
  const [q, setQ] = useState<{ text: string; ans: number } | null>(null);
  const [entry, setEntry] = useState("");
  const [score, setScore] = useState(0);
  const [streak, setStreak] = useState(0);
  const [best, setBest] = useState(0);
  const [flash, setFlash] = useState<"ok" | "no" | null>(null);
  const level = Math.min(6, Math.floor(streak / 3) + 1);

  const start = () => { setScore(0); setStreak(0); setBest(0); setTime(60); setEntry(""); setQ(genMath(1)); setPhase("run"); };

  useEffect(() => {
    if (phase !== "run") return;
    if (time <= 0) { setPhase("done"); return; }
    const t = setTimeout(() => setTime((v) => v - 1), 1000);
    return () => clearTimeout(t);
  }, [phase, time]);

  const submit = () => {
    if (entry === "" || !q) return;
    if (parseInt(entry, 10) === q.ans) {
      setScore((s) => s + 1);
      setStreak((s) => { const ns = s + 1; setBest((b) => Math.max(b, ns)); return ns; });
      setFlash("ok");
    } else { setStreak(0); setFlash("no"); }
    setTimeout(() => setFlash(null), 220);
    setEntry(""); setQ(genMath(level));
  };
  const press = (d: string) => setEntry((e) => (e + d).slice(0, 5));

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (phase !== "run") return;
      if (/[0-9]/.test(e.key)) press(e.key);
      if (e.key === "-") setEntry((x) => (x.startsWith("-") ? x : "-" + x));
      if (e.key === "Backspace") setEntry((x) => x.slice(0, -1));
      if (e.key === "Enter") submit();
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  });

  return (
    <ExerciseShell title="Math Ladder" subtitle="Solve as many as you can in 60s — speed scales difficulty" onBack={onBack}>
      {phase === "done" ? (
        <ResultCard accent="emerald" metric={score} metricLabel="solved"
          headline={`Best streak: ${best}. You reached level ${Math.min(6, Math.floor(best / 3) + 1)}.`}
          lines={[{ label: "solved", value: score, accent: "emerald" }, { label: "best streak", value: best, accent: "amber" }]}
          onAgain={start} onBack={onBack} />
      ) : (
        <div className="flex flex-col items-center gap-5">
          <Stage ring={flash === "ok" ? "border-emerald-600" : flash === "no" ? "border-rose-500" : "border-border"}>
            {phase === "idle" ? (
              <div className="flex flex-col items-center gap-3 px-8 text-center">
                <Calculator size={30} className="text-emerald-600 dark:text-emerald-500" />
                <p className="text-sm text-muted-foreground">Mental arithmetic against the clock. Each streak of 3 bumps the difficulty.</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <div className="font-mono text-4xl font-bold tabular-nums text-foreground">{q?.text}</div>
                <div className={cn("font-mono text-3xl font-bold tabular-nums", entry ? "text-primary" : "text-muted-foreground/40")}>{entry || "·"}</div>
              </div>
            )}
            {phase === "run" && (
              <>
                <div className={cn("absolute left-4 top-4 font-mono text-sm font-bold tabular-nums", time <= 10 ? "text-rose-500" : "text-muted-foreground")}>{time}s</div>
                <div className="absolute right-4 top-4 text-xs font-semibold text-muted-foreground">lvl {level} · {score}</div>
              </>
            )}
          </Stage>
          {phase === "idle" ? (
            <Btn accent="emerald" onClick={start} full><Play size={16} /> Start</Btn>
          ) : (
            <div className="grid w-full max-w-xs grid-cols-3 gap-2">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((d) => (
                <button key={d} onClick={() => press(String(d))} className="rounded-xl border border-border bg-card py-3 font-mono text-xl font-semibold text-foreground transition active:scale-90">{d}</button>
              ))}
              <button onClick={() => setEntry((x) => x.slice(0, -1))} className="rounded-xl bg-muted py-3 text-sm font-semibold text-muted-foreground">⌫</button>
              <button onClick={() => press("0")} className="rounded-xl border border-border bg-card py-3 font-mono text-xl font-semibold text-foreground transition active:scale-90">0</button>
              <button onClick={submit} className="rounded-xl bg-emerald-600 py-3 text-white transition active:scale-90"><Check size={18} className="mx-auto" /></button>
            </div>
          )}
        </div>
      )}
    </ExerciseShell>
  );
}

/* ========================== 4. PATTERN PUZZLE ==================== */
function genPattern(level: number) {
  const kind = pick(level < 2 ? ["arith", "arith", "geo"] : ["arith", "geo", "fib", "alt", "square"]);
  let terms: number[] = [], ans = 0;
  const start = rint(6) + 1;
  if (kind === "arith") { const d = rint(5) + 2; terms = [0, 1, 2, 3].map((i) => start + d * i); ans = start + d * 4; }
  else if (kind === "geo") { const r = rint(2) + 2; terms = [0, 1, 2, 3].map((i) => start * r ** i); ans = start * r ** 4; }
  else if (kind === "fib") { let a = start, b = start + rint(4) + 1; terms = [a, b]; for (let i = 0; i < 2; i++) { const c = a + b; terms.push(c); a = b; b = c; } ans = a + b; }
  else if (kind === "alt") { const d1 = rint(4) + 2, d2 = rint(4) + 3; terms = [start]; for (let i = 0; i < 3; i++) terms.push(terms[i] + (i % 2 ? d2 : d1)); ans = terms[3] + (3 % 2 ? d2 : d1); }
  else { terms = [1, 2, 3, 4].map((i) => i * i + start); ans = 25 + start; }
  const set = new Set<number>([ans]);
  const jitter = () => ans + (rint(2) ? 1 : -1) * (rint(5) + 1);
  let guard = 0;
  while (set.size < 4 && guard++ < 50) { const v = jitter(); if (v !== ans) set.add(v); }
  while (set.size < 4) set.add(ans + set.size * 3);
  return { terms, ans, opts: shuffle(Array.from(set)) };
}
function PatternPuzzle({ onBack }: { onBack: () => void }) {
  const TOTAL = 10;
  const [phase, setPhase] = useState<"idle" | "run" | "done">("idle");
  const [i, setI] = useState(0);
  const [score, setScore] = useState(0);
  const [q, setQ] = useState<ReturnType<typeof genPattern> | null>(null);
  const [picked, setPicked] = useState<number | null>(null);

  const next = (idx: number) => { setQ(genPattern(Math.floor(idx / 3))); setPicked(null); };
  const start = () => { setScore(0); setI(0); next(0); setPhase("run"); };
  const choose = (v: number) => {
    if (picked != null || !q) return;
    setPicked(v);
    if (v === q.ans) setScore((s) => s + 1);
    setTimeout(() => {
      if (i + 1 >= TOTAL) setPhase("done");
      else { setI((x) => x + 1); next(i + 1); }
    }, 650);
  };

  return (
    <ExerciseShell title="Pattern Puzzles" subtitle="Find the rule, predict the next number" onBack={onBack}>
      {phase === "done" ? (
        <ResultCard accent="primary" metric={`${score}/${TOTAL}`} metricLabel="correct"
          headline={score >= 8 ? "Sharp pattern recognition." : score >= 5 ? "Solid — keep training." : "These get easier with reps."}
          onAgain={start} onBack={onBack} />
      ) : phase === "idle" ? (
        <div className="flex flex-col items-center gap-5">
          <Stage><div className="flex flex-col items-center gap-3 px-8 text-center"><Shapes size={30} className="text-primary" /><p className="text-sm text-muted-foreground">Each sequence follows a hidden rule. Pick the number that comes next. 10 puzzles, rising difficulty.</p></div></Stage>
          <Btn onClick={start} full><Play size={16} /> Start</Btn>
        </div>
      ) : q ? (
        <div className="flex flex-col items-center gap-5">
          <Stage>
            <div className="flex flex-col items-center gap-4">
              <div className="absolute left-4 top-4 font-mono text-xs text-muted-foreground">{i + 1}/{TOTAL}</div>
              <div className="flex flex-wrap items-center justify-center gap-3 px-6 font-mono text-3xl font-bold tabular-nums text-foreground">
                {q.terms.map((t, k) => <span key={k}>{t}</span>)}
                <span className="text-primary">?</span>
              </div>
            </div>
          </Stage>
          <div className="grid w-full max-w-sm grid-cols-2 gap-3">
            {q.opts.map((o, k) => {
              const isAns = o === q.ans, isPicked = picked === o;
              const cls = picked == null ? "border-border bg-card text-foreground"
                : isAns ? "border-emerald-600 bg-emerald-600/10 text-emerald-600 dark:text-emerald-500"
                : isPicked ? "border-rose-500 bg-rose-500/10 text-rose-500"
                : "border-border bg-card text-muted-foreground";
              return <button key={k} onClick={() => choose(o)} className={cn("rounded-2xl border py-4 font-mono text-xl font-semibold tabular-nums transition active:scale-95", cls)}>{o}</button>;
            })}
          </div>
        </div>
      ) : null}
    </ExerciseShell>
  );
}

/* ========================== 5. NAME–FACE ======================== */
const NAMES = ["Aisha", "Marco", "Priya", "Diego", "Lena", "Omar", "Yuki", "Nadia", "Kofi", "Ines", "Raj", "Mei", "Tariq", "Sofia", "Liam", "Zara", "Hugo", "Anaya", "Noah", "Freya", "Kian", "Maya", "Theo", "Esme"];
function Avatar({ seed, size = 84 }: { seed: number; size?: number }) {
  const r = seeded(seed + 1);
  const skin = ["#F2C9A0", "#E0A878", "#C68642", "#8D5524", "#FFD9B3", "#A86B3C"][Math.floor(r() * 6)];
  const hair = ["#2B2B2B", "#5A3210", "#9A6A2E", "#B0413E", "#1F2A44", "#6E6E6E"][Math.floor(r() * 6)];
  const bg = ["#EBE7FC", "#E1F4ED", "#FBE6EA", "#FDF1DC", "#E4EEFB"][Math.floor(r() * 5)];
  const style = Math.floor(r() * 4);
  const glasses = r() > 0.65;
  return (
    <svg viewBox="0 0 100 100" width={size} height={size} style={{ borderRadius: 18, background: bg }}>
      <circle cx="50" cy="44" r="26" fill={skin} />
      {style === 0 && <path d="M22 44 Q24 16 50 16 Q76 16 78 44 Q70 30 50 30 Q30 30 22 44Z" fill={hair} />}
      {style === 1 && <path d="M22 46 Q22 14 50 14 Q78 14 78 46 L72 46 Q72 24 50 24 Q28 24 28 46Z" fill={hair} />}
      {style === 2 && <rect x="24" y="14" width="52" height="20" rx="10" fill={hair} />}
      {style === 3 && <path d="M24 40 Q26 18 50 18 Q74 18 76 40 Q66 26 50 26 Q34 26 24 40Z" fill={hair} />}
      <circle cx="40" cy="44" r="3" fill="#2A2433" />
      <circle cx="60" cy="44" r="3" fill="#2A2433" />
      {glasses && <g stroke="#3A3450" strokeWidth="2" fill="none"><circle cx="40" cy="44" r="7" /><circle cx="60" cy="44" r="7" /><line x1="47" y1="44" x2="53" y2="44" /></g>}
      <path d="M42 56 Q50 62 58 56" stroke="#7A4A3A" strokeWidth="2.5" fill="none" strokeLinecap="round" />
      <path d="M20 100 Q20 76 50 76 Q80 76 80 100Z" fill={hair} opacity="0.18" />
    </svg>
  );
}
function NameFace({ onBack }: { onBack: () => void }) {
  const COUNT = 5;
  const [phase, setPhase] = useState<"idle" | "study" | "test" | "done">("idle");
  const [people, setPeople] = useState<{ name: string; seed: number }[]>([]);
  const [studyT, setStudyT] = useState(0);
  const [order, setOrder] = useState<number[]>([]);
  const [qi, setQi] = useState(0);
  const [opts, setOpts] = useState<string[]>([]);
  const [picked, setPicked] = useState<string | null>(null);
  const [score, setScore] = useState(0);

  const buildQ = (idx: number, ppl = people, ord = order) => {
    const correct = ppl[ord[idx]].name;
    const distract = shuffle(NAMES.filter((n) => !ppl.some((p) => p.name === n))).slice(0, 3);
    setOpts(shuffle([correct, ...distract])); setPicked(null);
  };
  const start = () => {
    const ns = shuffle(NAMES).slice(0, COUNT);
    const ppl = ns.map((name, i) => ({ name, seed: rint(99999) + i * 7 }));
    const ord = shuffle(ppl.map((_, i) => i));
    setPeople(ppl); setOrder(ord); setScore(0); setQi(0); setPicked(null);
    setStudyT(COUNT * 3); setPhase("study");
  };
  useEffect(() => {
    if (phase !== "study") return;
    if (studyT <= 0) { buildQ(0); setPhase("test"); return; }
    const t = setTimeout(() => setStudyT((v) => v - 1), 1000);
    return () => clearTimeout(t);
  }, [phase, studyT]);

  const choose = (name: string) => {
    if (picked) return;
    setPicked(name);
    if (name === people[order[qi]].name) setScore((s) => s + 1);
    setTimeout(() => {
      if (qi + 1 >= order.length) setPhase("done");
      else { const nx = qi + 1; setQi(nx); buildQ(nx); }
    }, 700);
  };

  return (
    <ExerciseShell title="Name–Face" subtitle="Study the people, then recall their names" onBack={onBack}>
      {phase === "done" ? (
        <ResultCard accent="rose" metric={`${score}/${COUNT}`} metricLabel="recalled"
          headline={score === COUNT ? "Perfect recall." : "Linking a vivid detail to each name helps."}
          onAgain={start} onBack={onBack} />
      ) : phase === "idle" ? (
        <div className="flex flex-col items-center gap-5">
          <Stage><div className="flex flex-col items-center gap-3 px-8 text-center"><Users size={30} className="text-rose-500" /><p className="text-sm text-muted-foreground">Memorize {COUNT} faces with their names, then match each face to the right name.</p></div></Stage>
          <Btn accent="rose" onClick={start} full><Play size={16} /> Start</Btn>
        </div>
      ) : phase === "study" ? (
        <div className="flex flex-col items-center gap-4">
          <div className="font-mono text-sm font-bold text-muted-foreground">Memorize · {studyT}s</div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            {people.map((p, i) => (
              <div key={i} className="flex flex-col items-center gap-2 rounded-2xl border border-border bg-card p-3">
                <Avatar seed={p.seed} />
                <span className="text-sm font-semibold text-foreground">{p.name}</span>
              </div>
            ))}
          </div>
          <Btn kind="ghost" onClick={() => setStudyT(0)}>I&apos;m ready</Btn>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-5">
          <Stage>
            <div className="flex flex-col items-center gap-3">
              <div className="absolute left-4 top-4 font-mono text-xs text-muted-foreground">{qi + 1}/{COUNT}</div>
              <Avatar seed={people[order[qi]].seed} size={120} />
              <span className="text-sm text-muted-foreground">Who is this?</span>
            </div>
          </Stage>
          <div className="grid w-full max-w-sm grid-cols-2 gap-3">
            {opts.map((name, k) => {
              const correct = people[order[qi]].name;
              const isAns = name === correct, isPick = picked === name;
              const cls = !picked ? "border-border bg-card text-foreground"
                : isAns ? "border-emerald-600 bg-emerald-600/10 text-emerald-600 dark:text-emerald-500"
                : isPick ? "border-rose-500 bg-rose-500/10 text-rose-500"
                : "border-border bg-card text-muted-foreground";
              return (
                <button key={k} onClick={() => choose(name)} className={cn("flex items-center justify-center gap-1.5 rounded-2xl border py-4 text-sm font-semibold transition active:scale-95", cls)}>
                  {picked && isAns && <Check size={15} />}{picked && isPick && !isAns && <X size={15} />}{name}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </ExerciseShell>
  );
}

/* ============================== HUB ============================== */
const EXERCISES: { key: string; name: string; tag: string; icon: any; accent: Accent; desc: string }[] = [
  { key: "nback", name: "Dual N-Back", tag: "Working memory", icon: Brain, accent: "primary", desc: "Track position and sound together. The benchmark working-memory drill." },
  { key: "span", name: "Span Drill", tag: "Memory span", icon: Hash, accent: "amber", desc: "Hold a growing string of digits — forward or reversed." },
  { key: "math", name: "Math Ladder", tag: "Processing speed", icon: Calculator, accent: "emerald", desc: "60 seconds of arithmetic that speeds up as you streak." },
  { key: "pattern", name: "Pattern Puzzles", tag: "Fluid reasoning", icon: Shapes, accent: "primary", desc: "Spot the rule and predict what comes next." },
  { key: "face", name: "Name–Face", tag: "Associative recall", icon: Users, accent: "rose", desc: "The everyday one: match faces to names after a delay." },
];

export function MemoryGym() {
  const [view, setView] = useState<string>("hub");
  const back = () => setView("hub");

  if (view === "nback") return <DualNBack onBack={back} />;
  if (view === "span") return <SpanDrill onBack={back} />;
  if (view === "math") return <MathLadder onBack={back} />;
  if (view === "pattern") return <PatternPuzzle onBack={back} />;
  if (view === "face") return <NameFace onBack={back} />;

  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-4">
      <p className="text-sm text-muted-foreground">Five drills for working memory, speed, and recall. A few minutes daily; difficulty adapts to you in N-Back, Span, and Math.</p>
      <div className="flex flex-col gap-3">
        {EXERCISES.map((e, idx) => {
          const Icon = e.icon;
          return (
            <button key={e.key} onClick={() => setView(e.key)} className="group flex items-center gap-4 rounded-2xl border border-border bg-card p-4 text-left transition active:scale-[0.98] hover:bg-accent">
              <span className={cn("flex h-12 w-12 shrink-0 items-center justify-center rounded-xl", A[e.accent].soft, A[e.accent].text)}>
                <Icon size={22} />
              </span>
              <span className="flex-1">
                <span className="flex items-center gap-2">
                  <span className="text-base font-semibold text-foreground">{e.name}</span>
                  <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{e.tag}</span>
                </span>
                <span className="mt-0.5 block text-xs leading-snug text-muted-foreground">{e.desc}</span>
              </span>
              <span className="font-mono text-xs text-muted-foreground/40">0{idx + 1}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
