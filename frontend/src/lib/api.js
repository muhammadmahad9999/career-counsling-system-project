import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
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

export default client;
