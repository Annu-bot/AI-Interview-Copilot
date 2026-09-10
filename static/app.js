// Global Application State
let activeSessionId = null;
let activeResumeText = "";
let activeJdText = "";
let currentSessionData = null;
let currentQuestions = [];
let currentQuestionIndex = 0;
let userEvaluations = [];

// Initialize on page load
document.addEventListener("DOMContentLoaded", async () => {
  await refreshHistoryList();
});

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
    statusEl.textContent = `✓ Extracted ${data.character_count} chars from ${file.name}`;
    statusEl.className = "text-xs text-emerald-400";
  } catch (err) {
    statusEl.textContent = `⚠ ${err.message}`;
    statusEl.className = "text-xs text-red-400";
  }
}

// 1-Click Start Interview Flow
async function startInterviewFlow() {
  const resumeText = document.getElementById("resumeText").value.trim();
  const jdText = document.getElementById("jdText").value.trim();

  if (!resumeText || !jdText) {
    alert("Please provide both Resume and Job Description (paste text or upload files).");
    return;
  }

  activeResumeText = resumeText;
  activeJdText = jdText;

  showLoading(true, "AI is calculating skill match score & generating customized interview questions...");

  try {
    const res = await fetch("/api/v1/start-interview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        resume_text: resumeText,
        job_description_text: jdText,
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
    showActiveSessionBanner(`Active Interview: Session #${activeSessionId}`);
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
    matchedContainer.innerHTML = `<span class="text-xs text-slate-500">None identified</span>`;
  } else {
    data.matched_skills.forEach((skill) => {
      const tag = document.createElement("span");
      tag.className = "text-xs font-semibold px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-300 border border-emerald-500/20";
      tag.textContent = `✓ ${skill}`;
      matchedContainer.appendChild(tag);
    });
  }

  // Missing Skills / Gaps
  const missingContainer = document.getElementById("missingSkillsList");
  missingContainer.innerHTML = "";
  if (!data.missing_skills || data.missing_skills.length === 0) {
    missingContainer.innerHTML = `<span class="text-xs text-slate-500">No major gaps identified</span>`;
  } else {
    data.missing_skills.forEach((skill) => {
      const tag = document.createElement("span");
      tag.className = "text-xs font-semibold px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-300 border border-amber-500/20";
      tag.textContent = `⚠ ${skill}`;
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

// Return to Dashboard View (Preserves all Resume & JD inputs!)
function backToDashboard() {
  document.getElementById("heroSection").classList.remove("hidden");
  document.getElementById("inputSection").classList.remove("hidden");
  document.getElementById("actionSection").classList.remove("hidden");
  document.getElementById("interviewSection").classList.add("hidden");
  document.getElementById("finalSummarySection").classList.add("hidden");

  // Restore textarea values
  if (activeResumeText) document.getElementById("resumeText").value = activeResumeText;
  if (activeJdText) document.getElementById("jdText").value = activeJdText;

  document.getElementById("inputSection").scrollIntoView({ behavior: "smooth" });
  if (window.lucide) lucide.createIcons();
}

// Load Current Question
function loadCurrentQuestion() {
  if (!currentQuestions || currentQuestions.length === 0) {
    return;
  }

  if (currentQuestionIndex >= currentQuestions.length) {
    showFinalSummary();
    return;
  }

  const q = currentQuestions[currentQuestionIndex];
  document.getElementById("questionCounter").textContent = `${currentQuestionIndex + 1}/${currentQuestions.length}`;
  document.getElementById("questionCategoryBadge").textContent = q.category || "Technical Interview";
  document.getElementById("questionDifficultyBadge").textContent = q.difficulty || "Medium";
  document.getElementById("targetSkillDisplay").textContent = `Target: ${q.target_skill_or_topic || "Core Topic"}`;
  document.getElementById("currentQuestionText").textContent = q.question_text || "";

  // Check if answer was already evaluated for this question
  const existingEval = userEvaluations.find((e) => e.question_id === q.id || (e.question && e.question.id === q.id));

  if (existingEval) {
    document.getElementById("userAnswerInput").value = existingEval.user_answer || existingEval.answer || "";
    document.getElementById("userAnswerInput").disabled = true;
    document.getElementById("submitAnswerBtn").disabled = true;
    renderEvaluation(existingEval.evaluation || existingEval);
  } else {
    document.getElementById("userAnswerInput").value = "";
    document.getElementById("userAnswerInput").disabled = false;
    document.getElementById("submitAnswerBtn").disabled = false;
    document.getElementById("liveEvaluationCard").classList.add("hidden");
  }

  document.getElementById("interviewSection").scrollIntoView({ behavior: "smooth" });
  if (window.lucide) lucide.createIcons();
}

// Submit Typed Answer for Live Evaluation
async function submitAnswerForEvaluation() {
  const userAnswer = document.getElementById("userAnswerInput").value.trim();
  if (!userAnswer) {
    alert("Please type your response before submitting.");
    return;
  }

  const q = currentQuestions[currentQuestionIndex];

  showLoading(true, "Staff Engineer Evaluator is scoring your response & saving to history...");

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

  const score = evalData.score_out_of_10 || 0;
  const scoreBox = document.getElementById("evalScoreBox");
  scoreBox.textContent = Number(score).toFixed(1);

  const scoreLabel = document.getElementById("evalScoreLabel");
  if (score >= 8.5) {
    scoreLabel.textContent = "Exceptional / Senior Level";
    scoreBox.className = "w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-xl font-black text-emerald-400";
  } else if (score >= 7.0) {
    scoreLabel.textContent = "Solid Response (Proficient)";
    scoreBox.className = "w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-xl font-black text-indigo-400";
  } else if (score >= 5.0) {
    scoreLabel.textContent = "Average (Needs More Depth)";
    scoreBox.className = "w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-xl font-black text-amber-400";
  } else {
    scoreLabel.textContent = "Weak / Significant Gaps";
    scoreBox.className = "w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/30 flex items-center justify-center text-xl font-black text-red-400";
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

// Next Question
function nextQuestion() {
  currentQuestionIndex++;
  loadCurrentQuestion();
}

// Final Summary Screen
function showFinalSummary() {
  document.getElementById("interviewSection").classList.add("hidden");
  document.getElementById("finalSummarySection").classList.remove("hidden");
  if (window.lucide) lucide.createIcons();
}

// Reset / Start Fresh Session
function createNewSession() {
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

// ==========================================
// Session History Modal & Restoration
// ==========================================
async function openHistoryModal() {
  const modal = document.getElementById("historyModal");
  modal.classList.remove("hidden");

  const container = document.getElementById("historyListContainer");
  container.innerHTML = `<div class="text-center py-8 text-slate-400 text-sm">Loading past sessions...</div>`;

  try {
    const res = await fetch("/api/v1/sessions");
    const sessions = await res.json();

    if (!sessions || sessions.length === 0) {
      container.innerHTML = `<div class="text-center py-12 text-slate-500 text-sm">No saved sessions yet.<br>Start an interview to save one!</div>`;
      return;
    }

    container.innerHTML = "";
    sessions.forEach((s) => {
      const card = document.createElement("div");
      card.className = "bg-slate-950/80 border border-slate-800 hover:border-indigo-500/40 rounded-xl p-4 space-y-2 transition group";
      card.innerHTML = `
        <div class="flex items-center justify-between">
          <div class="text-xs font-bold text-white flex items-center gap-1.5">
            <span class="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono">#${s.id}</span>
            <span>${s.role_title || "Engineering Candidate"}</span>
          </div>
          <span class="text-xs font-black text-indigo-400 bg-indigo-950/60 px-2 py-0.5 rounded-lg border border-indigo-500/20">${s.fit_score_percentage}% Match</span>
        </div>
        <div class="text-[11px] text-slate-400">${s.created_at}</div>
        <p class="text-xs text-slate-300 line-clamp-2">${s.resume_snippet}</p>
        <div class="flex items-center justify-between pt-2 border-t border-slate-800/80">
          <button onclick="restoreSession(${s.id})" class="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
            <i data-lucide="rotate-ccw" class="w-3.5 h-3.5"></i> Launch / Resume
          </button>
          <button onclick="deleteSession(${s.id}, event)" class="text-xs text-red-400/80 hover:text-red-400 p-1">
            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
          </button>
        </div>
      `;
      container.appendChild(card);
    });

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    container.innerHTML = `<div class="text-center py-8 text-red-400 text-sm">Failed to load history: ${err.message}</div>`;
  }
}

function closeHistoryModal() {
  document.getElementById("historyModal").classList.add("hidden");
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

    showActiveSessionBanner(`Restored Session #${sessionId} (${data.created_at})`);
  } catch (err) {
    alert(`Failed to restore session: ${err.message}`);
  } finally {
    showLoading(false);
  }
}

// Delete session from DB
async function deleteSession(sessionId, event) {
  if (event) event.stopPropagation();
  if (!confirm(`Are you sure you want to delete session #${sessionId}?`)) return;

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
