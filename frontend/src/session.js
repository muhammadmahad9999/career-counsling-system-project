const STORAGE_KEY = "futurepath-prediction-session";

export const savePredictionSession = (value) => {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value));
};

export const loadPredictionSession = () => {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
};

export const clearPredictionSession = () => {
  sessionStorage.removeItem(STORAGE_KEY);
};
