// End-to-end officer → task → evidence → supervisor workflow.
(function () {
  const safe = value => String(value ?? "").replace(/[&<>'"]/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
  const role = () => document.getElementById("role-select")?.value || "station";
  const language = () => document.body.dataset.language === "kn" ? "kn" : "en";
  const officer = () => document.querySelector(".officer-name")?.textContent || "Authorized officer";
  const isSupervisor = () => ["command", "district"].includes(role());
  const copy = {
    en: { agents:"Need help with this FIR?", agentsIntro:"Choose a task only when you need a source-linked draft.", tasks:"Investigation tasks", taskIntro:"Owned work created only after an officer accepts an agent suggestion.", noTasks:"No tasks recorded for this case.", open:"Open", progress:"In progress", awaiting:"Awaiting supervisor", completed:"Completed", start:"Start task", submit:"Submit for review", approve:"Verify and complete", return:"Return to officer", history:"Agent and change history", changes:"changes since last agent review", evidence:"Evidence custody register", evidenceIntro:"Record collection and custody metadata. Binary files remain temporary in this development prototype.", addEvidence:"Record evidence intake", verify:"Verify custody", shift:"Shift action centre", shiftIntro:"Due work and source-linked briefing for the current officer.", runShift:"Prepare shift briefing", supervisor:"Supervisor command centre", supervisorIntro:"Human decisions, overdue work, weak links, coordination drafts, data quality, and agent audits.", noRecords:"No records in this queue.", upload:"Record evidence", recentRuns:"Recent agent reviews" },
    kn: { agents:"ಈ ವಿಭಾಗದ ಏಜೆಂಟ್‌ಗಳು", agentsIntro:"ಈ ಎಫ್‌ಐಆರ್ ಈಗಾಗಲೇ ಆಯ್ಕೆಯಾಗಿದ್ದು ಇಲ್ಲಿ ಕಾರ್ಯವನ್ನು ಚಲಾಯಿಸಿ.", tasks:"ತನಿಖಾ ಕಾರ್ಯಗಳು", taskIntro:"ಅಧಿಕಾರಿ ಏಜೆಂಟ್ ಸಲಹೆ ಸ್ವೀಕರಿಸಿದ ನಂತರ ಮಾತ್ರ ರಚಿಸಲಾದ ಜವಾಬ್ದಾರಿ ಕೆಲಸ.", noTasks:"ಈ ಪ್ರಕರಣಕ್ಕೆ ಯಾವುದೇ ಕಾರ್ಯ ದಾಖಲಾಗಿಲ್ಲ.", open:"ತೆರೆದಿದೆ", progress:"ಪ್ರಗತಿಯಲ್ಲಿದೆ", awaiting:"ಮೇಲ್ವಿಚಾರಕರಿಗಾಗಿ ಕಾಯುತ್ತಿದೆ", completed:"ಪೂರ್ಣ", start:"ಕಾರ್ಯ ಪ್ರಾರಂಭಿಸಿ", submit:"ಪರಿಶೀಲನೆಗೆ ಸಲ್ಲಿಸಿ", approve:"ಪರಿಶೀಲಿಸಿ ಪೂರ್ಣಗೊಳಿಸಿ", return:"ಅಧಿಕಾರಿಗೆ ಹಿಂತಿರುಗಿಸಿ", history:"ಏಜೆಂಟ್ ಮತ್ತು ಬದಲಾವಣೆ ಇತಿಹಾಸ", changes:"ಕೊನೆಯ ಏಜೆಂಟ್ ಪರಿಶೀಲನೆಯ ನಂತರದ ಬದಲಾವಣೆಗಳು", evidence:"ಸಾಕ್ಷ್ಯ ವಶ ಸರಪಳಿ ದಾಖಲೆ", evidenceIntro:"ಸಂಗ್ರಹಣೆ ಮತ್ತು ವಶ ಮೆಟಾಡೇಟಾ ದಾಖಲಿಸಿ. ಈ ಅಭಿವೃದ್ಧಿ ಮಾದರಿಯಲ್ಲಿ ಕಡತಗಳು ತಾತ್ಕಾಲಿಕವಾಗಿರುತ್ತವೆ.", addEvidence:"ಸಾಕ್ಷ್ಯ ಸ್ವೀಕೃತಿ ದಾಖಲಿಸಿ", verify:"ವಶವನ್ನು ಪರಿಶೀಲಿಸಿ", shift:"ಪಾಳಿ ಕಾರ್ಯ ಕೇಂದ್ರ", shiftIntro:"ಪ್ರಸ್ತುತ ಅಧಿಕಾರಿಗೆ ಬಾಕಿ ಕೆಲಸ ಮತ್ತು ಮೂಲ-ಸಂಬಂಧಿತ ಮಾಹಿತಿ.", runShift:"ಪಾಳಿ ಮಾಹಿತಿ ಸಿದ್ಧಪಡಿಸಿ", supervisor:"ಮೇಲ್ವಿಚಾರಕ ಕಮಾಂಡ್ ಕೇಂದ್ರ", supervisorIntro:"ಮಾನವ ನಿರ್ಧಾರಗಳು, ವಿಳಂಬಿತ ಕೆಲಸ, ದುರ್ಬಲ ಸಂಪರ್ಕಗಳು, ಸಮನ್ವಯ ಕರಡುಗಳು, ಡೇಟಾ ಗುಣಮಟ್ಟ ಮತ್ತು ಏಜೆಂಟ್ ಲೆಕ್ಕಪರಿಶೋಧನೆ.", noRecords:"ಈ ಸಾಲಿನಲ್ಲಿ ಯಾವುದೇ ದಾಖಲೆಗಳಿಲ್ಲ.", upload:"ಸಾಕ್ಷ್ಯ ದಾಖಲಿಸಿ", recentRuns:"ಇತ್ತೀಚಿನ ಏಜೆಂಟ್ ಪರಿಶೀಲನೆಗಳು" }
  };
  const t = key => copy[language()][key] || copy.en[key] || key;
  const agentMap = {
    overview: [["case-triage","Case Triage"],["investigation-planning","Investigation Plan"],["legal-procedure","Legal Procedure"]],
    timeline: [["timeline-reconstruction","Timeline Reconstruction"]],
    evidence: [["evidence-gap","Evidence Gap"],["evidence-intake","Evidence Intake"],["statement-consistency","Statement Consistency"]],
    links: [["linked-case-verification","Verify Linked Cases"],["district-coordination","District Coordination"]],
    reviews: [["supervisor-review","Supervisor Review"],["court-readiness","Court Readiness"]]
  };
  const roleActions = {
    command: [
      {panel:"reviews",label:"Review pending decisions",kn:"ಬಾಕಿ ನಿರ್ಧಾರಗಳನ್ನು ಪರಿಶೀಲಿಸಿ",detail:"Approve, return, or request verification."},
      {panel:"drilldown",label:"Check district attention",kn:"ಜಿಲ್ಲಾ ಗಮನ ಪರಿಶೀಲಿಸಿ",detail:"Compare district workload and recorded risk."},
      {panel:"quality",label:"Review data reliability",kn:"ಡೇಟಾ ವಿಶ್ವಾಸಾರ್ಹತೆ ಪರಿಶೀಲಿಸಿ",detail:"See gaps affecting statewide decisions."}
    ],
    district: [
      {panel:"reviews",label:"Decide officer requests",kn:"ಅಧಿಕಾರಿ ವಿನಂತಿಗಳನ್ನು ನಿರ್ಧರಿಸಿ",detail:"Record a supervisor decision."},
      {panel:"lifecycle",label:"Check investigation delays",kn:"ತನಿಖಾ ವಿಳಂಬ ಪರಿಶೀಲಿಸಿ",detail:"Find station and case bottlenecks."},
      {panel:"networks",label:"Review connected FIRs",kn:"ಸಂಬಂಧಿತ ಎಫ್‌ಐಆರ್ ಪರಿಶೀಲಿಸಿ",detail:"Verify before district coordination."}
    ],
    station: [
      {panel:"cases",label:"Continue my investigations",kn:"ನನ್ನ ತನಿಖೆಗಳನ್ನು ಮುಂದುವರಿಸಿ",detail:"Open assigned FIRs and next actions."},
      {panel:"intake",label:"Register FIR or evidence",kn:"ಎಫ್‌ಐಆರ್ ಅಥವಾ ಸಾಕ್ಷ್ಯ ದಾಖಲಿಸಿ",detail:"Record source facts and custody details."},
      {panel:"reconstruction",label:"Check timeline and gaps",kn:"ಕಾಲಕ್ರಮ ಮತ್ತು ಕೊರತೆ ಪರಿಶೀಲಿಸಿ",detail:"Separate recorded events from missing links."}
    ],
    patrol: [
      {panel:"alerts",label:"Check current alerts",kn:"ಪ್ರಸ್ತುತ ಎಚ್ಚರಿಕೆ ಪರಿಶೀಲಿಸಿ",detail:"Review recorded situations for this shift."},
      {panel:"map",label:"Review priority locations",kn:"ಆದ್ಯತೆಯ ಸ್ಥಳಗಳನ್ನು ಪರಿಶೀಲಿಸಿ",detail:"See why each area needs attention."},
      {panel:"patrol",label:"Prepare patrol allocation",kn:"ಗಸ್ತು ಹಂಚಿಕೆ ಸಿದ್ಧಪಡಿಸಿ",detail:"Supervisor confirms every deployment."}
    ],
    analyst: [
      {panel:"networks",label:"Verify linked FIRs",kn:"ಸಂಬಂಧಿತ ಎಫ್‌ಐಆರ್ ಪರಿಶೀಲಿಸಿ",detail:"Compare independent link signals."},
      {panel:"patterns",label:"Analyse recorded patterns",kn:"ದಾಖಲಿತ ಮಾದರಿಗಳನ್ನು ವಿಶ್ಲೇಷಿಸಿ",detail:"Distinguish clusters from proof."},
      {panel:"quality",label:"Check data quality",kn:"ಡೇಟಾ ಗುಣಮಟ್ಟ ಪರಿಶೀಲಿಸಿ",detail:"Find gaps that weaken conclusions."}
    ]
  };

  async function api(path, options) {
    const response = await fetch(`/api${path}`, { cache:"no-store", ...options });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
    return data;
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".case-tab").forEach(tab => tab.addEventListener("click", () => setTimeout(enhanceCaseWorkspace, 30)));
    document.querySelector('.nav-link[data-target="reviews"]')?.addEventListener("click", () => setTimeout(loadSupervisorCentre, 20));
    document.querySelector('.nav-link[data-target="today"]')?.addEventListener("click", () => setTimeout(loadShiftCentre, 20));
    document.getElementById("role-select")?.addEventListener("change", () => setTimeout(() => { loadShiftCentre(); loadSupervisorCentre(); }, 50));
    document.getElementById("language-switch")?.addEventListener("click", () => setTimeout(() => { enhanceCaseWorkspace(true); loadShiftCentre(); loadSupervisorCentre(); }, 50));
    document.addEventListener("drishti:tasks-changed", event => { if (Number(event.detail?.caseId) === activeCaseId()) enhanceCaseWorkspace(true); loadShiftCentre(); loadSupervisorCentre(); });
    const body = document.getElementById("case-workspace-body");
    new MutationObserver(() => {
      if (!body.querySelector(":scope > .contextual-agent-strip")) {
        delete body.dataset.workflowMarker;
        enhanceCaseWorkspace();
      }
    }).observe(body, { childList:true });
    document.addEventListener("click", handleWorkflowClick);
    document.addEventListener("submit", handleWorkflowSubmit);
    loadShiftCentre();
  });

  const activeCaseId = () => Number(document.getElementById("case-panel")?.dataset.caseId || 0);
  const activeTab = () => document.querySelector(".case-tab.active")?.dataset.caseTab || "overview";

  async function enhanceCaseWorkspace(force=false) {
    const caseId = activeCaseId(); const body = document.getElementById("case-workspace-body");
    if (!caseId || !document.getElementById("case-panel")?.classList.contains("active")) return;
    const marker = `${caseId}:${activeTab()}:${language()}`;
    if (!force && body.dataset.workflowMarker === marker) return;
    body.dataset.workflowMarker = marker;
    body.querySelectorAll(":scope > .contextual-agent-strip, :scope > .custody-workspace, :scope > .case-history-card").forEach(node => node.remove());
    const contextual = (agentMap[activeTab()] || []).filter(([id]) => id !== "district-coordination" || isSupervisor());
    body.insertAdjacentHTML("beforeend", `<details class="contextual-agent-strip"><summary><div><span class="eyebrow">OPTIONAL ASSISTANCE</span><h3>${t("agents")}</h3><p>${t("agentsIntro")}</p></div></summary><div class="contextual-agent-actions">${contextual.map(([id,label]) => `<button type="button" data-open-context-agent="${id}">${safe(label)}</button>`).join("")}</div></details>`);
    await loadCaseTaskBoard(caseId);
    if (activeTab() === "evidence") await loadCustodyWorkspace(caseId, body);
    if (activeTab() === "reviews") await loadCaseHistory(caseId, body);
  }

  async function loadCaseTaskBoard(caseId) {
    const board = document.getElementById("case-workflow-board"); board.hidden = false;
    try {
      const data = await api(`/tasks?caseId=${caseId}`); const groups = ["open","in_progress","awaiting_supervisor","completed"];
      board.innerHTML = `<div class="workflow-section-heading"><div><span class="eyebrow">ACCOUNTABLE WORK</span><h3>${t("tasks")}</h3><p>${t("taskIntro")}</p></div><span class="workflow-count">${data.count}</span></div><div class="task-board">${groups.map(status => `<section class="task-column"><h4>${statusLabel(status)} <span>${data.tasks.filter(task=>task.status===status).length}</span></h4>${data.tasks.filter(task=>task.status===status).map(renderTask).join("") || `<p class="workflow-empty">${t("noRecords")}</p>`}</section>`).join("")}</div>`;
    } catch (error) { board.innerHTML = `<div class="workflow-error">${safe(error.message)}</div>`; }
  }

  function statusLabel(status) { return ({open:t("open"),in_progress:t("progress"),awaiting_supervisor:t("awaiting"),completed:t("completed"),returned:"Returned"})[status] || status; }
  function renderTask(task) {
    const overdue = task.status !== "completed" && task.dueDate < new Date().toISOString().slice(0,10);
    let action = "";
    if (["open","returned"].includes(task.status)) action = `<button data-task-status="in_progress" data-task-id="${task.taskId}">${t("start")}</button>`;
    if (task.status === "in_progress") action = `<button data-task-status="awaiting_supervisor" data-task-id="${task.taskId}">${t("submit")}</button>`;
    if (task.status === "awaiting_supervisor" && isSupervisor()) action = `<button data-task-status="completed" data-task-id="${task.taskId}">${t("approve")}</button><button class="return" data-task-status="returned" data-task-id="${task.taskId}">${t("return")}</button>`;
    return `<article class="task-card ${overdue ? "overdue" : ""}"><div><span class="task-priority ${task.priority}">${safe(task.priority)}</span><time>${safe(task.dueDate)}${overdue ? " · overdue" : ""}</time></div><strong>${safe(task.title)}</strong><p>${safe(task.detail)}</p><small>${safe(task.owner)} · ${(task.sourceIds||[]).map(safe).join(", ")}</small><div class="task-actions">${action}</div></article>`;
  }

  async function loadCustodyWorkspace(caseId, body) {
    const data = await api(`/evidence?caseId=${caseId}`);
    body.insertAdjacentHTML("beforeend", `<section class="custody-workspace"><div class="workflow-section-heading"><div><span class="eyebrow">CHAIN OF CUSTODY</span><h3>${t("evidence")}</h3><p>${t("evidenceIntro")}</p></div></div><div class="custody-grid"><div class="custody-register">${data.records.map(record => `<article class="custody-record"><div><span class="record-state ${record.humanVerified ? "" : "inferred"}">${safe(record.custodyStatus || "received")}</span><code>${safe(record.sha256Short || String(record.sha256||"").slice(0,16))}</code></div><strong>${safe(record.fileName)}</strong><p>${safe(record.categoryLabel || record.category)} · ${safe(record.collectedBy || "Collector not recorded")} → ${safe(record.receivedBy || "Receiver not recorded")}</p><small>${safe(record.collectedAt || record.receivedAt)} · Seal ${safe(record.sealNumber || "not recorded")}</small>${isSupervisor() && !record.humanVerified ? `<button data-verify-evidence="${safe(record.id)}">${t("verify")}</button>` : ""}</article>`).join("") || `<p class="workflow-empty">${t("noRecords")}</p>`}</div>
      <form class="custody-form" id="custody-intake-form"><h4>${t("addEvidence")}</h4><label>File<input name="file" type="file" required accept="image/*,video/mp4,video/webm,application/pdf,text/plain,.doc,.docx"></label><label>Category<select name="category"><option value="document">Document</option><option value="cctv">CCTV</option><option value="photo">Photograph</option><option value="forensic">Forensic</option><option value="statement">Statement</option></select></label><label>Collected by<input name="collectedBy" value="${safe(officer())}" required></label><label>Collected at<input name="collectedAt" type="datetime-local" required></label><label>Collection location<input name="collectionLocation" required></label><label>Seal / packet number<input name="sealNumber" required></label><label>Received by<input name="receivedBy" value="Evidence officer" required></label><label>Custody note<textarea name="note" rows="2"></textarea></label><button type="submit">${t("upload")}</button><p class="custody-feedback" aria-live="polite"></p></form></div></section>`);
    const dateInput = body.querySelector('[name="collectedAt"]');
    const now = new Date(Date.now()-new Date().getTimezoneOffset()*60000).toISOString().slice(0,16); dateInput.value = now;
  }

  async function loadCaseHistory(caseId, body) {
    const data = await api(`/cases/${caseId}/agent-history`);
    body.insertAdjacentHTML("beforeend", `<section class="case-history-card"><div class="workflow-section-heading"><div><span class="eyebrow">APPEND-ONLY HISTORY</span><h3>${t("history")}</h3><p><strong>${data.changesSinceLastRun.total}</strong> ${t("changes")}</p></div></div><div class="history-summary"><span>${data.changesSinceLastRun.tasks} task events</span><span>${data.changesSinceLastRun.evidence} evidence events</span><span>${data.changesSinceLastRun.reviews} review events</span></div><div class="history-list">${data.runs.map(run => `<article><strong>${safe(run.agentId || "case-investigator")}</strong><span>${safe(run.status)} · ${safe(run.aiProvider)} ${safe(run.aiModel||"")}</span><time>${safe(run.timestamp)}</time></article>`).join("") || `<p class="workflow-empty">${t("noRecords")}</p>`}</div></section>`);
  }

  async function loadShiftCentre() {
    const centre = document.getElementById("shift-action-centre"); if (!centre) return;
    try {
      const tasks = (await api("/tasks")).tasks.filter(task => task.status !== "completed");
      const actions = roleActions[role()] || roleActions.station;
      const shiftAgent = role() === "patrol" ? "patrol-shift-briefing" : "shift-briefing";
      centre.innerHTML = `<div class="workflow-section-heading"><div><span class="eyebrow">START HERE</span><h3>${t("shift")}</h3><p>Choose the police work you need to do. Technical tools remain under More tools.</p></div><button data-open-context-agent="${shiftAgent}">${t("runShift")}</button></div>
        <div class="role-action-grid">${actions.map(action => `<button type="button" data-open-role-panel="${action.panel}"><strong>${safe(language()==="kn" ? action.kn : action.label)}</strong><span>${safe(action.detail)}</span><b aria-hidden="true">→</b></button>`).join("")}</div>
        <div class="shift-task-heading"><strong>Open accountable work</strong><span>${tasks.length} active</span></div><div class="shift-task-strip">${tasks.slice(0,5).map(task => `<article class="${task.dueDate < new Date().toISOString().slice(0,10) ? "overdue" : ""}"><strong>${safe(task.title)}</strong><span>${safe(task.owner)} · ${safe(task.dueDate)} · ${statusLabel(task.status)}</span></article>`).join("") || `<p class="workflow-empty">${t("noTasks")}</p>`}</div>`;
    } catch (error) { centre.innerHTML = `<div class="workflow-error">${safe(error.message)}</div>`; }
  }

  async function loadSupervisorCentre() {
    const centre = document.getElementById("supervisor-command-centre"); if (!centre) return;
    if (!isSupervisor()) { centre.innerHTML = ""; centre.hidden = true; return; }
    centre.hidden = false; centre.innerHTML = '<div class="workspace-loading">Building supervisor command centre…</div>';
    try {
      const data = await api(`/supervisor/command-centre?role=${role()}`); const summary = data.summary;
      centre.innerHTML = `<div class="workflow-section-heading"><div><span class="eyebrow">HUMAN DECISIONS</span><h3>${t("supervisor")}</h3><p>${t("supervisorIntro")}</p></div></div><div class="supervisor-kpis">${[["Awaiting decision",summary.awaitingDecision],["Overdue tasks",summary.overdueTasks],["Coordination drafts",summary.coordinationDrafts],["Weak links",summary.weakLinks],["Data quality",`${summary.qualityScore}%`],["Recent agent runs",summary.recentAgentRuns]].map(([label,value])=>`<article><span>${label}</span><strong>${value}</strong></article>`).join("")}</div><div class="supervisor-grid"><section><h4>Awaiting task decisions</h4>${data.awaitingTasks.map(renderTask).join("")||`<p class="workflow-empty">${t("noRecords")}</p>`}</section><section><h4>Overdue work</h4>${data.overdueTasks.map(renderTask).join("")||`<p class="workflow-empty">${t("noRecords")}</p>`}</section><section><h4>Links requiring verification</h4>${data.weakLinks.map(link=>`<article class="review-signal"><strong>FIR ${safe(link.crimeNo)} ↔ ${safe(link.linkedCrimeNo)}</strong><span>${link.connectionScore}/100 · not proof</span><button data-open-case-workflow="${link.caseId}">Open case</button></article>`).join("")||`<p class="workflow-empty">${t("noRecords")}</p>`}</section><section><h4>${t("recentRuns")}</h4>${data.recentAgentRuns.map(run=>`<article class="review-signal"><strong>${safe(run.agentId||"case-investigator")}</strong><span>${safe(run.aiProvider)} · ${safe(run.status)}</span><time>${safe(run.timestamp)}</time></article>`).join("")||`<p class="workflow-empty">${t("noRecords")}</p>`}</section></div>`;
    } catch (error) { centre.innerHTML = `<div class="workflow-error">${safe(error.message)}</div>`; }
  }

  async function handleWorkflowClick(event) {
    const rolePanel = event.target.closest("[data-open-role-panel]");
    if (rolePanel) {
      document.querySelector(`.nav-link[data-target="${rolePanel.dataset.openRolePanel}"]`)?.click();
      return;
    }
    const agent = event.target.closest("[data-open-context-agent]");
    if (agent) { window.DrishtiAgents?.open(agent.dataset.openContextAgent, activeCaseId() || null); return; }
    const taskButton = event.target.closest("[data-task-status]");
    if (taskButton) {
      taskButton.disabled = true;
      try { await api(`/tasks/${taskButton.dataset.taskId}/status`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({status:taskButton.dataset.taskStatus,officer:officer(),role:role(),note:`Recorded from ${activeTab()} workspace`})}); await enhanceCaseWorkspace(true); await loadShiftCentre(); await loadSupervisorCentre(); }
      catch(error) { taskButton.disabled=false; taskButton.textContent=error.message; }
      return;
    }
    const verify = event.target.closest("[data-verify-evidence]");
    if (verify) {
      verify.disabled=true;
      try { await api(`/evidence/${verify.dataset.verifyEvidence}/verify`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({officer:officer(),role:role(),status:"verified",note:"Checksum, seal, collector, and receiver metadata reviewed."})}); await enhanceCaseWorkspace(true); }
      catch(error) { verify.disabled=false; verify.textContent=error.message; }
    }
  }

  async function handleWorkflowSubmit(event) {
    if (event.target.id !== "custody-intake-form") return;
    event.preventDefault(); const form=event.target; const feedback=form.querySelector(".custody-feedback"); const data=new FormData(form); const file=data.get("file");
    const params=new URLSearchParams({caseId:String(activeCaseId()),category:data.get("category"),source:"case_workspace",note:data.get("note"),collectedBy:data.get("collectedBy"),collectedAt:new Date(data.get("collectedAt")).toISOString(),collectionLocation:data.get("collectionLocation"),sealNumber:data.get("sealNumber"),receivedBy:data.get("receivedBy")});
    feedback.textContent="Recording custody metadata…";
    try { const response=await fetch(`/api/evidence?${params}`,{method:"POST",headers:{"Content-Type":file.type||"application/octet-stream","X-Evidence-Filename":encodeURIComponent(file.name)},body:file}); const result=await response.json(); if(!response.ok) throw new Error(result.detail||"Evidence intake failed"); await enhanceCaseWorkspace(true); }
    catch(error){ feedback.textContent=error.message; }
  }
})();
