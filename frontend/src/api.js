import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

import { supabase } from './lib/supabase';

client.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession();
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }
  return config;
});

export const fetchOptions = async () => {
  const { data } = await client.get("/options");
  return data;
};

export const fetchHealth = async () => {
  const { data } = await client.get("/health");
  return data;
};

export const predictCareer = async (payload) => {
  const { data } = await client.post("/predict", payload);
  return data;
};

export const fetchRoadmap = async (career) => {
  const { data } = await client.get("/roadmap", {
    params: { career },
  });
  return data;
};

export const sendChatMessage = async (payload) => {
  const { data } = await client.post("/chat", payload);
  return data;
};

export const fetchConversations = async () => {
  const { data } = await client.get("/conversations");
  return data;
};

export const fetchConversationMessages = async (conversationId) => {
  const { data } = await client.get(`/conversations/${conversationId}/messages`);
  return data;
};

export const fetchShap = async (payload) => {
  const { data } = await client.post("/shap", payload);
  return data;
};

export const saveSession = async (payload) => {
  const { data } = await client.post("/save_session", payload);
  return data;
};

export const exportPdf = async (payload) => {
  const response = await client.post("/export_pdf", payload, {
    responseType: "blob", // Important for PDF download
  });
  return response.data;
};

export const transcribeVoice = async (audioBlob) => {
  const formData = new FormData();
  // Browsers record in audio/webm by default — Groq whisper-large-v3 accepts webm
  const ext = audioBlob.type.includes("webm") ? "webm" : "wav";
  formData.append("audio", audioBlob, `voice.${ext}`);
  const { data } = await client.post("/voice", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return data;
};

export const fetchMarketTrends = async (career, refresh = false) => {
  const { data } = await client.get("/market-trends", {
    params: { career, refresh },
  });
  return data;
};

export const generateMindMap = async (notes) => {
  const { data } = await client.post("/generate-mindmap", { notes });
  return data;
};

export const generateMindMapFromFile = async (file) => {
  const formData = new FormData();
  formData.append("file", file, file.name);
  const { data } = await client.post("/generate-mindmap/file", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const fetchAptitudeDiagnostic = async (scores) => {
  const { data } = await client.post("/diagnose-aptitude", scores);
  return data;
};

export const saveResource = async (payload) => {
  const { data } = await client.post("/save_resource", payload);
  return data;
};

export const fetchSavedResources = async () => {
  const { data } = await client.get("/saved_resources");
  return data;
};

export const saveEntryTestScore = async (payload) => {
  const { data } = await client.post("/save_entry_test_score", payload);
  return data;
};

export const fetchEntryTestScores = async () => {
  const { data } = await client.get("/entry_test_scores");
  return data;
};

export default client;
