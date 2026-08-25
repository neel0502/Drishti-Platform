// Drishti role-aware AI Agent Centre.
(function () {
  const state = { agents: [], cases: [], selected: null, category: "Recommended", result: null, pendingCaseId: null };
  const copy = {
    en: {
      title: "Police tasks", intro: "Choose one task and, when needed, an FIR. Drishti checks the listed records and prepares an editable draft for you.", recommended: "Recommended",
      control: "Draft only · officer decides", available: "START HERE", help: "Recommended for your shift", all: "All tasks",
      search: "Find a police task", choose: "Choose task", before: "NEXT STEP", reads: "Records used for this draft",
      case: "Choose the FIR", question: "Confirm what you need", run: "Check records and prepare draft", limit: "Nothing is submitted or changed. You review every finding and decide the next action.",
      loading: "Reviewing permitted records", loadingDetail: "The agent is gathering sources, challenging weak findings, and preparing an editable draft.",
      answer: "Officer brief", findings: "Source-linked findings", challenge: "Skeptic checks", actions: "Draft next steps", sources: "Sources", audit: "Model and audit record",
      review: "Record review request", recorded: "Review request recorded. A named human reviewer must decide it.", fail: "The agent could not complete this review.",
      noAgents: "No agents are approved for this role.", caseRequired: "Select a case before running this agent.", draft: "DRAFT · HUMAN APPROVAL REQUIRED",
      confidence: "confidence", selected: "Selected", modelFallback: "Safe fallback used", filters: "Filter agents",
      makeTasks: "Create selected investigation tasks", taskOwner: "Task owner", taskDue: "Due date", tasksCreated: "Selected tasks created and added to the case workflow."
    },
    kn: {
      title: "ಪೊಲೀಸ್ ಕಾರ್ಯಗಳು", intro: "ಒಂದು ಕಾರ್ಯವನ್ನು ಆಯ್ಕೆಮಾಡಿ. ದೃಷ್ಟಿ ಅನುಮೋದಿತ ದಾಖಲೆಗಳನ್ನು ಪರಿಶೀಲಿಸಿ, ಮೂಲಗಳನ್ನು ತೋರಿಸಿ, ನಿಮ್ಮ ಪರಿಶೀಲನೆಗೆ ಕೆಲಸ ಸಿದ್ಧಪಡಿಸುತ್ತದೆ.", recommended: "ಶಿಫಾರಸು",
      control: "ಕರಡು ಮಾತ್ರ · ಅಧಿಕಾರಿ ನಿರ್ಧರಿಸುತ್ತಾರೆ", available: "ನಿಮ್ಮ ಪಾತ್ರಕ್ಕೆ ಲಭ್ಯ", help: "ನೀವು ಏನು ಮಾಡಬೇಕು?", all: "ಎಲ್ಲಾ ಕಾರ್ಯಗಳು",
      search: "ಪೊಲೀಸ್ ಕಾರ್ಯಗಳನ್ನು ಹುಡುಕಿ", choose: "ಕಾರ್ಯ ಆಯ್ಕೆಮಾಡಿ", before: "ಪ್ರಾರಂಭಿಸುವ ಮೊದಲು", reads: "ದೃಷ್ಟಿ ಪರಿಶೀಲಿಸುವ ದಾಖಲೆಗಳು",
      case: "ಪರಿಶೀಲಿಸಬೇಕಾದ ಎಫ್‌ಐಆರ್", question: "ಏನು ಪರಿಶೀಲಿಸಬೇಕು?", run: "ದಾಖಲೆ ಪರಿಶೀಲಿಸಿ ಕರಡು ಸಿದ್ಧಪಡಿಸಿ", limit: "ದೃಷ್ಟಿ ದಾಖಲೆಯನ್ನು ಬದಲಿಸಲು, ಯಾರನ್ನಾದರೂ ಸಂಪರ್ಕಿಸಲು, ಕರಡನ್ನು ಅನುಮೋದಿಸಲು ಅಥವಾ ಪೊಲೀಸ್ ಕ್ರಮ ಕೈಗೊಳ್ಳಲು ಸಾಧ್ಯವಿಲ್ಲ.",
      loading: "ಅನುಮತಿತ ದಾಖಲೆಗಳನ್ನು ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ", loadingDetail: "ಏಜೆಂಟ್ ಮೂಲಗಳನ್ನು ಸಂಗ್ರಹಿಸಿ, ದುರ್ಬಲ ನಿರ್ಣಯಗಳನ್ನು ಪ್ರಶ್ನಿಸಿ, ಸಂಪಾದಿಸಬಹುದಾದ ಕರಡು ಸಿದ್ಧಪಡಿಸುತ್ತಿದೆ.",
      answer: "ಅಧಿಕಾರಿ ಮಾಹಿತಿ", findings: "ಮೂಲ-ಸಂಬಂಧಿತ ಕಂಡುಹಿಡಿಕೆಗಳು", challenge: "ಸಂದೇಹ ಪರಿಶೀಲನೆಗಳು", actions: "ಕರಡು ಮುಂದಿನ ಹಂತಗಳು", sources: "ಮೂಲಗಳು", audit: "ಮಾದರಿ ಮತ್ತು ಲೆಕ್ಕಪರಿಶೋಧನಾ ದಾಖಲೆ",
      review: "ಪರಿಶೀಲನಾ ವಿನಂತಿ ದಾಖಲಿಸಿ", recorded: "ಪರಿಶೀಲನಾ ವಿನಂತಿ ದಾಖಲಾಗಿದೆ. ಹೆಸರಿಸಲಾದ ಮಾನವ ಪರಿಶೀಲಕರು ನಿರ್ಧರಿಸಬೇಕು.", fail: "ಏಜೆಂಟ್ ಈ ಪರಿಶೀಲನೆಯನ್ನು ಪೂರ್ಣಗೊಳಿಸಲಿಲ್ಲ.",
      noAgents: "ಈ ಪಾತ್ರಕ್ಕೆ ಯಾವುದೇ ಏಜೆಂಟ್ ಅನುಮೋದಿಸಲ್ಪಟ್ಟಿಲ್ಲ.", caseRequired: "ಈ ಏಜೆಂಟ್ ಚಲಾಯಿಸುವ ಮೊದಲು ಪ್ರಕರಣ ಆಯ್ಕೆಮಾಡಿ.", draft: "ಕರಡು · ಮಾನವ ಅನುಮೋದನೆ ಅಗತ್ಯ",
      confidence: "ವಿಶ್ವಾಸ", selected: "ಆಯ್ಕೆಮಾಡಲಾಗಿದೆ", modelFallback: "ಸುರಕ್ಷಿತ ಪರ್ಯಾಯ ಬಳಕೆ", filters: "ಏಜೆಂಟ್‌ಗಳನ್ನು ಶೋಧಿಸಿ",
      makeTasks: "ಆಯ್ದ ತನಿಖಾ ಕಾರ್ಯಗಳನ್ನು ರಚಿಸಿ", taskOwner: "ಕಾರ್ಯ ಮಾಲೀಕರು", taskDue: "ಕೊನೆಯ ದಿನ", tasksCreated: "ಆಯ್ದ ಕಾರ್ಯಗಳನ್ನು ಪ್ರಕರಣ ಕಾರ್ಯಪ್ರವಾಹಕ್ಕೆ ಸೇರಿಸಲಾಗಿದೆ."
    }
  };
  const toolLabels = {
    case_reconstruction: "Case timeline and evidence gaps", case_brief: "Minimized FIR narrative",
    case_link_review: "Explainable linked-FIR signals", data_quality_review: "District data-quality audit",
    shift_context: "Shift priorities and recorded handoffs"
  };
  const categoryOrder = ["My shift", "Investigation", "Station work", "Supervision", "Case completion", "Governance"];
  const recommendedByRole = {
    command: ["shift-briefing", "supervisor-review", "district-coordination", "data-quality"],
    district: ["shift-briefing", "case-triage", "supervisor-review", "district-coordination"],
    station: ["shift-briefing", "case-triage", "evidence-gap", "investigation-planning"],
    patrol: ["patrol-shift-briefing"],
    analyst: ["shift-briefing", "linked-case-verification", "statement-consistency", "data-quality"]
  };
  const taskLabels = {
    "shift-briefing": "Prepare my shift briefing", "patrol-shift-briefing": "Prepare this patrol shift", "case-triage": "Decide what this FIR needs first",
    "evidence-gap": "Check what evidence is missing", "timeline-reconstruction": "Check the case timeline",
    "linked-case-verification": "Check whether FIRs may be connected", "statement-consistency": "Check conflicting records",
    "investigation-planning": "Prepare investigation steps", "supervisor-review": "Prepare supervisor review",
    "fir-drafting": "Review and structure the FIR", "legal-procedure": "Check procedure and approvals",
    "evidence-intake": "Check evidence custody details", "data-quality": "Check unreliable or incomplete data",
    "district-coordination": "Prepare cross-district review", "victim-follow-up": "Prepare victim follow-up",
    "court-readiness": "Check court-file readiness"
  };

  const language = () => document.body.dataset.language === "kn" ? "kn" : "en";
  const t = key => copy[language()][key] || copy.en[key] || key;
  const safe = value => String(value ?? "").replace(/[&<>'"]/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
  const role = () => {
    const value = document.getElementById("role-select").value;
    return ["command", "district", "station", "patrol", "analyst"].includes(value) ? value : "station";
  };
  async function getJson(path, options) {
    const response = await fetch(`/api${path}`, { cache: "no-store", ...options });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
    return data;
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("agent-search")?.addEventListener("input", renderCards);
    document.getElementById("role-select")?.addEventListener("change", () => { state.selected = null; loadCatalogue(); });
    document.getElementById("language-switch")?.addEventListener("click", () => window.setTimeout(() => { applyCopy(); renderFilters(); renderCards(); if (state.selected) selectAgent(state.selected.id); }, 0));
    document.querySelector('.nav-link[data-target="agents"]')?.addEventListener("click", loadCatalogue);
    loadCases();
    loadCatalogue();
    applyCopy();
    window.DrishtiAgents = {
      open: async (agentId, caseId) => {
        state.pendingCaseId = Number(caseId) || null;
        document.querySelector('.nav-link[data-target="agents"]')?.click();
        await loadCatalogue();
        selectAgent(agentId);
      }
    };
  });

  function applyCopy() {
    document.getElementById("agent-centre-title").textContent = t("title");
    document.getElementById("agent-centre-intro").textContent = t("intro");
    document.getElementById("agent-centre-control").textContent = t("control");
    document.getElementById("agent-catalogue-kicker").textContent = t("available");
    document.getElementById("agent-catalogue-title").textContent = t("help");
    document.getElementById("agent-search").placeholder = t("search");
    document.getElementById("agent-filter-chips").setAttribute("aria-label", t("filters"));
    const navText = document.querySelector('.nav-link[data-target="agents"] span:nth-child(2)');
    if (navText) navText.textContent = t("title");
  }

  async function loadCases() {
    try { state.cases = (await getJson("/reconstruction-options?limit=40")).cases || []; }
    catch (_) { state.cases = []; }
  }

  async function loadCatalogue() {
    const cards = document.getElementById("agent-cards");
    if (!cards) return;
    const requestedRole = role();
    cards.innerHTML = '<div class="workspace-loading">Loading approved agents…</div>';
    try {
      const data = await getJson(`/agents?role=${encodeURIComponent(requestedRole)}`);
      // Never let an earlier request overwrite the workspace after a fast role switch.
      if (requestedRole !== role()) return;
      state.agents = data.agents || [];
      state.category = "Recommended";
      document.getElementById("agents-nav-count").textContent = state.agents.length;
      renderFilters(); renderCards(); renderRunner();
    } catch (error) {
      if (requestedRole !== role()) return;
      cards.innerHTML = `<div class="workspace-empty">${safe(error.message)}</div>`;
    }
  }

  function renderFilters() {
    const categories = categoryOrder.filter(category => state.agents.some(agent => agent.category === category));
    document.getElementById("agent-filter-chips").innerHTML = ["Recommended", "All", ...categories].map(category =>
      `<button type="button" class="filter-chip ${state.category === category ? "active" : ""}" data-agent-category="${safe(category)}">${category === "Recommended" ? t("recommended") : category === "All" ? t("all") : safe(category)}</button>`
    ).join("");
    document.querySelectorAll("[data-agent-category]").forEach(button => button.addEventListener("click", () => {
      state.category = button.dataset.agentCategory; renderFilters(); renderCards();
    }));
  }

  function renderCards() {
    const query = (document.getElementById("agent-search")?.value || "").trim().toLowerCase();
    const recommended = new Set(recommendedByRole[role()] || []);
    const agents = state.agents.filter(agent =>
      (state.category === "All" || (state.category === "Recommended" ? recommended.has(agent.id) : agent.category === state.category)) &&
      (!query || [agent.name, agent.nameKn, agent.description, agent.descriptionKn, agent.category].some(value => String(value).toLowerCase().includes(query)))
    );
    document.getElementById("agent-cards").innerHTML = agents.length ? agents.map(agent => {
      const selected = state.selected?.id === agent.id;
      const technicalName = language() === "kn" ? agent.nameKn : agent.name;
      const taskName = language() === "kn" ? technicalName : (taskLabels[agent.id] || technicalName.replace(/ Agent$/, ""));
      return `<article class="agent-card ${selected ? "selected" : ""}"><div class="agent-card-top"><span class="agent-category">${safe(agent.category)}</span>${recommended.has(agent.id) ? '<span class="agent-recommended">Recommended</span>' : ''}</div><h4>${safe(taskName)}</h4><p>${safe(language() === "kn" ? agent.descriptionKn : agent.description)}</p><div class="agent-card-footer"><span>${agent.requiresCase ? "FIR required" : "No FIR required"}</span><button type="button" data-select-agent="${safe(agent.id)}">${selected ? t("selected") : t("choose")}</button></div><details class="agent-card-details"><summary>What Drishti checks</summary><span class="agent-technical-name">${safe(technicalName)} · ${agent.tools.length} approved record sources</span></details></article>`;
    }).join("") : `<div class="workspace-empty">${t("noAgents")}</div>`;
    document.querySelectorAll("[data-select-agent]").forEach(button => button.addEventListener("click", () => selectAgent(button.dataset.selectAgent)));
  }

  function selectAgent(id) {
    state.selected = state.agents.find(agent => agent.id === id) || null;
    state.result = null; renderCards(); renderRunner();
    document.getElementById("agent-runner")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function renderRunner() {
    const empty = document.getElementById("agent-runner-empty");
    const form = document.getElementById("agent-runner-form");
    const result = document.getElementById("agent-run-result");
    result.innerHTML = "";
    if (!state.selected) { empty.hidden = false; form.hidden = true; return; }
    const agent = state.selected; empty.hidden = true; form.hidden = false;
    const cases = state.cases.map(item => `<option value="${item.caseId}">FIR ${safe(item.crimeNo)} · ${safe(item.crimeType)} · ${safe(item.district)}</option>`).join("");
    const selectedTaskName = language() === "kn" ? agent.nameKn : (taskLabels[agent.id] || agent.name.replace(/ Agent$/, ""));
    form.innerHTML = `<div class="agent-runner-heading"><span class="eyebrow">${t("before")}</span><h3>${safe(selectedTaskName)}</h3><p>${safe(language() === "kn" ? agent.descriptionKn : agent.description)}</p></div>
      ${agent.requiresCase ? `<label class="agent-field"><span>${t("case")}</span><select id="agent-case-select"><option value="">Select FIR…</option>${cases}</select></label>` : ""}
      <label class="agent-field"><span>${t("question")}</span><textarea id="agent-question" rows="4">${safe(agent.defaultPrompt)}</textarea></label>
      <details class="agent-permission-box"><summary>${t("reads")}</summary>${agent.tools.map(tool => `<span><b>✓</b>${safe(toolLabels[tool] || tool)}</span>`).join("")}<small>${safe(agent.name)} · role-approved access only</small></details>
      <div class="agent-boundary"><span aria-hidden="true">⌁</span><p>${t("limit")}</p></div>
      <button class="primary-action full-width" id="agent-run-button" type="button">${t("run")}</button>`;
    if (agent.requiresCase && state.pendingCaseId) {
      const select = document.getElementById("agent-case-select");
      if ([...select.options].some(option => Number(option.value) === state.pendingCaseId)) select.value = String(state.pendingCaseId);
    }
    document.getElementById("agent-run-button").addEventListener("click", runAgent);
  }

  async function runAgent() {
    const agent = state.selected; const button = document.getElementById("agent-run-button");
    const caseId = Number(document.getElementById("agent-case-select")?.value || 0) || null;
    if (agent.requiresCase && !caseId) { document.getElementById("agent-run-result").innerHTML = `<div class="agent-error">${t("caseRequired")}</div>`; return; }
    button.disabled = true;
    document.getElementById("agent-run-result").innerHTML = `<div class="agent-progress"><span class="agent-progress-orbit" aria-hidden="true">✦</span><div><strong>${t("loading")}</strong><p>${t("loadingDetail")}</p><div class="agent-progress-steps"><span>Sources</span><span>Skeptic check</span><span>Draft</span></div></div></div>`;
    try {
      const data = await getJson("/agents/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ agentId: agent.id, caseId, role: role(), language: language(), query: document.getElementById("agent-question").value.trim() }) });
      state.result = data; renderResult(data);
    } catch (error) {
      document.getElementById("agent-run-result").innerHTML = `<div class="agent-error"><strong>${t("fail")}</strong><p>${safe(error.message)}</p><span>No record was changed.</span></div>`;
    } finally { button.disabled = false; }
  }

  function renderResult(data) {
    const fallback = data.run.aiProvider === "deterministic-fallback";
    const providerNotice = data.model?.warning ? `<div class="agent-provider-notice"><strong>Draft remained available</strong><span>${safe(data.model.warning)}</span></div>` : "";
    document.getElementById("agent-run-result").innerHTML = `<div class="agent-result-header"><span class="agent-draft-badge">${t("draft")}</span><span class="agent-model-state ${fallback ? "fallback" : ""}">${fallback ? t("modelFallback") : `OpenAI · ${safe(data.run.aiModel)}`}</span></div>
      ${providerNotice}
      <section class="agent-result-section agent-brief"><span class="eyebrow">${t("answer")}</span><p>${safe(data.answer)}</p></section>
      <section class="agent-result-section agent-actions-primary"><h4>${t("actions")}</h4><p class="agent-section-intro">Select only the work you want to record.</p>${data.recommendedActions.map((action, index) => `<article class="agent-action task-select-action"><input type="checkbox" data-task-action="${index}" checked aria-label="Select ${safe(action.title)}"><span>${index + 1}</span><div><strong>${safe(action.title)}</strong><p>${safe(action.reason)}</p><small>${safe(action.type)} · ${action.sourceIds.map(safe).join(", ")}</small></div></article>`).join("")}
      <div class="agent-task-setup"><label>${t("taskOwner")}<input id="agent-task-owner" value="${safe(document.querySelector(".officer-name")?.textContent || "Authorized officer")}"></label><label>${t("taskDue")}<input id="agent-task-due" type="date" value="${new Date(Date.now() + 3 * 86400000).toISOString().slice(0,10)}"></label><button type="button" id="agent-create-tasks">${t("makeTasks")}</button></div><p id="agent-task-feedback" class="agent-task-feedback" aria-live="polite"></p></section>
      <details class="agent-result-section agent-detail-section"><summary>${t("findings")} · ${data.claims.length}</summary>${data.claims.map(claim => `<article class="agent-finding"><div><span class="record-state">${safe(claim.recordStatus)}</span><span>${claim.confidenceBeforeReview}% ${t("confidence")}</span></div><p>${safe(claim.statement)}</p><small>${claim.supportingSourceIds.map(id => `↗ ${safe(id)}`).join(" · ")}</small></article>`).join("")}</details>
      <details class="agent-result-section agent-detail-section"><summary>${t("challenge")} · ${data.skepticReviews.length}</summary>${data.skepticReviews.map(review => `<details class="agent-challenge"><summary>${safe(review.verdict)} · ${review.confidenceAfterReview}%</summary><p>${safe(review.challenge)}</p></details>`).join("")}</details>
      <details class="agent-result-section agent-detail-section"><summary>${t("sources")} · ${data.citations.length}</summary><div class="agent-sources">${data.citations.map(citation => `<article><strong>${safe(citation.id)} · ${safe(citation.label)}</strong><p>${safe(citation.source)}</p><span>${safe(citation.confidence)}</span></article>`).join("")}</div></details>
      <button type="button" class="secondary-action full-width" id="agent-record-review">${t("review")}</button>
      <details class="agent-audit"><summary>${t("audit")}</summary><p>Run ${safe(data.run.runId)} · ${safe(data.run.aiProvider)} / ${safe(data.run.aiModel)} · Response ${safe(data.run.modelResponseId || "fallback")} · ${data.run.tokenUsage.totalTokens} tokens · Audit ${safe(data.run.auditHash)}</p></details>`;
    document.getElementById("agent-record-review").addEventListener("click", recordReview);
    document.getElementById("agent-create-tasks").addEventListener("click", createSelectedTasks);
  }

  async function createSelectedTasks() {
    const button = document.getElementById("agent-create-tasks"); const data = state.result;
    const selected = [...document.querySelectorAll("[data-task-action]:checked")].map(input => data.recommendedActions[Number(input.dataset.taskAction)]);
    if (!selected.length) return;
    button.disabled = true;
    try {
      await Promise.all(selected.map(action => getJson("/tasks", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
        caseId: data.case.caseId, title: action.title, detail: action.reason,
        owner: document.getElementById("agent-task-owner").value.trim(), dueDate: document.getElementById("agent-task-due").value,
        priority: action.type === "request_review" ? "high" : "normal", sourceIds: action.sourceIds,
        agentId: data.agent.id, agentRunId: data.run.runId, createdBy: document.querySelector(".officer-name")?.textContent || "Authorized officer"
      }) })));
      document.getElementById("agent-task-feedback").textContent = t("tasksCreated");
      document.dispatchEvent(new CustomEvent("drishti:tasks-changed", { detail: { caseId: data.case.caseId } }));
      button.textContent = t("tasksCreated");
    } catch (error) { document.getElementById("agent-task-feedback").textContent = error.message; button.disabled = false; }
  }

  async function recordReview() {
    const button = document.getElementById("agent-record-review"); const data = state.result;
    button.disabled = true;
    try {
      await getJson("/actions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...data.actionDraft, officer: document.querySelector(".officer-name")?.textContent || "Authorized officer", approved: false }) });
      button.textContent = t("recorded"); button.classList.add("recorded");
    } catch (error) { button.disabled = false; button.textContent = safe(error.message); }
  }
})();
