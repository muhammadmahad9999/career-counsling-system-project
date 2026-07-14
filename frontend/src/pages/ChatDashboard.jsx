import React, { useMemo, useState, useRef, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { Bot, Send, User, Mic, MicOff, Bookmark, Plus, MessageSquare, Clock } from "lucide-react";

import Navbar from "../components/Navbar";
import { sendChatMessage, transcribeVoice, saveResource, fetchSavedResources, fetchConversations, fetchConversationMessages } from "../api";
import { loadPredictionSession } from "../session";

const starterPrompts = [
  "Give me a roadmap for my recommended career.",
  "Which universities in my city match this field?",
  "What skills should I build first?",
  "Are there scholarships I should look for?",
  "Show me online courses for this career",
  "What's the salary and job market for this field?",
];

const featureButtons = [
  { label: "📚 Scholarships", action: "scholarships" },
  { label: "🎓 Courses", action: "courses" },
  { label: "🎯 Skill Gap", action: "skillgap" },
  { label: "💼 Market Info", action: "market" },
];

const liveResourceButtons = [
  { label: "🔴 Live Scholarships", action: "livescholarships", icon: "🎓" },
  { label: "🎥 YouTube Videos", action: "videos", icon: "📹" },
  { label: "📺 Learning Channels", action: "channels", icon: "📺" },
  { label: "📚 Resources & Blogs", action: "resources", icon: "📖" },
  { label: "💼 Job Portals", action: "jobportals", icon: "🔗" },
];

const allResources = [
  "Show me the latest scholarships from today",
  "Find YouTube videos for learning this career",
  "Recommend best learning channels",
  "Show me useful learning websites and blogs",
  "Where can I find job and internship postings?",
];

const parseRawUrls = (text, onSave) => {
  const rawUrlRegex = /(https?:\/\/[^\s]+)/g;
  const parts = [];
  let lastIndex = 0;
  let match;
  
  while ((match = rawUrlRegex.exec(text)) !== null) {
    const textBefore = text.substring(lastIndex, match.index);
    if (textBefore) {
      parts.push(textBefore);
    }
    
    const url = match[0];
    const cleanUrl = url.replace(/[.,:;)]$/, "");
    const trailingPunctuation = url.substring(cleanUrl.length);
    
    parts.push(
      <span key={`raw-link-container-${match.index}`} className="inline-flex items-center gap-1">
        <a
          href={cleanUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary-cyan underline hover:text-cyan-300 font-semibold"
        >
          {cleanUrl}
        </a>
        {onSave && (
          <button
            type="button"
            onClick={() => onSave(cleanUrl, "Suggested Resource")}
            className="text-[10px] px-1 py-0.5 rounded bg-white/5 hover:bg-primary-cyan/20 text-accent-teal hover:text-white transition-colors"
            title="Save to Bookmarks"
          >
            🔖
          </button>
        )}
      </span>
    );
    
    if (trailingPunctuation) {
      parts.push(trailingPunctuation);
    }
    
    lastIndex = rawUrlRegex.lastIndex;
  }
  
  const textAfter = text.substring(lastIndex);
  if (textAfter) {
    parts.push(textAfter);
  }
  
  return parts;
};

const buildInitialMessages = (recommendedCareer) => [
  {
    role: "assistant",
    content: recommendedCareer
      ? `Hello! Your current top recommendation is ${recommendedCareer}. Feel free to ask about roadmaps, universities, or scholarships.`
      : "Hello! Feel free to ask me about roadmaps, universities, scholarships, or your next career step.",
  },
];

const formatConversationTime = (value) => {
  if (!value) return "No messages yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Recently";
  return date.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
};

// ── Tool display config ──────────────────────────────────────────────────────
const TOOL_META = {
  get_youtube_videos: { label: "YouTube Search", icon: "🎥", color: "#f43f5e" },
  google_search:      { label: "Web Search",     icon: "🔍", color: "#00e5ff" },
  tavily_search:      { label: "Tavily Search",  icon: "🌐", color: "#06b6d4" },
  web_scrape:         { label: "Reading Page",   icon: "📄", color: "#8b5cf6" },
  get_online_courses: { label: "Course Search",  icon: "📚", color: "#10b981" },
};

const ToolCallIndicator = ({ tools }) => {
  if (!tools || tools.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5 mb-2">
      {tools.map((t, i) => {
        const meta = TOOL_META[t.name] || { label: t.name, icon: "🛠️", color: "#6b7280" };
        return (
          <span
            key={i}
            title={t.query ? `Query: ${t.query}` : t.name}
            style={{ borderColor: meta.color, color: meta.color }}
            className="inline-flex items-center gap-1 text-[10px] font-semibold border rounded-full px-2 py-0.5 bg-white/5"
          >
            <span>{meta.icon}</span>
            <span>{meta.label}</span>
            {t.query && (
              <span className="opacity-60 max-w-[120px] truncate">— {t.query}</span>
            )}
          </span>
        );
      })}
    </div>
  );
};

// ── Full Markdown Renderer ────────────────────────────────────────────────────
const renderMarkdown = (text, onSave) => {
  if (!text) return null;

  const urlRegex = /(\[([^\]]+)\]\((https?:\/\/[^\s)]+)\))|(https?:\/\/[^\s]+)/g;

  const renderInline = (line) => {
    // Handle bold (**text** or __text__), italic (*text* or _text_), inline code `code`
    const parts = [];
    const inlineRe = /(\*\*([^*]+)\*\*|__([^_]+)__)|(\*([^*]+)\*|_([^_]+)_)|(`([^`]+)`)|\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|(https?:\/\/[^\s]+)/g;
    let last = 0;
    let m;
    inlineRe.lastIndex = 0;
    while ((m = inlineRe.exec(line)) !== null) {
      if (m.index > last) parts.push(line.slice(last, m.index));
      if (m[1])  parts.push(<strong key={m.index} className="font-bold text-white">{m[2] || m[3]}</strong>);
      else if (m[4])  parts.push(<em key={m.index} className="italic text-gray-300">{m[5] || m[6]}</em>);
      else if (m[7])  parts.push(<code key={m.index} className="bg-white/10 rounded px-1 text-xs font-mono text-emerald-300">{m[8]}</code>);
      else if (m[9]) {
        // Markdown link
        const href = m[10]; const label = m[9];
        parts.push(
          <span key={m.index} className="inline-flex items-center gap-1">
            <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary-cyan underline hover:text-cyan-300 font-semibold">{label}</a>
            {onSave && <button type="button" onClick={() => onSave(href, label)} className="text-[10px] px-1 py-0.5 rounded bg-white/5 hover:bg-primary-cyan/20 text-accent-teal" title="Save">🔖</button>}
          </span>
        );
      } else if (m[11]) {
        // Raw URL
        const href = m[11].replace(/[.,;:)]$/, "");
        parts.push(
          <span key={m.index} className="inline-flex items-center gap-1">
            <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary-cyan underline hover:text-cyan-300 font-semibold">{href}</a>
            {onSave && <button type="button" onClick={() => onSave(href, "Resource")} className="text-[10px] px-1 py-0.5 rounded bg-white/5 hover:bg-primary-cyan/20 text-accent-teal" title="Save">🔖</button>}
          </span>
        );
      }
      last = inlineRe.lastIndex;
    }
    if (last < line.length) parts.push(line.slice(last));
    return parts.length ? parts : line;
  };

  const lines = text.split("\n");
  const elements = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Blank line
    if (line.trim() === "") { elements.push(<div key={`br-${i}`} className="h-2" />); i++; continue; }

    // H1 / H2 / H3
    if (line.startsWith("### ")) { elements.push(<h3 key={i} className="font-bold text-sm text-primary-cyan mt-3 mb-1">{renderInline(line.slice(4))}</h3>); i++; continue; }
    if (line.startsWith("## "))  { elements.push(<h2 key={i} className="font-bold text-base text-primary-cyan mt-3 mb-1">{renderInline(line.slice(3))}</h2>); i++; continue; }
    if (line.startsWith("# "))   { elements.push(<h1 key={i} className="font-bold text-lg text-white mt-3 mb-1">{renderInline(line.slice(2))}</h1>); i++; continue; }

    // Horizontal rule
    if (/^[-*_]{3,}$/.test(line.trim())) { elements.push(<hr key={i} className="border-white/10 my-2" />); i++; continue; }

    // Numbered list — collect consecutive items
    if (/^\d+\.\s/.test(line)) {
      const items = [];
      while (i < lines.length && /^\d+\.\s/.test(lines[i])) {
        items.push(<li key={i} className="mb-1">{renderInline(lines[i].replace(/^\d+\.\s/, ""))}</li>);
        i++;
      }
      elements.push(<ol key={`ol-${i}`} className="list-decimal list-inside space-y-0.5 text-sm mb-2 text-gray-200">{items}</ol>);
      continue;
    }

    // Bullet list — -, *, or +
    if (/^[-*+]\s/.test(line)) {
      const items = [];
      while (i < lines.length && /^[-*+]\s/.test(lines[i])) {
        items.push(<li key={i} className="mb-0.5">{renderInline(lines[i].replace(/^[-*+]\s/, ""))}</li>);
        i++;
      }
      elements.push(<ul key={`ul-${i}`} className="list-disc list-inside space-y-0.5 text-sm mb-2 text-gray-200">{items}</ul>);
      continue;
    }

    // Normal paragraph
    elements.push(<p key={i} className="text-sm leading-relaxed mb-1 text-gray-100">{renderInline(line)}</p>);
    i++;
  }

  return elements;
};

const ChatDashboard = () => {
  const location = useLocation();
  const session = loadPredictionSession();
  const recommendedCareer =
    location.state?.career ||
    session?.prediction?.primary_recommendation?.career ||
    session?.prediction?.recommendations?.[0]?.career ||
    "";
  const city = session?.student?.City || "";

  const [savedResources, setSavedResources] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [messages, setMessages] = useState(() => buildInitialMessages(recommendedCareer));
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState(""); // real-time interim text
  const [voiceLang, setVoiceLang] = useState("en-US");
  const [conversationId, setConversationId] = useState(() => {
    return localStorage.getItem("active_conversation_id") || "";
  });
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recognitionRef = useRef(null); // Web Speech API instance

  const loadSavedResources = async () => {
    try {
      const data = await fetchSavedResources();
      setSavedResources(data);
    } catch (err) {
      console.error("Failed to load saved resources:", err);
    }
  };

  const loadConversations = async () => {
    setLoadingConversations(true);
    try {
      const data = await fetchConversations();
      setConversations(data || []);
    } catch (err) {
      console.error("Failed to load conversations:", err);
    } finally {
      setLoadingConversations(false);
    }
  };

  useEffect(() => {
    loadSavedResources();
    loadConversations().then(() => {
      const savedId = localStorage.getItem("active_conversation_id");
      if (savedId) {
        // Fetch and load conversation history for this conversation ID
        setSending(true);
        fetchConversationMessages(savedId).then((history) => {
          if (history && history.length > 0) {
            setMessages(history);
          }
        }).catch((err) => {
          console.error("Failed to load active conversation on mount:", err);
          localStorage.removeItem("active_conversation_id");
          setConversationId("");
        }).finally(() => {
          setSending(false);
        });
      }
    });
  }, []);

  const handleSaveResource = async (url, title) => {
    try {
      const lower = url.toLowerCase();
      let resType = "other";
      if (lower.includes("youtube.com") || lower.includes("youtu.be")) resType = "youtube";
      else if (lower.includes("scholarship") || lower.includes("fellowship")) resType = "scholarship";
      else if (lower.includes("course") || lower.includes("udemy") || lower.includes("coursera") || lower.includes("edx")) resType = "course";
      else if (lower.includes("edu") || lower.includes("uni") || lower.includes("university") || lower.includes("admissions")) resType = "university";
      else if (lower.includes("article") || lower.includes("blog") || lower.includes("news")) resType = "article";

      await saveResource({
        title: title || "Suggested Link",
        url: url,
        resource_type: resType,
        notes: "Saved from Career Advisor Chat"
      });
      alert("Resource bookmarked successfully!");
      loadSavedResources();
    } catch (err) {
      console.error(err);
      alert("Failed to bookmark resource.");
    }
  };

  const handleNewChat = () => {
    setConversationId("");
    localStorage.removeItem("active_conversation_id");
    setMessages(buildInitialMessages(recommendedCareer));
    loadConversations();
  };


  const handleSelectConversation = async (id) => {
    if (id === conversationId) return;
    setConversationId(id);
    localStorage.setItem("active_conversation_id", id);
    setSending(true);
    try {
      const history = await fetchConversationMessages(id);
      if (history && history.length > 0) {
        setMessages(history);
      } else {
        setMessages(buildInitialMessages(recommendedCareer));
      }
    } catch (err) {
      console.error("Failed to load conversation messages:", err);
      localStorage.removeItem("active_conversation_id");
      setConversationId("");
      alert("Failed to load conversation history.");
    } finally {
      setSending(false);
    }
  };

  const toggleListen = async () => {
    // ── STOP ────────────────────────────────────────────────────────────────
    if (isListening) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
        recognitionRef.current = null;
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
      setIsListening(false);
      setLiveTranscript("");
      return;
    }

    // ── START: Try Web Speech API first (real-time streaming) ───────────────
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous     = true;  // keep going until user clicks stop
      recognition.interimResults = true;  // fire results as words are spoken
      recognition.lang           = "en-US";
      recognitionRef.current = recognition;

      let confirmed = ""; // finalized phrases accumulated

      recognition.onstart = () => {
        setIsListening(true);
        setLiveTranscript("");
        confirmed = "";
      };

      recognition.onresult = (event) => {
        let interim = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const chunk = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            confirmed += chunk + " ";
          } else {
            interim = chunk; // live word being spoken right now
          }
        }
        const full = (confirmed + interim).trim();
        setInput(full);          // update input box live
        setLiveTranscript(interim); // track interim portion
      };

      recognition.onerror = (e) => {
        console.warn("[STT] Web Speech error:", e.error);
        if (e.error !== "no-speech" && e.error !== "aborted") {
          setIsListening(false);
          setLiveTranscript("");
        }
      };

      recognition.onend = () => {
        // Browser auto-stops after silence — just update state
        setIsListening(false);
        setLiveTranscript("");
      };

      try {
        recognition.start();
        return; // success — don't fall through to Groq path
      } catch (err) {
        console.warn("[STT] SpeechRecognition.start() failed, trying Groq:", err);
        recognitionRef.current = null;
      }
    }

    // ── FALLBACK: MediaRecorder → Groq Whisper (batch, for unsupported browsers) ─
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];

      const preferredMime = [
        "audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4",
      ].find((m) => MediaRecorder.isTypeSupported(m)) || "";

      const mediaRecorder = preferredMime
        ? new MediaRecorder(stream, { mimeType: preferredMime })
        : new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        if (!audioChunksRef.current.length) { alert("No audio captured."); return; }
        const blob = new Blob(audioChunksRef.current, { type: mediaRecorder.mimeType || "audio/webm" });
        setIsTranscribing(true);
        try {
          const res = await transcribeVoice(blob);
          if (res.text && res.text.trim().length > 1) {
            setInput((p) => (p ? p + " " : "") + res.text.trim());
          } else {
            setMessages((c) => [...c, { role: "assistant", content: "I couldn't hear that clearly. Please try again.", tools_used: [] }]);
          }
        } catch (e) {
          setMessages((c) => [...c, { role: "assistant", content: "Voice transcription failed. Check your microphone.", tools_used: [] }]);
        } finally {
          setIsTranscribing(false);
        }
      };

      mediaRecorder.start(250);
      setIsListening(true);
    } catch (err) {
      console.error("[STT] Mic error:", err);
      alert("Microphone permission denied or unsupported browser.");
    }
  };


  const snapshot = useMemo(
    () => [
      ["Stream", session?.student?.Stream || "Not set"],
      ["Top match", recommendedCareer || "Not available"],
      ["Model", session?.prediction?.used_model || "Not available"],
    ],
    [recommendedCareer, session]
  );

  const handleSend = async (text = input) => {
    const trimmed = text.trim();
    if (!trimmed || sending) {
      return;
    }

    setMessages((current) => [...current, { role: "user", content: trimmed }]);
    setInput("");
    setSending(true);

    try {
      const response = await sendChatMessage({
        message: trimmed,
        city,
        recommended_career: recommendedCareer,
        conversation_id: conversationId,
      });
      setMessages((current) => [...current, {
        role: "assistant",
        content: response.response,
        tools_used: response.tools_used || [],
      }]);
      
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
        localStorage.setItem("active_conversation_id", response.conversation_id);
      }
      loadConversations();

    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content:
            error?.response?.data?.detail ||
            "The AI counselor could not respond right now. Check that the FastAPI backend is running.",
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleFeatureButton = async (action) => {
    if (!recommendedCareer) {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: "Please complete the aptitude test first to get a career recommendation!",
        },
      ]);
      return;
    }

    setSending(true);
    try {
      let featureMessage = "";
      switch (action) {
        case "scholarships":
          featureMessage = `Show scholarships for ${recommendedCareer}`;
          break;
        case "courses":
          featureMessage = `Recommend online courses for ${recommendedCareer}`;
          break;
        case "skillgap":
          featureMessage = `Analyze skill gaps for ${recommendedCareer}`;
          break;
        case "market":
          featureMessage = `What's the market info and salary for ${recommendedCareer}?`;
          break;
        case "livescholarships":
          featureMessage = "Show me the latest scholarships from today";
          break;
        case "videos":
          featureMessage = "Find YouTube videos for learning";
          break;
        case "channels":
          featureMessage = "Recommend best learning channels";
          break;
        case "resources":
          featureMessage = "Show me useful learning websites and blogs";
          break;
        case "jobportals":
          featureMessage = "Where can I find job and internship postings?";
          break;
        default:
          return;
      }
      setMessages((current) => [...current, { role: "user", content: featureMessage }]);

      const response = await sendChatMessage({
        message: featureMessage,
        city,
        recommended_career: recommendedCareer,
        conversation_id: conversationId,
      });
      setMessages((current) => [...current, {
        role: "assistant",
        content: response.response,
        tools_used: response.tools_used || [],
      }]);
      
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
        localStorage.setItem("active_conversation_id", response.conversation_id);
      }
      loadConversations();

    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: error?.response?.data?.detail || "Error fetching feature data.",
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="min-h-screen bg-dark flex flex-col text-white font-grotesk">
      <Navbar />

      <div className="flex flex-1 pt-24 px-4 md:px-6 gap-4 overflow-hidden max-h-screen pb-8">
        
        {/* Left Sidebar: Conversations Thread List */}
        <aside className="hidden md:flex flex-col w-[260px] bg-card-bg border border-card-border rounded-[28px] p-4 h-[82vh] shadow-[0_0_20px_rgba(0,0,0,0.35)]">
          <button
            type="button"
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-primary-cyan to-accent-teal text-dark font-bold py-3 px-4 rounded-2xl hover:opacity-90 transition-opacity mb-4"
          >
            <Plus size={18} />
            New Chat
          </button>
          
          <div className="flex items-center gap-2 px-1 mb-3 text-xs uppercase tracking-[0.2em] text-text-gray font-semibold">
            <MessageSquare size={14} className="text-primary-cyan" />
            <span>Chat History</span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 pr-1 scrollbar-thin">
            {loadingConversations ? (
              <div className="text-center text-xs text-text-gray py-4 animate-pulse">
                Loading conversations...
              </div>
            ) : conversations.length === 0 ? (
              <div className="text-center text-xs text-text-gray py-4 italic">
                No past conversations. Start typing to create one!
              </div>
            ) : (
              conversations.map((conv) => (
                <button
                  key={conv.id}
                  type="button"
                  onClick={() => handleSelectConversation(conv.id)}
                  className={`w-full text-left flex items-start gap-3 p-3 rounded-2xl border transition-all ${
                    conversationId === conv.id
                      ? "bg-primary-cyan/15 border-primary-cyan text-white shadow-[0_0_12px_rgba(6,182,212,0.15)]"
                      : "bg-dark/40 border-white/5 text-text-gray hover:text-white hover:border-white/10"
                  }`}
                >
                  <MessageSquare size={16} className="mt-1 shrink-0 text-primary-cyan" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold truncate leading-normal">
                      {conv.title || "Untitled Chat"}
                    </p>
                    <span className="text-[10px] text-text-gray block mt-1 opacity-70">
                      {formatConversationTime(conv.last_message_at)}
                    </span>
                  </div>
                </button>
              ))
            )}
          </div>
        </aside>

        {/* Center: Main Chat Panel */}
        <section className="flex-1 flex flex-col bg-card-bg border border-card-border rounded-[28px] h-[82vh] overflow-hidden">
          <div className="p-5 border-b border-card-border bg-dark/50 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-full bg-gradient-to-r from-primary-cyan to-accent-teal flex items-center justify-center text-dark shadow-[0_0_15px_rgba(6,182,212,0.25)]">
                <Bot size={22} />
              </div>
              <div>
                <h2 className="font-bold text-sm md:text-base">AI Career Counselor</h2>
                <p className="text-[10px] md:text-xs text-emerald-300 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                  Active counselor context and thread memory
                </p>
              </div>
            </div>
            {conversationId && (
              <span className="hidden sm:inline-block text-[10px] bg-white/5 border border-white/10 px-3 py-1 rounded-full text-text-gray font-mono">
                Thread: {conversationId.substring(0, 8)}...
              </span>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-6 space-y-5 scrollbar-thin">
            {messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-[22px] p-4 ${
                    message.role === "user"
                      ? "bg-primary-cyan text-dark rounded-br-md font-semibold"
                      : "bg-dark/80 border border-white/10 text-gray-100 rounded-bl-md"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] opacity-70">
                      {message.role === "user" ? <User size={14} /> : <Bot size={14} />}
                      {message.role}
                    </div>
                  </div>
                  {message.role === "assistant" && <ToolCallIndicator tools={message.tools_used} />}
                  <div className="leading-relaxed">
                    {message.role === "assistant"
                      ? renderMarkdown(message.content, handleSaveResource)
                      : <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    }
                  </div>
                </div>
              </div>
            ))}

            {/* Transcription waiting indicator */}
            {isTranscribing ? (
              <div className="flex justify-start">
                <div className="bg-dark/80 border border-rose-500/30 text-gray-100 rounded-[22px] rounded-bl-md p-4 flex items-center gap-2">
                  <span className="w-2 h-2 bg-rose-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></span>
                  <span className="w-2 h-2 bg-rose-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></span>
                  <span className="w-2 h-2 bg-rose-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></span>
                  <span className="text-xs text-rose-300 font-medium">Transcribing voice...</span>
                </div>
              </div>
            ) : sending ? (
              <div className="flex justify-start">
                <div className="bg-dark/80 border border-white/10 text-gray-100 rounded-[22px] rounded-bl-md p-4 flex items-center gap-2">
                  <span className="w-2 h-2 bg-primary-cyan rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></span>
                  <span className="w-2 h-2 bg-primary-cyan rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></span>
                  <span className="w-2 h-2 bg-primary-cyan rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></span>
                  <span className="text-xs text-text-gray font-medium">Roshni is typing...</span>
                </div>
              </div>
            ) : null}
          </div>

          <div className="p-4 border-t border-card-border bg-dark/50">
            {isListening && (
              <div className="flex items-center gap-3 mb-2 px-2 h-8 bg-rose-950/20 border border-rose-500/10 rounded-xl py-1">
                {/* Voice Animation Wave */}
                <div className="flex items-end gap-0.5 h-full px-1 py-0.5 shrink-0">
                  <span className="voice-wave-bar" />
                  <span className="voice-wave-bar" />
                  <span className="voice-wave-bar" />
                  <span className="voice-wave-bar" />
                  <span className="voice-wave-bar" />
                  <span className="voice-wave-bar" />
                </div>
                <span className="text-[11px] text-rose-300 font-medium truncate flex-1">
                  {liveTranscript
                    ? <span className="italic opacity-90">"{liveTranscript}"</span>
                    : "Listening — speak now..."}
                </span>
                <span className="text-[10px] text-text-gray shrink-0">click mic to stop</span>
              </div>
            )}
            <div className="flex items-center gap-3 bg-dark border border-white/10 rounded-full px-4 py-2">
              <input
                type="text"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    handleSend();
                  }
                }}
                placeholder={isTranscribing ? "Transcribing..." : isListening ? "🎤 Speaking..." : "Ask about your roadmap, universities, admissions, or scholarships..."}
                className="flex-1 bg-transparent border-none outline-none text-white placeholder-gray-500 text-sm"
              />
              <button
                type="button"
                onClick={toggleListen}
                disabled={isTranscribing}
                className={`p-3 rounded-full transition-colors ${
                  isListening
                    ? "bg-rose-500 text-white animate-pulse"
                    : isTranscribing
                    ? "bg-rose-900/60 text-rose-400 cursor-wait"
                    : "bg-white/10 text-text-gray hover:text-white hover:bg-white/20"
                }`}
                title={isListening ? "Click to stop recording" : "Click to start voice input"}
              >
                {isListening ? <MicOff size={18} /> : <Mic size={18} />}
              </button>
              <button
                type="button"
                onClick={() => handleSend()}
                disabled={sending}
                className="p-3 bg-primary-cyan text-dark rounded-full hover:bg-cyan-300 transition-colors disabled:opacity-60"
              >
                <Send size={18} />
              </button>
            </div>
          </div>
        </section>

        {/* Right Sidebar: Prediction Snapshot & Bookmarks */}
        <aside className="hidden lg:flex flex-col w-[300px] bg-card-bg border border-card-border rounded-[28px] p-5 h-[82vh] shadow-[0_0_20px_rgba(0,0,0,0.35)] overflow-y-auto scrollbar-thin">
          <h2 className="text-base font-bold mb-4 flex items-center gap-2">
            <Bot size={16} className="text-accent-teal" />
            Prediction Snapshot
          </h2>
          <div className="space-y-3 text-xs">
            {snapshot.map(([label, value]) => (
              <div key={label} className="bg-dark/60 border border-white/5 rounded-2xl p-3">
                <p className="text-text-gray mb-1 text-[10px] uppercase tracking-wider">{label}</p>
                <p className="font-semibold text-white truncate">{value}</p>
              </div>
            ))}
          </div>

          <div className="mt-6 border-t border-white/5 pt-4">
            <p className="text-[10px] uppercase tracking-[0.25em] text-primary-cyan mb-2">Quick Prompts</p>
            <div className="space-y-2 max-h-[160px] overflow-y-auto pr-1 scrollbar-thin">
              {starterPrompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => handleSend(prompt)}
                  className="w-full text-left border border-white/10 rounded-2xl px-3 py-2 text-xs text-text-gray hover:text-white hover:border-primary-cyan transition-colors"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-6 border-t border-white/5 pt-4">
            <p className="text-[10px] uppercase tracking-[0.25em] text-primary-cyan mb-2">Features</p>
            <div className="grid grid-cols-2 gap-2">
              {featureButtons.map((btn) => (
                <button
                  key={btn.action}
                  type="button"
                  onClick={() => handleFeatureButton(btn.action)}
                  disabled={sending || !recommendedCareer}
                  className="border border-white/10 rounded-xl px-2 py-1.5 text-[10px] font-semibold text-text-gray hover:text-white hover:border-accent-teal transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {btn.label}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-6 border-t border-white/5 pt-4">
            <p className="text-[10px] uppercase tracking-[0.25em] text-accent-teal mb-2 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></span> Live Resources
            </p>
            <div className="grid grid-cols-1 gap-2 max-h-[100px] overflow-y-auto pr-1 scrollbar-thin">
              {liveResourceButtons.map((btn) => (
                <button
                  key={btn.action}
                  type="button"
                  onClick={() => handleFeatureButton(btn.action)}
                  disabled={sending}
                  className="w-full text-left border border-accent-teal/30 bg-accent-teal/5 hover:bg-accent-teal/10 rounded-lg px-3 py-1.5 text-[10px] font-semibold text-text-gray hover:text-accent-teal transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {btn.label}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-6 border-t border-white/5 pt-4 flex-1 flex flex-col min-h-[150px]">
            <p className="text-[10px] uppercase tracking-[0.25em] text-primary-cyan mb-2 flex items-center gap-2">
              <Bookmark size={12} className="text-primary-cyan" /> Bookmarks ({savedResources.length})
            </p>
            <div className="space-y-2 overflow-y-auto pr-1 scrollbar-thin flex-1 max-h-[180px]">
              {savedResources.length === 0 ? (
                <p className="text-[10px] text-text-gray italic">No bookmarks. Click 🔖 in chat.</p>
              ) : (
                savedResources.map((res) => (
                  <div key={res.id} className="bg-dark/40 border border-white/5 rounded-xl p-2 hover:border-accent-teal transition-colors">
                    <a
                      href={res.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block text-xs font-semibold text-white hover:text-accent-teal truncate"
                      title={res.title}
                    >
                      {res.title}
                    </a>
                    <span className="text-[9px] text-text-gray block truncate opacity-70 mt-0.5">
                      {res.url}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </aside>

      </div>
    </div>
  );
};

export default ChatDashboard;
