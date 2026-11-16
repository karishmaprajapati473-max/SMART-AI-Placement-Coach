const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function getQuestion(questionId) {
  const response = await fetch(
    `${API_BASE_URL}/questions/${encodeURIComponent(questionId)}`,
    { credentials: "include" }
  );

  const data = await response.json();

  if (!response.ok || data.status === "error") {
    throw new Error(data.message || "Question load nahi hua.");
  }

  return data;
}

export async function evaluateCode({
  language,
  questionId,
  code,
  revisedConcept
}) {
  const response = await fetch(`${API_BASE_URL}/evaluate`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      language,
      question_id: questionId,
      code,
      revised_concept: revisedConcept || null,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || data.message || "Code evaluation failed.");
  }

  return data;
}

export async function runCode({ language, questionId, code, inputData }) {
  const response = await fetch(`${API_BASE_URL}/run`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      language,
      question_id: questionId,
      code,
      input_data: inputData,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || data.message || "Code run failed.");
  }

  return data;
}

export async function signupUser({ name, email, password }) {
  const response = await fetch(`${API_BASE_URL}/signup`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Signup failed.");
  }

  return data;
}

export async function loginUser({ email, password }) {
  const response = await fetch(`${API_BASE_URL}/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Login failed.");
  }

  return data;
}

export async function getCurrentUser() {
  const response = await fetch(`${API_BASE_URL}/me`, {
    credentials: "include",
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Session expired.");
  }

  return data;
}

export async function logoutUser() {
  const response = await fetch(`${API_BASE_URL}/logout`, {
    method: "POST",
    credentials: "include",
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Logout failed.");
  }

  localStorage.removeItem("smartUser");
  return data;
}

export async function getMyProgress() {
  const response = await fetch(`${API_BASE_URL}/progress/me`, {
    method: "GET",
    credentials: "include",
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Could not load student progress.");
  }

  return data;
}

export async function getMLConsent() {
  const response = await fetch(`${API_BASE_URL}/ml/consent`, {
    method: "GET",
    credentials: "include",
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Could not load ML consent.");
  }

  return data;
}

export async function updateMLConsent(enabled) {
  const response = await fetch(`${API_BASE_URL}/ml/consent`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Could not update ML consent.");
  }

  return data;
}

export async function getPendingMLSamples() {
  const response = await fetch(`${API_BASE_URL}/ml/review/pending`, {
    credentials: "include",
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Could not load pending samples.");
  }

  return data;
}

export async function reviewMLSample(
  sampleId,
  { action, label = null, reviewerNote = "" }
) {
  const response = await fetch(`${API_BASE_URL}/ml/review/${sampleId}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      action,
      label,
      reviewer_note: reviewerNote,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Sample review failed.");
  }

  return data;
}

export async function exportMLSamples() {
  const response = await fetch(`${API_BASE_URL}/ml/review/export`, {
    credentials: "include",
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Could not export approved samples.");
  }

  return data;
}

export async function recordRevisionEvent({
  weakConcept,
  questionId,
  topic,
  language,
  eventKey,
}) {
  const response = await fetch(`${API_BASE_URL}/progress/revision-event`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      weak_concept: weakConcept,
      question_id: questionId,
      topic,
      language,
      event_key: eventKey,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Could not record revision event.");
  }

  return data;
}

export async function getRevisionImprovement() {
  const response = await fetch(
    `${API_BASE_URL}/progress/revision-improvement`,
    {
      method: "GET",
      credentials: "include",
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Could not load revision improvement.");
  }

  return data;
}
