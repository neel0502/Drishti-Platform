// Persistent role-scoped voice/text command layer for Drishti.
(function () {
  const state = { cases: [], selectedCaseId: null, recognition: null, speaking: false, progressTimer: null, lastRoute: null, lastResult: null, returnFocus: null, voiceFailed: false };
  const copy = {
    en: {
      kicker: "DRISHTI COMMAND ASSISTANT", title: "What should we check?", context: "Role-scoped · source-linked · officer decides",
      ready: "Ready", readyDetail: "Ask about your shift, an FIR, evidence, timeline or linked cases.", case: "Case context",
      select: "Select an FIR when needed", speak: "Speak", stop: "Stop", run: "Check records",
      boundary: "Drishti prepares a draft. It cannot dispatch, contact, alter records or approve action.",
      noCase: "Select an FIR or say its FIR number before asking for a case review.", notAllowed: "That workflow is not available for this police role.",
      checking: "Checking approved records", checkingDetail: "Reading only the minimum records allowed for this role.",
      challenging: "Challenging weak findings", challengingDetail: "The Skeptic is separating recorded facts from uncertain leads.",
      drafting: "Preparing officer draft", draftingDetail: "No action is executed. The result remains editable and unapproved.",
      complete: "Draft ready for officer review", completeDetail: "Sources and uncertainty are shown below.",
      failed: "Review remained unavailable", failedDetail: "No record was changed. Try again or open Police Tasks.",
      brief: "Officer brief", findings: "Source-linked findings", sources: "Records checked", decision: "Officer decision required",
      decisionDetail: "Verify the cited records, edit the draft if needed, then accept, reject or request supervisor review.",
      openTasks: "Open full Police Task", openCase: "Open FIR", read: "Read briefing", stopReading: "Stop reading", fallback: "Validated fallback",
      navigated: "Workspace opened", navigatedDetail: "Drishti navigated without changing any police record.",
      listening: "Listening", listeningDetail: "Speak naturally in English or Kannada. Review the text before running.", confidence: "confidence after record checks",
      voiceUnavailable: "Voice input is not supported in this browser. Type the command instead."
    },
    kn: {
      kicker: "ದೃಷ್ಟಿ ಕಮಾಂಡ್ ಸಹಾಯಕ", title: "ಏನು ಪರಿಶೀಲಿಸಬೇಕು?", context: "ಪಾತ್ರ-ಮಿತ · ಮೂಲ-ಸಂಬಂಧಿತ · ಅಧಿಕಾರಿ ನಿರ್ಧಾರ",
      ready: "ಸಿದ್ಧ", readyDetail: "ನಿಮ್ಮ ಪಾಳಿ, ಎಫ್‌ಐಆರ್, ಸಾಕ್ಷ್ಯ, ಕಾಲಕ್ರಮ ಅಥವಾ ಸಂಬಂಧಿತ ಪ್ರಕರಣಗಳ ಬಗ್ಗೆ ಕೇಳಿ.", case: "ಪ್ರಕರಣ ಸಂದರ್ಭ",
      select: "ಅಗತ್ಯವಿದ್ದಾಗ ಎಫ್‌ಐಆರ್ ಆಯ್ಕೆಮಾಡಿ", speak: "ಮಾತನಾಡಿ", stop: "ನಿಲ್ಲಿಸಿ", run: "ದಾಖಲೆ ಪರಿಶೀಲಿಸಿ",
      boundary: "ದೃಷ್ಟಿ ಕರಡು ಸಿದ್ಧಪಡಿಸುತ್ತದೆ. ಅದು ನಿಯೋಜನೆ, ಸಂಪರ್ಕ, ದಾಖಲೆ ಬದಲಾವಣೆ ಅಥವಾ ಕ್ರಮ ಅನುಮೋದನೆ ಮಾಡಲಾರದು.",
      noCase: "ಪ್ರಕರಣ ಪರಿಶೀಲನೆಗೆ ಎಫ್‌ಐಆರ್ ಆಯ್ಕೆಮಾಡಿ ಅಥವಾ ಅದರ ಸಂಖ್ಯೆಯನ್ನು ಹೇಳಿ.", notAllowed: "ಈ ಪೊಲೀಸ್ ಪಾತ್ರಕ್ಕೆ ಆ ಕಾರ್ಯಪ್ರವಾಹ ಲಭ್ಯವಿಲ್ಲ.",
      checking: "ಅನುಮೋದಿತ ದಾಖಲೆ ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ", checkingDetail: "ಈ ಪಾತ್ರಕ್ಕೆ ಅನುಮತಿಸಿದ ಕನಿಷ್ಠ ದಾಖಲೆಗಳನ್ನು ಮಾತ್ರ ಓದುತ್ತಿದೆ.",
      challenging: "ದುರ್ಬಲ ಕಂಡುಹಿಡಿಕೆ ಪ್ರಶ್ನಿಸಲಾಗುತ್ತಿದೆ", challengingDetail: "ದಾಖಲಿತ ವಾಸ್ತವಾಂಶಗಳನ್ನು ಅನಿಶ್ಚಿತ ಸುಳಿವುಗಳಿಂದ ಬೇರ್ಪಡಿಸಲಾಗುತ್ತಿದೆ.",
      drafting: "ಅಧಿಕಾರಿ ಕರಡು ಸಿದ್ಧವಾಗುತ್ತಿದೆ", draftingDetail: "ಯಾವ ಕ್ರಮವೂ ಜಾರಿಯಾಗುವುದಿಲ್ಲ. ಫಲಿತಾಂಶ ಸಂಪಾದಿಸಬಹುದಾದ ಮತ್ತು ಅನುಮೋದಿಸದ ಕರಡು.",
      complete: "ಅಧಿಕಾರಿ ಪರಿಶೀಲನೆಗೆ ಕರಡು ಸಿದ್ಧ", completeDetail: "ಮೂಲಗಳು ಮತ್ತು ಅನಿಶ್ಚಿತತೆ ಕೆಳಗೆ ತೋರಿಸಲಾಗಿದೆ.",
      failed: "ಪರಿಶೀಲನೆ ಲಭ್ಯವಾಗಲಿಲ್ಲ", failedDetail: "ಯಾವ ದಾಖಲೆಯೂ ಬದಲಾಗಿಲ್ಲ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ ಅಥವಾ ಪೊಲೀಸ್ ಕಾರ್ಯ ತೆರೆಯಿರಿ.",
      brief: "ಅಧಿಕಾರಿ ಮಾಹಿತಿ", findings: "ಮೂಲ-ಸಂಬಂಧಿತ ಕಂಡುಹಿಡಿಕೆಗಳು", sources: "ಪರಿಶೀಲಿಸಿದ ದಾಖಲೆಗಳು", decision: "ಅಧಿಕಾರಿ ನಿರ್ಧಾರ ಅಗತ್ಯ",
      decisionDetail: "ಉಲ್ಲೇಖಿತ ದಾಖಲೆಗಳನ್ನು ಪರಿಶೀಲಿಸಿ, ಕರಡು ತಿದ್ದುಪಡಿ ಮಾಡಿ, ನಂತರ ಸ್ವೀಕರಿಸಿ, ತಿರಸ್ಕರಿಸಿ ಅಥವಾ ಮೇಲ್ವಿಚಾರಕ ಪರಿಶೀಲನೆ ಕೋರಿರಿ.",
      openTasks: "ಪೂರ್ಣ ಪೊಲೀಸ್ ಕಾರ್ಯ ತೆರೆಯಿರಿ", openCase: "ಎಫ್‌ಐಆರ್ ತೆರೆಯಿರಿ", read: "ಮಾಹಿತಿ ಓದಿ", stopReading: "ಓದುವುದನ್ನು ನಿಲ್ಲಿಸಿ", fallback: "ಪರಿಶೀಲಿತ ಪರ್ಯಾಯ",
      navigated: "ಕಾರ್ಯಸ್ಥಳ ತೆರೆಯಿತು", navigatedDetail: "ಯಾವ ಪೊಲೀಸ್ ದಾಖಲೆಯನ್ನೂ ಬದಲಿಸದೆ ದೃಷ್ಟಿ ಪುಟ ತೆರೆಯಿತು.",
      listening: "ಆಲಿಸಲಾಗುತ್ತಿದೆ", listeningDetail: "ಇಂಗ್ಲಿಷ್ ಅಥವಾ ಕನ್ನಡದಲ್ಲಿ ಸಹಜವಾಗಿ ಮಾತನಾಡಿ. ಚಾಲನೆಗೆ ಮೊದಲು ಪಠ್ಯ ಪರಿಶೀಲಿಸಿ.", confidence: "ದಾಖಲೆ ಪರಿಶೀಲನೆಯ ನಂತರ ವಿಶ್ವಾಸ",
      voiceUnavailable: "ಈ ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಧ್ವನಿ ಇನ್‌ಪುಟ್ ಲಭ್ಯವಿಲ್ಲ. ಬದಲಿಗೆ ಕಮಾಂಡ್ ಟೈಪ್ ಮಾಡಿ."
    }
  };
  const roleLabels = {
    en: { command: "State Command", district: "District SP", station: "Station Officer", patrol: "Patrol Supervisor", analyst: "Crime Analyst" },
    kn: { command: "ರಾಜ್ಯ ಕಮಾಂಡ್", district: "ಜಿಲ್ಲಾ ಎಸ್ಪಿ", station: "ಠಾಣಾ ಅಧಿಕಾರಿ", patrol: "ಗಸ್ತು ಮೇಲ್ವಿಚಾರಕ", analyst: "ಅಪರಾಧ ವಿಶ್ಲೇಷಕ" }
  };
  const suggestions = {
    en: {
      command: ["Brief me for today", "Prepare supervisor review", "Check cross-district links"],
      district: ["Brief me for today", "What evidence is missing?", "Prepare SP review"],
      station: ["What evidence is missing?", "Check the timeline", "Review and structure this FIR"],
      patrol: ["Brief me for this patrol shift", "What locations need confirmation?"],
      analyst: ["Why may these FIRs be linked?", "Challenge this connection", "Check conflicting records"]
    },
    kn: {
      command: ["ಇಂದಿನ ಮಾಹಿತಿ ನೀಡಿ", "ಮೇಲ್ವಿಚಾರಕ ಪರಿಶೀಲನೆ ಸಿದ್ಧಪಡಿಸಿ", "ಅಂತರ-ಜಿಲ್ಲಾ ಸಂಪರ್ಕ ಪರಿಶೀಲಿಸಿ"],
      district: ["ಇಂದಿನ ಮಾಹಿತಿ ನೀಡಿ", "ಯಾವ ಸಾಕ್ಷ್ಯ ಕಾಣೆಯಾಗಿದೆ?", "ಎಸ್ಪಿ ಪರಿಶೀಲನೆ ಸಿದ್ಧಪಡಿಸಿ"],
      station: ["ಯಾವ ಸಾಕ್ಷ್ಯ ಕಾಣೆಯಾಗಿದೆ?", "ಕಾಲಕ್ರಮ ಪರಿಶೀಲಿಸಿ", "ಈ ಎಫ್‌ಐಆರ್ ಕರಡು ಪರಿಶೀಲಿಸಿ"],
      patrol: ["ಈ ಗಸ್ತು ಪಾಳಿಯ ಮಾಹಿತಿ ನೀಡಿ", "ಯಾವ ಸ್ಥಳಗಳಿಗೆ ದೃಢೀಕರಣ ಬೇಕು?"],
      analyst: ["ಈ ಎಫ್‌ಐಆರ್‌ಗಳು ಏಕೆ ಸಂಬಂಧಿತವಾಗಿರಬಹುದು?", "ಈ ಸಂಪರ್ಕವನ್ನು ಪ್ರಶ್ನಿಸಿ", "ವಿರೋಧಿ ದಾಖಲೆ ಪರಿಶೀಲಿಸಿ"]
    }
  };
  const safe = value => String(value ?? "").replace(/[&<>'"]/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
  const language = () => document.body.dataset.language === "kn" ? "kn" : "en";
  const t = key => copy[language()][key] || copy.en[key] || key;
  const role = () => {
    const value = document.getElementById("role-select")?.value || "station";
    return ["command", "district", "station", "patrol", "analyst"].includes(value) ? value : "station";
  };

  document.addEventListener("DOMContentLoaded", () => {
    bindAssistant();
    loadCases();
    applyCopy();
  });

  function bindAssistant() {
    document.getElementById("command-orb").addEventListener("click", openAssistant);
    document.getElementById("command-assistant-close").addEventListener("click", closeAssistant);
    document.getElementById("command-assistant-scrim").addEventListener("click", closeAssistant);
    document.getElementById("command-run").addEventListener("click", runCommand);
    document.getElementById("command-mic").addEventListener("click", toggleVoice);
    document.getElementById("command-case-select").addEventListener("change", event => { state.selectedCaseId = Number(event.target.value) || null; });
    document.getElementById("role-select").addEventListener("change", () => { applyCopy(); renderSuggestions(); applyRoleBoundary(); });
    document.getElementById("language-switch").addEventListener("click", () => setTimeout(applyCopy, 0));
    document.addEventListener("drishti:case-opened", event => {
      state.selectedCaseId = Number(event.detail?.caseId) || null;
      syncCaseSelect();
    });
    document.addEventListener("keydown", event => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "j") { event.preventDefault(); openAssistant(); return; }
      if (event.key === "Escape" && document.getElementById("command-assistant").classList.contains("open")) closeAssistant();
      if (event.key === "Tab" && document.getElementById("command-assistant").classList.contains("open")) trapFocus(event);
    });
    document.getElementById("command-input").addEventListener("keydown", event => {
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") { event.preventDefault(); runCommand(); }
    });
  }

  async function loadCases() {
    try {
      const response = await fetch("/api/reconstruction-options?limit=40", { cache: "no-store" });
      const data = await response.json();
      state.cases = data.cases || [];
      const active = Number(window.DrishtiWorkspace?.getActiveCaseId?.()) || null;
      state.selectedCaseId = active;
      renderCases();
    } catch (_) { state.cases = []; renderCases(); }
  }

  function applyCopy() {
    document.getElementById("command-assistant-kicker").textContent = t("kicker");
    document.getElementById("command-assistant-title").textContent = t("title");
    document.getElementById("command-assistant-context").textContent = t("context");
    document.querySelector("#command-case-label > span").textContent = t("case");
    document.getElementById("command-input").placeholder = language() === "kn" ? "ದೃಷ್ಟಿ, ಈ ಎಫ್‌ಐಆರ್‌ನಲ್ಲಿ ಯಾವ ಸಾಕ್ಷ್ಯ ಕಾಣೆಯಾಗಿದೆ?" : "Drishti, what evidence is missing in this FIR?";
    document.querySelector("#command-mic small").textContent = t("speak");
    document.getElementById("command-run").textContent = t("run");
    document.getElementById("command-boundary").textContent = t("boundary");
    document.getElementById("command-role-chip").textContent = roleLabels[language()][role()];
    renderCases(); renderSuggestions(); applyRoleBoundary();
    if (!document.getElementById("command-assistant").dataset.state || document.getElementById("command-assistant").dataset.state === "ready") setStatus("ready", t("ready"), t("readyDetail"));
  }

  function renderCases() {
    const select = document.getElementById("command-case-select");
    const options = state.cases.map(item => `<option value="${Number(item.caseId)}">FIR ${safe(item.crimeNo)} · ${safe(item.crimeType)} · ${safe(item.district)}</option>`).join("");
    select.innerHTML = `<option value="">${safe(t("select"))}</option>${options}`;
    syncCaseSelect();
  }

  function syncCaseSelect() {
    const select = document.getElementById("command-case-select");
    if (state.selectedCaseId && [...select.options].some(option => Number(option.value) === state.selectedCaseId)) select.value = String(state.selectedCaseId);
  }

  function renderSuggestions() {
    document.getElementById("command-suggestions").innerHTML = (suggestions[language()][role()] || []).map(value => `<button type="button">${safe(value)}</button>`).join("");
    document.querySelectorAll("#command-suggestions button").forEach(button => button.addEventListener("click", () => {
      document.getElementById("command-input").value = button.textContent;
      document.getElementById("command-input").focus();
    }));
  }

  function applyRoleBoundary() {
    const patrol = role() === "patrol";
    document.getElementById("command-case-label").hidden = patrol;
    if (patrol) state.selectedCaseId = null;
  }

  function openAssistant() {
    const panel = document.getElementById("command-assistant");
    if (!panel.classList.contains("open")) state.returnFocus = document.activeElement;
    panel.classList.add("open"); panel.setAttribute("aria-hidden", "false");
    document.getElementById("command-assistant-scrim").hidden = false;
    document.getElementById("command-orb").setAttribute("aria-expanded", "true");
    const active = Number(window.DrishtiWorkspace?.getActiveCaseId?.()) || null;
    if (active) { state.selectedCaseId = active; syncCaseSelect(); }
    setTimeout(() => document.getElementById("command-input").focus(), 40);
  }

  function closeAssistant() {
    stopSpeech();
    const panel = document.getElementById("command-assistant");
    panel.classList.remove("open"); panel.setAttribute("aria-hidden", "true");
    document.getElementById("command-assistant-scrim").hidden = true;
    document.getElementById("command-orb").setAttribute("aria-expanded", "false");
    const returnTarget = state.returnFocus instanceof HTMLElement && document.contains(state.returnFocus) ? state.returnFocus : document.getElementById("command-orb");
    returnTarget.focus(); state.returnFocus = null;
  }

  function trapFocus(event) {
    const panel = document.getElementById("command-assistant");
    const focusable = [...panel.querySelectorAll('button:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])')]
      .filter(element => !element.hidden && element.offsetParent !== null);
    if (!focusable.length) return;
    const first = focusable[0]; const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }

  function setStatus(stateName, title, detail) {
    const panel = document.getElementById("command-assistant");
    panel.dataset.state = stateName;
    document.getElementById("command-status-title").textContent = title;
    document.getElementById("command-status-detail").textContent = detail;
  }

  function resolveCaseFromQuery(query) {
    const normalized = query.toLowerCase().replaceAll(" ", "");
    const match = state.cases.find(item => normalized.includes(String(item.crimeNo || "").toLowerCase().replaceAll(" ", "")));
    if (match) { state.selectedCaseId = Number(match.caseId); syncCaseSelect(); }
    return match || state.cases.find(item => Number(item.caseId) === state.selectedCaseId) || null;
  }

  function routeCommand(query) {
    const q = query.toLowerCase(); const currentRole = role();
    if (/open|show|ತೆರೆ|ತೋರಿಸು/.test(q) && /(my cases|cases|ಪ್ರಕರಣ)/.test(q) && !/(link|ಸಂಪರ್ಕ)/.test(q)) return { navigation: "cases" };
    if (/open|show|ತೆರೆ|ತೋರಿಸು/.test(q) && /(review queue|ಪರಿಶೀಲನಾ ಸರತಿ)/.test(q)) return { navigation: "reviews" };
    if (/(brief|shift|today|ಪಾಳಿ|ಇಂದು|ಸ್ಥಳ)/.test(q) || currentRole === "patrol") return { agentId: currentRole === "patrol" ? "patrol-shift-briefing" : "shift-briefing", requiresCase: false };
    if (/(missing evidence|evidence gap|what evidence|ಸಾಕ್ಷ್ಯ.*ಕಾಣೆ|ಯಾವ ಸಾಕ್ಷ್ಯ)/.test(q)) return { agentId: "evidence-gap", requiresCase: true };
    if (/(timeline|chronology|time gap|ಕಾಲಕ್ರಮ|ಸಮಯ)/.test(q)) return { agentId: "timeline-reconstruction", requiresCase: true };
    if (/(link|connect|similar fir|ಸಂಪರ್ಕ|ಸಂಬಂಧಿತ)/.test(q)) return { agentId: "linked-case-verification", requiresCase: true };
    if (/(conflict|contradict|statement|ವಿರೋಧ|ಹೇಳಿಕೆ)/.test(q)) return { agentId: "statement-consistency", requiresCase: true };
    if (/(draft.*fir|structure.*fir|fir draft|ಎಫ್‌ಐಆರ್.*ಕರಡು)/.test(q)) return { agentId: "fir-drafting", requiresCase: true, roles: ["station", "district"] };
    if (/(supervisor|sp review|command review|ಮೇಲ್ವಿಚಾರಕ|ಎಸ್ಪಿ)/.test(q)) return { agentId: "supervisor-review", requiresCase: true, roles: ["command", "district"] };
    return { agentId: "case-triage", requiresCase: true, roles: ["command", "district", "station", "analyst"] };
  }

  async function runCommand() {
    const input = document.getElementById("command-input"); const query = input.value.trim();
    if (!query) { input.focus(); return; }
    const route = routeCommand(query); const selectedCase = resolveCaseFromQuery(query);
    if (/open|show|ತೆರೆ|ತೋರಿಸು/.test(query.toLowerCase()) && /(fir|ಎಫ್‌ಐಆರ್)/.test(query.toLowerCase()) && selectedCase) {
      window.DrishtiWorkspace?.openCase?.(selectedCase.caseId);
      setStatus("ready", t("navigated"), t("navigatedDetail"));
      document.getElementById("command-output").innerHTML = "";
      return;
    }
    if (route.navigation) {
      window.DrishtiWorkspace?.openPanel?.(route.navigation);
      setStatus("ready", t("navigated"), t("navigatedDetail"));
      document.getElementById("command-output").innerHTML = "";
      return;
    }
    if (route.roles && !route.roles.includes(role())) { setStatus("error", t("notAllowed"), t("boundary")); return; }
    if (route.requiresCase && !selectedCase) { setStatus("error", t("noCase"), t("readyDetail")); document.getElementById("command-case-select").focus(); return; }
    state.lastRoute = route;
    const button = document.getElementById("command-run"); button.disabled = true;
    document.getElementById("command-output").innerHTML = `<div class="command-empty">${safe(t("checkingDetail"))}</div>`;
    beginProgress();
    try {
      const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 65000);
      const response = await fetch("/api/agents/run", { method: "POST", headers: { "Content-Type": "application/json" }, signal: controller.signal, body: JSON.stringify({
        agentId: route.agentId, caseId: route.requiresCase ? Number(selectedCase.caseId) : null, role: role(), language: language(), query
      }) });
      clearTimeout(timeout);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
      state.lastResult = data;
      finishProgress(); renderResult(data, route);
    } catch (error) {
      finishProgress(true);
      document.getElementById("command-output").innerHTML = `<div class="command-error"><strong>${safe(t("failed"))}</strong><p>${safe(error.name === "AbortError" ? t("failedDetail") : error.message)}</p></div>`;
    } finally { button.disabled = false; }
  }

  function beginProgress() {
    clearInterval(state.progressTimer);
    const steps = [["checking", "checkingDetail"], ["challenging", "challengingDetail"], ["drafting", "draftingDetail"]];
    let index = 0; setStatus("working", t(steps[0][0]), t(steps[0][1]));
    state.progressTimer = setInterval(() => { index = Math.min(index + 1, steps.length - 1); setStatus("working", t(steps[index][0]), t(steps[index][1])); }, 2400);
  }

  function finishProgress(failed = false) {
    clearInterval(state.progressTimer); state.progressTimer = null;
    setStatus(failed ? "error" : "ready", failed ? t("failed") : t("complete"), failed ? t("failedDetail") : t("completeDetail"));
  }

  function renderResult(data, route) {
    const fallback = data.run?.aiProvider === "deterministic-fallback";
    const stages = (data.stages || []).slice(0, 3);
    const claims = (data.claims || []).slice(0, 5);
    const citations = (data.citations || []).slice(0, 6);
    document.getElementById("command-output").innerHTML = `<div class="command-result">
      <div class="command-result-head"><span class="command-draft-badge">${safe(language() === "kn" ? "ಕರಡು · ಅಧಿಕಾರಿ ನಿರ್ಧಾರ" : "DRAFT · OFFICER DECIDES")}</span><span class="command-provider">${fallback ? safe(t("fallback")) : `OpenAI · ${safe(data.run.aiModel)}`}</span></div>
      <div class="command-answer"><strong>${safe(t("brief"))}</strong><br>${safe(data.answer)}</div>
      <div class="command-stage-row">${stages.map(stage => `<article class="command-stage"><b>${safe(stage.name.replace(" Agent", ""))}</b><small>${safe(stage.status)}</small></article>`).join("")}</div>
      <section class="command-section"><h3>${safe(t("findings"))}</h3>${claims.map(claim => `<article class="command-finding"><strong>${safe(claim.statement)}</strong><p>${Number(claim.confidenceBeforeReview)}% ${safe(t("confidence"))}</p><span>${(claim.supportingSourceIds || []).map(id => `↗ ${safe(id)}`).join(" · ")}</span></article>`).join("")}</section>
      <section class="command-section"><h3>${safe(t("sources"))}</h3>${citations.map(citation => `<article class="command-source"><strong>${safe(citation.id)} · ${safe(citation.label)}</strong><p>${safe(citation.source)}</p><span>${safe(citation.confidence)}</span></article>`).join("")}</section>
      <article class="command-decision"><strong>${safe(t("decision"))}</strong><p>${safe(t("decisionDetail"))}</p></article>
      <div class="command-output-actions"><button type="button" class="primary" id="command-open-task">${safe(t("openTasks"))}</button>${role() !== "patrol" ? `<button type="button" id="command-open-case">${safe(t("openCase"))}</button>` : ""}<button type="button" id="command-read-result">${safe(t("read"))}</button></div>
    </div>`;
    document.getElementById("command-open-task")?.addEventListener("click", () => window.DrishtiAgents?.open(route.agentId, route.requiresCase ? data.case.caseId : null));
    document.getElementById("command-open-case")?.addEventListener("click", () => window.DrishtiWorkspace?.openCase?.(data.case.caseId));
    document.getElementById("command-read-result")?.addEventListener("click", () => toggleSpeech(data.answer));
  }

  function toggleVoice() {
    if (state.recognition) { state.recognition.stop(); return; }
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) { setStatus("error", t("voiceUnavailable"), t("readyDetail")); return; }
    const recognition = new Recognition(); state.recognition = recognition;
    recognition.lang = language() === "kn" ? "kn-IN" : "en-IN"; recognition.interimResults = true; recognition.continuous = false;
    const button = document.getElementById("command-mic"); button.setAttribute("aria-pressed", "true"); document.querySelector("#command-mic small").textContent = t("stop");
    setStatus("listening", t("listening"), t("listeningDetail"));
    recognition.onresult = event => { document.getElementById("command-input").value = [...event.results].map(result => result[0].transcript).join(" "); };
    state.voiceFailed = false;
    recognition.onerror = () => { state.voiceFailed = true; setStatus("error", t("voiceUnavailable"), t("readyDetail")); };
    recognition.onend = () => { state.recognition = null; button.setAttribute("aria-pressed", "false"); document.querySelector("#command-mic small").textContent = t("speak"); if (!state.voiceFailed) setStatus("ready", t("ready"), t("readyDetail")); };
    recognition.start();
  }

  function toggleSpeech(text) {
    if (state.speaking) { stopSpeech(); return; }
    if (!("speechSynthesis" in window)) return;
    const utterance = new SpeechSynthesisUtterance(String(text || "")); utterance.lang = language() === "kn" ? "kn-IN" : "en-IN"; utterance.rate = .95;
    utterance.onend = stopSpeech; state.speaking = true;
    const button = document.getElementById("command-read-result"); if (button) button.textContent = t("stopReading");
    window.speechSynthesis.speak(utterance);
  }

  function stopSpeech() {
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    state.speaking = false;
    const button = document.getElementById("command-read-result"); if (button) button.textContent = t("read");
  }
})();
