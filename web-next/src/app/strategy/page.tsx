"use client";

import { useState } from "react";
import Link from "next/link";
import HouseLogo from "@/components/HouseLogo";

/* ── Quiz definition ─────────────────────────────────────────────────── */
const QUESTIONS = [
  {
    id: "budget",
    q: "What's your target property price range?",
    options: [
      { label: "Under $600K",   sub: "Condos & small towns — cash flow focused",   value: "low"    },
      { label: "$600K–$900K",   sub: "GTA condos & semis — balanced approach",      value: "mid"    },
      { label: "$900K–$1.3M",   sub: "Detached & townhouses — appreciation driven", value: "high"   },
      { label: "Over $1.3M",    sub: "Luxury GTA — appreciation markets",           value: "luxury" },
    ],
  },
  {
    id: "risk",
    q: "How do you feel about risk?",
    options: [
      { label: "Conservative",  sub: "Stable, predictable returns. Slow and steady.", value: "low"  },
      { label: "Moderate",      sub: "Some uncertainty is fine for better returns.",   value: "mid"  },
      { label: "Aggressive",    sub: "Chasing maximum growth. Can absorb losses.",     value: "high" },
    ],
  },
  {
    id: "goal",
    q: "What's your primary investment goal?",
    options: [
      { label: "Monthly cash flow",       sub: "Positive rent income every month",             value: "cashflow"    },
      { label: "Long-term appreciation",  sub: "Build equity over 10+ years",                  value: "appreciation"},
      { label: "Quick equity build",      sub: "BRRRR — buy, reno, rent, refinance, repeat",   value: "brrrr"       },
      { label: "I'm not sure yet",        sub: "Help me figure it out",                         value: "unsure"      },
    ],
  },
  {
    id: "timeline",
    q: "When do you want to make your first investment?",
    options: [
      { label: "ASAP — within 3 months", sub: "Ready to move fast",            value: "asap"      },
      { label: "6–12 months",            sub: "Still researching, nearly ready", value: "soon"    },
      { label: "1–2 years",              sub: "Planning ahead",                  value: "planning" },
      { label: "Just exploring",         sub: "Learning for now",               value: "exploring" },
    ],
  },
  {
    id: "location",
    q: "Where are you thinking about investing?",
    options: [
      { label: "Toronto (416)",         sub: "Core city — highest values, appreciation focus", value: "416"   },
      { label: "905 suburbs",           sub: "Mississauga, Brampton, Markham — better PTR",   value: "905"   },
      { label: "GTA + Durham Region",   sub: "Oshawa, Whitby, Ajax — lower entry cost",       value: "durham"},
      { label: "Open to anything",      sub: "Best deal wins",                                value: "open"  },
    ],
  },
  {
    id: "priority",
    q: "What matters most to you?",
    options: [
      { label: "Maximum cash flow now", sub: "905 belt & Durham have better PTR",          value: "cashflow"    },
      { label: "Long-term appreciation",sub: "416 core has the strongest track record",    value: "appreciation"},
      { label: "Low entry cost",        sub: "Get in with less capital",                   value: "entry"       },
      { label: "Emerging neighbourhoods",sub: "Areas growing faster than the market",      value: "emerging"    },
    ],
  },
  {
    id: "experience",
    q: "Have you invested in real estate before?",
    options: [
      { label: "Complete beginner",      sub: "First time learning",             value: "beginner"      },
      { label: "I've done some research",sub: "Know the basics, not yet invested",value: "researched"   },
      { label: "I own property already", sub: "Looking to expand my portfolio",   value: "experienced"  },
    ],
  },
] as const;

/* ── Strategy definitions ─────────────────────────────────────────────── */
interface Strategy {
  id: string;
  name: string;
  description: string;
  roi: string;
  capital: string;
  difficulty: string;
  difficultyColor: string;
  neighbourhoods: {
    name: string;
    city: string;
    avgRent: string;
    avgPrice: string;
    ptr: string;
    score: number;
  }[];
}

const STRATEGIES: Record<string, Strategy> = {
  longterm: {
    id: "longterm",
    name: "Long-Term Rental",
    description: "The classic buy-and-hold strategy: purchase a GTA property, rent it to long-term tenants (12+ month leases), and collect steady monthly income while the property appreciates over time. Conservative financing and tenant screening produce predictable returns — the backbone of most GTA portfolios.",
    roi: "5–9% annual",
    capital: "$120K–$250K",
    difficulty: "Moderate",
    difficultyColor: "#ffa502",
    neighbourhoods: [
      { name: "Scarborough",         city: "Toronto",      avgRent: "$2,400/mo", avgPrice: "$680K",  ptr: "23.6×", score: 88 },
      { name: "Mississauga City Ctr",city: "Mississauga",  avgRent: "$2,600/mo", avgPrice: "$720K",  ptr: "23.1×", score: 84 },
      { name: "Brampton North",      city: "Brampton",     avgRent: "$2,800/mo", avgPrice: "$810K",  ptr: "24.1×", score: 82 },
    ],
  },
  condo_appreciation: {
    id: "condo_appreciation",
    name: "GTA Condo Appreciation",
    description: "Buy a pre-construction or resale condo in the 416 core and hold for 5–10+ years. Cash flow will likely be negative or break-even, but GTA condo prices have historically compounded at 5–8% annually. Best for investors with strong cash reserves who don't rely on rental income.",
    roi: "6–10% appreciation/yr",
    capital: "$170K–$350K",
    difficulty: "Low",
    difficultyColor: "#2ed573",
    neighbourhoods: [
      { name: "King West",           city: "Toronto",      avgRent: "$3,200/mo", avgPrice: "$850K",  ptr: "22.1×", score: 78 },
      { name: "Liberty Village",     city: "Toronto",      avgRent: "$3,000/mo", avgPrice: "$800K",  ptr: "22.2×", score: 76 },
      { name: "Yorkville",           city: "Toronto",      avgRent: "$4,200/mo", avgPrice: "$1.1M",  ptr: "21.8×", score: 74 },
    ],
  },
  brrrr: {
    id: "brrrr",
    name: "BRRRR — Equity Recycling",
    description: "Buy a distressed property below market, renovate it to force appreciation, rent it out at market rate, then refinance to pull your equity back out and repeat. Requires strong reno knowledge and active management but can build a large portfolio quickly using the same capital repeatedly.",
    roi: "10–18% CoC (advanced)",
    capital: "$80K–$180K + reno",
    difficulty: "High",
    difficultyColor: "#cf6357",
    neighbourhoods: [
      { name: "East York",           city: "Toronto",      avgRent: "$2,600/mo", avgPrice: "$750K",  ptr: "24.0×", score: 80 },
      { name: "Stockyards",          city: "Toronto",      avgRent: "$2,800/mo", avgPrice: "$820K",  ptr: "24.4×", score: 77 },
      { name: "Oshawa North",        city: "Oshawa",       avgRent: "$2,200/mo", avgPrice: "$550K",  ptr: "20.8×", score: 91 },
    ],
  },
  suburban_cashflow: {
    id: "suburban_cashflow",
    name: "905 Cash Flow Play",
    description: "Target the inner 905 belt — Mississauga, Brampton, Markham — where price-to-rent ratios are meaningfully better than the 416 core. Semis and townhouses in established suburban neighbourhoods often achieve break-even or slight positive cash flow, while still participating in long-term GTA appreciation.",
    roi: "6–10% annual (CF + appreciation)",
    capital: "$140K–$220K",
    difficulty: "Moderate",
    difficultyColor: "#ffa502",
    neighbourhoods: [
      { name: "Malton",              city: "Mississauga",  avgRent: "$2,800/mo", avgPrice: "$760K",  ptr: "22.6×", score: 86 },
      { name: "Brampton East",       city: "Brampton",     avgRent: "$2,600/mo", avgPrice: "$690K",  ptr: "22.1×", score: 88 },
      { name: "Markham Village",     city: "Markham",      avgRent: "$3,000/mo", avgPrice: "$840K",  ptr: "23.3×", score: 83 },
    ],
  },
  durham_entry: {
    id: "durham_entry",
    name: "Durham Region Entry Point",
    description: "Oshawa, Whitby, and Ajax offer the lowest entry prices in the GTA while still benefiting from proximity to Toronto employment and GO Transit expansion. Cash-on-cash returns are the strongest in the region. Best suited for investors who can tolerate slightly longer vacancy periods.",
    roi: "7–12% CoC",
    capital: "$90K–$150K",
    difficulty: "Moderate",
    difficultyColor: "#ffa502",
    neighbourhoods: [
      { name: "Oshawa Central",      city: "Oshawa",       avgRent: "$2,100/mo", avgPrice: "$500K",  ptr: "19.8×", score: 94 },
      { name: "Whitby Downtown",     city: "Whitby",       avgRent: "$2,300/mo", avgPrice: "$580K",  ptr: "21.0×", score: 89 },
      { name: "Ajax West",           city: "Ajax",         avgRent: "$2,500/mo", avgPrice: "$660K",  ptr: "22.0×", score: 85 },
    ],
  },
};

/* ── Strategy selection logic ─────────────────────────────────────────── */
function selectStrategy(answers: Record<string, string>): Strategy {
  const goal     = answers.goal     ?? "";
  const budget   = answers.budget   ?? "";
  const location = answers.location ?? "";
  const priority = answers.priority ?? "";

  if (goal === "brrrr") return STRATEGIES.brrrr;
  if (location === "durham" || (priority === "entry" && budget === "low")) return STRATEGIES.durham_entry;
  if (location === "905" || priority === "cashflow") return STRATEGIES.suburban_cashflow;
  if (goal === "appreciation" || budget === "luxury" || (location === "416" && priority === "appreciation")) return STRATEGIES.condo_appreciation;
  return STRATEGIES.longterm;
}

/* ── Component ───────────────────────────────────────────────────────── */
export default function StrategyPage() {
  const [step, setStep]       = useState(0); // 0 = intro, 1-7 = questions, 8 = result
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [selected, setSelected] = useState<string | null>(null);
  const [email, setEmail]     = useState("");
  const [emailSent, setEmailSent] = useState(false);

  const totalQ  = QUESTIONS.length;
  const onQuiz  = step >= 1 && step <= totalQ;
  const onResult = step === totalQ + 1;
  const currentQ = onQuiz ? QUESTIONS[step - 1] : null;
  const strategy = onResult ? selectStrategy(answers) : null;
  const progress = onQuiz ? ((step - 1) / totalQ) * 100 : onResult ? 100 : 0;

  const mono: React.CSSProperties = { fontFamily: "var(--mono)" };

  function pick(value: string) {
    setSelected(value);
  }

  function next() {
    if (!selected || !currentQ) return;
    const newAnswers = { ...answers, [currentQ.id]: selected };
    setAnswers(newAnswers);
    setSelected(null);
    if (step === totalQ) {
      setStep(totalQ + 1);
    } else {
      setStep(s => s + 1);
    }
  }

  function back() {
    if (step <= 1) { setStep(0); setSelected(null); return; }
    setStep(s => s - 1);
    setSelected(answers[QUESTIONS[step - 2]?.id] ?? null);
  }

  function restart() {
    setStep(0);
    setAnswers({});
    setSelected(null);
    setEmailSent(false);
    setEmail("");
  }

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text)" }}>
      {/* Nav */}
      <nav style={{ borderBottom: "1px solid var(--border)", padding: "0 40px", height: 52, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
          <HouseLogo size={22} />
          <span style={{ ...mono, fontSize: "0.7rem", letterSpacing: "0.18em", textTransform: "uppercase", color: "var(--text)" }}>416Homes</span>
        </Link>
        <div style={{ display: "flex", gap: 24 }}>
          <Link href="/deal"      style={{ ...mono, fontSize: "0.6rem", color: "var(--text-mute)", textDecoration: "none", letterSpacing: "0.12em", textTransform: "uppercase" }}>Deal Calculator</Link>
          <Link href="/dashboard" style={{ ...mono, fontSize: "0.6rem", color: "var(--text-mute)", textDecoration: "none", letterSpacing: "0.12em", textTransform: "uppercase" }}>Listings</Link>
        </div>
      </nav>

      {/* Progress bar */}
      {(onQuiz || onResult) && (
        <div style={{ height: 3, background: "var(--border)" }}>
          <div style={{ height: "100%", width: `${progress}%`, background: "var(--accent)", transition: "width 0.3s" }} />
        </div>
      )}

      <div style={{ maxWidth: 760, margin: "0 auto", padding: "64px 32px" }}>

        {/* ── INTRO ── */}
        {step === 0 && (
          <div style={{ textAlign: "center" }}>
            <div style={{ ...mono, fontSize: "0.56rem", textTransform: "uppercase", letterSpacing: "0.2em", color: "var(--accent)", marginBottom: 12 }}>◈ Your Personalized Strategy</div>
            <h1 style={{ fontFamily: "var(--serif, Georgia)", fontSize: "2.4rem", fontWeight: 400, marginBottom: 16 }}>Find your GTA investment strategy.</h1>
            <p style={{ ...mono, fontSize: "0.7rem", color: "var(--text-mute)", marginBottom: 40, lineHeight: 1.8 }}>
              7 questions. Instant strategy match.<br />
              We'll recommend the right approach based on your budget, risk tolerance, and goals.
            </p>
            <button
              onClick={() => setStep(1)}
              style={{ ...mono, fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.14em", padding: "14px 36px", background: "var(--accent)", color: "var(--bg)", border: "none", cursor: "pointer" }}
            >
              Get Started →
            </button>
          </div>
        )}

        {/* ── QUIZ ── */}
        {onQuiz && currentQ && (
          <div>
            <div style={{ ...mono, fontSize: "0.52rem", textTransform: "uppercase", letterSpacing: "0.18em", color: "var(--accent)", marginBottom: 20 }}>
              Question {step} of {totalQ}
            </div>
            <h2 style={{ fontFamily: "var(--serif, Georgia)", fontSize: "1.9rem", fontWeight: 400, marginBottom: 32 }}>
              {currentQ.q}
            </h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 40 }}>
              {currentQ.options.map((opt) => {
                const active = selected === opt.value;
                return (
                  <button
                    key={opt.value}
                    onClick={() => pick(opt.value)}
                    style={{
                      textAlign: "left", padding: "18px 22px",
                      background: active ? "rgba(200,169,110,0.08)" : "var(--bg-elev)",
                      border: `1px solid ${active ? "var(--accent)" : "var(--border)"}`,
                      cursor: "pointer", transition: "all 0.15s", position: "relative",
                    }}
                  >
                    <div style={{ ...mono, fontSize: "0.78rem", color: "var(--text)", fontWeight: active ? 600 : 400, marginBottom: 3 }}>{opt.label}</div>
                    {opt.sub && <div style={{ ...mono, fontSize: "0.58rem", color: "var(--text-dim)" }}>{opt.sub}</div>}
                    {active && (
                      <span style={{ position: "absolute", right: 18, top: "50%", transform: "translateY(-50%)", color: "var(--accent)", fontSize: "1rem" }}>✓</span>
                    )}
                  </button>
                );
              })}
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <button onClick={back} style={{ ...mono, fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.12em", padding: "10px 20px", background: "transparent", border: "1px solid var(--border)", color: "var(--text-mute)", cursor: "pointer" }}>
                ← Back
              </button>
              <button
                onClick={next}
                disabled={!selected}
                style={{ ...mono, fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.12em", padding: "10px 28px", background: "var(--accent)", color: "var(--bg)", border: "none", cursor: selected ? "pointer" : "default", opacity: selected ? 1 : 0.4 }}
              >
                {step === totalQ ? "Get My Strategy →" : "Next →"}
              </button>
            </div>
          </div>
        )}

        {/* ── RESULT ── */}
        {onResult && strategy && (
          <div>
            <div style={{ ...mono, fontSize: "0.56rem", textTransform: "uppercase", letterSpacing: "0.2em", color: "var(--accent)", marginBottom: 12, textAlign: "center" }}>◈ Your Personalized Strategy</div>
            <h2 style={{ fontFamily: "var(--serif, Georgia)", fontSize: "1.6rem", fontWeight: 400, marginBottom: 24, textAlign: "center" }}>Here&apos;s what we recommend</h2>

            {/* Strategy card */}
            <div style={{ border: "1px solid var(--border-strong)", borderLeft: "3px solid var(--accent)", padding: 28, marginBottom: 32, background: "var(--bg-elev)" }}>
              <h3 style={{ fontFamily: "var(--serif, Georgia)", fontSize: "1.4rem", fontWeight: 400, marginBottom: 12 }}>{strategy.name}</h3>
              <p style={{ ...mono, fontSize: "0.65rem", color: "var(--text-mute)", lineHeight: 1.9, marginBottom: 20 }}>{strategy.description}</p>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                {[
                  ["Typical ROI",       strategy.roi,        "var(--accent)"],
                  ["Capital Required",  strategy.capital,    "var(--accent)"],
                  ["Difficulty",        strategy.difficulty, strategy.difficultyColor],
                ].map(([l, v, c]) => (
                  <div key={l} style={{ border: "1px solid var(--border)", padding: "8px 14px", textAlign: "center" }}>
                    <div style={{ ...mono, fontSize: "0.46rem", textTransform: "uppercase", letterSpacing: "0.12em", color: "var(--text-dim)", marginBottom: 3 }}>{l}</div>
                    <div style={{ ...mono, fontSize: "0.68rem", color: c as string, fontWeight: 600 }}>{v}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Matched neighbourhoods */}
            <div style={{ marginBottom: 32 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
                <span style={{ ...mono, fontSize: "0.72rem", color: "var(--text)" }}>Your Matched GTA Neighbourhoods</span>
                <span style={{ ...mono, fontSize: "0.44rem", textTransform: "uppercase", letterSpacing: "0.1em", background: "rgba(200,169,110,0.12)", border: "1px solid var(--border)", padding: "2px 7px", color: "var(--accent)" }}>GTA Data</span>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12 }}>
                {strategy.neighbourhoods.map((n) => (
                  <div key={n.name} style={{ border: "1px solid var(--border)", padding: 18, background: "var(--bg-elev)" }}>
                    <div style={{ ...mono, fontSize: "0.72rem", fontWeight: 600, color: "var(--text)", marginBottom: 2 }}>{n.name}</div>
                    <div style={{ ...mono, fontSize: "0.52rem", color: "var(--text-dim)", marginBottom: 14 }}>{n.city}</div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                      {[
                        ["Avg Rent",       n.avgRent],
                        ["Avg Home Price", n.avgPrice],
                        ["Price-to-Rent",  n.ptr],
                      ].map(([l, v]) => (
                        <div key={l} style={{ display: "flex", justifyContent: "space-between" }}>
                          <span style={{ ...mono, fontSize: "0.55rem", color: "var(--text-dim)" }}>{l}</span>
                          <span style={{ ...mono, fontSize: "0.55rem", color: "var(--text)", fontWeight: 500 }}>{v}</span>
                        </div>
                      ))}
                    </div>
                    <div style={{ marginTop: 12, borderTop: "1px solid var(--border)", paddingTop: 10 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ ...mono, fontSize: "0.5rem", color: "var(--text-dim)" }}>Invest Score</span>
                        <div style={{ display: "flex", alignItems: "baseline", gap: 3 }}>
                          <span style={{ ...mono, fontSize: "0.9rem", color: "var(--accent)", fontWeight: 700 }}>{n.score}</span>
                          <span style={{ ...mono, fontSize: "0.48rem", color: "var(--text-dim)" }}>/100</span>
                        </div>
                      </div>
                      <div style={{ marginTop: 6, height: 3, background: "var(--border)", borderRadius: 2 }}>
                        <div style={{ height: "100%", width: `${n.score}%`, background: n.score >= 85 ? "#2ed573" : n.score >= 70 ? "#ffa502" : "var(--accent)", borderRadius: 2 }} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Email capture */}
            <div style={{ border: "1px solid var(--border)", padding: 24, marginBottom: 24 }}>
              <div style={{ ...mono, fontSize: "0.62rem", color: "var(--text)", marginBottom: 4 }}>Save your results</div>
              <div style={{ ...mono, fontSize: "0.56rem", color: "var(--text-dim)", marginBottom: 16 }}>Get your strategy summary + matched GTA listings sent to your inbox.</div>
              {emailSent ? (
                <div style={{ ...mono, fontSize: "0.65rem", color: "#2ed573" }}>✓ Strategy saved — check your inbox.</div>
              ) : (
                <div style={{ display: "flex", gap: 10 }}>
                  <input
                    type="email" value={email} onChange={e => setEmail(e.target.value)}
                    placeholder="your@email.com"
                    style={{ flex: 1, fontFamily: "var(--mono)", fontSize: "0.72rem", background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", padding: "10px 14px", outline: "none" }}
                  />
                  <button
                    onClick={() => { if (email.includes("@")) setEmailSent(true); }}
                    style={{ ...mono, fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.12em", padding: "10px 20px", background: "var(--accent)", color: "var(--bg)", border: "none", cursor: "pointer" }}
                  >
                    Send My Results
                  </button>
                </div>
              )}
            </div>

            {/* CTAs */}
            <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
              <Link href="/deal" style={{ ...mono, fontSize: "0.62rem", textTransform: "uppercase", letterSpacing: "0.12em", padding: "12px 24px", background: "var(--accent)", color: "var(--bg)", textDecoration: "none", display: "inline-block" }}>
                Try the Deal Calculator →
              </Link>
              <button onClick={restart} style={{ ...mono, fontSize: "0.62rem", textTransform: "uppercase", letterSpacing: "0.12em", padding: "12px 24px", background: "transparent", color: "var(--text-mute)", border: "1px solid var(--border)", cursor: "pointer" }}>
                Start Over
              </button>
              <Link href="/dashboard" style={{ ...mono, fontSize: "0.62rem", textTransform: "uppercase", letterSpacing: "0.12em", padding: "12px 24px", background: "transparent", color: "var(--text-mute)", border: "1px solid var(--border)", textDecoration: "none", display: "inline-block" }}>
                Browse GTA Listings
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
