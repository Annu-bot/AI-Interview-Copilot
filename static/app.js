// -------------------------------------------------------------
// AI Interview Copilot - V3 Voice & Adaptive Interview Core
// -------------------------------------------------------------

// Global Application State
let activeSessionId = null;
let activeResumeText = "";
let activeJdText = "";
let currentSessionData = null;
let currentQuestions = [];
let currentQuestionIndex = 0;
let userEvaluations = [];

// Timer State
let timerInterval = null;
let timerSeconds = 0;

// Speech Synthesis (TTS) State
let isSpeakingTts = false;
let autoSpeakEnabled = true;
let synthVoices = [];

// Speech Recognition (STT) State
let recognition = null;
let isRecordingVoice = false;

// Initialize on page load
document.addEventListener("DOMContentLoaded", async () => {
  await refreshHistoryList();
  setupDragAndDrop();
  setupKeyboardShortcuts();
  initSpeechSynthesis();
  initSpeechRecognition();
  loadAutoSpeakPref();
});

// Setup Global Keyboard Shortcuts
function setupKeyboardShortcuts() {
  document.addEventListener("keydown", (e) => {
    // Ctrl + Enter or Cmd + Enter to trigger action
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      const interviewSection = document.getElementById("interviewSection");
      if (interviewSection && !interviewSection.classList.contains("hidden")) {
        const submitBtn = document.getElementById("submitAnswerBtn");
        if (submitBtn && !submitBtn.disabled) {
          submitAnswerForEvaluation();
        }
      } else {
        startInterviewFlow();
      }
    }
  });
}

// -------------------------------------------------------------
// Speech Synthesis (TTS) Engine — AI Speaks Question
// -------------------------------------------------------------
function initSpeechSynthesis() {
  if (!("speechSynthesis" in window)) {
    console.warn("Speech Synthesis is not supported in this browser.");
    const ttsBtn = document.getElementById("ttsPlayBtn");
    if (ttsBtn) ttsBtn.classList.add("hidden");
    return;
  }

  // Load available system voices
  function populateVoices() {
    synthVoices = window.speechSynthesis.getVoices();
  }

  populateVoices();
  if (speechSynthesis.onvoiceschanged !== undefined) {
    speechSynthesis.onvoiceschanged = populateVoices;
  }
}

function getBestEnglishVoice() {
  if (!synthVoices || synthVoices.length === 0) {
    synthVoices = window.speechSynthesis.getVoices();
  }

  // Prefer high quality / natural English voices
  const preferredNames = ["Google US English", "Samantha", "Microsoft David", "Natural", "Daniel", "Karen"];
  for (const name of preferredNames) {
    const found = synthVoices.find((v) => v.name.includes(name) && v.lang.startsWith("en"));
    if (found) return found;
  }

  // Fallback to any English voice
  const enVoice = synthVoices.find((v) => v.lang.startsWith("en"));
  return enVoice || synthVoices[0] || null;
}

// Helper to enable/disable Microphone based on AI speech state
function setMicEnabled(enabled, tooltipMsg = "") {
  const micBtn = document.getElementById("voiceRecordBtn");
  if (!micBtn) return;
  micBtn.disabled = !enabled;
  if (!enabled) {
    micBtn.classList.add("opacity-40", "cursor-not-allowed");
    micBtn.setAttribute("title", tooltipMsg || "Microphone disabled while AI is speaking");
  } else {
    micBtn.classList.remove("opacity-40", "cursor-not-allowed");
    micBtn.setAttribute("title", tooltipMsg || "Click to speak your response");
  }
}

function toggleTtsSpeech() {
  if (isSpeakingTts) {
    stopTtsSpeech();
  } else {
    speakCurrentQuestion();
  }
}

function speakCurrentQuestion() {
  if (!("speechSynthesis" in window)) return;
  stopTtsSpeech();

  if (!currentQuestions || currentQuestionIndex >= currentQuestions.length) return;

  const q = currentQuestions[currentQuestionIndex];
  const textToSpeak = (q.question_text || "").trim();

  if (!textToSpeak) return;

  const utterance = new SpeechSynthesisUtterance(textToSpeak);
  const voice = getBestEnglishVoice();
  if (voice) utterance.voice = voice;

  utterance.rate = 1.0;
  utterance.pitch = 1.0;

  utterance.onstart = () => {
    isSpeakingTts = true;
    updateTtsUi(true);
    setMicEnabled(false, "Microphone locked while AI is speaking...");
  };

  utterance.onend = () => {
    isSpeakingTts = false;
    updateTtsUi(false);
    setMicEnabled(true);
  };

  utterance.onerror = (e) => {
    console.warn("TTS Error:", e);
    isSpeakingTts = false;
    updateTtsUi(false);
    setMicEnabled(true);
  };

  window.speechSynthesis.speak(utterance);
}

function stopTtsSpeech() {
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
  isSpeakingTts = false;
  updateTtsUi(false);
  setMicEnabled(true);
}

function updateTtsUi(speaking) {
  const ttsBtnText = document.getElementById("ttsPlayText");
  const ttsBtnIcon = document.getElementById("ttsPlayIcon");
  const waveVisualizer = document.getElementById("voiceWaveVisualizer");

  if (speaking) {
    if (ttsBtnText) ttsBtnText.textContent = "Stop Voice";
    if (ttsBtnIcon) ttsBtnIcon.setAttribute("data-lucide", "square");
    if (waveVisualizer) {
      waveVisualizer.classList.remove("hidden");
      waveVisualizer.classList.add("wave-active");
    }
  } else {
    if (ttsBtnText) ttsBtnText.textContent = "Speak Question";
    if (ttsBtnIcon) ttsBtnIcon.setAttribute("data-lucide", "volume-2");
    if (waveVisualizer) {
      waveVisualizer.classList.add("hidden");
      waveVisualizer.classList.remove("wave-active");
    }
  }
  if (window.lucide) lucide.createIcons();
}

function toggleAutoSpeakPref() {
  const checkbox = document.getElementById("autoSpeakCheckbox");
  autoSpeakEnabled = checkbox ? checkbox.checked : true;
  localStorage.setItem("interview_copilot_auto_speak", autoSpeakEnabled ? "1" : "0");
}

function loadAutoSpeakPref() {
  const saved = localStorage.getItem("interview_copilot_auto_speak");
  if (saved !== null) {
    autoSpeakEnabled = saved === "1";
    const checkbox = document.getElementById("autoSpeakCheckbox");
    if (checkbox) checkbox.checked = autoSpeakEnabled;
  }
}

// -------------------------------------------------------------
// Speech Recognition (STT) Engine — Candidate Speaks Answer
// -------------------------------------------------------------
function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn("Speech recognition is not supported in this browser.");
    const voiceBtn = document.getElementById("voiceRecordBtn");
    if (voiceBtn) voiceBtn.classList.add("hidden");
    return;
  }

  recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = "en-US";

  recognition.onresult = (event) => {
    let interimTranscript = "";
    let finalTranscript = "";

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finalTranscript += transcript + " ";
      } else {
        interimTranscript += transcript;
      }
    }

    const input = document.getElementById("userAnswerInput");
    if (finalTranscript) {
      input.value = (input.value ? input.value.trim() + " " : "") + finalTranscript.trim();
    }
    updateAnswerWordCount();
  };

  recognition.onerror = (event) => {
    console.warn("Speech recognition error:", event.error);
    stopVoiceRecording();
  };

  recognition.onend = () => {
    if (isRecordingVoice) stopVoiceRecording();
  };
}

function toggleVoiceRecording() {
  if (!recognition) {
    alert("Speech recognition is not supported in your browser. Please try Google Chrome or Microsoft Edge.");
    return;
  }

  if (isRecordingVoice) {
    stopVoiceRecording();
  } else {
    startVoiceRecording();
  }
}

function startVoiceRecording() {
  // Stop AI speech if user starts talking
  stopTtsSpeech();

  try {
    recognition.start();
    isRecordingVoice = true;
    const btn = document.getElementById("voiceRecordBtn");
    if (btn) btn.classList.add("mic-recording");
    const feedback = document.getElementById("sttLiveFeedback");
    if (feedback) feedback.classList.remove("hidden");
  } catch (e) {
    console.error("Could not start speech recognition", e);
  }
}

function stopVoiceRecording() {
  try {
    recognition.stop();
  } catch (e) {}
  isRecordingVoice = false;
  const btn = document.getElementById("voiceRecordBtn");
  if (btn) btn.classList.remove("mic-recording");
  const feedback = document.getElementById("sttLiveFeedback");
  if (feedback) feedback.classList.add("hidden");
}

function clearAnswerInput() {
  document.getElementById("userAnswerInput").value = "";
  updateAnswerWordCount();
}

// -------------------------------------------------------------
// Drag & Drop File Upload Handlers
// -------------------------------------------------------------
function setupDragAndDrop() {
  setupDropZone("resumeDropzone", "resumeFile", "resumeText", "resumeFileStatus");
  setupDropZone("jdDropzone", "jdFile", "jdText", "jdFileStatus");
}

function setupDropZone(dropzoneId, inputId, textId, statusId) {
  const dropzone = document.getElementById(dropzoneId);
  if (!dropzone) return;

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove("dragover");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      const fakeEvent = { target: { files: files } };
      handleFileUpload(fakeEvent, textId, statusId);
    }
  });
}

// Character & Word Counter Helpers
function updateCharCount(textareaId, counterId) {
  const text = document.getElementById(textareaId).value;
  document.getElementById(counterId).textContent = `${text.length} chars`;
}

function updateAnswerWordCount() {
  const text = document.getElementById("userAnswerInput").value.trim();
  const words = text ? text.split(/\s+/).length : 0;
  document.getElementById("answerWordCount").textContent = `${words} words`;
}

// Quick Sample Demo Loader
function loadSampleData() {
  const sampleResume = `SENIOR DISTRIBUTED SYSTEMS ENGINEER
Experience:
- 5+ years designing RESTful APIs and distributed backend services in Python (FastAPI, Django).
- Built relational database schemas in PostgreSQL with SQLAlchemy, optimizing slow queries with indexing.
- Implemented asynchronous worker queues using Redis and Celery for background processing.
- Containerized applications using Docker and configured basic CI/CD pipelines via GitHub Actions.

Technical Skills: Python, FastAPI, Django, PostgreSQL, Redis, Docker, Git, REST APIs, Linux.`;

  const sampleJD = `Senior Backend Engineer (Distributed Systems)
Responsibilities:
- Architect high-throughput, low-latency microservices handling millions of events daily.
- Design event-driven architectures with Apache Kafka or RabbitMQ.
- Lead system decomposition from monolith to microservices and implement distributed caching strategies.
- Manage Kubernetes clusters in AWS (EKS), ensuring 99.99% uptime and auto-scaling.
- Mentor junior engineers and conduct architectural design reviews.

Requirements:
- 5+ years experience in Python or Go.
- Deep expertise in Event-Driven Architecture (Kafka / RabbitMQ).
- Strong knowledge of Distributed Systems (CAP theorem, consensus, caching, sharding).
- Hands-on experience with Kubernetes and AWS.`;

  document.getElementById("resumeText").value = sampleResume;
  document.getElementById("jdText").value = sampleJD;
  updateCharCount("resumeText", "resumeCharCount");
  updateCharCount("jdText", "jdCharCount");
}

// Refresh history count badge
async function refreshHistoryList() {
  try {
    const res = await fetch("/api/v1/sessions");
    if (res.ok) {
      const sessions = await res.json();
      const badge = document.getElementById("historyCountBadge");
      if (sessions.length > 0) {
        badge.textContent = sessions.length;
        badge.classList.remove("hidden");
      } else {
        badge.classList.add("hidden");
      }
    }
  } catch (e) {
    console.warn("Could not fetch session history count", e);
  }
}

// Handle File Upload for Resume / JD
async function handleFileUpload(event, targetTextareaId, statusId) {
  const file = event.target.files[0];
  if (!file) return;

  const statusEl = document.getElementById(statusId);
  statusEl.classList.remove("hidden");
  statusEl.textContent = `Extracting ${file.name}...`;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/v1/parse-document", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to parse document");
    }
    document.getElementById(targetTextareaId).value = data.text;
    statusEl.textContent = `Loaded ${file.name} (${data.character_count} chars)`;
    statusEl.className = "text-xs font-mono text-emerald-400 mt-1";
    
    // Update counters
    if (targetTextareaId === "resumeText") updateCharCount("resumeText", "resumeCharCount");
    if (targetTextareaId === "jdText") updateCharCount("jdText", "jdCharCount");
  } catch (err) {
    statusEl.textContent = `Error: ${err.message}`;
    statusEl.className = "text-xs font-mono text-red-400 mt-1";
  }
}

// -------------------------------------------------------------
// 1-Click Start Interview Flow (Up to 10 Questions with Intro & Stages)
// -------------------------------------------------------------
async function startInterviewFlow() {
  const resumeText = document.getElementById("resumeText").value.trim();
  const jdText = document.getElementById("jdText").value.trim();
  const questionCountSelect = document.getElementById("questionCountSelect");
  const numQuestions = questionCountSelect ? parseInt(questionCountSelect.value, 10) : 10;

  if (!resumeText || !jdText) {
    alert("Please provide both Resume and Job Description (paste text or upload files).");
    return;
  }

  activeResumeText = resumeText;
  activeJdText = jdText;

  showLoading(true, `Analyzing candidate profile & assembling ${numQuestions}-question interview loop...`);

  try {
    const res = await fetch("/api/v1/start-interview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        resume_text: resumeText,
        job_description_text: jdText,
        num_questions: numQuestions,
        session_id: activeSessionId,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to start interview");
    }

    currentSessionData = data;
    activeSessionId = data.session_id;
    currentQuestions = data.questions || [];
    currentQuestionIndex = 0;
    userEvaluations = [];

    // Populate Match Score & Skills in the interview top bar
    populateMatchAndSkills(data);

    // Switch directly into the interview view
    switchToInterviewView();
    loadCurrentQuestion();
    await refreshHistoryList();
    showActiveSessionBanner(`Session #${activeSessionId}`);
  } catch (err) {
    alert(`Failed to start interview: ${err.message}`);
  } finally {
    showLoading(false);
  }
}

// Populate Match Score and Expandable Skills Drawer
function populateMatchAndSkills(data) {
  const fitScore = data.fit_score_percentage || 0;
  document.getElementById("fitScoreDisplay").textContent = `${fitScore}%`;

  // Matched Skills
  const matchedContainer = document.getElementById("matchedSkillsList");
  matchedContainer.innerHTML = "";
  if (!data.matched_skills || data.matched_skills.length === 0) {
    matchedContainer.innerHTML = `<span class="text-xs text-zinc-500">None identified</span>`;
  } else {
    data.matched_skills.forEach((skill) => {
      const tag = document.createElement("span");
      tag.className = "text-xs font-medium px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
      tag.textContent = skill;
      matchedContainer.appendChild(tag);
    });
  }

  // Missing Skills / Gaps
  const missingContainer = document.getElementById("missingSkillsList");
  missingContainer.innerHTML = "";
  if (!data.missing_skills || data.missing_skills.length === 0) {
    missingContainer.innerHTML = `<span class="text-xs text-zinc-500">No major gaps identified</span>`;
  } else {
    data.missing_skills.forEach((skill) => {
      const tag = document.createElement("span");
      tag.className = "text-xs font-medium px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20";
      tag.textContent = skill;
      missingContainer.appendChild(tag);
    });
  }
}

// Toggle Collapsible Skills Drawer
function toggleSkillsDrawer() {
  const drawer = document.getElementById("skillsDrawer");
  const chevron = document.getElementById("skillsChevron");

  if (drawer.classList.contains("hidden")) {
    drawer.classList.remove("hidden");
    chevron.classList.add("rotate-180");
  } else {
    drawer.classList.add("hidden");
    chevron.classList.remove("rotate-180");
  }
  if (window.lucide) lucide.createIcons();
}

// Switch Views to Interview Screen
function switchToInterviewView() {
  document.getElementById("heroSection").classList.add("hidden");
  document.getElementById("inputSection").classList.add("hidden");
  document.getElementById("actionSection").classList.add("hidden");
  document.getElementById("finalSummarySection").classList.add("hidden");
  document.getElementById("interviewSection").classList.remove("hidden");
  if (window.lucide) lucide.createIcons();
}

// Return to Dashboard View
function backToDashboard() {
  stopTimer();
  stopTtsSpeech();
  stopVoiceRecording();

  document.getElementById("heroSection").classList.remove("hidden");
  document.getElementById("inputSection").classList.remove("hidden");
  document.getElementById("actionSection").classList.remove("hidden");
  document.getElementById("interviewSection").classList.add("hidden");
  document.getElementById("finalSummarySection").classList.add("hidden");

  // Restore textarea values
  if (activeResumeText) {
    document.getElementById("resumeText").value = activeResumeText;
    updateCharCount("resumeText", "resumeCharCount");
  }
  if (activeJdText) {
    document.getElementById("jdText").value = activeJdText;
    updateCharCount("jdText", "jdCharCount");
  }

  document.getElementById("inputSection").scrollIntoView({ behavior: "smooth" });
  if (window.lucide) lucide.createIcons();
}

// -------------------------------------------------------------
// Load & Render Current Question with Voice TTS
// -------------------------------------------------------------
function loadCurrentQuestion() {
  stopTtsSpeech();
  stopVoiceRecording();

  if (!currentQuestions || currentQuestions.length === 0) return;

  if (currentQuestionIndex >= currentQuestions.length) {
    showFinalSummary();
    return;
  }

  const q = currentQuestions[currentQuestionIndex];
  document.getElementById("questionCounter").textContent = `${currentQuestionIndex + 1}/${currentQuestions.length}`;
  
  // Render Stage & Category
  const stageBadge = document.getElementById("questionStageBadge");
  if (stageBadge) {
    stageBadge.textContent = q.stage || `Stage ${currentQuestionIndex + 1}: Technical Deep-Dive`;
  }

  document.getElementById("questionCategoryBadge").textContent = q.category || "Technical Assessment";
  document.getElementById("questionDifficultyBadge").textContent = q.difficulty || "Medium";
  document.getElementById("targetSkillDisplay").textContent = `Target: ${q.target_skill_or_topic || "Core Topic"}`;
  document.getElementById("currentQuestionText").textContent = q.question_text || "";

  // Progress Bar
  const progressPercent = Math.round(((currentQuestionIndex + 1) / currentQuestions.length) * 100);
  const progressBarFill = document.getElementById("progressBarFill");
  if (progressBarFill) progressBarFill.style.width = `${progressPercent}%`;

  // Start question timer
  startTimer();

  // Check if answer was already evaluated for this question
  const existingEval = userEvaluations.find((e) => e.question_id === q.id || (e.question && e.question.id === q.id));

  if (existingEval) {
    document.getElementById("userAnswerInput").value = existingEval.user_answer || existingEval.answer || "";
    document.getElementById("userAnswerInput").disabled = true;
    document.getElementById("submitAnswerBtn").disabled = true;
    setMicEnabled(false, "Question already evaluated");
    updateAnswerWordCount();
    renderEvaluation(existingEval.evaluation || existingEval);
  } else {
    document.getElementById("userAnswerInput").value = "";
    document.getElementById("userAnswerInput").disabled = false;
    document.getElementById("submitAnswerBtn").disabled = false;
    document.getElementById("liveEvaluationCard").classList.add("hidden");
    updateAnswerWordCount();

    // Auto-Speak Question via TTS if enabled
    if (autoSpeakEnabled) {
      setMicEnabled(false, "Microphone disabled while AI is speaking...");
      setTimeout(() => {
        speakCurrentQuestion();
      }, 400);
    } else {
      setMicEnabled(true);
    }
  }

  document.getElementById("interviewSection").scrollIntoView({ behavior: "smooth" });
  if (window.lucide) lucide.createIcons();
}

// Submit Typed Answer for Live Evaluation
async function submitAnswerForEvaluation() {
  const userAnswer = document.getElementById("userAnswerInput").value.trim();
  if (!userAnswer) {
    alert("Please provide your response before submitting.");
    return;
  }

  stopTimer();
  stopTtsSpeech();
  stopVoiceRecording();
  setMicEnabled(false);

  const q = currentQuestions[currentQuestionIndex];

  showLoading(true, "Staff Engineer Evaluator is scoring your response...");

  try {
    const res = await fetch("/api/v1/evaluate-answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question_text: q.question_text,
        evaluation_criteria: q.evaluation_criteria,
        user_answer: userAnswer,
        target_skill_or_topic: q.target_skill_or_topic,
        session_id: activeSessionId,
        question_id: q.id,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to evaluate answer");
    }

    const evalData = data.evaluation;
    userEvaluations.push({
      question_id: q.id,
      question: q,
      answer: userAnswer,
      evaluation: evalData,
    });

    renderEvaluation(evalData);
  } catch (err) {
    alert(`Evaluation failed: ${err.message}`);
    setMicEnabled(true);
  } finally {
    showLoading(false);
  }
}

// Render Evaluation Feedback Card
function renderEvaluation(evalData) {
  const evalCard = document.getElementById("liveEvaluationCard");
  evalCard.classList.remove("hidden");

  document.getElementById("userAnswerInput").disabled = true;
  document.getElementById("submitAnswerBtn").disabled = true;
  setMicEnabled(false, "Question already evaluated");

  const score = evalData.score_out_of_10 || 0;
  const scoreBox = document.getElementById("evalScoreBox");
  scoreBox.textContent = Number(score).toFixed(1);

  const scoreLabel = document.getElementById("evalScoreLabel");
  if (score >= 8.5) {
    scoreLabel.textContent = "Exceptional / Senior Level";
    scoreBox.className = "w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-lg font-mono font-bold text-emerald-400";
  } else if (score >= 7.0) {
    scoreLabel.textContent = "Solid Response (Proficient)";
    scoreBox.className = "w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-lg font-mono font-bold text-blue-400";
  } else if (score >= 5.0) {
    scoreLabel.textContent = "Average (Needs More Depth)";
    scoreBox.className = "w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-lg font-mono font-bold text-amber-400";
  } else {
    scoreLabel.textContent = "Weak / Significant Gaps";
    scoreBox.className = "w-12 h-12 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center justify-center text-lg font-mono font-bold text-red-400";
  }

  // Strengths
  const strengthsList = document.getElementById("evalStrengthsList");
  strengthsList.innerHTML = "";
  (evalData.strengths || []).forEach((s) => {
    const li = document.createElement("li");
    li.textContent = s;
    strengthsList.appendChild(li);
  });

  // Missing Points
  const gapsList = document.getElementById("evalGapsList");
  gapsList.innerHTML = "";
  (evalData.missing_points_and_gaps || []).forEach((g) => {
    const li = document.createElement("li");
    li.textContent = g;
    gapsList.appendChild(li);
  });

  // Feedback & Model Answer
  document.getElementById("evalDetailedFeedback").textContent = evalData.detailed_feedback || "";
  document.getElementById("evalModelAnswer").textContent = evalData.ideal_model_answer || "";

  // Pro Tips
  const tipsList = document.getElementById("evalTipsList");
  tipsList.innerHTML = "";
  (evalData.interview_tips || []).forEach((t) => {
    const li = document.createElement("li");
    li.textContent = t;
    tipsList.appendChild(li);
  });

  evalCard.scrollIntoView({ behavior: "smooth" });
  if (window.lucide) lucide.createIcons();
}

// Copy Benchmark Answer
function copyModelAnswer() {
  const modelAnswer = document.getElementById("evalModelAnswer").textContent;
  if (!modelAnswer) return;

  navigator.clipboard.writeText(modelAnswer).then(() => {
    const copyBtnText = document.getElementById("copyBtnText");
    copyBtnText.textContent = "Copied!";
    setTimeout(() => {
      copyBtnText.textContent = "Copy Answer";
    }, 2000);
  });
}

// Next Question
function nextQuestion() {
  currentQuestionIndex++;
  loadCurrentQuestion();
}

// Final Summary Screen
function showFinalSummary() {
  stopTimer();
  stopTtsSpeech();
  stopVoiceRecording();

  document.getElementById("interviewSection").classList.add("hidden");
  document.getElementById("finalSummarySection").classList.remove("hidden");
  if (window.lucide) lucide.createIcons();
}

// Reset / Start Fresh Session
function createNewSession() {
  stopTimer();
  stopTtsSpeech();
  stopVoiceRecording();

  activeSessionId = null;
  activeResumeText = "";
  activeJdText = "";
  currentSessionData = null;
  currentQuestions = [];
  currentQuestionIndex = 0;
  userEvaluations = [];

  document.getElementById("resumeText").value = "";
  document.getElementById("jdText").value = "";
  document.getElementById("resumeFileStatus").classList.add("hidden");
  document.getElementById("jdFileStatus").classList.add("hidden");
  document.getElementById("interviewSection").classList.add("hidden");
  document.getElementById("finalSummarySection").classList.add("hidden");
  document.getElementById("activeSessionBanner").classList.add("hidden");

  updateCharCount("resumeText", "resumeCharCount");
  updateCharCount("jdText", "jdCharCount");

  document.getElementById("heroSection").classList.remove("hidden");
  document.getElementById("inputSection").classList.remove("hidden");
  document.getElementById("actionSection").classList.remove("hidden");

  window.scrollTo({ top: 0, behavior: "smooth" });
  if (window.lucide) lucide.createIcons();
}

// Show Active Session Banner
function showActiveSessionBanner(title) {
  const banner = document.getElementById("activeSessionBanner");
  banner.classList.remove("hidden");
  document.getElementById("activeSessionTitle").textContent = title;
  document.getElementById("activeSessionDate").textContent = `Session ID: ${activeSessionId}`;
  if (window.lucide) lucide.createIcons();
}

// Live Question Timer Logic
function startTimer() {
  stopTimer();
  timerSeconds = 0;
  updateTimerDisplay();
  timerInterval = setInterval(() => {
    timerSeconds++;
    updateTimerDisplay();
  }, 1000);
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

function updateTimerDisplay() {
  const mins = Math.floor(timerSeconds / 60);
  const secs = timerSeconds % 60;
  const timerEl = document.getElementById("questionTimer");
  if (timerEl) {
    timerEl.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }
}

// -------------------------------------------------------------
// Session History Modal & Restoration
// -------------------------------------------------------------
async function openHistoryModal() {
  const modal = document.getElementById("historyModal");
  modal.classList.remove("hidden");

  const container = document.getElementById("historyListContainer");
  container.innerHTML = `<div class="text-center py-8 text-zinc-400 text-xs">Loading sessions...</div>`;

  try {
    const res = await fetch("/api/v1/sessions");
    const sessions = await res.json();

    if (!sessions || sessions.length === 0) {
      container.innerHTML = `<div class="text-center py-12 text-zinc-500 text-xs">No saved sessions yet.<br>Start an interview to save one!</div>`;
      return;
    }

    container.innerHTML = "";
    sessions.forEach((s) => {
      const card = document.createElement("div");
      card.className = "surface-card rounded-lg p-3.5 space-y-2 transition group hover:border-blue-500/40";
      card.innerHTML = `
        <div class="flex items-center justify-between">
          <div class="text-xs font-semibold text-white flex items-center gap-1.5">
            <span class="px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300 font-mono text-[10px]">#${s.id}</span>
            <span>${s.role_title || "Engineering Candidate"}</span>
          </div>
          <span class="text-[11px] font-mono font-bold text-blue-400 bg-blue-950/40 px-2 py-0.5 rounded border border-blue-500/20">${s.fit_score_percentage}% Match</span>
        </div>
        <div class="text-[10px] text-zinc-400 font-mono">${s.created_at}</div>
        <p class="text-xs text-zinc-300 line-clamp-2">${s.resume_snippet}</p>
        <div class="flex items-center justify-between pt-2 border-t border-zinc-800/80">
          <button onclick="restoreSession(${s.id})" class="text-xs font-medium text-blue-400 hover:text-blue-300 flex items-center gap-1">
            <i data-lucide="rotate-ccw" class="w-3 h-3"></i> Resume Session
          </button>
          <button onclick="deleteSession(${s.id}, event)" class="text-xs text-red-400/70 hover:text-red-400 p-1">
            <i data-lucide="trash-2" class="w-3 h-3"></i>
          </button>
        </div>
      `;
      container.appendChild(card);
    });

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    container.innerHTML = `<div class="text-center py-8 text-red-400 text-xs">Failed to load history: ${err.message}</div>`;
  }
}

function closeHistoryModal() {
  document.getElementById("historyModal").classList.add("hidden");
}

function closeHistoryModalOnBackdrop(event) {
  if (event.target.id === "historyModal") {
    closeHistoryModal();
  }
}

// Restore a past session from SQLite Database
async function restoreSession(sessionId) {
  showLoading(true, `Restoring Session #${sessionId}...`);
  closeHistoryModal();

  try {
    const res = await fetch(`/api/v1/sessions/${sessionId}`);
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Could not load session");
    }

    activeSessionId = data.id;
    activeResumeText = data.resume_text || "";
    activeJdText = data.jd_text || "";
    currentQuestions = data.questions ? data.questions.questions : [];
    currentQuestionIndex = 0;
    userEvaluations = data.evaluations || [];

    document.getElementById("resumeText").value = activeResumeText;
    document.getElementById("jdText").value = activeJdText;
    updateCharCount("resumeText", "resumeCharCount");
    updateCharCount("jdText", "jdCharCount");

    if (data.analysis) {
      populateMatchAndSkills(data.analysis);
    } else {
      populateMatchAndSkills({ fit_score_percentage: data.fit_score_percentage, matched_skills: [], missing_skills: [] });
    }

    if (currentQuestions.length > 0) {
      switchToInterviewView();
      loadCurrentQuestion();
    } else {
      backToDashboard();
    }

    showActiveSessionBanner(`Restored Session #${sessionId}`);
  } catch (err) {
    alert(`Failed to restore session: ${err.message}`);
  } finally {
    showLoading(false);
  }
}

// Delete session from DB
async function deleteSession(sessionId, event) {
  if (event) event.stopPropagation();
  if (!confirm(`Delete interview session #${sessionId}?`)) return;

  try {
    const res = await fetch(`/api/v1/sessions/${sessionId}`, { method: "DELETE" });
    if (res.ok) {
      if (activeSessionId === sessionId) {
        createNewSession();
      }
      await openHistoryModal();
      await refreshHistoryList();
    }
  } catch (err) {
    alert("Could not delete session: " + err.message);
  }
}

// Helper: Toggle Loading Spinner
function showLoading(show, message = "Processing...") {
  const spinner = document.getElementById("loadingIndicator");
  const msgEl = document.getElementById("loadingMessage");
  if (show) {
    msgEl.textContent = message;
    spinner.classList.remove("hidden");
  } else {
    spinner.classList.add("hidden");
  }
}
