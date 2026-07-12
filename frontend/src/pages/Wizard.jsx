import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Brain,
  Heart,
  BookOpen,
  User,
  CheckCircle2,
} from "lucide-react";

import Navbar from "../components/Navbar";
import Loading from "../components/Loading";
import { fetchHealth, fetchOptions, predictCareer } from "../api";
import { savePredictionSession } from "../session";
import questionsData from "../data/questions.json";

/* ───────── helpers ───────── */
const STEPS = [
  { label: "Profile", icon: User },
  { label: "Aptitude Test", icon: BookOpen },
  { label: "Personality", icon: Brain },
  { label: "Interests", icon: Heart },
  { label: "Review", icon: CheckCircle2 },
];

const APT_CATEGORIES = { Math: [], Logic: [], Verbal: [], "Applied Problem-Solving": [] };
questionsData.aptitude_test.questions.forEach((q) => {
  if (APT_CATEGORIES[q.category]) APT_CATEGORIES[q.category].push(q);
});

const PSYCH_TRAITS = {};
questionsData.psychology_test.questions.forEach((q) => {
  if (!PSYCH_TRAITS[q.trait]) PSYCH_TRAITS[q.trait] = [];
  PSYCH_TRAITS[q.trait].push(q);
});

const INTEREST_CATS = {};
questionsData.interest_test.questions.forEach((q) => {
  if (!INTEREST_CATS[q.riasec]) INTEREST_CATS[q.riasec] = [];
  INTEREST_CATS[q.riasec].push(q);
});

function scoreAptitude(answers) {
  const catScores = {};
  const difficultyWeights = { easy: 1, medium: 2, hard: 3 };

  Object.entries(APT_CATEGORIES).forEach(([cat, qs]) => {
    let earnedWeight = 0;
    let totalWeight = 0;
    qs.forEach((q) => {
      const w = difficultyWeights[q.difficulty] || 1;
      totalWeight += w;
      if (answers[q.id] === q.correct) earnedWeight += w;
    });
    catScores[cat] = totalWeight > 0 ? Math.round((earnedWeight / totalWeight) * 100) : 50;
  });

  return {
    Aptitude_Math: catScores.Math ?? 50,
    Aptitude_Logic: catScores.Logic ?? 50,
    Aptitude_Verbal: catScores.Verbal ?? 50,
    Aptitude_Spatial: catScores["Applied Problem-Solving"] ?? 50,
  };
}

function scorePsych(answers) {
  const traitAvg = {};
  Object.entries(PSYCH_TRAITS).forEach(([trait, qs]) => {
    let sum = 0;
    qs.forEach((q) => {
      const raw = answers[q.id] ?? 3;
      sum += q.weight === "negative" ? 6 - raw : raw;
    });
    traitAvg[trait] = Math.round((sum / qs.length) * 2 * 10) / 10;
  });
  return {
    Psych_Openness: traitAvg.Openness ?? 5,
    Psych_Conscientiousness: traitAvg.Conscientiousness ?? 5,
    Psych_Extraversion: traitAvg.Extraversion ?? 5,
    Psych_Agreeableness: traitAvg.Agreeableness ?? 5,
    Psych_Neuroticism: traitAvg.Neuroticism ?? 5,
  };
}

function scoreInterests(answers) {
  const catScores = {};
  Object.entries(INTEREST_CATS).forEach(([cat, qs]) => {
    let pts = 0;
    qs.forEach((q) => {
      const a = answers[q.id];
      pts += a === "Yes" ? 2 : a === "Maybe" ? 1 : 0;
    });
    catScores[cat] = pts;
  });
  const sorted = Object.entries(catScores).sort((a, b) => b[1] - a[1]);
  return sorted
    .slice(0, 3)
    .map(([c]) => c.split("(")[0].trim())
    .join(", ");
}

function scoreHolland(answers) {
  const points = { Realistic: 0, Investigative: 0, Artistic: 0, Social: 0, Enterprising: 0, Conventional: 0 };
  const counts = { Realistic: 4, Investigative: 4, Artistic: 3, Social: 3, Enterprising: 3, Conventional: 3 };

  questionsData.interest_test.questions.forEach((q) => {
    const a = answers[q.id];
    const pts = a === "Yes" ? 2 : a === "Maybe" ? 1 : 0;
    points[q.riasec] += pts;
  });

  return {
    Interest_R: Math.round((points.Realistic / (counts.Realistic * 2)) * 100),
    Interest_I: Math.round((points.Investigative / (counts.Investigative * 2)) * 100),
    Interest_A: Math.round((points.Artistic / (counts.Artistic * 2)) * 100),
    Interest_S: Math.round((points.Social / (counts.Social * 2)) * 100),
    Interest_E: Math.round((points.Enterprising / (counts.Enterprising * 2)) * 100),
    Interest_C: Math.round((points.Conventional / (counts.Conventional * 2)) * 100)
  };
}

/* ───────── component ───────── */
const Wizard = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // profile state
  const [profile, setProfile] = useState({
    name: "", Stream: "", Extracurricular_Activity: "",
    FSc_Marks: 850,
    Marks_Math: 70, Marks_Physics: 70,
    Marks_Computer: 70, Marks_Biology: 70,
    Marks_Chemistry: 70,
    Model_Name: "Hybrid",
  });

  // test answers
  const [aptAnswers, setAptAnswers] = useState({});
  const [psychAnswers, setPsychAnswers] = useState({});
  const [intAnswers, setIntAnswers] = useState({});

  // options from API
  const [options, setOptions] = useState({
    streams: [],
    activities: [],
    models: ["Ensemble", "Stacking", "Hybrid"],
  });
  const [backendOk, setBackendOk] = useState(false);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [step]);

  useEffect(() => {
    (async () => {
      try {
        const [health, opts] = await Promise.all([fetchHealth(), fetchOptions()]);
        setOptions(opts);
        setProfile((p) => ({
          ...p,
          Stream: p.Stream || opts.streams[0] || "",
          Extracurricular_Activity: p.Extracurricular_Activity || opts.activities[0] || "",
        }));
        setBackendOk(health.status === "ok");
      } catch { setBackendOk(false); }
    })();
  }, []);

  /* computed scores */
  const aptScores = useMemo(() => scoreAptitude(aptAnswers), [aptAnswers]);
  const psychScores = useMemo(() => scorePsych(psychAnswers), [psychAnswers]);
  const interestText = useMemo(() => scoreInterests(intAnswers), [intAnswers]);
  const interestScores = useMemo(() => scoreHolland(intAnswers), [intAnswers]);

  /* navigation */
  const goNext = () => {
    if (step === 1 && (!profile.name.trim() || !profile.Stream)) {
      setError("Please fill in your name and stream."); return;
    }
    setError(""); setStep((s) => Math.min(s + 1, 5));
  };
  const goBack = () => { setError(""); setStep((s) => Math.max(s - 1, 1)); };

  const handleSubmit = async () => {
    setError("");
    const totalQ = questionsData.aptitude_test.questions.length + questionsData.psychology_test.questions.length + questionsData.interest_test.questions.length;
    const answered = Object.keys(aptAnswers).length + Object.keys(psychAnswers).length + Object.keys(intAnswers).length;
    if (answered < totalQ) {
      setError(`Please complete all ${totalQ} assessment questions before generating your prediction. Currently, you have answered only ${answered}/${totalQ} questions.`);
      return;
    }
    if (!profile.FSc_Marks || profile.FSc_Marks <= 0) {
      setError("FSc Marks cannot be zero. Please enter valid marks in Step 1.");
      return;
    }
    setSubmitting(true);

    // Clean up fields not applicable to the selected stream (set to -1 = missing)
    const cleanProfile = { ...profile };
    const stream = profile.Stream;
    if (stream === "Pre-Medical") {
      cleanProfile.Marks_Math = -1;
      cleanProfile.Marks_Computer = -1;
    } else if (stream === "Pre-Engineering") {
      cleanProfile.Marks_Biology = -1;
      cleanProfile.Marks_Computer = -1;
    } else if (stream === "ICS") {
      cleanProfile.Marks_Biology = -1;
      cleanProfile.Marks_Chemistry = -1;
    } else if (stream === "Arts") {
      cleanProfile.Marks_Biology = -1;
      cleanProfile.Marks_Chemistry = -1;
      cleanProfile.Marks_Physics = -1;
      cleanProfile.Marks_Computer = -1;
      // Math is optional for Arts — if not entered (0 or blank), set to -1
      if (!cleanProfile.Marks_Math || cleanProfile.Marks_Math <= 0) {
        cleanProfile.Marks_Math = -1;
      }
    }

    const payload = {
      // Schema compatibility fields (not used by model, kept for API schema)
      name: cleanProfile.name,
      Gender: "Male",
      Age: 18,
      City: "Lahore",
      Matric_Marks: 850,
      // Core model features
      Stream: cleanProfile.Stream,
      FSc_Marks: cleanProfile.FSc_Marks,
      Marks_Math: cleanProfile.Marks_Math,
      Marks_Physics: cleanProfile.Marks_Physics,
      Marks_Computer: cleanProfile.Marks_Computer,
      Marks_Biology: cleanProfile.Marks_Biology,
      Marks_Chemistry: cleanProfile.Marks_Chemistry,
      Extracurricular_Activity: cleanProfile.Extracurricular_Activity,
      Model_Name: cleanProfile.Model_Name,
      ...aptScores, ...psychScores, ...interestScores,
      Interest_Text: interestText || "General",
    };
    try {
      const prediction = await predictCareer(payload);
      const session = { student: payload, studentName: profile.name, prediction };
      savePredictionSession(session);
      navigate("/results", { state: session });
    } catch (e) {
      setError(e?.response?.data?.detail || "Prediction failed. Check backend.");
    } finally { setSubmitting(false); }
  };

  if (submitting) return <Loading />;

  const progress = (step / 5) * 100;

  return (
    <div className="min-h-screen bg-dark text-white font-grotesk">
      <Navbar />
      <div className="pt-24 px-4 md:px-10 pb-12">
        <div className="max-w-5xl mx-auto">

          {/* ── Header ── */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6 gap-4">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-primary-cyan mb-1">Career Assessment</p>
              <h1 className="text-3xl md:text-4xl font-bold flex items-center gap-3">
                {React.createElement(STEPS[step - 1].icon, { size: 28, className: "text-primary-cyan" })}
                {STEPS[step - 1].label}
              </h1>
            </div>
            <div className={`rounded-2xl px-4 py-2 border text-sm ${backendOk ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-200" : "border-amber-400/30 bg-amber-400/10 text-amber-100"}`}>
              {backendOk ? "✓ Backend connected" : "⚠ Backend offline"}
            </div>
          </div>

          {/* ── Step indicators ── */}
          <div className="flex gap-2 mb-2">
            {STEPS.map((s, i) => (
              <button key={s.label} onClick={() => i + 1 <= step && setStep(i + 1)}
                className={`flex-1 h-2 rounded-full transition-all ${i + 1 <= step ? "bg-gradient-to-r from-primary-cyan to-accent-teal" : "bg-white/10"}`} />
            ))}
          </div>
          <p className="text-xs text-text-gray mb-8">Step {step} of 5 — {Math.round(progress)}% complete</p>

          {/* ── Content Card ── */}
          <div className="bg-card-bg border border-card-border rounded-[32px] p-6 md:p-10 shadow-[0_0_50px_rgba(0,0,0,0.35)] relative overflow-hidden min-h-[500px]">
            <div className="absolute -top-24 -right-24 w-72 h-72 bg-primary-cyan/10 rounded-full blur-[100px]" />

            <AnimatePresence mode="wait">
              {step === 1 && (
                <StepProfile key="s1" profile={profile} setProfile={setProfile} options={options} />
              )}
              {step === 2 && (
                <StepAptitude key="s2" answers={aptAnswers} setAnswers={setAptAnswers} />
              )}
              {step === 3 && (
                <StepPsychology key="s3" answers={psychAnswers} setAnswers={setPsychAnswers} />
              )}
              {step === 4 && (
                <StepInterests key="s4" answers={intAnswers} setAnswers={setIntAnswers} />
              )}
              {step === 5 && (
                <StepReview key="s5" profile={profile} aptScores={aptScores}
                  psychScores={psychScores} interestText={interestText}
                  aptTotal={Object.keys(aptAnswers).length}
                  psychTotal={Object.keys(psychAnswers).length}
                  intTotal={Object.keys(intAnswers).length}
                  onSubmit={handleSubmit} />
              )}
            </AnimatePresence>

            {error && (
              <div className="mt-6 border border-rose-400/30 bg-rose-400/10 text-rose-100 rounded-2xl px-4 py-3">{error}</div>
            )}

            {/* ── Nav buttons ── */}
            <div className="flex justify-between mt-10 pt-6 border-t border-white/10">
              <button onClick={goBack} disabled={step === 1}
                className={`px-5 py-3 rounded-2xl inline-flex items-center gap-2 ${step === 1 ? "opacity-0 pointer-events-none" : "text-text-gray hover:text-white hover:bg-white/5"}`}>
                <ChevronLeft size={18} /> Back
              </button>
              {step < 5 ? (
                <button onClick={goNext}
                  className="bg-primary-cyan text-dark font-bold px-6 py-3 rounded-2xl inline-flex items-center gap-2 hover:bg-cyan-300 transition-colors">
                  Next <ChevronRight size={18} />
                </button>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ═══════════════════════════════════════════
   STEP 1 — Profile & Academics
   ═══════════════════════════════════════════ */

// Activities mapped per stream (from training dataset)
const STREAM_ACTIVITIES = {
  "Pre-Medical": [
    "Biology Olympiad Team",
    "Chemistry Lab Club",
    "First Aid Training Program",
    "Health Awareness Campaign",
    "Medical Volunteer Camp",
    "Red Crescent Society",
  ],
  "Pre-Engineering": [
    "Astronomy Club",
    "Engineering Society",
    "Physics Experiment Club",
    "Renewable Energy Project Group",
    "Robotics Club",
    "Science Fair Participant",
  ],
  "ICS": [
    "Coding Club",
    "Cyber Security Club",
    "Math Olympiad Team",
    "Open Source Contribution Team",
    "Science Society",
    "Tech Entrepreneurs Club",
  ],
  "Arts": [
    "Art & Design Society",
    "Debating Society",
    "Drama & Theatre Club",
    "Environmental Awareness Club",
    "Literary Society",
    "Model United Nations",
    "Social Welfare Society",
  ],
};

const STREAM_INFO = {
  "Pre-Medical": "Subjects: Biology • Chemistry • Physics",
  "Pre-Engineering": "Subjects: Mathematics • Physics • Chemistry",
  "ICS": "Subjects: Mathematics • Physics • Computer Science",
  "Arts": "Subjects: Mathematics (optional elective) — FSc total marks required",
};

function StepProfile({ profile, setProfile, options }) {
  const u = (k, v) => setProfile((p) => ({ ...p, [k]: v }));
  const inputCls = "w-full bg-dark border border-white/10 rounded-2xl px-4 py-4 outline-none focus:border-primary-cyan transition-colors";
  const numInputCls = inputCls + " [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none";
  const handleNum = (k) => (e) => {
    const raw = e.target.value.replace(/[^0-9]/g, "");
    u(k, raw === "" ? "" : Number(raw));
  };

  // When stream changes, auto-select first matching activity
  const handleStreamChange = (v) => {
    u("Stream", v);
    const acts = STREAM_ACTIVITIES[v] || [];
    u("Extracurricular_Activity", acts[0] || "");
  };

  // Stream-based subject visibility
  const stream = profile.Stream;
  // Arts students can optionally take Math; Pre-Engineering & ICS always have Math
  const showMath     = stream === "Pre-Engineering" || stream === "ICS" || stream === "Arts";
  const showPhysics  = stream === "Pre-Medical" || stream === "Pre-Engineering" || stream === "ICS";
  const showChemistry = stream === "Pre-Medical" || stream === "Pre-Engineering";
  const showComputer = stream === "ICS";
  const showBiology  = stream === "Pre-Medical";

  const subjectFields = [
    { f: "Marks_Biology",   l: "Biology Marks (out of 100)",           ph: "e.g. 85", show: showBiology },
    { f: "Marks_Chemistry", l: "Chemistry Marks (out of 100)",         ph: "e.g. 80", show: showChemistry },
    { f: "Marks_Physics",   l: "Physics Marks (out of 100)",           ph: "e.g. 78", show: showPhysics },
    { f: "Marks_Math",      l: "Mathematics Marks (out of 100)",       ph: "e.g. 90", show: showMath },
    { f: "Marks_Computer",  l: "Computer Science Marks (out of 100)",  ph: "e.g. 88", show: showComputer },
  ].filter(x => x.show);

  const streamActivities = STREAM_ACTIVITIES[stream] || (options.activities || []);

  return (
    <motion.div initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -18 }} className="space-y-6 relative z-10">
      <p className="text-text-gray">Tell us about yourself and your academic background.</p>

      {/* Name + Stream row */}
      <div className="grid md:grid-cols-2 gap-5">
        <label className="space-y-2">
          <span className="text-sm text-text-gray">Full Name *</span>
          <input value={profile.name} onChange={(e) => u("name", e.target.value)} className={inputCls} placeholder="Ali Khan" />
        </label>
        <label className="space-y-2">
          <span className="text-sm text-text-gray">FSc Stream *</span>
          <select value={profile.Stream} onChange={(e) => handleStreamChange(e.target.value)} className={inputCls}>
            {(options.streams || []).map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </label>
      </div>

      {/* Stream info callout */}
      {stream && (
        <div className="flex items-center gap-3 bg-primary-cyan/5 border border-primary-cyan/20 rounded-2xl px-4 py-3">
          <span className="text-primary-cyan text-lg">ℹ️</span>
          <p className="text-sm text-primary-cyan/90">{STREAM_INFO[stream]}</p>
        </div>
      )}

      {/* Extracurricular Activity */}
      <label className="space-y-2 block">
        <span className="text-sm text-text-gray">Extracurricular Activity</span>
        <select value={profile.Extracurricular_Activity} onChange={(e) => u("Extracurricular_Activity", e.target.value)} className={inputCls}>
          {streamActivities.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
      </label>

      {/* Academic Marks Section */}
      <div>
        <p className="text-sm uppercase tracking-[0.25em] text-accent-teal pt-2 mb-1">Academic Marks</p>
        <p className="text-xs text-text-gray/60 mb-4">Enter your FSc marks and individual subject marks below.</p>
        <div className="grid md:grid-cols-2 gap-5">
          {/* FSc Total always shown */}
          <label className="space-y-2">
            <span className="text-sm text-text-gray">FSc Total Marks (out of 1100) *</span>
            <input
              type="text" inputMode="numeric"
              value={profile.FSc_Marks}
              onChange={handleNum("FSc_Marks")}
              className={numInputCls}
              placeholder="e.g. 850"
            />
          </label>

          {/* Stream-specific subject marks */}
          {subjectFields.map(({ f, l, ph }) => (
            <label key={f} className="space-y-2">
              <span className="text-sm text-text-gray">{l}</span>
              <input
                type="text" inputMode="numeric"
                value={profile[f]}
                onChange={handleNum(f)}
                className={numInputCls}
                placeholder={ph}
              />
            </label>
          ))}

          {/* Arts: Math is shown above; show a note about it being optional */}
          {stream === "Arts" && (
            <div className="md:col-span-2 bg-amber-400/5 border border-amber-400/20 rounded-2xl px-4 py-3 text-amber-200/80 text-xs">
              ⚡ If you did not take Mathematics as an elective, leave the Mathematics field at 0.
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

/* ═══════════════════════════════════════════
   STEP 2 — Aptitude Test (MCQ)
   ═══════════════════════════════════════════ */
function StepAptitude({ answers, setAnswers }) {
  const pick = (id, val) => setAnswers((a) => ({ ...a, [id]: val }));
  return (
    <motion.div initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -18 }} className="space-y-8 relative z-10">
      <p className="text-text-gray">Select the correct answer for each question. <span className="text-primary-cyan font-semibold">{Object.keys(answers).length}/{questionsData.aptitude_test.questions.length}</span> answered.</p>
      {Object.entries(APT_CATEGORIES).map(([cat, qs]) => (
        <div key={cat}>
          <h3 className="text-lg font-bold text-accent-teal mb-4 flex items-center gap-2">
            <BookOpen size={18} /> {cat} Reasoning
          </h3>
          <div className="space-y-4">
            {qs.map((q, qi) => (
              <div key={q.id} className="bg-dark/60 border border-white/10 rounded-2xl p-5">
                <p className="font-medium mb-1">Q{qi + 1}. {q.text_en}</p>
                {q.text_ur && <p className="text-sm text-text-gray mb-3 font-noto-nastaliq">{q.text_ur}</p>}
                <div className="grid grid-cols-2 gap-3">
                  {Object.entries(q.options).map(([key, val]) => {
                    const selected = answers[q.id] === key;
                    return (
                      <button key={key} type="button" onClick={() => pick(q.id, key)}
                        className={`text-left px-4 py-3 rounded-xl border transition-all ${selected ? "border-primary-cyan bg-primary-cyan/15 text-white" : "border-white/10 text-text-gray hover:border-white/25 hover:text-white"}`}>
                        <span className="font-bold text-primary-cyan mr-2">{key})</span> {val}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </motion.div>
  );
}

/* ═══════════════════════════════════════════
   STEP 3 — Personality (Big Five Likert)
   ═══════════════════════════════════════════ */
const LIKERT = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"];
function StepPsychology({ answers, setAnswers }) {
  const pick = (id, val) => setAnswers((a) => ({ ...a, [id]: val }));
  return (
    <motion.div initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -18 }} className="space-y-8 relative z-10">
      <p className="text-text-gray">Rate how much you agree with each statement. <span className="text-primary-cyan font-semibold">{Object.keys(answers).length}/{questionsData.psychology_test.questions.length}</span> answered.</p>
      {Object.entries(PSYCH_TRAITS).map(([trait, qs]) => (
        <div key={trait}>
          <h3 className="text-lg font-bold text-accent-teal mb-4 flex items-center gap-2">
            <Brain size={18} /> {trait}
          </h3>
          <div className="space-y-4">
            {qs.map((q) => {
              const val = answers[q.id] ?? 0;
              return (
                <div key={q.id} className="bg-dark/60 border border-white/10 rounded-2xl p-5">
                  <p className="font-medium mb-1">{q.text_en}</p>
                  {q.text_ur && <p className="text-sm text-text-gray mb-4 font-noto-nastaliq">{q.text_ur}</p>}
                  <div className="flex flex-wrap gap-2">
                    {LIKERT.map((label, i) => {
                      const score = i + 1;
                      const selected = val === score;
                      return (
                        <button key={label} type="button" onClick={() => pick(q.id, score)}
                          className={`px-4 py-2 rounded-xl border text-sm transition-all ${selected ? "border-accent-teal bg-accent-teal/15 text-white font-semibold" : "border-white/10 text-text-gray hover:border-white/25"}`}>
                          {label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </motion.div>
  );
}

/* ═══════════════════════════════════════════
   STEP 4 — Interest Test (Yes/Maybe/No)
   ═══════════════════════════════════════════ */
const INT_OPTS = ["Yes", "Maybe", "No"];
const INT_COLORS = { Yes: "border-emerald-400 bg-emerald-400/15 text-emerald-200", Maybe: "border-amber-400 bg-amber-400/15 text-amber-200", No: "border-rose-400 bg-rose-400/15 text-rose-200" };
function StepInterests({ answers, setAnswers }) {
  const pick = (id, val) => setAnswers((a) => ({ ...a, [id]: val }));
  return (
    <motion.div initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -18 }} className="space-y-8 relative z-10">
      <p className="text-text-gray">Do you enjoy these activities? <span className="text-primary-cyan font-semibold">{Object.keys(answers).length}/{questionsData.interest_test.questions.length}</span> answered.</p>
      {Object.entries(INTEREST_CATS).map(([cat, qs]) => (
        <div key={cat}>
          <h3 className="text-lg font-bold text-accent-teal mb-4 flex items-center gap-2">
            <Heart size={18} /> {cat}
          </h3>
          <div className="space-y-4">
            {qs.map((q) => (
              <div key={q.id} className="bg-dark/60 border border-white/10 rounded-2xl p-5 flex flex-col md:flex-row md:items-center gap-4">
                <div className="flex-1">
                  <p className="font-medium">{q.text_en}</p>
                  {q.text_ur && <p className="text-sm text-text-gray font-noto-nastaliq">{q.text_ur}</p>}
                </div>
                <div className="flex gap-2 shrink-0">
                  {INT_OPTS.map((opt) => {
                    const selected = answers[q.id] === opt;
                    return (
                      <button key={opt} type="button" onClick={() => pick(q.id, opt)}
                        className={`px-5 py-2 rounded-xl border text-sm font-semibold transition-all ${selected ? INT_COLORS[opt] : "border-white/10 text-text-gray hover:border-white/25"}`}>
                        {opt}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </motion.div>
  );
}

/* ═══════════════════════════════════════════
   STEP 5 — Review & Submit
   ═══════════════════════════════════════════ */
function StepReview({ profile, aptScores, psychScores, interestText, aptTotal, psychTotal, intTotal, onSubmit }) {
  const totalQ = questionsData.aptitude_test.questions.length + questionsData.psychology_test.questions.length + questionsData.interest_test.questions.length;
  const answered = aptTotal + psychTotal + intTotal;
  return (
    <motion.div initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -18 }} className="space-y-6 relative z-10">
      <p className="text-text-gray">Review your assessment before generating your career prediction.</p>
      <div className="grid md:grid-cols-2 gap-5">
        <div className="bg-dark/60 border border-white/10 rounded-3xl p-6">
          <p className="text-sm uppercase tracking-[0.25em] text-primary-cyan mb-3">Profile</p>
          <div className="space-y-2 text-sm text-text-gray">
            {[["Name", profile.name],["City", profile.City],["Stream", profile.Stream],["Matric", profile.Matric_Marks],["FSc", profile.FSc_Marks]].map(([l,v]) => (
              <div key={l} className="flex justify-between"><span>{l}</span><span className="text-white font-medium">{v}</span></div>
            ))}
          </div>
        </div>
        <div className="bg-dark/60 border border-white/10 rounded-3xl p-6">
          <p className="text-sm uppercase tracking-[0.25em] text-accent-teal mb-3">Test Completion</p>
          <div className="space-y-2 text-sm text-text-gray">
            <div className="flex justify-between"><span>Aptitude</span><span className="text-white font-medium">{aptTotal}/20</span></div>
            <div className="flex justify-between"><span>Personality</span><span className="text-white font-medium">{psychTotal}/20</span></div>
            <div className="flex justify-between"><span>Interests</span><span className="text-white font-medium">{intTotal}/20</span></div>
            <div className="flex justify-between border-t border-white/10 pt-2 mt-2"><span>Total</span><span className="text-primary-cyan font-bold">{answered}/{totalQ}</span></div>
          </div>
        </div>
        <div className="bg-dark/60 border border-white/10 rounded-3xl p-6">
          <p className="text-sm uppercase tracking-[0.25em] text-primary-cyan mb-3">Aptitude Scores</p>
          <div className="space-y-2 text-sm text-text-gray">
            {Object.entries(aptScores).map(([k, v]) => (
              <div key={k} className="flex justify-between"><span>{k.replace("Aptitude_","")}</span>
                <div className="flex items-center gap-2"><div className="w-20 h-2 rounded-full bg-white/10 overflow-hidden"><div className="h-full bg-primary-cyan rounded-full" style={{ width: `${v}%` }} /></div><span className="text-white font-medium w-8 text-right">{v}%</span></div>
              </div>
            ))}
          </div>
        </div>
        <div className="bg-dark/60 border border-white/10 rounded-3xl p-6">
          <p className="text-sm uppercase tracking-[0.25em] text-accent-teal mb-3">Top Interests</p>
          <p className="text-white">{interestText || "No interests selected yet."}</p>
          <p className="text-sm uppercase tracking-[0.25em] text-accent-teal mb-3 mt-4">Personality</p>
          <div className="space-y-2 text-sm text-text-gray">
            {Object.entries(psychScores).map(([k, v]) => (
              <div key={k} className="flex justify-between"><span>{k.replace("Psych_","")}</span><span className="text-white font-medium">{v}/10</span></div>
            ))}
          </div>
        </div>
      </div>
      <button type="button" onClick={onSubmit}
        className="w-full md:w-auto bg-gradient-to-r from-primary-cyan to-accent-teal text-dark font-bold px-8 py-4 rounded-2xl shadow-[0_12px_30px_rgba(0,229,255,0.18)] hover:scale-[1.01] transition-transform inline-flex items-center justify-center gap-3">
        <Sparkles size={20} /> Generate Career Prediction
      </button>
    </motion.div>
  );
}

export default Wizard;
