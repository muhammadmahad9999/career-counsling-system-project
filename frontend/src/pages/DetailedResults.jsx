import React, { useEffect, useMemo, useState, useCallback } from "react";
import { Link, useLocation } from "react-router-dom";
import { ArrowRight, BarChart2, CheckCircle, MessageSquareText, Route, Sparkles, Download, Save, ThumbsUp, AlertTriangle, PieChart as PieChartIcon, TrendingUp, RefreshCw, MapPin, Building2, Award, Wifi, Users, Brain, Compass, Check, HelpCircle, Bookmark } from "lucide-react";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, PieChart, Pie, Legend, AreaChart, Area } from "recharts";

import Navbar from "../components/Navbar";
import { loadPredictionSession } from "../session";
import { fetchShap, saveSession, exportPdf, fetchMarketTrends, fetchAptitudeDiagnostic, saveEntryTestScore, fetchEntryTestScores, fetchSavedResources } from "../api";

const tabs = ["Overview", "Top Matches", "Explainability (XAI)", "Aptitude Diagnostic", "Action Plan", "Market Trends", "Saved Bookmarks & Scores"];

const DetailedResults = () => {
  const location = useLocation();
  const session = location.state || loadPredictionSession();
  const [activeTab, setActiveTab] = useState("Overview");
  const [shapData, setShapData] = useState(null);
  const [marketData, setMarketData] = useState(null);
  const [marketLoading, setMarketLoading] = useState(false);
  const [marketFetched, setMarketFetched] = useState(false);

  // Aptitude Weakness Diagnostic States
  const [diagnostic, setDiagnostic] = useState(null);
  const [diagnosticLoading, setDiagnosticLoading] = useState(false);
  const [diagnosticError, setDiagnosticError] = useState("");
  const [quizAnswers, setQuizAnswers] = useState({});
  const [showExplanations, setShowExplanations] = useState({});

  const recommendations = session?.prediction?.recommendations || [];
  const primary = session?.prediction?.primary_recommendation || recommendations[0];

  const weakest_cat = useMemo(() => {
    if (!session?.student) return null;
    const scores = {
      Logic: session.student.Aptitude_Logic || 50,
      Math: session.student.Aptitude_Math || 50,
      Verbal: session.student.Aptitude_Verbal || 50,
      Spatial: session.student.Aptitude_Spatial || 50,
    };
    return Object.keys(scores).reduce((a, b) => (scores[a] < scores[b] ? a : b));
  }, [session]);

  const highlights = useMemo(() => {
    if (!session?.student || !primary) {
      return [];
    }

    return [
      `${session.student.Stream} stream aligns with ${primary.career}.`,
      `Aptitude profile was processed using the ${session.prediction.used_model} strategy.`,
      `Interest statement points toward ${primary.skills_required?.slice(0, 2).join(" and ") || "strong domain alignment"}.`,
      `Roadmap and university guidance were pulled from your reference dataset.`,
    ];
  }, [primary, session]);

  useEffect(() => {
    if (session?.student) {
      fetchShap(session.student)
        .then((res) => setShapData(res.top_features))
        .catch((e) => console.error("SHAP error:", e));
    }
  }, [session]);

  useEffect(() => {
    if (activeTab === "Aptitude Diagnostic" && !diagnostic && session?.student) {
      setDiagnosticLoading(true);
      setDiagnosticError("");
      const scores = {
        Aptitude_Logic: session.student.Aptitude_Logic || 50,
        Aptitude_Verbal: session.student.Aptitude_Verbal || 50,
        Aptitude_Spatial: session.student.Aptitude_Spatial || 50,
        Aptitude_Math: session.student.Aptitude_Math || 50,
      };
      fetchAptitudeDiagnostic(scores)
        .then((res) => {
          setDiagnostic(res);
        })
        .catch((err) => {
          console.error("Diagnostic error:", err);
          setDiagnosticError("Failed to load diagnostic report. Please check backend connection.");
        })
        .finally(() => {
          setDiagnosticLoading(false);
        });
    }
  }, [activeTab, diagnostic, session]);

  // Bookmarks and Entry Test Scores States
  const [savedResources, setSavedResources] = useState([]);
  const [entryTestScores, setEntryTestScores] = useState([]);
  const [scoresLoading, setScoresLoading] = useState(false);
  const [savingScore, setSavingScore] = useState(false);
  const [newScoreType, setNewScoreType] = useState("Admission Test");
  const [newScoreSubject, setNewScoreSubject] = useState("");
  const [newScoreValue, setNewScoreValue] = useState("");
  const [newScoreTotal, setNewScoreTotal] = useState("");

  const loadSavedData = useCallback(async () => {
    setScoresLoading(true);
    try {
      const [resources, scores] = await Promise.all([
        fetchSavedResources(),
        fetchEntryTestScores()
      ]);
      setSavedResources(resources || []);
      setEntryTestScores(scores || []);
    } catch (err) {
      console.error("Failed to load saved data:", err);
    } finally {
      setScoresLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === "Saved Bookmarks & Scores" && session?.student) {
      loadSavedData();
    }
  }, [activeTab, session, loadSavedData]);

  const handleAddScore = async (e) => {
    e.preventDefault();
    if (!newScoreSubject || !newScoreValue || !newScoreTotal) {
      alert("Please fill all score fields.");
      return;
    }
    setSavingScore(true);
    try {
      await saveEntryTestScore({
        test_type: newScoreType,
        subject: newScoreSubject,
        score: parseFloat(newScoreValue),
        total: parseFloat(newScoreTotal),
        weak_topics: []
      });
      alert("Score added successfully!");
      setNewScoreSubject("");
      setNewScoreValue("");
      setNewScoreTotal("");
      loadSavedData();
    } catch (err) {
      console.error("Failed to add score:", err);
      alert("Failed to add score.");
    } finally {
      setSavingScore(false);
    }
  };

  const [saving, setSaving] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const handleSave = async () => {
    if (!session) return;
    setSaving(true);
    try {
      await saveSession({ student: session.student, prediction: session.prediction });
      alert("Session saved to SQLite Database successfully!");
    } catch (e) {
      alert("Failed to save session.");
    } finally {
      setSaving(false);
    }
  };

  const handleDownload = async () => {
    if (!session) return;
    setDownloading(true);
    try {
      const blob = await exportPdf({ student: session.student, prediction: session.prediction });
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "AI_Career_Report.pdf");
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (e) {
      alert("Failed to download PDF.");
    } finally {
      setDownloading(false);
    }
  };

  if (!session || !primary) {
    return (
      <div className="min-h-screen bg-dark text-white font-grotesk">
        <Navbar />
        <div className="pt-28 px-6 max-w-4xl mx-auto">
          <div className="bg-card-bg border border-card-border rounded-[32px] p-10">
            <h1 className="text-3xl font-bold mb-4">No prediction session found</h1>
            <p className="text-text-gray mb-8">
              Start from the wizard so the React app can send your data to FastAPI and store the
              latest prediction session.
            </p>
            <Link
              to="/wizard"
              className="inline-flex items-center gap-2 bg-primary-cyan text-dark font-bold px-6 py-3 rounded-2xl"
            >
              Go to Wizard
              <ArrowRight size={18} />
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const getPersonalityDescription = (trait, score) => {
    if (trait === 'Openness') {
      return score >= 6 ? "You are very creative, curious, and open to trying new things. (آپ تخلیقی اور نئی چیزیں سیکھنے کے شوقین ہیں)" : "You prefer routine, structure, and familiar traditional methods. (آپ روایتی اور آزمودہ طریقوں کو پسند کرتے ہیں)";
    }
    if (trait === 'Conscientiousness') {
      return score >= 6 ? "You are highly organized, disciplined, and plan ahead carefully. (آپ منظم اور وقت کے پابند ہیں)" : "You are flexible, easy-going, and prefer spontaneous actions over strict plans. (آپ لچکدار مزاج کے ہیں اور آزادانہ کام پسند کرتے ہیں)";
    }
    if (trait === 'Extraversion') {
      return score >= 6 ? "You are outgoing, energetic, and love interacting with people. (آپ گھلنے ملنے والے اور لوگوں سے بات چیت پسند کرتے ہیں)" : "You are quiet, reserved, and prefer working independently or in small groups. (آپ اکیلے یا چھوٹے گروہ میں کام کرنا پسند کرتے ہیں)";
    }
    if (trait === 'Agreeableness') {
      return score >= 6 ? "You are very cooperative, friendly, and care deeply about others. (آپ ہمدرد، دوستانہ اور دوسروں کا خیال رکھنے والے ہیں)" : "You are competitive, analytical, and put logic over emotions in decisions. (آپ منطقی فیصلے کرتے ہیں اور مقاصد پر زیادہ توجہ دیتے ہیں)";
    }
    if (trait === 'Neuroticism') {
      return score >= 6 ? "You are sensitive and may easily feel stress in pressure situations. (آپ حساس ہیں اور دباؤ والے حالات میں پریشان ہو سکتے ہیں)" : "You are calm, emotionally stable, and handle stress very well. (آپ پرسکون رہتے ہیں اور مشکل حالات کا ڈٹ کر مقابلہ کرتے ہیں)";
    }
    return "";
  };

  const getAptitudeDescription = (aptitude, score) => {
    if (aptitude === 'Logic') {
      return score >= 60 ? "You are excellent at solving puzzles, finding patterns, and making logical decisions. (آپ مسائل حل کرنے اور منطقی فیصلے کرنے میں بہترین ہیں)" : "You rely more on intuition and experience rather than strict logic rules. (آپ اصولوں کے بجائے تجربے اور وجدان پر زیادہ انحصار کرتے ہیں)";
    }
    if (aptitude === 'Verbal') {
      return score >= 60 ? "You have strong communication skills and understand written or spoken information quickly. (آپ کی بات چیت کی مہارت بہترین ہے aur آپ جلدی بات سمجھ لیتے ہیں)" : "You prefer hands-on learning rather than reading long texts. (آپ لمبی تحریروں کے بجائے عملی کام سے زیادہ سیکھتے ہیں)";
    }
    if (aptitude === 'Spatial') {
      return score >= 60 ? "You are excellent at finding innovative, practical solutions to real-world challenges. (آپ عملی مسائل کے نئے اور منفرد حل تلاش کرنے میں بہترین ہیں)" : "You prefer standard, established methods over open-ended problem-solving. (آپ نئے حل تلاش کرنے کے بجائے قائم شدہ طریقوں کو ترجیح دیتے ہیں)";
    }
    if (aptitude === 'Math') {
      return score >= 60 ? "You are very comfortable with numbers, calculations, and data analysis. (آپ ریاضی اور اعداد و شمار کے حساب کتاب میں بہت اچھے ہیں)" : "You prefer creative or people-oriented tasks over numerical calculations. (آپ ریاضی کے حساب کے بجائے تخلیقی یا لوگوں سے جڑے کام پسند کرتے ہیں)";
    }
    return "";
  };

  const personalityTraits = session ? [
    { name: "Openness to Experience", score: session.student.Psych_Openness || 0, key: "Openness" },
    { name: "Discipline & Organization", score: session.student.Psych_Conscientiousness || 0, key: "Conscientiousness" },
    { name: "Social Energy", score: session.student.Psych_Extraversion || 0, key: "Extraversion" },
    { name: "Teamwork & Empathy", score: session.student.Psych_Agreeableness || 0, key: "Agreeableness" },
    { name: "Emotional Sensitivity", score: session.student.Psych_Neuroticism || 0, key: "Neuroticism" },
  ] : [];

  const aptitudes = session ? [
    { name: "Problem Solving (Logic)", score: session.student.Aptitude_Logic || 0, key: "Logic" },
    { name: "Communication (Verbal)", score: session.student.Aptitude_Verbal || 0, key: "Verbal" },
    { name: "Applied Problem-Solving", score: session.student.Aptitude_Spatial || 0, key: "Spatial" },
    { name: "Numbers & Data (Math)", score: session.student.Aptitude_Math || 0, key: "Math" },
  ] : [];

  const getSimpleExplanation = () => {
    if (!shapData || shapData.length === 0) return "Loading AI reasoning...";
    
    const topFactors = shapData.filter(d => d.value > 0).slice(0, 3).map(d => {
      let featureName = d.feature;
      // Make technical feature names simple
      if (featureName.includes("TFIDF_Interest") || featureName === "Interest Statement") return "your written passions";
      if (featureName.includes("TFIDF_Chat") || featureName === "Counseling Chat") return "your counseling chat inputs";
      if (featureName.includes("Psych_") || featureName === "Personality Profile") return "your personality traits";
      if (featureName.includes("Aptitude_") || featureName === "Aptitude Test") return "your problem-solving logic";
      if (featureName.includes("Marks_") || featureName === "Stream" || featureName === "Academic Stream" || featureName === "Academic Marks") return "your academic background";
      return featureName;
    });
    
    const uniqueFactors = [...new Set(topFactors)];
    
    return `The AI confidently matched you with ${primary.career} mostly because of ${uniqueFactors.join(" and ")}. These elements perfectly align with what this career requires!`;
  };

  const getCategoryContributions = () => {
    if (!shapData) return [];
    // Use abs_value (sum of |individual SHAP|) not Math.abs(d.value) (abs of net sum).
    // Net sum cancels opposing RIASEC features; abs_value correctly reflects total impact.
    let categories = { "Aptitude & Logic": 0, "Personality": 0, "Academics": 0, "Passions & Interests": 0 };
    shapData.forEach(d => {
      let val = d.abs_value != null ? d.abs_value : Math.abs(d.value);
      if (d.feature === "Aptitude Test" || d.feature.includes("Aptitude")) {
        categories["Aptitude & Logic"] += val;
      } else if (d.feature === "Personality Profile" || d.feature.includes("Psych")) {
        categories["Personality"] += val;
      } else if (d.feature === "Academic Stream" || d.feature === "Academic Marks" || d.feature.includes("Marks") || d.feature === "Stream") {
        categories["Academics"] += val;
      } else {
        categories["Passions & Interests"] += val;
      }
    });
    
    const COLORS = ['#00e5ff', '#8b5cf6', '#10b981', '#f43f5e'];
    return Object.keys(categories).map((k, i) => ({ 
      name: k, 
      value: categories[k],
      color: COLORS[i % COLORS.length]
    })).filter(d => d.value > 0);
  };

  const getProsAndCons = () => {
    if (!shapData) return { pros: [], cons: [] };
    
    const formatFeature = (f) => {
      if (f.includes("TFIDF_Interest") || f === "Interest Statement") return "Your personal interests and hobbies";
      if (f.includes("TFIDF_Chat") || f === "Counseling Chat") return "Your chat responses";
      if (f === "Academic Stream") return "Your academic stream";
      if (f === "Academic Marks") return "Your academic marks";
      if (f === "Aptitude Test") return "Your aptitude scores";
      if (f === "Personality Profile") return "Your personality profile";
      return f.replace(/_/g, " ");
    };

    return {
      pros: shapData.filter(d => d.value > 0).slice(0, 3).map(d => formatFeature(d.feature)),
      cons: shapData.filter(d => d.value < 0).slice(0, 2).map(d => formatFeature(d.feature))
    };
  };

  const formattedShapData = useMemo(() => {
    if (!shapData) return null;
    return shapData.map(d => {
      let readableName = d.feature.replace(/_/g, " ");
      if (d.feature.includes("TFIDF_Interest") || d.feature === "Interest Statement") readableName = "Interest Statement";
      if (d.feature.includes("TFIDF_Chat") || d.feature === "Counseling Chat") readableName = "Counseling Chat";
      // Use abs_value for bar chart height so opposing features don't cancel visually
      const displayValue = d.abs_value != null ? d.abs_value : Math.abs(d.value);
      return { ...d, readableFeature: readableName, displayValue };
    });
  }, [shapData]);

  // Normalize probabilities relative to the top-3 sum so they display as meaningful %
  // (raw softmax spreads across ~35 classes making numbers look artificially small)
  const top3ProbSum = recommendations.reduce((sum, r) => sum + (r.probability || 0), 0);
  const normPct = (prob) => top3ProbSum > 0 ? Math.round(((prob || 0) / top3ProbSum) * 100) : 0;
  const confidence = normPct(primary.probability);

  return (
    <div className="min-h-screen bg-dark text-white font-grotesk">
      <Navbar />

      <div className="pt-24 px-4 md:px-10 pb-12">
        <div className="max-w-7xl mx-auto space-y-8">
          <section className="bg-card-bg border border-primary-cyan/20 rounded-[36px] p-8 md:p-10 relative overflow-hidden">
            <div className="absolute -top-20 right-0 w-72 h-72 bg-primary-cyan/10 blur-[110px] rounded-full" />

            <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-8 relative z-10">
              <div className="max-w-3xl">
                <div className="inline-flex items-center gap-2 rounded-full border border-primary-cyan/20 bg-primary-cyan/10 px-4 py-2 text-sm text-primary-cyan mb-5">
                  <Sparkles size={16} />
                  Live FastAPI prediction
                </div>
                <h1 className="text-4xl md:text-5xl font-bold mb-3">{primary.career}</h1>
                <p className="text-lg text-text-gray leading-relaxed">
                  Analysis for{" "}
                  <span className="text-white font-semibold">
                    {session.studentName || session.student.name || "Student"}
                  </span>{" "}
                  using the {session.prediction.used_model} model flow.
                </p>
                <p className="text-text-gray mt-4 max-w-2xl">
                  {primary.description ||
                    "This recommendation is based on your academic profile, aptitude scores, psychometric inputs, and interest statement."}
                </p>
              </div>

              <div className="bg-dark/60 border border-primary-cyan/20 rounded-[28px] p-6 min-w-[250px]">
                <div className="flex items-center gap-2 text-primary-cyan mb-3">
                  <BarChart2 size={20} />
                  <span className="uppercase tracking-[0.24em] text-xs">Match confidence</span>
                </div>
                <div className="text-5xl font-bold mb-2">{confidence}%</div>
                <div className="text-text-gray text-sm">
                  Top recommendation from the backend prediction pipeline.
                </div>
              </div>
            </div>

            <div className="mt-8 flex flex-wrap gap-3 relative z-10">
              <Link
                to="/roadmap"
                state={{ career: primary.career }}
                className="inline-flex items-center gap-2 bg-primary-cyan text-dark font-bold px-6 py-3 rounded-2xl hover:bg-cyan-300 transition-colors"
              >
                View full roadmap
                <Route size={18} />
              </Link>
              <Link
                to="/chat"
                state={{ career: primary.career }}
                className="inline-flex items-center gap-2 border border-white/15 text-white font-bold px-6 py-3 rounded-2xl hover:bg-white/5 transition-colors"
              >
                Ask AI counselor
                <MessageSquareText size={18} />
              </Link>
              <button
                onClick={handleSave}
                disabled={saving}
                className="inline-flex items-center gap-2 border border-white/15 text-white font-bold px-4 py-3 rounded-2xl hover:bg-white/5 transition-colors disabled:opacity-50"
                title="Save session to SQLite Database"
              >
                <Save size={18} />
              </button>
              <button
                onClick={handleDownload}
                disabled={downloading}
                className="inline-flex items-center gap-2 border border-white/15 text-white font-bold px-4 py-3 rounded-2xl hover:bg-white/5 transition-colors disabled:opacity-50"
                title="Download PDF Report"
              >
                <Download size={18} />
              </button>
            </div>
          </section>

          <section className="flex flex-wrap gap-3">
            {tabs.map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`px-5 py-3 rounded-2xl border transition-colors ${
                  activeTab === tab
                    ? "border-primary-cyan bg-primary-cyan/10 text-primary-cyan"
                    : "border-white/10 text-text-gray hover:text-white hover:border-white/20"
                }`}
              >
                {tab}
              </button>
            ))}
          </section>

          {activeTab === "Overview" ? (
            <section className="grid lg:grid-cols-[1.1fr_0.9fr] gap-8">
              <div className="bg-card-bg border border-card-border rounded-[32px] p-8">
                <h2 className="text-2xl font-bold mb-6">Why this career stands out</h2>
                <div className="space-y-4">
                  {highlights.map((item) => (
                    <div
                      key={item}
                      className="flex items-start gap-3 bg-dark/60 border border-white/5 rounded-2xl p-4"
                    >
                      <CheckCircle className="text-accent-teal mt-1 shrink-0" size={18} />
                      <p className="text-text-gray leading-relaxed">{item}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-card-bg border border-card-border rounded-[32px] p-8">
                <h2 className="text-2xl font-bold mb-6">Student profile used</h2>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  {[
                    ["Stream", session.student.Stream],
                    ["FSc Marks", session.student.FSc_Marks],
                    ["Activity", session.student.Extracurricular_Activity],
                    ["Model", session.prediction.used_model],
                    ...(session.student.Stream === "Pre-Medical"
                      ? [
                          ["Biology", session.student.Marks_Biology !== -1 ? session.student.Marks_Biology : "—"],
                          ["Chemistry", session.student.Marks_Chemistry !== -1 ? session.student.Marks_Chemistry : "—"],
                          ["Physics", session.student.Marks_Physics !== -1 ? session.student.Marks_Physics : "—"],
                        ]
                      : session.student.Stream === "Pre-Engineering"
                      ? [
                          ["Mathematics", session.student.Marks_Math !== -1 ? session.student.Marks_Math : "—"],
                          ["Physics", session.student.Marks_Physics !== -1 ? session.student.Marks_Physics : "—"],
                          ["Chemistry", session.student.Marks_Chemistry !== -1 ? session.student.Marks_Chemistry : "—"],
                        ]
                      : session.student.Stream === "ICS"
                      ? [
                          ["Mathematics", session.student.Marks_Math !== -1 ? session.student.Marks_Math : "—"],
                          ["Physics", session.student.Marks_Physics !== -1 ? session.student.Marks_Physics : "—"],
                          ["Computer Science", session.student.Marks_Computer !== -1 ? session.student.Marks_Computer : "—"],
                        ]
                      : session.student.Stream === "Arts"
                      ? [
                          ["Mathematics", session.student.Marks_Math !== -1 ? session.student.Marks_Math : "—"],
                        ]
                      : []),
                  ].map(([label, value]) => (
                    <div key={label} className="bg-dark/60 border border-white/5 rounded-2xl p-4">
                      <p className="text-text-gray mb-2">{label}</p>
                      <p className="font-semibold text-white">{value}</p>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          ) : null}

          {activeTab === "Overview" ? (
            <>
              <section className="bg-card-bg border border-card-border rounded-[32px] p-8 mb-8">
                <div className="flex items-center gap-3 mb-6">
                  <Sparkles className="text-accent-teal" size={24} />
                  <h2 className="text-2xl font-bold">Your Natural Talents (Aptitude)</h2>
                </div>
                <p className="text-text-gray mb-8">
                  This shows your strongest mental abilities. These talents naturally match the requirements of {primary.career}.
                </p>
                <div className="grid md:grid-cols-2 gap-6">
                  {aptitudes.map((apt) => (
                    <div key={apt.name} className="bg-dark/60 border border-white/5 rounded-2xl p-6 hover:border-accent-teal/30 transition-colors">
                      <div className="flex justify-between items-center mb-4">
                        <span className="font-bold text-white text-lg">{apt.name}</span>
                        <span className="text-accent-teal font-bold">{apt.score}%</span>
                      </div>
                      <div className="h-2.5 w-full bg-white/10 rounded-full mb-4 overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-accent-teal to-primary-cyan rounded-full" 
                          style={{ width: `${apt.score}%` }}
                        ></div>
                      </div>
                      <p className="text-text-gray text-sm leading-relaxed">
                        {getAptitudeDescription(apt.key, apt.score)}
                      </p>
                    </div>
                  ))}
                </div>
              </section>

              <section className="bg-card-bg border border-card-border rounded-[32px] p-8">
                <div className="flex items-center gap-3 mb-6">
                  <Sparkles className="text-primary-cyan" size={24} />
                  <h2 className="text-2xl font-bold">Your Personality Profile</h2>
                </div>
                <p className="text-text-gray mb-8">
                  We translated your psychology test scores into simple, non-technical insights to help you understand your unique strengths better.
                </p>
                <div className="grid md:grid-cols-2 gap-6">
                  {personalityTraits.map((trait) => (
                    <div key={trait.name} className="bg-dark/60 border border-white/5 rounded-2xl p-6 hover:border-primary-cyan/30 transition-colors">
                      <div className="flex justify-between items-center mb-4">
                        <span className="font-bold text-white text-lg">{trait.name}</span>
                        <span className="text-primary-cyan font-bold">{Math.round(trait.score * 10)}%</span>
                      </div>
                      {/* Progress Bar */}
                      <div className="h-2.5 w-full bg-white/10 rounded-full mb-4 overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-primary-cyan to-accent-teal rounded-full" 
                          style={{ width: `${trait.score * 10}%` }}
                        ></div>
                      </div>
                      <p className="text-text-gray text-sm leading-relaxed">
                        {getPersonalityDescription(trait.key, trait.score)}
                      </p>
                    </div>
                  ))}
                </div>
              </section>
            </>
          ) : null}

          {activeTab === "Aptitude Diagnostic" ? (
            <div className="space-y-8">
              {/* Score Chart Comparison Card */}
              <section className="bg-card-bg border border-card-border rounded-[32px] p-8">
                <div className="flex flex-col lg:flex-row gap-8 items-center">
                  <div className="w-full lg:w-1/2 space-y-4">
                    <div className="flex items-center gap-3">
                      <BarChart2 className="text-primary-cyan" size={24} />
                      <h2 className="text-2xl font-bold">Aptitude Score Breakdown</h2>
                    </div>
                    <p className="text-text-gray text-sm leading-relaxed">
                      Your cognitive profile is evaluated across 4 domains. We highlight your weakest area in <span className="text-red-400 font-semibold">Red</span> and suggest tailored improvement strategies to support your career alignment.
                    </p>
                    <div className="p-4 rounded-2xl bg-white/5 border border-white/5 flex items-center gap-4">
                      <div className="p-3 rounded-xl bg-red-500/10 text-red-400">
                        <AlertTriangle size={24} />
                      </div>
                      <div>
                        <p className="text-xs uppercase tracking-wider text-text-gray">Identified Weakness</p>
                        <p className="text-lg font-bold text-white">{weakest_cat === "Spatial" ? "Applied Problem-Solving" : weakest_cat} Reasoning ({session?.student?.[`Aptitude_${weakest_cat}`] || 50}%)</p>
                      </div>
                    </div>
                  </div>
                  <div className="w-full lg:w-1/2 bg-dark/40 border border-white/5 rounded-2xl p-6">
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart
                        data={[
                          { name: "Logic", Score: session?.student?.Aptitude_Logic || 50, isWeak: weakest_cat === "Logic" },
                          { name: "Math", Score: session?.student?.Aptitude_Math || 50, isWeak: weakest_cat === "Math" },
                          { name: "Verbal", Score: session?.student?.Aptitude_Verbal || 50, isWeak: weakest_cat === "Verbal" },
                          { name: "Applied Problem-Solving", Score: session?.student?.Aptitude_Spatial || 50, isWeak: weakest_cat === "Spatial" },
                        ]}
                        layout="vertical"
                        margin={{ top: 10, right: 30, left: 10, bottom: 5 }}
                      >
                        <XAxis type="number" domain={[0, 100]} stroke="#6b7280" fontSize={11} />
                        <YAxis dataKey="name" type="category" stroke="#6b7280" fontSize={11} width={60} />
                        <Tooltip
                          contentStyle={{ backgroundColor: "#060f14", borderColor: "#ffffff10", borderRadius: "12px", color: "#fff" }}
                          cursor={{ fill: "rgba(255,255,255,0.05)" }}
                        />
                        <Bar dataKey="Score" radius={[0, 6, 6, 0]} barSize={20}>
                          {[
                            weakest_cat === "Logic",
                            weakest_cat === "Math",
                            weakest_cat === "Verbal",
                            weakest_cat === "Spatial",
                          ].map((isWeak, idx) => (
                            <Cell key={`cell-${idx}`} fill={isWeak ? "#f43f5e" : "#00e5ff"} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </section>

              {/* API Load / Spinner */}
              {diagnosticLoading && (
                <div className="flex flex-col items-center justify-center py-20 bg-card-bg border border-card-border rounded-[32px] space-y-4">
                  <RefreshCw className="animate-spin text-primary-cyan" size={40} />
                  <p className="text-text-gray font-medium">Generating weakness diagnostics & sample questions using AI...</p>
                </div>
              )}

              {/* Error Callout */}
              {diagnosticError && !diagnosticLoading && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-[32px] p-8 text-center space-y-4">
                  <AlertTriangle className="text-red-400 mx-auto" size={40} />
                  <p className="text-white font-medium">{diagnosticError}</p>
                  <button
                    onClick={() => {
                      setDiagnostic(null);
                      setDiagnosticError("");
                    }}
                    className="px-6 py-2.5 bg-red-500 text-white rounded-xl hover:bg-red-600 transition-colors font-semibold"
                  >
                    Retry Loading Report
                  </button>
                </div>
              )}

              {/* Main Diagnostic Data */}
              {diagnostic && !diagnosticLoading && (
                <div className="grid lg:grid-cols-[1fr_1.2fr] gap-8">
                  {/* Left Column: Analysis & Improvement Tips */}
                  <div className="space-y-8">
                    <section className="bg-card-bg border border-card-border rounded-[32px] p-8 relative overflow-hidden">
                      <div className="absolute top-0 left-0 w-2.5 h-full bg-red-500" />
                      <div className="flex items-center gap-3 mb-4">
                        <Brain className="text-red-400" size={24} />
                        <h3 className="text-xl font-bold">AI Performance Critique</h3>
                      </div>
                      <p className="text-white leading-relaxed text-base">
                        {diagnostic.analysis}
                      </p>
                    </section>

                    <section className="bg-card-bg border border-card-border rounded-[32px] p-8">
                      <div className="flex items-center gap-3 mb-6">
                        <Compass className="text-accent-teal" size={24} />
                        <h3 className="text-xl font-bold">Actionable Improvement Tips</h3>
                      </div>
                      <div className="space-y-4">
                        {diagnostic.improvement_tips?.map((tip, idx) => (
                          <div key={idx} className="flex gap-4 bg-dark/40 border border-white/5 rounded-2xl p-4">
                            <span className="flex items-center justify-center w-8 h-8 rounded-full bg-accent-teal/10 text-accent-teal font-bold text-sm shrink-0">
                              {idx + 1}
                            </span>
                            <p className="text-text-gray leading-relaxed text-sm">{tip}</p>
                          </div>
                        ))}
                      </div>
                    </section>
                  </div>

                  {/* Right Column: Interactive Practice Quiz */}
                  <section className="bg-card-bg border border-card-border rounded-[32px] p-8 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between mb-6 border-b border-white/5 pb-4">
                        <div className="flex items-center gap-3">
                          <HelpCircle className="text-primary-cyan" size={24} />
                          <h3 className="text-xl font-bold">Concept Practice Exercises</h3>
                        </div>
                        <span className="text-xs px-3 py-1 rounded-full bg-primary-cyan/10 text-primary-cyan font-mono">
                          Topic: {weakest_cat === "Spatial" ? "Applied Problem-Solving" : weakest_cat}
                        </span>
                      </div>

                      <div className="space-y-8">
                        {diagnostic.practice_questions?.map((q, qIdx) => {
                          const chosen = quizAnswers[q.id || qIdx];
                          const isCorrect = chosen === q.correct_answer;
                          const showExp = showExplanations[q.id || qIdx];

                          return (
                            <div key={q.id || qIdx} className="space-y-4">
                              <div className="flex gap-3">
                                <span className="font-mono text-primary-cyan text-sm mt-0.5 font-bold">Q{qIdx + 1}.</span>
                                <p className="text-white font-medium text-sm leading-relaxed">{q.question}</p>
                              </div>

                              <div className="grid sm:grid-cols-2 gap-3 pl-6">
                                {q.options?.map((option) => {
                                  const isOptionChosen = chosen === option;
                                  const isOptionCorrect = option === q.correct_answer;

                                  let btnClass = "border-white/10 hover:border-white/20 bg-white/5 text-white/80";
                                  if (chosen) {
                                    if (isOptionCorrect) {
                                      btnClass = "border-emerald-500 bg-emerald-500/20 text-emerald-400 font-semibold";
                                    } else if (isOptionChosen) {
                                      btnClass = "border-red-500 bg-red-500/20 text-red-400 font-semibold";
                                    } else {
                                      btnClass = "border-white/5 bg-white/0 opacity-60 text-white/40 cursor-not-allowed";
                                    }
                                  }

                                  return (
                                    <button
                                      key={option}
                                      disabled={!!chosen}
                                      onClick={() => {
                                        setQuizAnswers(prev => ({ ...prev, [q.id || qIdx]: option }));
                                      }}
                                      className={`w-full text-left px-4 py-3 rounded-xl border text-sm transition-all flex items-center justify-between ${btnClass}`}
                                    >
                                      <span>{option}</span>
                                      {chosen && isOptionCorrect && <Check size={16} className="text-emerald-400 shrink-0" />}
                                    </button>
                                  );
                                })}
                              </div>

                              {chosen && (
                                <div className="pl-6">
                                  <button
                                    onClick={() => {
                                      setShowExplanations(prev => ({ ...prev, [q.id || qIdx]: !showExp }));
                                    }}
                                    className="text-xs text-primary-cyan hover:underline flex items-center gap-1"
                                  >
                                    {showExp ? "Hide logical explanation" : "Show logical explanation"}
                                  </button>
                                  {showExp && (
                                    <div className="mt-3 p-4 rounded-xl bg-white/5 border border-white/5 text-xs text-text-gray leading-relaxed">
                                      <p className="font-semibold text-white mb-1">Explanation:</p>
                                      {q.explanation}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    <div className="mt-8 pt-6 border-t border-white/5 flex flex-col sm:flex-row gap-4 items-center justify-between">
                      <p className="text-xs text-text-gray">
                        Answer all questions to unlock the explanations and verify your reasoning.
                      </p>
                      <button
                        onClick={() => {
                          setQuizAnswers({});
                          setShowExplanations({});
                          setDiagnostic(null);
                        }}
                        className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary-cyan/10 border border-primary-cyan/20 text-primary-cyan hover:bg-primary-cyan/25 transition-all text-xs font-semibold"
                      >
                        <RefreshCw size={14} />
                        Get Fresh Practice Questions
                      </button>
                    </div>
                  </section>
                </div>
              )}
            </div>
          ) : null}

          {activeTab === "Top Matches" ? (
            <section className="grid md:grid-cols-3 gap-6">
              {recommendations.map((item) => (
                <article
                  key={item.career}
                  className="bg-card-bg border border-card-border rounded-[28px] p-6 flex flex-col"
                >
                  <div className="flex items-center justify-between mb-5">
                    <span className="text-sm uppercase tracking-[0.25em] text-primary-cyan">
                      Rank {item.rank}
                    </span>
                    <span className="text-xl font-bold">{normPct(item.probability)}%</span>
                  </div>
                  <h3 className="text-2xl font-bold mb-3">{item.career}</h3>
                  <p className="text-text-gray leading-relaxed mb-5">
                    {item.description || "No description available in the roadmap dataset."}
                  </p>
                  <div className="mt-auto">
                    <p className="text-xs uppercase tracking-[0.25em] text-text-gray mb-2">Key skills</p>
                    <div className="flex flex-wrap gap-2">
                      {(item.skills_required || []).slice(0, 4).map((skill) => (
                        <span
                          key={skill}
                          className="px-3 py-1 rounded-full bg-primary-cyan/10 text-primary-cyan text-xs"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                </article>
              ))}
            </section>
          ) : null}

          {activeTab === "Action Plan" ? (
            <section className="grid lg:grid-cols-[1fr_1fr] gap-8">
              <div className="bg-card-bg border border-card-border rounded-[32px] p-8">
                <h2 className="text-2xl font-bold mb-6">Roadmap preview</h2>
                <div className="space-y-4">
                  {(primary.roadmap_steps || []).map((step) => (
                    <div
                      key={step}
                      className="bg-dark/60 border border-white/5 rounded-2xl px-4 py-4 text-text-gray"
                    >
                      {step}
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-card-bg border border-card-border rounded-[32px] p-8">
                <h2 className="text-2xl font-bold mb-6">Best next moves</h2>
                <div className="space-y-5 text-text-gray">
                  <div>
                    <p className="text-sm uppercase tracking-[0.25em] text-accent-teal mb-2">
                      Skills to strengthen
                    </p>
                    <p>{(primary.skills_required || []).join(", ") || "No skills listed yet."}</p>
                  </div>
                  <div>
                    <p className="text-sm uppercase tracking-[0.25em] text-accent-teal mb-2">
                      Universities to explore
                    </p>
                    <p>{(primary.top_universities || []).join(", ") || "No universities listed yet."}</p>
                  </div>
                  <div className="pt-2">
                    <Link
                      to="/roadmap"
                      state={{ career: primary.career }}
                      className="inline-flex items-center gap-2 text-primary-cyan font-semibold hover:text-cyan-300"
                    >
                      Open the full roadmap page
                      <ArrowRight size={18} />
                    </Link>
                  </div>
                </div>
              </div>
            </section>
          ) : null}

          {activeTab === "Explainability (XAI)" ? (
            <div className="space-y-8">
              {/* Highlight AI Explanation */}
              <section className="bg-gradient-to-r from-primary-cyan/20 to-accent-teal/10 border border-primary-cyan/30 rounded-[32px] p-8 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-8 opacity-20">
                  <Sparkles size={120} />
                </div>
                <h2 className="text-3xl font-bold mb-4 text-white">Why did the AI choose {primary.career}?</h2>
                <p className="text-lg text-white/90 leading-relaxed max-w-3xl relative z-10">
                  {getSimpleExplanation()}
                </p>
              </section>

              {/* Pros, Cons, and Weighting Chart */}
              <section className="grid lg:grid-cols-[1fr_1fr] gap-8">
                
                {/* Pros and Cons */}
                <div className="bg-card-bg border border-card-border rounded-[32px] p-8 flex flex-col justify-center">
                  <h2 className="text-2xl font-bold mb-6">Alignment Breakdown</h2>
                  
                  <div className="mb-6">
                    <div className="flex items-center gap-2 text-[#10b981] mb-3">
                      <ThumbsUp size={20} />
                      <h3 className="font-bold text-lg">Strongest Alignments</h3>
                    </div>
                    <ul className="space-y-2">
                      {getProsAndCons().pros.map((pro, i) => (
                        <li key={i} className="flex items-center gap-3 text-text-gray bg-[#10b981]/10 px-4 py-2 rounded-xl">
                          <div className="w-2 h-2 rounded-full bg-[#10b981]"></div>
                          {pro}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <div className="flex items-center gap-2 text-[#f43f5e] mb-3">
                      <AlertTriangle size={20} />
                      <h3 className="font-bold text-lg">Potential Challenges</h3>
                    </div>
                    <ul className="space-y-2">
                      {getProsAndCons().cons.length > 0 ? getProsAndCons().cons.map((con, i) => (
                        <li key={i} className="flex items-center gap-3 text-text-gray bg-[#f43f5e]/10 px-4 py-2 rounded-xl">
                          <div className="w-2 h-2 rounded-full bg-[#f43f5e]"></div>
                          {con} (May need improvement)
                        </li>
                      )) : (
                        <li className="text-text-gray italic px-4">No major challenges detected by the model!</li>
                      )}
                    </ul>
                  </div>
                </div>

                {/* Donut Chart: Decision Weights */}
                <div className="bg-card-bg border border-card-border rounded-[32px] p-8">
                  <div className="flex items-center gap-3 mb-2">
                    <PieChartIcon className="text-primary-cyan" size={24} />
                    <h2 className="text-2xl font-bold">What influenced the decision?</h2>
                  </div>
                  <p className="text-sm text-text-gray mb-4">A visual breakdown of how much each area contributed to the final prediction.</p>
                  
                  {shapData ? (
                    <div className="h-[280px] w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={getCategoryContributions()}
                            cx="50%"
                            cy="50%"
                            innerRadius={70}
                            outerRadius={100}
                            paddingAngle={5}
                            dataKey="value"
                            stroke="none"
                          >
                            {getCategoryContributions().map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Pie>
                          <Tooltip 
                            formatter={(value) => value.toFixed(2)} 
                            contentStyle={{ backgroundColor: '#0d1117', borderColor: '#30363d', borderRadius: '12px' }} 
                          />
                          <Legend verticalAlign="bottom" height={36} iconType="circle" />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div className="h-[280px] flex items-center justify-center text-text-gray">
                      Analyzing contributions...
                    </div>
                  )}
                </div>

              </section>

              {/* Technical Charts */}
              <section className="grid lg:grid-cols-2 gap-8">
                <div className="bg-card-bg border border-card-border rounded-[32px] p-8 flex flex-col">
                  <h2 className="text-2xl font-bold mb-2">Skill Radar Analysis</h2>
                  <p className="text-sm text-text-gray mb-6">Visualizing your Aptitude & Personality traits</p>
                  
                  {/* Radar Help Text */}
                  <div className="bg-dark/40 border border-white/5 rounded-xl p-3 mb-4 flex items-start gap-3">
                    <div className="text-primary-cyan mt-0.5">ℹ️</div>
                    <p className="text-xs text-text-gray leading-relaxed">
                      <strong>How to read this:</strong> The blue shape represents your profile. The further it stretches towards an edge (like "Logic" or "Math"), the stronger your natural ability is in that specific area.
                    </p>
                  </div>

                  <div className="h-[260px] w-full mt-auto">
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart cx="50%" cy="50%" outerRadius="70%" data={[
                        { subject: 'Logic', A: session.student.Aptitude_Logic, fullMark: 100 },
                        { subject: 'Math', A: session.student.Aptitude_Math, fullMark: 100 },
                        { subject: 'Applied Problem-Solving', A: session.student.Aptitude_Spatial, fullMark: 100 },
                        { subject: 'Verbal', A: session.student.Aptitude_Verbal, fullMark: 100 },
                        { subject: 'Openness', A: session.student.Psych_Openness * 10, fullMark: 100 },
                        { subject: 'Extraversion', A: session.student.Psych_Extraversion * 10, fullMark: 100 },
                      ]}>
                        <PolarGrid stroke="#ffffff33" />
                        <PolarAngleAxis dataKey="subject" tick={{ fill: '#8b949e', fontSize: 12 }} />
                        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                        <Radar name="Student" dataKey="A" stroke="#00e5ff" fill="#00e5ff" fillOpacity={0.3} />
                        <Tooltip contentStyle={{ backgroundColor: '#0d1117', borderColor: '#30363d', borderRadius: '8px' }} />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="bg-card-bg border border-card-border rounded-[32px] p-8 flex flex-col">
                  <h2 className="text-2xl font-bold mb-2">Detailed Feature Impact</h2>
                  <p className="text-sm text-text-gray mb-6">Advanced view: How specific metrics moved the needle</p>
                  
                  {/* Bar Chart Help Legend */}
                  <div className="bg-dark/40 border border-white/5 rounded-xl p-3 mb-4 flex flex-col gap-2">
                    <p className="text-xs text-text-gray mb-1"><strong>How to read this chart:</strong></p>
                    <div className="flex items-center gap-4 text-xs">
                      <div className="flex items-center gap-1.5">
                        <div className="w-3 h-3 bg-[#10b981] rounded-sm"></div>
                        <span className="text-white">Pushed Towards Match</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <div className="w-3 h-3 bg-[#f43f5e] rounded-sm"></div>
                        <span className="text-white">Pushed Away</span>
                      </div>
                    </div>
                  </div>

                  {formattedShapData ? (
                    <div className="h-[260px] w-full mt-auto">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart layout="vertical" data={formattedShapData} margin={{ top: 0, right: 30, left: 30, bottom: 0 }}>
                          <XAxis type="number" hide />
                          <YAxis dataKey="readableFeature" type="category" axisLine={false} tickLine={false} tick={{ fill: '#c9d1d9', fontSize: 12 }} width={120} />
                          <Tooltip 
                            cursor={{ fill: '#ffffff10' }} 
                            contentStyle={{ backgroundColor: '#0d1117', borderColor: '#30363d', color: '#fff', borderRadius: '8px' }} 
                            formatter={(val, name, props) => {
                              const direction = props.payload?.direction || (props.payload?.value >= 0 ? 'supports' : 'reduces');
                              return [`${val.toFixed(3)} (${direction})`, 'Impact'];
                            }}
                          />
                          <Bar dataKey="displayValue" radius={[0, 4, 4, 0]} barSize={20}>
                            {formattedShapData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.value >= 0 ? "#10b981" : "#f43f5e"} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div className="h-[260px] flex items-center justify-center text-text-gray mt-auto">
                      Calculating Explainability...
                    </div>
                  )}
                </div>
              </section>
            </div>
          ) : null}

          {activeTab === "Action Plan" ? (
            <section className="bg-card-bg border border-card-border rounded-[32px] p-8 md:p-10 text-center">
              <div className="w-20 h-20 bg-primary-cyan/10 rounded-full flex items-center justify-center mx-auto mb-6">
                <Route className="text-primary-cyan" size={32} />
              </div>
              <h2 className="text-3xl font-bold mb-4">Ready to start?</h2>
              <p className="text-text-gray text-lg max-w-2xl mx-auto leading-relaxed mb-8">
                Your next step is viewing the step-by-step educational pathway to become a{" "}
                <span className="text-white font-semibold">{primary.career}</span>.
              </p>
              <Link
                to="/roadmap"
                state={{ career: primary.career }}
                className="inline-flex items-center gap-2 bg-gradient-to-r from-primary-cyan to-accent-teal text-dark font-bold px-8 py-4 rounded-2xl shadow-[0_12px_30px_rgba(0,229,255,0.18)] hover:scale-[1.02] transition-transform"
              >
                Open Full Roadmap
                <ArrowRight size={20} />
              </Link>
            </section>
          ) : null}

          {/* ── MARKET TRENDS TAB ─────────────────────────────────────────────── */}
          {activeTab === "Market Trends" ? (
            <MarketTrendsPanel
              career={primary?.career}
              marketData={marketData}
              setMarketData={setMarketData}
              marketLoading={marketLoading}
              setMarketLoading={setMarketLoading}
              marketFetched={marketFetched}
              setMarketFetched={setMarketFetched}
            />
          ) : null}

          {/* ── SAVED BOOKMARKS & SCORES TAB ──────────────────────────────────── */}
          {activeTab === "Saved Bookmarks & Scores" ? (
            <div className="space-y-8 animate-fadeIn">
              <div className="grid lg:grid-cols-2 gap-8">
                
                {/* LEFT: Bookmarked Resources */}
                <section className="bg-card-bg border border-card-border rounded-[32px] p-8 flex flex-col h-[70vh]">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="p-3 rounded-2xl bg-primary-cyan/10 text-primary-cyan flex items-center justify-center shrink-0">
                      <Bookmark size={24} />
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold">Saved Resources</h2>
                      <p className="text-xs text-text-gray">Suggested courses, videos, and articles saved for your career path</p>
                    </div>
                  </div>

                  {scoresLoading ? (
                    <div className="flex-1 flex flex-col items-center justify-center space-y-3">
                      <RefreshCw className="animate-spin text-primary-cyan" size={32} />
                      <p className="text-text-gray text-sm">Loading your bookmarked resources...</p>
                    </div>
                  ) : savedResources.length === 0 ? (
                    <div className="flex-1 flex flex-col items-center justify-center border-2 border-dashed border-white/5 rounded-2xl p-6 text-center">
                      <p className="text-text-gray text-sm">You haven't bookmarked any resources yet.</p>
                      <p className="text-xs text-text-gray/70 mt-2">
                        Use the Chat Assistant to ask about courses, scholarships, and roadmaps, and click the 🔖 badge next to links to save them.
                      </p>
                    </div>
                  ) : (
                    <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
                      {savedResources.map((res) => (
                        <div key={res.id} className="bg-dark/40 border border-white/5 hover:border-accent-teal/50 rounded-2xl p-4 transition-all">
                          <div className="flex justify-between items-start gap-2">
                            <div>
                              <span className="inline-block text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-accent-teal/10 text-accent-teal font-bold mb-2">
                                {res.resource_type || "Resource"}
                              </span>
                              <h3 className="font-bold text-white text-sm md:text-base leading-snug">
                                {res.title}
                              </h3>
                            </div>
                            <a
                              href={res.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs font-semibold px-4 py-2 rounded-xl bg-primary-cyan text-dark hover:bg-cyan-300 transition-colors shrink-0"
                            >
                              Open Link
                            </a>
                          </div>
                          <p className="text-[11px] text-text-gray/80 mt-2 truncate bg-black/20 p-2 rounded-lg border border-white/5">
                            {res.url}
                          </p>
                          {res.saved_at && (
                            <span className="text-[10px] text-text-gray/50 block mt-2">
                              Saved on {new Date(res.saved_at).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </section>

                {/* RIGHT: Entry Test Scores & Add Form */}
                <div className="space-y-8 flex flex-col h-[70vh]">
                  {/* Scores List */}
                  <section className="bg-card-bg border border-card-border rounded-[32px] p-8 flex flex-col flex-1 min-h-0">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="p-3 rounded-2xl bg-accent-teal/10 text-accent-teal flex items-center justify-center shrink-0">
                        <Award size={24} />
                      </div>
                      <div>
                        <h2 className="text-2xl font-bold">Entry & Aptitude Scores</h2>
                        <p className="text-xs text-text-gray">Academic metrics and aptitude sub-test results</p>
                      </div>
                    </div>

                    {scoresLoading ? (
                      <div className="flex-1 flex flex-col items-center justify-center space-y-3">
                        <RefreshCw className="animate-spin text-accent-teal" size={32} />
                        <p className="text-text-gray text-sm">Loading your scores...</p>
                      </div>
                    ) : entryTestScores.length === 0 ? (
                      <div className="flex-1 flex flex-col items-center justify-center border-2 border-dashed border-white/5 rounded-2xl p-6 text-center">
                        <p className="text-text-gray text-sm">No score records found in database.</p>
                      </div>
                    ) : (
                      <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar space-y-3">
                        <table className="w-full text-left text-xs border-collapse">
                          <thead>
                            <tr className="border-b border-white/10 text-text-gray">
                              <th className="py-2">Type</th>
                              <th className="py-2">Subject / Test</th>
                              <th className="py-2 text-right">Obtained</th>
                              <th className="py-2 text-right">Total</th>
                              <th className="py-2 text-right">Percentage</th>
                            </tr>
                          </thead>
                          <tbody>
                            {entryTestScores.map((score, index) => {
                              const pct = score.total > 0 ? (score.score / score.total * 100).toFixed(1) : "N/A";
                              const isAptitude = score.test_type === "Aptitude";
                              return (
                                <tr key={score.id || index} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                                  <td className="py-3 pr-2">
                                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                      isAptitude ? "bg-primary-cyan/10 text-primary-cyan" : "bg-purple-500/10 text-purple-300"
                                    }`}>
                                      {score.test_type}
                                    </span>
                                  </td>
                                  <td className="py-3 font-semibold text-white">{score.subject}</td>
                                  <td className="py-3 text-right font-medium text-white">
                                    {score.score !== null && score.score !== undefined ? score.score : "-"}
                                  </td>
                                  <td className="py-3 text-right text-text-gray">{score.total}</td>
                                  <td className="py-3 text-right font-bold text-accent-teal">
                                    {score.score !== null && score.score !== undefined ? `${pct}%` : "Pending"}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </section>

                  {/* Add New Score Card */}
                  <section className="bg-card-bg border border-card-border rounded-[32px] p-8 shrink-0">
                    <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                      <span className="text-primary-cyan text-sm">✦</span> Record Admission / Practice Test Score
                    </h3>
                    <form onSubmit={handleAddScore} className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-[11px] text-text-gray mb-1">Test Type</label>
                          <select
                            value={newScoreType}
                            onChange={(e) => setNewScoreType(e.target.value)}
                            className="w-full bg-dark border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:border-primary-cyan outline-none"
                          >
                            <option value="Admission Test">Admission Test (e.g. ECAT/MDCAT)</option>
                            <option value="Aptitude">Cognitive Aptitude Test</option>
                            <option value="Academic">Academic Exam Marks</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-[11px] text-text-gray mb-1">Subject / Test Name</label>
                          <input
                            type="text"
                            placeholder="e.g. ECAT Math, MDCAT Physics"
                            value={newScoreSubject}
                            onChange={(e) => setNewScoreSubject(e.target.value)}
                            className="w-full bg-dark border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:border-primary-cyan outline-none"
                            required
                          />
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-[11px] text-text-gray mb-1">Obtained Score</label>
                          <input
                            type="number"
                            step="any"
                            placeholder="e.g. 320"
                            value={newScoreValue}
                            onChange={(e) => setNewScoreValue(e.target.value)}
                            className="w-full bg-dark border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:border-primary-cyan outline-none"
                            required
                          />
                        </div>
                        <div>
                          <label className="block text-[11px] text-text-gray mb-1">Total Marks</label>
                          <input
                            type="number"
                            step="any"
                            placeholder="e.g. 400"
                            value={newScoreTotal}
                            onChange={(e) => setNewScoreTotal(e.target.value)}
                            className="w-full bg-dark border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:border-primary-cyan outline-none"
                            required
                          />
                        </div>
                      </div>
                      <button
                        type="submit"
                        disabled={savingScore}
                        className="w-full py-2.5 rounded-xl bg-gradient-to-r from-primary-cyan to-accent-teal text-dark font-bold text-xs hover:shadow-[0_0_10px_rgba(0,229,255,0.4)] transition-all disabled:opacity-50"
                      >
                        {savingScore ? "Saving Score..." : "Save Test Score"}
                      </button>
                    </form>
                  </section>
                </div>

              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};

// ── Market Trends Panel Component ─────────────────────────────────────────────
const MarketTrendsPanel = ({ career, marketData, setMarketData, marketLoading, setMarketLoading, marketFetched, setMarketFetched }) => {
  const loadMarket = useCallback(async (forceRefresh = false) => {
    if (!career) return;
    setMarketLoading(true);
    try {
      const data = await fetchMarketTrends(career, forceRefresh);
      setMarketData(data);
      setMarketFetched(true);
    } catch (e) {
      console.error("Market trends error:", e);
    } finally {
      setMarketLoading(false);
    }
  }, [career, setMarketData, setMarketLoading, setMarketFetched]);

  useEffect(() => {
    if (!marketFetched) loadMarket(false);
  }, [marketFetched, loadMarket]);

  // Safe helper to convert PKR ranges into average numeric values for Recharts
  const getSalaryAvg = (salaryStr) => {
    if (!salaryStr) return 0;
    const cleanStr = salaryStr.replace(/,/g, "");
    const matches = cleanStr.match(/\d+/g);
    if (!matches) return 0;
    const vals = matches.map(Number);
    if (vals.length === 2) return Math.round((vals[0] + vals[1]) / 2);
    return vals[0] || 0;
  };

  const chartData = useMemo(() => {
    if (!marketData) return [];
    return [
      {
        name: "Entry Level",
        salary: getSalaryAvg(marketData.entry_salary_pkr),
        display: marketData.entry_salary_pkr,
      },
      {
        name: "Mid Level",
        salary: getSalaryAvg(marketData.mid_salary_pkr),
        display: marketData.mid_salary_pkr,
      },
      {
        name: "Senior Level",
        salary: getSalaryAvg(marketData.senior_salary_pkr),
        display: marketData.senior_salary_pkr,
      },
    ];
  }, [marketData]);

  // Gender Representation Data for Recharts Pie Chart
  const genderData = useMemo(() => {
    if (!marketData?.gender_representation) return [];
    const gr = marketData.gender_representation;
    return [
      { name: "Male", value: gr.male_percentage || 50, color: "#00e5ff" },
      { name: "Female", value: gr.female_percentage || 50, color: "#ec4899" },
    ];
  }, [marketData]);

  const competitionColor = (c) => ({
    "Low": "#10b981", "Medium": "#f59e0b", "High": "#f43f5e", "Very High": "#dc2626"
  }[c] || "#6b7280");

  const remoteBadge = (r) => ({
    "Yes": { label: "Remote Friendly", color: "#10b981" },
    "Partial": { label: "Hybrid / Partial Remote", color: "#f59e0b" },
    "No": { label: "On-site Only", color: "#f43f5e" },
  }[r] || { label: r || "Unknown", color: "#6b7280" });

  const formatPKR = (num) => {
    if (!num) return "0";
    return num >= 100000 ? `${(num / 100000).toFixed(1)} Lakh` : `${(num / 1000).toFixed(0)}K`;
  };

  return (
    <section className="space-y-6">
      {/* Header */}
      <div className="bg-card-bg border border-primary-cyan/20 rounded-[32px] p-8 relative overflow-hidden">
        <div className="absolute -top-16 right-0 w-64 h-64 bg-primary-cyan/8 blur-[100px] rounded-full" />
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-primary-cyan/20 bg-primary-cyan/10 px-4 py-2 text-sm text-primary-cyan mb-4">
              <TrendingUp size={15} />
              Pakistan Live Job Market Info
            </div>
            <h2 className="text-2xl font-bold mb-1">Pakistan Industry Demand & Salary Tracker</h2>
            <p className="text-text-gray text-sm">
              Real-time analysis for <span className="text-white font-semibold">{career}</span> using live search and AI extraction.
            </p>
            {marketData && (
              <div className="mt-3 flex items-center gap-2">
                <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${
                  marketData.cache_status === "live"
                    ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/20"
                    : "bg-yellow-500/15 text-yellow-400 border border-yellow-500/20"
                }`}>
                  <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
                  {marketData.cache_status === "live" ? "Live Data — Just Fetched" : `Cached (${marketData.cache_age_days} day${marketData.cache_age_days !== 1 ? 's' : ''} ago)`}
                </span>
                <span className="text-xs text-text-gray">{marketData.data_source}</span>
              </div>
            )}
          </div>
          <button
            onClick={() => loadMarket(true)}
            disabled={marketLoading}
            className="flex items-center gap-2 border border-white/15 text-white font-medium px-4 py-2.5 rounded-2xl hover:bg-white/5 transition-colors disabled:opacity-50 text-sm whitespace-nowrap"
          >
            <RefreshCw size={15} className={marketLoading ? "animate-spin" : ""} />
            {marketLoading ? "Fetching live data..." : "Refresh Live Data"}
          </button>
        </div>
      </div>

      {marketLoading && !marketData && (
        <div className="bg-card-bg border border-card-border rounded-[32px] p-16 flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-2 border-primary-cyan border-t-transparent rounded-full animate-spin" />
          <p className="text-text-gray text-sm font-semibold">Searching web & synthesizing market data via AI...</p>
          <p className="text-text-gray/60 text-xs">Analyzing top job platforms and salary surveys in Pakistan (takes 5-8 seconds)</p>
        </div>
      )}

      {marketData && (
        <>
          {/* Main Visuals: Salary Chart & Gender Ratio */}
          <div className="grid lg:grid-cols-[1.3fr_0.7fr] gap-6">
            
            {/* 1. Beautiful Salary Progression Chart */}
            <div className="bg-card-bg border border-card-border rounded-[32px] p-8 flex flex-col justify-between">
              <div>
                <h3 className="text-lg font-bold mb-1 flex items-center gap-2">
                  <BarChart2 size={18} className="text-primary-cyan" />
                  Salary Progression Trend (PKR/month)
                </h3>
                <p className="text-xs text-text-gray mb-6">
                  Avg. monthly salary range of this role from entry to senior tier in Pakistan.
                </p>
              </div>

              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="salaryGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#00e5ff" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#00e5ff" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="name" stroke="#6b7280" fontSize={11} tickLine={false} />
                    <YAxis 
                      stroke="#6b7280" 
                      fontSize={11} 
                      tickLine={false} 
                      axisLine={false}
                      tickFormatter={formatPKR}
                    />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const item = payload[0].payload;
                          return (
                            <div className="bg-dark border border-white/10 rounded-2xl p-4 shadow-xl">
                              <p className="text-xs text-text-gray font-medium uppercase tracking-widest">{item.name}</p>
                              <p className="text-base font-bold text-primary-cyan mt-1">{item.display} PKR/mo</p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Area type="monotone" dataKey="salary" stroke="#00e5ff" strokeWidth={3} fillOpacity={1} fill="url(#salaryGrad)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* 2. Gender Representation Ratio */}
            <div className="bg-card-bg border border-card-border rounded-[32px] p-8 flex flex-col justify-between">
              <div>
                <h3 className="text-lg font-bold mb-1 flex items-center gap-2">
                  <Users size={18} className="text-pink-400" />
                  Gender Distribution (PK)
                </h3>
                <p className="text-xs text-text-gray mb-4">
                  Estimated male vs female ratio in the professional workspace in Pakistan.
                </p>
              </div>

              <div className="h-44 w-full flex items-center justify-center relative">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={genderData}
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={75}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {genderData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value) => [`${value}%`, "Representation"]}
                      contentStyle={{ backgroundColor: "#12131a", borderColor: "rgba(255,255,255,0.1)", borderRadius: "12px" }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                {/* Center text overlay */}
                <div className="absolute text-center">
                  <span className="text-2xl font-bold text-white">
                    {marketData.gender_representation?.female_percentage || 35}%
                  </span>
                  <p className="text-[10px] text-pink-400 uppercase font-semibold tracking-wider">Female</p>
                </div>
              </div>

              <div className="flex justify-around mt-2">
                {genderData.map((g) => (
                  <div key={g.name} className="text-center">
                    <span className="inline-block w-2.5 h-2.5 rounded-full mr-2" style={{ backgroundColor: g.color }} />
                    <span className="text-xs text-text-gray font-medium">{g.name}: </span>
                    <span className="text-xs font-bold text-white">{g.value}%</span>
                  </div>
                ))}
              </div>
            </div>

          </div>

          {/* 3. Side-by-Side: Pakistani Government vs Private Job Paths */}
          {marketData.gov_vs_private && (
            <div className="bg-card-bg border border-card-border rounded-[32px] p-8">
              <h3 className="text-lg font-bold mb-2 flex items-center gap-2">
                <Building2 size={18} className="text-accent-teal" />
                Pakistani Government vs Private Job Sectors
              </h3>
              <p className="text-xs text-text-gray mb-6">
                A comparison of career paths across public services and private corporations in Pakistan.
              </p>

              <div className="grid md:grid-cols-2 gap-6">
                {/* Government Sector Card */}
                <div className="bg-dark/40 border border-emerald-500/20 hover:border-emerald-500/40 rounded-2xl p-6 transition-colors">
                  <div className="flex items-center gap-2 mb-4">
                    <span className="p-2 bg-emerald-500/10 text-emerald-400 rounded-xl">🇵🇰</span>
                    <div>
                      <h4 className="font-bold text-white">Government Sector</h4>
                      <p className="text-[10px] text-emerald-400 font-semibold uppercase tracking-wider">Public Office & Commissions</p>
                    </div>
                  </div>
                  <ul className="space-y-3 text-sm text-text-gray">
                    <li className="flex justify-between border-b border-white/5 pb-2">
                      <span>Salary Scale</span>
                      <span className="font-bold text-white">{marketData.gov_vs_private.gov_salary_pkr}</span>
                    </li>
                    <li className="flex justify-between border-b border-white/5 pb-2">
                      <span>Typical Entry Grade</span>
                      <span className="font-bold text-white">{marketData.gov_vs_private.gov_typical_grade}</span>
                    </li>
                    <li className="flex justify-between border-b border-white/5 pb-2">
                      <span>Job Security</span>
                      <span className="font-bold text-emerald-400">{marketData.gov_vs_private.gov_job_security}</span>
                    </li>
                    <li className="flex justify-between">
                      <span>Pension / Benefits</span>
                      <span className="font-bold text-emerald-400">{marketData.gov_vs_private.gov_pension_benefits}</span>
                    </li>
                  </ul>
                </div>

                {/* Private Sector Card */}
                <div className="bg-dark/40 border border-primary-cyan/20 hover:border-primary-cyan/40 rounded-2xl p-6 transition-colors">
                  <div className="flex items-center gap-2 mb-4">
                    <span className="p-2 bg-primary-cyan/10 text-primary-cyan rounded-xl">🏢</span>
                    <div>
                      <h4 className="font-bold text-white">Private Sector</h4>
                      <p className="text-[10px] text-primary-cyan font-semibold uppercase tracking-wider">Corporate & Multinational</p>
                    </div>
                  </div>
                  <ul className="space-y-3 text-sm text-text-gray">
                    <li className="flex justify-between border-b border-white/5 pb-2">
                      <span>Starting Salary</span>
                      <span className="font-bold text-white">{marketData.gov_vs_private.private_salary_pkr}</span>
                    </li>
                    <li className="flex justify-between border-b border-white/5 pb-2">
                      <span>Career Growth Speed</span>
                      <span className="font-bold text-primary-cyan">{marketData.gov_vs_private.private_growth_speed}</span>
                    </li>
                    <li className="flex justify-between border-b border-white/5 pb-2">
                      <span>Performance Bonuses</span>
                      <span className="font-bold text-primary-cyan">{marketData.gov_vs_private.private_bonuses}</span>
                    </li>
                    <li className="flex justify-between">
                      <span>Remote Work Friendly</span>
                      <span className="font-bold text-primary-cyan">{marketData.gov_vs_private.private_remote_work}</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* 4. Overseas Opportunities & Global Score */}
          {marketData.overseas_opportunities && (
            <div className="bg-card-bg border border-card-border rounded-[32px] p-8 grid md:grid-cols-[0.8fr_1.2fr] gap-8 items-center">
              <div>
                <h3 className="text-lg font-bold mb-1 flex items-center gap-2">
                  <Sparkles size={18} className="text-yellow-400" />
                  Overseas Score
                </h3>
                <p className="text-xs text-text-gray mb-6">
                  Global demand level for graduates holding this degree from Pakistan.
                </p>
                <div className="flex items-center gap-4">
                  <div className="relative w-24 h-24 flex items-center justify-center border-4 border-white/10 rounded-full">
                    <div className="absolute inset-0 border-4 border-yellow-400 rounded-full border-t-transparent animate-spin-slow" />
                    <span className="text-3xl font-black text-white">{marketData.overseas_opportunities.score}</span>
                    <span className="text-xs text-text-gray absolute bottom-2">/ 10</span>
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-yellow-400">Global Portability</div>
                    <p className="text-xs text-text-gray mt-1">Based on global recognition and migration channels.</p>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="bg-dark/60 border border-white/8 rounded-2xl p-5">
                  <div className="text-xs text-text-gray mb-2 uppercase tracking-widest">Typical International Salary Range</div>
                  <div className="text-xl font-bold text-white">{marketData.overseas_opportunities.overseas_salary_usd}</div>
                  <p className="text-[10px] text-text-gray/60 mt-1">Average monthly salary range in USD for foreign recruiters.</p>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <div className="bg-dark/40 border border-white/6 rounded-2xl p-4">
                    <div className="text-[10px] text-text-gray mb-2 uppercase tracking-wider">Top Destinational Markets</div>
                    <div className="flex flex-wrap gap-1.5">
                      {(marketData.overseas_opportunities.accepted_countries || []).map((country, idx) => (
                        <span key={idx} className="text-xs px-2 py-1 bg-white/5 border border-white/10 text-white rounded-lg">
                          🌍 {country}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="bg-dark/40 border border-white/6 rounded-2xl p-4">
                    <div className="text-[10px] text-text-gray mb-2 uppercase tracking-wider">Equivalency Exam / License</div>
                    <div className="text-xs font-semibold text-white mt-1">
                      {marketData.overseas_opportunities.needs_equivalency}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Market Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-card-bg border border-card-border rounded-2xl p-5">
              <div className="text-xs text-text-gray mb-2 uppercase tracking-widest">Growth Rate</div>
              <div className="text-base font-bold text-emerald-400">{marketData.growth_rate}</div>
            </div>
            <div className="bg-card-bg border border-card-border rounded-2xl p-5">
              <div className="text-xs text-text-gray mb-2 uppercase tracking-widest">Market Trend</div>
              <div className="text-base font-bold text-primary-cyan">{marketData.job_market_trend}</div>
            </div>
            <div className="bg-card-bg border border-card-border rounded-2xl p-5">
              <div className="text-xs text-text-gray mb-2 flex items-center gap-1 uppercase tracking-widest"><Wifi size={12} />Remote Work</div>
              <div className="text-base font-bold" style={{ color: remoteBadge(marketData.remote_friendly).color }}>
                {remoteBadge(marketData.remote_friendly).label}
              </div>
            </div>
            <div className="bg-card-bg border border-card-border rounded-2xl p-5">
              <div className="text-xs text-text-gray mb-2 flex items-center gap-1 uppercase tracking-widest"><Users size={12} />Competition</div>
              <div className="text-base font-bold" style={{ color: competitionColor(marketData.competition_level) }}>
                {marketData.competition_level}
              </div>
            </div>
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
            {/* Top Employers */}
            <div className="bg-card-bg border border-card-border rounded-[32px] p-8">
              <h3 className="text-base font-bold mb-5 flex items-center gap-2">
                <Building2 size={16} className="text-primary-cyan" />
                Top Employers in Pakistan
              </h3>
              <div className="flex flex-wrap gap-2">
                {(marketData.top_employers || []).map((e, i) => (
                  <span key={i} className="px-3 py-1.5 bg-primary-cyan/10 border border-primary-cyan/20 text-primary-cyan rounded-xl text-sm hover:scale-[1.03] transition-transform cursor-default">
                    {e}
                  </span>
                ))}
              </div>
            </div>

            {/* Key Hiring Cities */}
            <div className="bg-card-bg border border-card-border rounded-[32px] p-8">
              <h3 className="text-base font-bold mb-5 flex items-center gap-2">
                <MapPin size={16} className="text-accent-teal" />
                Key Hiring Hubs in Pakistan
              </h3>
              <div className="flex flex-wrap gap-2">
                {(marketData.key_cities || []).map((city, i) => (
                  <span key={i} className="px-3 py-1.5 bg-accent-teal/10 border border-accent-teal/20 text-accent-teal rounded-xl text-sm hover:scale-[1.03] transition-transform cursor-default">
                    📍 {city}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
            {/* Skills in Demand */}
            <div className="bg-card-bg border border-card-border rounded-[32px] p-8">
              <h3 className="text-base font-bold mb-5 flex items-center gap-2">
                <CheckCircle size={16} className="text-emerald-400" />
                Currently In-Demand Skills
              </h3>
              <div className="space-y-2">
                {(marketData.skills_in_demand || []).map((s, i) => (
                  <div key={i} className="flex items-center gap-3 bg-dark/40 border border-white/6 rounded-xl px-4 py-2.5 hover:bg-dark/60 transition-colors">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0" />
                    <span className="text-sm text-white">{s}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Certifications */}
            <div className="bg-card-bg border border-card-border rounded-[32px] p-8">
              <h3 className="text-base font-bold mb-5 flex items-center gap-2">
                <Award size={16} className="text-yellow-400" />
                Key Certifications & Growth
              </h3>
              <div className="space-y-2">
                {(marketData.certifications || []).map((c, i) => (
                  <div key={i} className="flex items-center gap-3 bg-dark/40 border border-white/6 rounded-xl px-4 py-2.5 hover:bg-dark/60 transition-colors">
                    <span className="text-yellow-400">🏆</span>
                    <span className="text-sm text-white">{c}</span>
                  </div>
                ))}
              </div>
              <div className="mt-4 p-4 bg-purple-500/10 border border-purple-500/20 rounded-2xl">
                <div className="text-xs text-text-gray mb-1 uppercase tracking-widest">Freelance Potential</div>
                <div className="text-base font-bold text-purple-400">{marketData.freelance_potential}</div>
              </div>
            </div>
          </div>

          {/* AI Summary */}
          {marketData.summary && (
            <div className="bg-gradient-to-br from-primary-cyan/10 to-purple-500/5 border border-primary-cyan/20 rounded-[32px] p-8">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles size={16} className="text-primary-cyan" />
                <span className="text-sm font-semibold text-primary-cyan uppercase tracking-widest">AI Market Summary</span>
              </div>
              <p className="text-text-gray leading-relaxed text-sm">{marketData.summary}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
};

export default DetailedResults;
