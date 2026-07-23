// DRISHTI APPLICATION CONTROLLER - FRONTEND

// Use the backend served by the same host in local and Catalyst deployments.
const API_BASE = window.location.protocol === "file:"
  ? "https://drishtiksp-50044068191.development.catalystappsail.in/api"
  : "/api";

// State variables
let activePanel = "home";
let districtGeoJSON = null;
let dashboardMap = null;
let mainMap = null;
let profileMap = null;
let networkInstance = null;
let activeAlertsList = [];
let reconstructionMap = null;
let reconstructionLayer = null;
let reconstructionData = null;
let reconstructionInterval = null;
let patrolMap = null;
let patrolLayer = null;
let forecastChart = null;
let activeNetworkGraph = null;
let profileLoaded = false;
let currentProfile = null;
let mockFir = null;
let mockExtraction = null;
let syntheticScenario = null;

// DOM Ready
document.addEventListener("DOMContentLoaded", () => {
  initOperationalShell();
  initNavigation();
  initMapFilters();
  initSearch();
  initCommandQueryAssistant();
  initDistrictDrilldown();
  initReconstruction();
  initAnalyticsLabs();
  initRoleWorkspaces();
  initMockIntake();
  initResponsiveShell();
  loadDemoScenarios();
  
  // Catalyst can cold-start before the analytics data is ready. Wait for
  // readiness so the first page load populates without a manual refresh.
  initializeDashboardData();
});

const workspaceMeta = {
  home:["Command & Control","State Command Overview"],
  alerts:["Command & Control","Situations & Watches"],
  drilldown:["Command & Control","District Crime Intelligence"],
  search:["Investigation","Intelligence Search"],
  profile:["Investigation","Intelligence Profile"],
  reconstruction:["Investigation","Incident Reconstruction"],
  networks:["Investigation","Crime Networks"],
  hypotheses:["Investigation","Investigative Hypotheses"],
  map:["Crime Analysis","State Crime Map"],
  patterns:["Crime Analysis","Crime Pattern Analysis"],
  lifecycle:["Crime Analysis","Case Lifecycle Intelligence"],
  forecast:["Crime Analysis","Predictive Analysis Validation"],
  ai:["Crime Analysis","AI Evidence & Confidence"],
  patrol:["Deployment","Patrol Deployment Planner"],
  quality:["Governance","Data Integrity & Quality"],
  intake:["Investigation","FIR Registration & Evidence Intake"]
};

const roleWorkspaces = {
  command: {
    guidance: "Statewide oversight, cross-district approvals, and resource coordination.",
    allowed: ["home","alerts","drilldown","search","intake","profile","reconstruction","networks","hypotheses","map","patterns","lifecycle","forecast","ai","patrol","quality"],
    defaultPanel: "home"
  },
  district: {
    guidance: "District supervision, station performance, investigations, and coordination requests.",
    allowed: ["home","alerts","drilldown","search","intake","profile","reconstruction","networks","hypotheses","map","patterns","lifecycle","patrol","quality"],
    defaultPanel: "drilldown"
  },
  station: {
    guidance: "Register a development FIR, inspect leads, identify evidence gaps, and request support.",
    allowed: ["home","search","intake","profile","reconstruction","networks","hypotheses","map","lifecycle","quality"],
    defaultPanel: "intake"
  },
  patrol: {
    guidance: "Review shift risk, priority zones, situations, and allocated patrol units.",
    allowed: ["home","alerts","map","patrol"],
    defaultPanel: "patrol"
  },
  analyst: {
    guidance: "Link entities, analyse evidence, test hypotheses, and produce intelligence support.",
    allowed: ["home","search","intake","profile","reconstruction","networks","hypotheses","map","patterns","lifecycle","forecast","ai","quality"],
    defaultPanel: "search"
  }
};

function initRoleWorkspaces() {
  const select = document.getElementById("role-select");
  const storedRole = localStorage.getItem("drishti-demo-role") || "command";
  select.value = roleWorkspaces[storedRole] ? storedRole : "command";
  const applyRole = (role, shouldNavigate = false) => {
    const config = roleWorkspaces[role] || roleWorkspaces.command;
    document.getElementById("role-guidance").textContent = config.guidance;
    document.querySelectorAll(".nav-link").forEach(link => {
      link.hidden = !config.allowed.includes(link.dataset.target);
    });
    document.body.dataset.demoRole = role;
    localStorage.setItem("drishti-demo-role", role);
    if (!config.allowed.includes(activePanel) || shouldNavigate) triggerNav(config.defaultPanel);
  };
  applyRole(select.value);
  select.addEventListener("change", () => applyRole(select.value, true));
}

function initMockIntake() {
  const firForm = document.getElementById("mock-fir-form");
  const evidenceForm = document.getElementById("mock-evidence-form");
  const searchButton = document.getElementById("mock-open-search");
  const reconstructionButton = document.getElementById("mock-open-reconstruction");
  const stationSelect = document.getElementById("mock-station");
  const officerSelect = document.getElementById("mock-officer");
  const offenceSelect = document.getElementById("mock-offence");
  const classifyButton = document.getElementById("mock-classify-fir");
  const classificationResult = document.getElementById("mock-classification-result");
  const syntheticButton = document.getElementById("synthetic-generate");
  const syntheticResult = document.getElementById("synthetic-scenario-result");
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  document.getElementById("mock-incident-time").value = now.toISOString().slice(0, 16);

  fetchJson("/fir-intake-options").then(options => {
    stationSelect.innerHTML = options.stations.map(item => `<option value="${item.id}">${escapeLab(item.name)}</option>`).join("");
    offenceSelect.innerHTML = options.offences.map(item => `<option value="${item.id}">${escapeLab(item.name)}</option>`).join("");
    const populateOfficers = () => {
      const stationId = Number(stationSelect.value);
      const candidates = options.officers.filter(item => item.stationId === stationId);
      const usable = candidates.length ? candidates : options.officers;
      officerSelect.innerHTML = usable.map(item => `<option value="${item.id}">${escapeLab(item.name)}</option>`).join("");
    };
    stationSelect.addEventListener("change", populateOfficers);
    populateOfficers();
  }).catch(error => {
    document.getElementById("mock-fir-status").textContent = `Schema choices unavailable: ${error.message}`;
  });

  classifyButton.addEventListener("click", async () => {
    const narrative = document.getElementById("mock-narrative").value.trim();
    classificationResult.textContent = "Analysing FIR narrative against historic KSP offence labels…";
    try {
      const response = await fetch(`${API_BASE}/fir-classification`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({narrative}) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Classification unavailable");
      const best = result.suggestions[0];
      const matchingOption = [...offenceSelect.options].find(option => option.text.trim().toLowerCase() === best.offence.toLowerCase());
      if (matchingOption) offenceSelect.value = matchingOption.value;
      classificationResult.innerHTML = `<strong>AI suggestion:</strong> ${escapeLab(best.offence)} (${best.confidence}%). Alternatives: ${result.suggestions.slice(1).map(item => `${escapeLab(item.offence)} ${item.confidence}%`).join(" · ")}. <span style="color:var(--alert-amber)">Officer must confirm the official offence classification.</span>`;
    } catch (error) { classificationResult.textContent = error.message; }
  });

  syntheticButton.addEventListener("click", async () => {
    syntheticResult.textContent = "Generating schema-compatible synthetic demo FIRs…";
    try {
      const response = await fetch(`${API_BASE}/synthetic-scenarios/generate`, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({scenario:document.getElementById("synthetic-scenario-type").value, caseCount:Number(document.getElementById("synthetic-case-count").value)})});
      const data = await response.json(); if (!response.ok) throw new Error(data.detail || "Scenario generation unavailable");
      syntheticScenario = data;
      syntheticResult.classList.remove("empty-state-detail");
      syntheticResult.innerHTML = `<div class="demo-safety-note"><strong>SYNTHETIC TEST DATA.</strong> ${escapeLab(data.notice)}</div><h3 style="margin-top:12px">${escapeLab(data.title)}</h3><p>${escapeLab(data.testPlan)}</p><div class="details-list">${data.cases.map(item => `<div class="details-item"><span class="details-label">${escapeLab(item.crimeNo)} · ${escapeLab(item.district)}</span><span class="details-value">${escapeLab(item.offence)} · ${escapeLab(item.vehicle)} · ${escapeLab(item.phone)}</span></div>`).join("")}</div><p class="header-muted-label">Schema coverage: ${data.schemaTables.map(escapeLab).join(" · ")}</p><button id="synthetic-validate" class="btn btn-secondary" type="button">Validate scenario with AI</button><div id="synthetic-validation" class="header-muted-label"></div>`;
      document.querySelector("#synthetic-validate").addEventListener("click", runSyntheticValidation);
    } catch (error) { syntheticResult.textContent = error.message; }
  });

  firForm.addEventListener("submit", async event => {
    event.preventDefault();
    const incidentTime = document.getElementById("mock-incident-time").value;
    const payload = {
      complainantName: document.getElementById("mock-complainant").value.trim(),
      victimName: document.getElementById("mock-victim").value.trim() || null,
      accusedName: document.getElementById("mock-accused").value.trim() || null,
      crimeMinorHeadId: Number(offenceSelect.value), policeStationId: Number(stationSelect.value),
      policePersonId: Number(officerSelect.value), incidentFromDate: new Date(incidentTime).toISOString(),
      latitude: Number(document.getElementById("mock-latitude").value), longitude: Number(document.getElementById("mock-longitude").value),
      briefFacts: document.getElementById("mock-narrative").value.trim()
    };
    const status = document.getElementById("mock-fir-status");
    status.textContent = "Creating schema-correct FIR in Catalyst Development…";
    try {
      const response = await fetch(`${API_BASE}/firs`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload) });
      const created = await response.json();
      if (!response.ok) throw new Error(created.detail || "FIR creation failed");
      mockFir = { id: created.crimeNo, caseId: created.caseId, complainant: payload.complainantName, offence: offenceSelect.options[offenceSelect.selectedIndex].text, location: document.getElementById("mock-location").value.trim(), incidentTime, narrative: payload.briefFacts };
      status.textContent = `Development FIR ${created.crimeNo} created in Catalyst: ${created.createdTables.join(", ")}.`;
      refreshMockHandoff();
    } catch (error) {
      status.textContent = `FIR was not created: ${error.message}`;
    }
  });

  evidenceForm.addEventListener("submit", event => {
    event.preventDefault();
    const file = document.getElementById("mock-evidence-file").files[0];
    const sampleText = document.getElementById("mock-evidence-text").value.trim();
    const source = [sampleText, mockFir?.narrative || ""].filter(Boolean).join(" ");
    const phones = [...new Set(source.match(/(?:\+91[-\s]?)?[6-9]\d{4}[-\s]?\d{5}/g) || [])];
    const vehicles = [...new Set(source.match(/\b(?:KA|MH|DL|TN)-?\d{2}[ -]?[A-Z]{1,3}[ -]?\d{3,4}\b/gi) || [])];
    const time = source.match(/\b(?:[01]?\d|2[0-3])(?::[0-5]\d)?\s?(?:AM|PM)\b/i)?.[0];
    const location = mockFir?.location || (source.match(/near\s+([^,.]+)/i)?.[1]);
    mockExtraction = { phones, vehicles, time, location, fileName: file?.name || "Pasted sample note" };
    document.getElementById("mock-evidence-status").textContent = `Sample extraction complete from ${mockExtraction.fileName}. No file was sent outside this browser.`;
    const results = document.getElementById("mock-extraction-results");
    results.classList.remove("empty-state-detail");
    results.innerHTML = `<strong>Extracted investigation leads</strong><div class="extraction-grid"><div><span>Phone identifiers</span><b>${phones.length ? phones.map(escapeLab).join(", ") : "None found"}</b></div><div><span>Vehicle identifiers</span><b>${vehicles.length ? vehicles.map(escapeLab).join(", ") : "None found"}</b></div><div><span>Time clue</span><b>${escapeLab(time || "Not stated")}</b></div><div><span>Location clue</span><b>${escapeLab(location || "Not stated")}</b></div></div><p>API handoff ready: entity extraction, similarity search, and evidence-gap assessment.</p>`;
    refreshMockHandoff();
  });

  searchButton.addEventListener("click", () => {
    const lead = mockExtraction?.phones?.[0] || mockExtraction?.vehicles?.[0] || mockFir?.offence || "Chain Snatching";
    fillSearch(lead);
  });
  reconstructionButton.addEventListener("click", () => triggerNav("reconstruction"));
}

async function runSyntheticValidation() {
  if (!syntheticScenario?.cases?.length) return;
  const output = document.querySelector("#synthetic-validation"); const scenarioCase = syntheticScenario.cases[0];
  output.textContent = "Running synthetic case through the live classification, semantic-search, and evidence checks…";
  try {
    const [classificationResponse, semanticResponse] = await Promise.all([
      fetch(`${API_BASE}/fir-classification`, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({narrative:scenarioCase.narrative})}),
      fetch(`${API_BASE}/semantic-search?q=${encodeURIComponent(scenarioCase.narrative)}`)
    ]);
    const classification = await classificationResponse.json(); const semantic = await semanticResponse.json();
    if (!classificationResponse.ok) throw new Error(classification.detail || "Classification validation unavailable");
    if (!semanticResponse.ok) throw new Error(semantic.detail || "Semantic validation unavailable");
    const gaps = [scenarioCase.vehicle, scenarioCase.phone].filter(value => /not (recorded|applicable)/i.test(value));
    output.innerHTML = `<div class="quality-flag"><strong>AI validation complete — synthetic sandbox only.</strong><br>Offence suggestion: ${escapeLab(classification.suggestions[0].offence)} (${classification.suggestions[0].confidence}%).<br>Closest indexed FIR: ${escapeLab(semantic.cases[0]?.crimeNo || "none")} (${semantic.cases[0]?.semanticConfidence ?? 0}% narrative similarity).<br>Evidence gaps: ${gaps.length ? escapeLab(gaps.join("; ")) : "none declared"}.<br><em>Results validate system behaviour; they do not validate a real investigation.</em></div>`;
  } catch (error) { output.textContent = error.message; }
}

function refreshMockHandoff() {
  const hasFir = Boolean(mockFir);
  const hasExtraction = Boolean(mockExtraction);
  document.getElementById("mock-open-search").disabled = !(hasFir || hasExtraction);
  document.getElementById("mock-open-reconstruction").disabled = !hasFir;
  document.getElementById("mock-handoff-copy").textContent = hasFir && hasExtraction
      ? `Development FIR ${mockFir.id} now has extractable leads. Search historic intelligence, then inspect a reconstruction and missing-evidence checklist.`
    : hasFir
      ? `Development FIR ${mockFir.id} is created in Catalyst. Add a sample evidence note to extract phone, vehicle, time, and location leads.`
      : "Create a development FIR and extract a lead to generate a traceable investigation handoff.";
}

function initOperationalShell() {
  const themeToggle = document.getElementById("theme-toggle");
  const storedTheme = localStorage.getItem("drishti-theme");
  const applyTheme = dark => {
    document.body.classList.toggle("dark-mode", dark);
    themeToggle.textContent = dark ? "☀" : "◐";
    themeToggle.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
  };
  applyTheme(storedTheme === "dark");
  themeToggle.addEventListener("click", () => {
    const dark = !document.body.classList.contains("dark-mode");
    applyTheme(dark);
    localStorage.setItem("drishti-theme", dark ? "dark" : "light");
  });

  document.getElementById("current-header-date").textContent = new Intl.DateTimeFormat("en-IN", {
    weekday:"short", day:"2-digit", month:"short", year:"numeric"
  }).format(new Date());

  document.querySelectorAll("[data-open-panel]").forEach(button => {
    button.addEventListener("click", () => {
      document.querySelector(`.nav-link[data-target="${button.dataset.openPanel}"]`)?.click();
    });
  });

  document.addEventListener("keydown", event => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      document.getElementById("global-search-input").focus();
    }
  });
}

async function fetchJson(path) {
  const response = await fetch(`${API_BASE}${path}`, { cache:"no-store" });
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
  return body;
}

async function initContextSelectors() {
  const profileSelect = document.getElementById("profile-person-select");
  const caseSelect = document.getElementById("reconstruction-case-select");
  try {
    const [profiles, cases] = await Promise.all([
      fetchJson("/profile-options"),
      fetchJson("/reconstruction-options")
    ]);
    profileSelect.innerHTML = profiles.profiles.map(item =>
      `<option value="${escapeLab(item.name)}">${escapeLab(item.name)} · ${item.caseCount} FIRs · ${item.districtCount} districts</option>`
    ).join("");
    caseSelect.innerHTML = cases.cases.map(item =>
      `<option value="${item.caseId}">FIR ${escapeLab(item.crimeNo)} · ${escapeLab(item.crimeType)} · ${escapeLab(item.district)}</option>`
    ).join("");
  } catch (error) {
    profileSelect.innerHTML = `<option value="">Profiles unavailable: ${escapeLab(error.message)}</option>`;
    caseSelect.innerHTML = `<option value="">Cases unavailable: ${escapeLab(error.message)}</option>`;
  }
  document.getElementById("profile-load-person").addEventListener("click", () => {
    if (profileSelect.value) loadSuspectProfile(profileSelect.value);
  });
  document.getElementById("reconstruction-load-case").addEventListener("click", () => {
    if (caseSelect.value) loadIncidentReconstruction(caseSelect.value);
  });
}

function updateWorkspaceHeader(target) {
  const [group, title] = workspaceMeta[target] || ["Operations","Drishti Workspace"];
  document.getElementById("workspace-group").textContent = group;
  document.getElementById("workspace-title").textContent = title;
  document.title = `${title} — Drishti`;
}

async function initializeDashboardData() {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    try {
      const response = await fetch(`${API_BASE}/health`, { cache: "no-store" });
      const health = await response.json();
      if (response.ok && health.dataSource) {
        const source = health.dataSource;
        const label = source.active === 'catalyst' ? 'Catalyst Data Store' : source.fallback ? 'CSV Fallback Active' : 'Local CSV Dataset';
        document.getElementById('data-source-status').textContent = label;
        document.querySelector('.status-indicator').title = source.message || label;
      }
      if (response.ok && health.dataLoaded) break;
    } catch (error) {
      console.debug("Backend is still starting:", error);
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  await Promise.all([
    fetchDashboardData(),
    fetchMapData(),
    fetchSituationsData(),
    fetchNetworkGroups()
  ]);
  await initContextSelectors();
}

// ─── ANALYTICS LABS ──────────────────────────────────────────────────────
function escapeLab(value) {
  return String(value ?? "").replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
}

function populateLabDistricts(geojson, apiDistricts = []) {
  const districts = apiDistricts.length ? apiDistricts : geojson.features.map(feature => ({ id: feature.properties.districtId, name: feature.properties.districtName }))
    .filter(item => item.id && item.name).filter((item, index, all) => all.findIndex(other => other.id === item.id) === index)
    .sort((a, b) => a.name.localeCompare(b.name));
  ["pattern-district", "lifecycle-district", "patrol-district", "quality-district", "forecast-district", "ai-district"].forEach(id => {
    const select = document.getElementById(id);
    select.innerHTML = ["patrol-district", "forecast-district", "ai-district"].includes(id) ? '' : '<option value="">All Karnataka</option>';
    districts.forEach(district => select.insertAdjacentHTML('beforeend', `<option value="${district.id}">${escapeLab(district.name)}</option>`));
  });
  document.getElementById("patrol-district").value = districts.some(d => d.id === 1) ? "1" : String(districts[0]?.id || "");
  ["forecast-district", "ai-district"].forEach(id => {
    const select = document.getElementById(id);
    select.value = districts.some(d => d.id === 1) ? "1" : String(districts[0]?.id || "");
  });
}

function initAnalyticsLabs() {
  document.getElementById("pattern-run").addEventListener("click", runPatternDiscovery);
  document.getElementById("lifecycle-run").addEventListener("click", runLifecycleAnalysis);
  document.getElementById("patrol-run").addEventListener("click", runPatrolPlan);
  document.getElementById("quality-run").addEventListener("click", runQualityAudit);
  document.getElementById("forecast-run").addEventListener("click", runForecastBacktest);
  document.getElementById("ai-refresh").addEventListener("click", runAIConfidence);
  document.getElementById("hypothesis-form").addEventListener("submit", saveHypothesisBoard);
  loadHypothesisBoards();
}

const labLoaded = new Set();

async function loadDemoScenarios() {
  const container = document.getElementById("demo-scenarios");
  try {
    const response = await fetch(`${API_BASE}/demo-scenarios`);
    const data = await response.json();
    container.innerHTML = data.scenarios.map((scenario, index) => `
      <button class="demo-scenario-card" type="button" data-index="${index}">
        <span class="scenario-number">${String(index + 1).padStart(2, "0")}</span>
        <strong>${escapeLab(scenario.label)}</strong>
        <span>${escapeLab(scenario.description)}</span>
        <small>${escapeLab(scenario.crimeNo || scenario.query)}</small>
      </button>`).join("");
    container.querySelectorAll(".demo-scenario-card").forEach((button, index) => {
      button.addEventListener("click", () => runDemoScenario(data.scenarios[index]));
    });
    document.getElementById("search-guidance").textContent = data.notice;
  } catch (error) {
    container.innerHTML = `<div class="analysis-note warning">Unable to load demo scenarios: ${escapeLab(error.message)}</div>`;
  }
}

function runDemoScenario(scenario) {
  if (scenario.action === "command") {
    const input = document.getElementById("command-query-input");
    input.value = scenario.query;
    document.getElementById("command-query-form").requestSubmit();
  } else if (scenario.action === "reconstruct" && scenario.caseId) {
    loadIncidentReconstruction(scenario.caseId);
  } else if (scenario.action === "links" && scenario.caseId) {
    loadCaseMO(scenario.caseId);
  } else {
    fillSearch(scenario.query);
  }
}

async function fetchLab(path, button) {
  const original = button.textContent;
  button.disabled = true; button.textContent = "Analysing…";
  try {
    const response = await fetch(`${API_BASE}${path}`); const body = await response.json();
    if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail || "Analysis failed"));
    return body;
  } finally { button.disabled = false; button.textContent = original; }
}

async function runPatternDiscovery() {
  const button = document.getElementById("pattern-run");
  const params = new URLSearchParams({ clusterCount: document.getElementById("pattern-count").value });
  const fields = { districtId:"pattern-district", crimeHeadId:"pattern-category", dateFrom:"pattern-from", dateTo:"pattern-to" };
  Object.entries(fields).forEach(([key, id]) => { const value = document.getElementById(id).value; if (value) params.set(key, value); });
  try {
    const data = await fetchLab(`/patterns/discover?${params}`, button);
    document.getElementById("pattern-summary").innerHTML = `<strong>${data.clusters.length} patterns</strong> discovered across ${data.sampledCaseCount.toLocaleString()} sampled FIRs (${data.caseCount.toLocaleString()} matched). ${escapeLab(data.method)}<br><span style="color:var(--alert-amber)">${escapeLab(data.caveat)}</span>`;
    document.getElementById("pattern-results").innerHTML = data.clusters.map(cluster => `<article class="cluster-card"><div class="cluster-head"><h3 class="cluster-title">Pattern ${cluster.id} · ${escapeLab(cluster.topCrimeTypes[0])}</h3><span class="cluster-score">${cluster.cohesion}% cohesion</span></div><div class="funnel-label">${cluster.size.toLocaleString()} cases · ${cluster.share}% of sample · ${cluster.dateSpan.from} to ${cluster.dateSpan.to}</div>${cluster.qualityFlag ? `<div class="quality-flag">${escapeLab(cluster.qualityFlag)} · ${cluster.uniqueNarrativeRate}% unique narratives</div>` : ''}<div class="term-row">${cluster.topTerms.map(term => `<span class="term-pill">${escapeLab(term)}</span>`).join('')}</div><div class="funnel-label">Concentrations: ${cluster.topDistricts.map(escapeLab).join(' · ')}</div>${cluster.representativeCases.map(item => `<div class="case-evidence"><a href="#" onclick="fillSearch('${escapeLab(item.crimeNo)}');return false;">FIR ${escapeLab(item.crimeNo)}</a> · ${escapeLab(item.district)} · ${item.date}<p>${escapeLab(item.facts)}</p></div>`).join('')}</article>`).join('');
  } catch (error) { document.getElementById("pattern-summary").textContent = error.message; }
}

async function runLifecycleAnalysis() {
  const button = document.getElementById("lifecycle-run"); const district = document.getElementById("lifecycle-district").value;
  try {
    const [data, priority] = await Promise.all([
      fetchLab(`/lifecycle${district ? `?districtId=${district}` : ''}`, button),
      fetch(`${API_BASE}/lifecycle/priority${district ? `?districtId=${district}` : ''}`).then(response => response.json())
    ]); const initial = data.funnel[0].count;
    document.getElementById("lifecycle-funnel").innerHTML = data.funnel.map(stage => `<div class="funnel-stage"><div class="funnel-label">${escapeLab(stage.stage)}</div><div class="funnel-value">${stage.count.toLocaleString()}</div><div class="funnel-label">${Math.round(stage.count / initial * 100)}% of FIRs</div></div>`).join('');
    const metrics = [[data.timings.medianFIRToArrestDays,"Median days: FIR → arrest"],[data.timings.medianFIRToChargesheetDays,"Median days: FIR → chargesheet"],[data.exceptions.arrestWithoutChargesheet,"Arrest, no chargesheet",true],[data.exceptions.chargesheetWithoutArrest,"Chargesheet, no arrest",true],[data.exceptions.pendingOver90Days,"Pending over 90 days",true],[data.exceptions.chronologyConflicts,"Chronology conflicts",true]];
    document.getElementById("lifecycle-metrics").innerHTML = metrics.map(([value,label,alert]) => `<div class="metric-card ${alert ? 'alert':''}"><div class="value">${value ?? '—'}</div><div class="label">${escapeLab(label)}</div></div>`).join('');
    document.getElementById("lifecycle-table").innerHTML = data.bottlenecks.map(row => `<tr><td>${escapeLab(row.station)}</td><td>${row.cases}</td><td>${row.pending}</td><td>${row.pendingRate}%</td><td>${row.medianChargeDays == null ? '—' : `${Math.round(row.medianChargeDays)} days`}</td></tr>`).join('');
    const priorityTable = document.getElementById("lifecycle-priority-table"); const priorityNote = document.getElementById("lifecycle-priority-note");
    if (priority.detail) throw new Error(priority.detail);
    priorityTable.innerHTML = priority.cases.length ? priority.cases.map(item => `<tr><td class="text-mono">${escapeLab(item.crimeNo)}</td><td>${escapeLab(item.crimeType)}</td><td>${escapeLab(item.station)}</td><td>${item.ageDays} days</td><td><span class="status-pill ${item.delayRisk >= 70 ? 'red-pill' : 'amber-pill'}">${item.delayRisk}%</span></td><td>${escapeLab(item.signals.join(' · '))}</td></tr>`).join('') : '<tr><td colspan="6">No open FIRs currently meet the supervisory-review threshold.</td></tr>';
    priorityNote.textContent = `${priority.model}. ${priority.training} ${priority.caveat}`;
    document.getElementById("lifecycle-note").textContent = `${data.district} · analysis date ${data.analysisDate}. ${data.method}`;
  } catch (error) { document.getElementById("lifecycle-note").textContent = error.message; }
}

async function runPatrolPlan() {
  const button = document.getElementById("patrol-run"); const district = document.getElementById("patrol-district").value || "1"; const units = document.getElementById("patrol-units").value;
  const heinous = document.getElementById("patrol-heinous").value; const recency = document.getElementById("patrol-recency").value; const [shiftStart, shiftEnd] = document.getElementById("patrol-shift").value.split('-');
  try {
    const data = await fetchLab(`/patrol/plan?districtId=${district}&availableUnits=${units}&heinousWeight=${heinous}&recencyWeight=${recency}&shiftStart=${shiftStart}&shiftEnd=${shiftEnd}`, button);
    document.getElementById("patrol-window").textContent = `${data.analysisWindow.from} to ${data.analysisWindow.to}`;
    document.getElementById("patrol-summary").innerHTML = `<div class="metric-card"><div class="value">${data.availableUnits}</div><div class="label">Units allocated</div></div><div class="metric-card"><div class="value">${data.coverageIndex}%</div><div class="label">Scenario demand coverage</div></div><div class="metric-card"><div class="value">${data.baselineCoverageIndex}%</div><div class="label">Default-weight baseline</div></div><div class="metric-card ${data.coverageDelta < 0 ? 'alert':''}"><div class="value">${data.coverageDelta > 0 ? '+':''}${data.coverageDelta} pts</div><div class="label">Coverage change</div></div><div class="metric-card"><div class="value">${data.zones.filter(z => z.allocatedUnits > 0).length}</div><div class="label">Staffed priority zones</div></div>`;
    document.getElementById("patrol-note").className = "analysis-note warning"; document.getElementById("patrol-note").innerHTML = `${escapeLab(data.method)}<br><strong>${escapeLab(data.caveat)}</strong>`;
    document.getElementById("patrol-zones").innerHTML = data.zones.map(zone => `<article class="cluster-card ${zone.allocatedUnits ? '' : 'zone-card-zero'}"><div class="cluster-head"><h3>${zone.zone} · ${escapeLab(zone.topCrime)}</h3><span class="cluster-score">${zone.allocatedUnits} unit${zone.allocatedUnits === 1 ? '' : 's'}</span></div><div class="funnel-label">Peak ${escapeLab(zone.peakWindow)} · score ${zone.riskScore}</div><p style="margin-top:8px;color:var(--text-secondary);font-size:11px">${escapeLab(zone.rationale)}</p></article>`).join('');
    window.setTimeout(() => {
      try { renderPatrolMap(data.zones); } catch (mapError) { console.warn('Patrol map could not render', mapError); }
    }, 50);
  } catch (error) { document.getElementById("patrol-note").textContent = error.message; }
}

async function runQualityAudit() {
  const button = document.getElementById("quality-run"); const district = document.getElementById("quality-district").value;
  try {
    const data = await fetchLab(`/data-quality${district ? `?districtId=${district}` : ''}`, button);
    document.getElementById("quality-summary").innerHTML = `<div class="metric-card"><div class="value">${data.qualityScore}</div><div class="label">Quality score / 100</div></div><div class="metric-card"><div class="value">${data.fieldCompleteness}%</div><div class="label">Core field completeness</div></div><div class="metric-card"><div class="value">${data.records.toLocaleString()}</div><div class="label">Records audited</div></div>`;
    document.getElementById("quality-checks").innerHTML = data.checks.map(check => `<article class="cluster-card quality-${check.severity}"><div class="cluster-head"><h3>${escapeLab(check.name)}</h3><span class="cluster-score">${check.count.toLocaleString()}</span></div><div class="funnel-label">${escapeLab(check.severity)} priority · ${data.records ? (check.count/data.records*100).toFixed(1) : 0}% of case scope</div></article>`).join('');
    document.getElementById("quality-table").innerHTML = data.districts.map(row => `<tr><td>${escapeLab(row.district)}</td><td>${row.records.toLocaleString()}</td><td>${row.issues.toLocaleString()}</td><td>${row.issueRate}%</td></tr>`).join('');
    document.getElementById("quality-recommendations").innerHTML = data.recommendations.map(item => `<li>${escapeLab(item)}</li>`).join('');
  } catch (error) { document.getElementById("quality-summary").innerHTML = `<div class="analysis-note warning">${escapeLab(error.message)}</div>`; }
}

async function saveHypothesisBoard(event) {
  event.preventDefault(); const status = document.getElementById("hypothesis-status");
  const lines = id => document.getElementById(id).value.split('\n').map(value => value.trim()).filter(Boolean);
  const caseIds = document.getElementById("hypothesis-cases").value.split(',').map(value => parseInt(value.trim())).filter(Number.isFinite);
  const payload = { title:document.getElementById("hypothesis-title").value, hypothesis:document.getElementById("hypothesis-text").value, caseIds, evidence:lines("hypothesis-evidence"), gaps:lines("hypothesis-gaps"), status:"open" };
  try {
    const response = await fetch(`${API_BASE}/hypotheses`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload) });
    if (!response.ok) throw new Error('Unable to save board');
    event.target.reset(); status.textContent = 'Board saved with timestamp and linked FIR validation.'; await loadHypothesisBoards();
  } catch (error) { status.textContent = error.message; }
}

async function loadHypothesisBoards() {
  try {
    const response = await fetch(`${API_BASE}/hypotheses`); if (!response.ok) return; const data = await response.json();
    document.getElementById("hypothesis-boards").innerHTML = data.boards.length ? data.boards.slice().reverse().map(board => `<article class="cluster-card"><div class="cluster-head"><h3>${escapeLab(board.title)}</h3><span class="status-pill blue-pill">${escapeLab(board.status)}</span></div><p class="board-hypothesis">${escapeLab(board.hypothesis)}</p><div class="term-row">${board.cases.map(item => `<span class="term-pill">FIR ${escapeLab(item.crimeNo)}</span>`).join('')}</div><div class="board-columns"><div><strong>Evidence</strong>${board.evidence.map(item => `<p>+ ${escapeLab(item)}</p>`).join('') || '<p>None recorded</p>'}</div><div><strong>Gaps</strong>${board.gaps.map(item => `<p>– ${escapeLab(item)}</p>`).join('') || '<p>None recorded</p>'}</div></div></article>`).join('') : '<div class="analysis-note">No boards saved yet. Create a testable hypothesis on the left.</div>';
  } catch (error) { console.error('Unable to load hypothesis boards', error); }
}

async function runForecastBacktest() {
  const button = document.getElementById("forecast-run"); const district=document.getElementById("forecast-district").value || "1"; const category=document.getElementById("forecast-category").value; const months=document.getElementById("forecast-months").value;
  try {
    const data=await fetchLab(`/forecast/backtest?districtId=${district}&holdoutMonths=${months}${category ? `&crimeHeadId=${category}`:''}`,button); const metrics=data.metrics;
    document.getElementById("forecast-metrics").innerHTML=`<div class="metric-card"><div class="value">${metrics.mae}</div><div class="label">ML mean absolute error</div></div><div class="metric-card"><div class="value">${metrics.mape ?? '—'}%</div><div class="label">Mean percentage error</div></div><div class="metric-card"><div class="value">${metrics.naiveMAE}</div><div class="label">Naive baseline MAE</div></div><div class="metric-card ${metrics.improvementVsNaive < 0 ? 'alert':''}"><div class="value">${metrics.improvementVsNaive}%</div><div class="label">ML improvement vs naive</div></div>`;
    document.getElementById("forecast-method").textContent=`${data.district} · ${data.crimeCategory} · ${data.model}`; document.getElementById("forecast-note").textContent=`${data.modelDetails.algorithm}: ${data.modelDetails.features.join("; ")}. ${data.caveat}`; renderForecastChart(data.series);
  } catch(error){document.getElementById("forecast-note").textContent=error.message;}
}

async function runAIConfidence() {
  const button = document.getElementById("ai-refresh"); const district = document.getElementById("ai-district").value || "1";
  const summary = document.getElementById("ai-confidence-summary"); const models = document.getElementById("ai-confidence-models");
  try {
    const [patterns, forecast, hotspots] = await Promise.all([
      fetchLab(`/patterns/discover?districtId=${district}&clusterCount=4`, button),
      fetch(`${API_BASE}/forecast/backtest?districtId=${district}&holdoutMonths=6`).then(r=>r.json()),
      fetch(`${API_BASE}/hotspots/forecast?districtId=${district}`).then(r=>r.json())
    ]);
    if (forecast.detail) throw new Error(forecast.detail); if (hotspots.detail) throw new Error(hotspots.detail);
    const cohesion = Math.round(patterns.clusters.reduce((sum, item)=>sum+item.cohesion,0)/patterns.clusters.length);
    summary.innerHTML = `<strong>AI evidence loaded for ${escapeLab(forecast.district)}.</strong> Every result below is evidence-led and requires officer review before operational action.`;
    models.innerHTML = [
      ["Narrative pattern discovery", `${cohesion}% cluster cohesion`, "TF-IDF vectors + MiniBatch K-Means", "FIR narrative text, crime type, district", "Review representative FIRs; clusters are leads, not proof."],
      ["Crime-volume forecasting", `${forecast.metrics.improvementVsNaive}% vs naive baseline`, forecast.model, forecast.modelDetails.features.join("; "), "Use for planning only; validate against current operational intelligence."],
      ["Hotspot demand outlook", `${hotspots.zones[0]?.predictedIncidents ?? 0} predicted incidents in top cell`, hotspots.model, "Geocoded FIR volume, recent lags, seasonality", "Deploy only after supervisor review; never treat as certainty of crime."]
    ].map(item=>`<article class="cluster-card"><div class="cluster-head"><h3>${escapeLab(item[0])}</h3><span class="cluster-score">${escapeLab(item[1])}</span></div><div class="funnel-label">Model: ${escapeLab(item[2])}</div><p style="font-size:11px;color:var(--text-secondary);margin-top:8px"><strong>Evidence:</strong> ${escapeLab(item[3])}</p><div class="quality-flag">Officer check: ${escapeLab(item[4])}</div></article>`).join("");
  } catch(error) { summary.textContent = error.message; }
}

function renderForecastChart(series) {
  const context=document.getElementById("forecast-chart").getContext('2d'); if(forecastChart) forecastChart.destroy();
  forecastChart=new Chart(context,{type:'line',data:{labels:series.map(item=>item.month),datasets:[{label:'Actual',data:series.map(item=>item.actual),borderColor:'#58A6FF',backgroundColor:'rgba(88,166,255,.12)',tension:.25},{label:'Predicted',data:series.map(item=>item.predicted),borderColor:'#D29922',borderDash:[6,4],tension:.25}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#C9D1D9'}}},scales:{x:{ticks:{color:'#8B949E'},grid:{color:'#21262D'}},y:{beginAtZero:true,ticks:{color:'#8B949E'},grid:{color:'#21262D'}}}}});
}

function initResponsiveShell() {
  const button=document.getElementById('mobile-menu-btn'); const sidebar=document.querySelector('.sidebar');
  button.addEventListener('click',()=>sidebar.classList.toggle('mobile-open'));
  document.querySelectorAll('.nav-link').forEach(link=>link.addEventListener('click',()=>sidebar.classList.remove('mobile-open')));
}

function renderPatrolMap(zones) {
  if (!patrolMap) { patrolMap = L.map("patrol-map", { zoomControl:true }); L.tileLayer(mapTilesUrl, { attribution:mapAttrib }).addTo(patrolMap); }
  if (patrolLayer) patrolLayer.remove(); patrolLayer = L.layerGroup().addTo(patrolMap);
  zones.forEach(zone => { const marker = L.marker([zone.lat,zone.lng], { icon:L.divIcon({ className:'zone-marker', html:zone.zone, iconSize:[34,34] }) }); marker.bindPopup(`<strong>${zone.zone}: ${escapeLab(zone.topCrime)}</strong><br>${zone.allocatedUnits} units · ${zone.cases} cases<br>Peak ${escapeLab(zone.peakWindow)}`).addTo(patrolLayer); L.circle([zone.lat,zone.lng], { radius:1300 + zone.riskScore*18, color:zone.allocatedUnits ? '#58A6FF':'#484F58', fillOpacity:.12, weight:1 }).addTo(patrolLayer); });
  patrolMap.fitBounds(L.latLngBounds(zones.map(zone => [zone.lat,zone.lng])).pad(.2));
}

// ─── NAVIGATION ───────────────────────────────────────────────────────────
function initNavigation() {
  const navLinks = document.querySelectorAll(".nav-link");
  
  navLinks.forEach(link => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      
      const target = link.getAttribute("data-target");
      if (!target) return;
      
      // Update active nav style
      navLinks.forEach(l => l.classList.remove("active"));
      link.classList.add("active");
      
      // Toggle panel display
      document.querySelectorAll(".content-panel").forEach(panel => {
        panel.classList.remove("active");
      });
      document.getElementById(`${target}-panel`).classList.add("active");
      
      activePanel = target;
      updateWorkspaceHeader(target);
      if (!labLoaded.has(target)) {
        labLoaded.add(target);
        if (target === "patterns") runPatternDiscovery();
        else if (target === "lifecycle") runLifecycleAnalysis();
        else if (target === "patrol") runPatrolPlan();
        else if (target === "quality") runQualityAudit();
        else if (target === "forecast") runForecastBacktest();
        else if (target === "ai") runAIConfidence();
      }
      
      // Resize/reinitialize maps & graphs on transition to ensure correct dimensions
      setTimeout(() => {
        if (target === "home" && dashboardMap) {
          dashboardMap.invalidateSize();
        } else if (target === "map" && mainMap) {
          mainMap.invalidateSize();
        } else if (target === "profile" && profileMap) {
          profileMap.invalidateSize(true);
          if (profilePolyline?.getBounds().isValid()) profileMap.fitBounds(profilePolyline.getBounds(), { padding:[35,35], maxZoom:11 });
        } else if (target === "networks" && networkInstance) {
          networkInstance.redraw();
          networkInstance.fit({ animation:{ duration:250 } });
        } else if (target === "networks" && activeNetworkGraph) {
          renderNetworkCanvas(activeNetworkGraph);
        } else if (target === "reconstruction" && reconstructionMap) {
          reconstructionMap.invalidateSize(true);
        } else if (target === "patrol" && patrolMap) {
          patrolMap.invalidateSize(true);
        }
        if (target === "alerts" && alertMap) alertMap.invalidateSize(true);
      }, 220);
    });
  });
}

// ─── SCREEN 1: HOME (COMMAND CENTRE) ──────────────────────────────────────
let sparklineChart = null;
let trendChart = null;

async function fetchDashboardData() {
  try {
    const res = await fetch(`${API_BASE}/dashboard`);
    const data = await res.json();
    
    // Update Morning Brief
    document.getElementById("dashboard-brief").textContent = data.morningBrief;
    
    // Update KPIs
    document.getElementById("kpi-crimes").textContent = data.kpi.crimesThisMonth.value.toLocaleString();
    const crimesDelta = document.getElementById("kpi-crimes-delta");
    crimesDelta.textContent = data.kpi.crimesThisMonth.delta;
    crimesDelta.className = `kpi-delta ${data.kpi.crimesThisMonth.deltaColor}`;
    
    document.getElementById("kpi-solved").textContent = data.kpi.casesSolved.value.toLocaleString();
    const solvedRate = document.getElementById("kpi-solved-rate");
    solvedRate.textContent = data.kpi.casesSolved.rate;
    solvedRate.className = `kpi-delta ${data.kpi.casesSolved.comparisonColor}`;
    document.getElementById("kpi-solved-comparison").textContent = data.kpi.casesSolved.comparison;
    
    document.getElementById("kpi-arrests").textContent = data.kpi.arrestsMade.value.toLocaleString();
    document.getElementById("kpi-arrests-subtext").textContent = data.kpi.arrestsMade.subtext;
    
    document.getElementById("kpi-alert-districts").textContent = data.kpi.attentionDistricts.value;
    document.getElementById("kpi-alert-names").textContent = data.kpi.attentionDistricts.districts;
    
    // Render sparkline
    renderSparkline(data.kpi.crimesThisMonth.sparkline);
    
    // Render trend chart
    renderTrendChart(data.trend);
    
    // Update what needs attention
    renderAttentionFeed(data.alerts);
    
  } catch (err) {
    console.error("Error fetching dashboard data:", err);
  }
}

function renderSparkline(points) {
  const ctx = document.getElementById("crimes-sparkline").getContext("2d");
  if (sparklineChart) sparklineChart.destroy();
  
  sparklineChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: points.map((_, i) => i),
      datasets: [{
        data: points,
        borderColor: '#F85149',
        borderWidth: 1.5,
        pointRadius: 0,
        fill: false,
        tension: 0.3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: { x: { display: false }, y: { display: false } }
    }
  });
}

function renderTrendChart(trend) {
  const ctx = document.getElementById("trend-chart-canvas").getContext("2d");
  if (trendChart) trendChart.destroy();
  
  // Custom plugin to draw Festive Season background overlay band
  const festivalBandPlugin = {
    id: 'festivalBand',
    beforeDraw: (chart) => {
      const { ctx, chartArea: { top, bottom, height }, scales: { x, y } } = chart;
      
      const startIndex = trend.labels.indexOf(trend.festiveOverlay.start);
      const endIndex = trend.labels.indexOf(trend.festiveOverlay.end);
      
      if (startIndex !== -1 && endIndex !== -1) {
        const left = x.getPixelForValue(startIndex);
        const right = x.getPixelForValue(endIndex);
        
        // Draw band background
        ctx.save();
        ctx.fillStyle = 'rgba(210, 153, 34, 0.06)';
        ctx.fillRect(left, top, right - left, height);
        
        // Draw band border
        ctx.strokeStyle = 'rgba(210, 153, 34, 0.2)';
        ctx.lineWidth = 1;
        ctx.strokeRect(left, top, right - left, height);
        
        // Draw text label
        ctx.fillStyle = '#D29922';
        ctx.font = '500 11px Inter';
        ctx.textAlign = 'center';
        ctx.fillText(trend.festiveOverlay.label, left + (right - left) / 2, top + 20);
        ctx.restore();
      }
    }
  };
  
  trendChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: trend.labels,
      datasets: [{
        label: 'Monthly Crime Count',
        data: trend.values,
        borderColor: '#1E6FD9',
        borderWidth: 2,
        backgroundColor: 'rgba(30, 111, 217, 0.05)',
        fill: true,
        tension: 0.3,
        pointBackgroundColor: '#58A6FF',
        pointRadius: 3,
        pointHoverRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: {
          grid: { color: '#21262D' },
          ticks: { color: '#8B949E', font: { family: 'Inter', size: 11 } }
        },
        y: {
          grid: { color: '#21262D' },
          ticks: { color: '#8B949E', font: { family: 'Inter', size: 11 } }
        }
      }
    },
    plugins: [festivalBandPlugin]
  });
}

function renderAttentionFeed(alerts) {
  const container = document.getElementById("dashboard-attention-feed");
  container.innerHTML = "";
  
  alerts.forEach(alert => {
    const card = document.createElement("div");
    card.className = `alert-card-item ${alert.severity}`;
    
    // Map links to dashboard navigation triggers
    let clickTarget = "home";
    if (alert.link === "alerts") clickTarget = "alerts";
    else if (alert.link === "networks") clickTarget = "networks";
    else if (alert.link === "profiles") clickTarget = "search";
    
    card.innerHTML = `
      <div class="alert-header-row">
        <span class="alert-item-title">${alert.title}</span>
        <span class="status-pill ${alert.severity === 'urgent' ? 'red-pill' : 'amber-pill'}">${alert.severity}</span>
      </div>
      <p class="alert-item-desc">${alert.description}</p>
      <a href="#" class="alert-card-link" onclick="triggerNav('${clickTarget}')">
        Investigate
        <svg viewBox="0 0 24 24" width="12" height="12"><path fill="currentColor" d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/></svg>
      </a>
    `;
    container.appendChild(card);
  });
}

function triggerNav(targetId) {
  document.querySelector(`a[data-target="${targetId}"]`).click();
}

// ─── SCREEN 2: CRIME MAP (Leaflet Integration) ────────────────────────────
let mapIncidents = [];
let hourSliderIndex = 20; // default 8 PM
let playInterval = null;

// Tile styling options (using dark CartoDB tiles)
const mapTilesUrl = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";
const mapAttrib = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

async function fetchMapData() {
  try {
    const res = await fetch(`${API_BASE}/map`);
    const data = await res.json();
    districtGeoJSON = data.geojson;
    mapIncidents = data.incidents;
    populateLabDistricts(data.geojson, data.districts);
    
    initMapLayers(data.geojson, mapIncidents);
    updateSliderChart(data.hourlyDistribution);
  } catch (err) {
    console.error("Error loading map coordinates:", err);
  }
}

let geojsonLayer = null;
let incidentMarkersGroup = L.layerGroup();
let hotspotForecastLayer = null;

function initMapLayers(geojson, incidents) {
  // 1. Dashboard mini map
  if (!dashboardMap) {
    dashboardMap = L.map("dashboard-map", {
      center: [15.3, 76.2], // Center of Karnataka
      zoom: 6,
      zoomControl: true,
      attributionControl: false
    });
    L.tileLayer(mapTilesUrl).addTo(dashboardMap);
  }
  
  // 2. Main full screen Map
  if (!mainMap) {
    mainMap = L.map("main-crime-map", {
      center: [15.3, 76.2],
      zoom: 7
    });
    L.tileLayer(mapTilesUrl, { attribution: mapAttrib }).addTo(mainMap);
    incidentMarkersGroup.addTo(mainMap);
  }
  
  // Draw choropleth boundaries on both maps
  renderChoropleth(geojson);
  
  // Filter and place dots based on slider hour
  updateIncidentMarkers();
}

// Shading algorithm from cream to deep red
function getDistrictColor(crimeCount) {
  return crimeCount > 15000 ? '#800026' :
         crimeCount > 5000  ? '#BD0026' :
         crimeCount > 2000  ? '#E31A1C' :
         crimeCount > 1000  ? '#FC4E2A' :
         crimeCount > 500   ? '#FD8D3C' :
         crimeCount > 200   ? '#FEB24C' :
         crimeCount > 50    ? '#FED976' :
                              '#FFEDA0';
}

function renderChoropleth(geojson) {
  if (geojsonLayer) {
    mainMap.removeLayer(geojsonLayer);
  }
  
  // Styling function for borders and fills
  function styleDistrict(feature) {
    const crimeCount = feature.properties.crimeCount || 0;
    const isPulsing = feature.properties.pulsing || false;
    
    return {
      fillColor: getDistrictColor(crimeCount),
      weight: 1,
      opacity: 0.8,
      color: '#21262D', // border lines
      fillOpacity: isPulsing ? 0.75 : 0.6
    };
  }
  
  // Hover interactions
  function onEachFeature(feature, layer) {
    layer.on({
      mouseover: (e) => {
        const l = e.target;
        l.setStyle({
          weight: 2,
          color: '#58A6FF',
          fillOpacity: 0.8
        });
        
        // Show tooltip popup
        const props = feature.properties;
        const tooltipContent = `
          <div style="font-family:Inter; color:#fff; padding:2px;">
            <strong>${props.districtName}</strong><br/>
            <span>Total Crimes: ${props.crimeCount.toLocaleString()}</span><br/>
            <span style="color:#D29922; font-size:11px;">Top Category: ${props.topCrime}</span>
          </div>
        `;
        l.bindToolTip = l.bindTooltip(tooltipContent, { sticky: true, className: 'map-tooltip' }).openTooltip();
      },
      mouseout: (e) => {
        geojsonLayer.resetStyle(e.target);
      },
      click: (e) => {
        // Trigger drill down panel for this district
        const distId = feature.properties.districtId;
        if (distId) {
          loadDistrictDrilldown(distId);
          triggerNav("drilldown");
        }
      }
    });
  }
  
  geojsonLayer = L.geoJSON(geojson, {
    style: styleDistrict,
    onEachFeature: onEachFeature
  }).addTo(mainMap);
  
  // Add simplified version to Dashboard map
  L.geoJSON(geojson, {
    style: styleDistrict
  }).addTo(dashboardMap);
}

function updateIncidentMarkers() {
  incidentMarkersGroup.clearLayers();
  
  // Filter incidents based on time slider and dropdown selectors
  const catFilter = document.getElementById("map-filter-category").value;
  const distFilter = document.getElementById("map-filter-district").value;
  
  // Get values from hour slider
  const selectedHour = parseInt(document.getElementById("time-of-day-slider").value);
  
  mapIncidents.forEach(inc => {
    // Hour check: extract hour from incident date time
    const incHour = new Date(inc.time).getHours();
    
    // Filter logic
    if (incHour !== selectedHour) return;
    if (catFilter && inc.categoryId !== parseInt(catFilter)) return;
    if (distFilter && inc.districtId !== parseInt(distFilter)) return;
    
    // Generate custom dot marker
    const markerColor = inc.type.includes("Murder") || inc.type.includes("Burglary") ? "#F85149" : "#58A6FF";
    
    const dot = L.circleMarker([inc.lat, inc.lng], {
      radius: 5,
      fillColor: markerColor,
      color: "#ffffff",
      weight: 1.2,
      opacity: 0.9,
      fillOpacity: 0.8
    });
    
    dot.bindPopup(`
      <div style="font-family:Inter; font-size:12px; color:#fff; width: 220px; line-height: 1.4;">
        <div style="font-weight:700; margin-bottom:4px; color:#58A6FF;">${inc.type}</div>
        <div style="font-size:10px; color:#8b949e; margin-bottom:6px;">FIR NO: <span style="font-family:monospace;">${inc.crimeNo}</span></div>
        <div style="font-size:11px; margin-bottom:6px;"><strong>Brief Facts:</strong> ${inc.facts}</div>
        <div style="font-size:10px; color:#8b949e;">Date: ${inc.date}</div>
      </div>
    `);
    
    incidentMarkersGroup.addLayer(dot);
  });
}

function getCategoryText(id) {
  const map = {
    "1": "Body",
    "2": "Property",
    "3": "Women",
    "4": "Economic",
    "6": "Cyber",
    "7": "NDPS"
  };
  return map[id] || "";
}

function initMapFilters() {
  document.getElementById("map-filter-category").addEventListener("change", updateIncidentMarkers);
  document.getElementById("map-filter-district").addEventListener("change", updateIncidentMarkers);
  document.getElementById("btn-ml-hotspots").addEventListener("click", runHotspotForecast);
  
  // Hour slider change
  const slider = document.getElementById("time-of-day-slider");
  const timeLabel = document.getElementById("slider-time-label");
  const contextDesc = document.getElementById("slider-context-desc");
  
  slider.addEventListener("input", (e) => {
    const val = parseInt(e.target.value);
    
    // Label updates
    let displayHour = val % 12;
    if (displayHour === 0) displayHour = 12;
    const ampm = val >= 12 ? "PM" : "AM";
    
    let label = `${displayHour}:00 ${ampm}`;
    let desc = "Standard routine patrolling window.";
    
    if (val === 20) {
      label += " — Evening Peak";
      desc = "Most chain snatchings happen between 6 PM and 9 PM near metro stations and bus stands.";
    } else if (val >= 0 && val <= 4) {
      label += " — Midnight Burglary Risk";
      desc = "House burglaries match the midnight entry method during these early hours.";
    } else if (val >= 9 && val <= 13) {
      label += " — Business Hours";
      desc = "Cyber frauds and scam texts see a high report rate during standard banking windows.";
    }
    
    timeLabel.textContent = label;
    contextDesc.textContent = desc;
    
    updateIncidentMarkers();
  });
  
  // Play Slider button
  const playBtn = document.getElementById("btn-play-slider");
  const playIcon = document.getElementById("play-icon");
  const pauseIcon = document.getElementById("pause-icon");
  
  playBtn.addEventListener("click", () => {
    if (playInterval) {
      // Pause
      clearInterval(playInterval);
      playInterval = null;
      playIcon.style.display = "block";
      pauseIcon.style.display = "none";
    } else {
      // Play
      playIcon.style.display = "none";
      pauseIcon.style.display = "block";
      
      playInterval = setInterval(() => {
        let cur = parseInt(slider.value);
        cur = (cur + 1) % 24;
        slider.value = cur;
        slider.dispatchEvent(new Event('input'));
      }, 1500); // 1.5 seconds per hour frame
    }
  });
  
  // Floating alert cards maps triggers
  document.getElementById("btn-map-alert-investigate").addEventListener("click", () => {
    if (activeAlertsList.length > 0) loadAlertDetails(activeAlertsList[0].id);
    triggerNav("alerts");
  });
  
  document.getElementById("btn-map-alert-dismiss").addEventListener("click", () => {
    document.getElementById("map-alert-card").style.display = "none";
  });
  document.getElementById("btn-close-map-alert").addEventListener("click", () => {
    document.getElementById("map-alert-card").style.display = "none";
  });
  document.getElementById("btn-floating-situations").addEventListener("click", () => {
    triggerNav("alerts");
  });
}

async function runHotspotForecast() {
  const button = document.getElementById("btn-ml-hotspots");
  const district = document.getElementById("map-filter-district").value || "1";
  const category = document.getElementById("map-filter-category").value;
  const outlook = document.getElementById("map-ml-outlook");
  try {
    const data = await fetchLab(`/hotspots/forecast?districtId=${district}${category ? `&crimeHeadId=${category}` : ""}`, button);
    if (hotspotForecastLayer) hotspotForecastLayer.remove();
    hotspotForecastLayer = L.layerGroup().addTo(mainMap);
    data.zones.forEach((zone, index) => L.circleMarker([zone.lat, zone.lng], {radius:7 + Math.min(zone.predictedIncidents, 8), color:"#ffbf47", fillColor:"#f85149", fillOpacity:.68, weight:2}).bindPopup(`<strong>ML hotspot ${index+1}</strong><br>Forecast: ${zone.predictedIncidents} incidents<br>Recent FIRs: ${zone.recentIncidents}<br>${escapeLab(data.forecastMonth)}`).addTo(hotspotForecastLayer));
    outlook.hidden = false;
    outlook.innerHTML = `<strong>ML hotspot outlook · ${escapeLab(data.forecastMonth)}</strong>${escapeLab(data.district)} · ${data.zones.length} forecast cells shown in red/amber.<br><br>${escapeLab(data.method)}<br><br><em>${escapeLab(data.caveat)}</em>`;
  } catch (error) { outlook.hidden=false; outlook.textContent=error.message; }
}

let sliderChart = null;
function updateSliderChart(dist) {
  // Optional time bar sparkline in maps could be drawn. We skip to avoid visual clutter unless needed.
}

function fillSearch(value) {
  const cleanValue = value.replace(/\s*\(.*\)\s*/, "").trim();
  const searchInput = document.getElementById("global-search-input");
  if (searchInput) {
    searchInput.value = cleanValue;
    triggerNav("search");
    searchInput.dispatchEvent(new Event('input'));
  }
}

// ─── SCREEN 3: SEARCH & INVESTIGATE ───────────────────────────────────────
function initSearch() {
  const searchInput = document.getElementById("global-search-input");
  const searchSubmit = document.getElementById("global-search-submit");
  const openSearchWorkspace = () => {
    if (activePanel !== "search") triggerNav("search");
  };
  const runSearch = () => searchInput.dispatchEvent(new Event("input"));

  searchInput.addEventListener("focus", openSearchWorkspace);
  searchInput.addEventListener("keydown", event => {
    if (event.key === "Enter") {
      event.preventDefault();
      openSearchWorkspace();
      runSearch();
    }
  });
  searchSubmit.addEventListener("click", () => {
    openSearchWorkspace();
    runSearch();
  });
  
  searchInput.addEventListener("input", async (e) => {
    const q = e.target.value.trim();
    if (q.length < 2) {
      document.getElementById("search-results-area").style.display = "none";
      document.getElementById("search-guidance").textContent = "Enter at least two characters, or choose a validated scenario.";
      return;
    }

    // The global input is the entry point to investigation. Make results
    // visible immediately rather than leaving them hidden on the prior screen.
    openSearchWorkspace();
    
    try {
      const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      
      renderSearchResults(data);
    } catch (err) {
      console.error("Search query failure:", err);
    }
  });
}

function initCommandQueryAssistant() {
  const form = document.getElementById("command-query-form");
  const input = document.getElementById("command-query-input");
  const result = document.getElementById("command-query-result");
  if (!form || !input || !result) return;

  const runQuery = async value => {
    const query = value.trim();
    if (query.length < 4) return;
    result.hidden = false;
    result.innerHTML = "<strong>Analysing FIR records…</strong><span>Identifying explicit district, offence, time, and repeat-accused conditions.</span>";
    try {
      const response = await fetch(`${API_BASE}/command-query?q=${encodeURIComponent(query)}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Command query unavailable");
      const suspects = (data.suspects || []).map(person => `<span>${escapeLab(person.name)} · ${person.caseCount} FIRs · ${person.districtCount} districts</span>`).join("");
      result.innerHTML = `<strong>${escapeLab(data.answer)}</strong><div>${escapeLab(data.scope)}</div>${data.languageMode === "Kannada-assisted" ? `<div class="command-query-meta">Kannada query interpreted as: ${escapeLab(data.interpretedQuery)}</div>` : ""}${suspects ? `<div class="command-query-suspects">${suspects}</div>` : ""}<div class="command-query-meta">Recommended action: ${escapeLab(data.recommendedAction)}<br>${escapeLab(data.method)}</div>`;
      renderSearchResults({ people: [], phones: [], vehicles: [], cases: data.cases || [] });
      document.getElementById("search-guidance").textContent = "Command query results are shown below. Review the stated filters before acting on any intelligence.";
    } catch (error) {
      result.innerHTML = `<strong>Query could not be completed</strong><span>${escapeLab(error.message)}</span>`;
    }
  };

  form.addEventListener("submit", event => {
    event.preventDefault();
    runQuery(input.value);
  });
  document.querySelectorAll("[data-command-query]").forEach(button => {
    button.addEventListener("click", () => {
      input.value = button.dataset.commandQuery;
      runQuery(input.value);
    });
  });

  const semanticForm = document.getElementById("semantic-query-form");
  const semanticInput = document.getElementById("semantic-query-input");
  const semanticResult = document.getElementById("semantic-query-result");
  semanticForm?.addEventListener("submit", async event => {
    event.preventDefault(); const query = semanticInput.value.trim(); if (query.length < 4) return;
    semanticResult.hidden = false; semanticResult.innerHTML = "<strong>Finding similar FIR narratives…</strong>";
    try {
      const response = await fetch(`${API_BASE}/semantic-search?q=${encodeURIComponent(query)}`); const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Semantic search unavailable");
      semanticResult.innerHTML = `<strong>AI semantic search completed.</strong><div>Top FIR similarity: ${data.cases[0]?.semanticConfidence ?? 0}%</div><div class="command-query-meta">${escapeLab(data.model)}<br>${escapeLab(data.caveat)}</div>`;
      renderSearchResults(data);
      document.getElementById("search-guidance").textContent = "Semantic results are narrative-similar FIRs. Validate every source FIR and do not treat similarity as a confirmed linkage.";
    } catch (error) { semanticResult.innerHTML = `<strong>Search could not be completed</strong><span>${escapeLab(error.message)}</span>`; }
  });
}

function renderSearchResults(data) {
  const resultsArea = document.getElementById("search-results-area");
  resultsArea.style.display = "block";
  const total = ["people", "phones", "vehicles", "cases"]
    .reduce((sum, key) => sum + (data[key]?.length || 0), 0);
  const guidance = document.getElementById("search-guidance");
  guidance.className = `analysis-note${total ? "" : " warning"}`;
  guidance.textContent = total
    ? `${total} evidence-linked result${total === 1 ? "" : "s"} found. Open a profile, reconstruct an FIR, or inspect MO links.`
    : "No matching Catalyst records. Try an offence such as burglary, an accused name, a FIR number, phone 98450, or vehicle KA-05.";
  
  // 1. Suspect People
  const peopleSec = document.getElementById("section-people");
  const peopleGrid = document.getElementById("grid-people");
  peopleGrid.innerHTML = "";
  
  if (data.people && data.people.length > 0) {
    peopleSec.style.display = "block";
    data.people.forEach(p => {
      const card = document.createElement("div");
      card.className = "result-card";
      
      const pills = p.pills.map(pill => `<span class="status-pill ${pill.includes('PRIORITY') ? 'red-pill' : 'amber-pill'}">${pill}</span>`).join("");
      
      card.innerHTML = `
        <div class="result-card-header">
          <div>
            <div class="result-card-title">${p.name}</div>
            ${p.aliases ? `<div class="result-card-alias">alias: ${p.aliases}</div>` : ''}
          </div>
          <span class="status-pill ${p.status === 'NO ARREST RECORD' ? 'amber-pill' : 'blue-pill'}">${p.status}</span>
        </div>
        <div class="result-card-meta">Age ${p.age} · ${p.gender} · Latest linked FIR: ${p.lastSeen}</div>
        <div class="result-pills-row">${pills}</div>
        <div class="result-details-grid">
          <div class="result-details-row">
            <span class="result-det-label">Case Count</span>
            <span class="result-det-val">${p.caseCount} FIRs</span>
          </div>
          <div class="result-details-row">
            <span class="result-det-label">Active areas</span>
            <span class="result-det-val">${p.districts}</span>
          </div>
          <div class="result-details-row">
            <span class="result-det-label">Modus Operandi</span>
            <span class="result-det-val" style="color:var(--accent-blue-lt);">${p.crimeType}</span>
          </div>
        </div>
        <button class="btn btn-secondary btn-sm w-100" style="width:100%;" onclick="loadSuspectProfile('${p.name}')">View Intel Profile</button>
      `;
      peopleGrid.appendChild(card);
    });
  } else {
    peopleSec.style.display = "none";
  }
  
  // 2. Phones
  const phonesSec = document.getElementById("section-phones");
  const phonesGrid = document.getElementById("grid-phones");
  phonesGrid.innerHTML = "";
  
  if (data.phones && data.phones.length > 0) {
    phonesSec.style.display = "block";
    data.phones.forEach(ph => {
      const card = document.createElement("div");
      card.className = "result-card";
      card.innerHTML = `
        <div class="result-card-header">
          <div class="result-card-title">${ph.number}</div>
        </div>
        <div class="result-card-meta">Registered to: ${ph.owner}</div>
        <div class="mo-badge-alert" style="margin-bottom:12px; font-size:11px; padding:6px 10px;">
          <span>${ph.warning}</span>
        </div>
        <div class="result-details-grid">
          <div class="result-details-row">
            <span class="result-det-label">Appears in</span>
            <span class="result-det-val">${ph.caseCount} FIRs</span>
          </div>
          <div class="result-details-row">
            <span class="result-det-label">Linked districts</span>
            <span class="result-det-val">${ph.districts}</span>
          </div>
        </div>
        <button class="btn btn-secondary btn-sm" style="width:100%;" onclick="fillSearch('${ph.owner}')">Inspect Registered Owner</button>
      `;
      phonesGrid.appendChild(card);
    });
  } else {
    phonesSec.style.display = "none";
  }
  
  // 3. Vehicles
  const vehiclesSec = document.getElementById("section-vehicles");
  const vehiclesGrid = document.getElementById("grid-vehicles");
  vehiclesGrid.innerHTML = "";
  
  if (data.vehicles && data.vehicles.length > 0) {
    vehiclesSec.style.display = "block";
    data.vehicles.forEach(v => {
      const card = document.createElement("div");
      card.className = "result-card";
      card.innerHTML = `
        <div class="result-card-header">
          <div class="result-card-title">${v.plate}</div>
        </div>
        <div class="result-card-meta">${v.description}</div>
        <div class="mo-badge-alert" style="margin-bottom:12px; font-size:11px; padding:6px 10px;">
          <span>${v.warning}</span>
        </div>
        <div class="result-details-grid">
          <div class="result-details-row">
            <span class="result-det-label">Appears in</span>
            <span class="result-det-val">${v.caseCount} Cases</span>
          </div>
          <div class="result-details-row">
            <span class="result-det-label">Patterns</span>
            <span class="result-det-val" style="text-align:right;">${v.pattern}</span>
          </div>
        </div>
        <button class="btn btn-secondary btn-sm" style="width:100%;" onclick="triggerNav('networks')">View Network Map</button>
      `;
      vehiclesGrid.appendChild(card);
    });
  } else {
    vehiclesSec.style.display = "none";
  }
  
  // 4. Cases
  const casesSec = document.getElementById("section-cases");
  const casesBody = document.getElementById("table-cases-body");
  casesBody.innerHTML = "";
  
  if (data.cases && data.cases.length > 0) {
    casesSec.style.display = "block";
    data.cases.forEach(c => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td class="text-mono">${c.crimeNo}</td>
        <td>${c.date}</td>
        <td><span class="status-pill border-pill">${c.type}</span></td>
        <td>${c.district}</td>
        <td><span class="status-pill ${c.status === 'Closed / Final Report' ? 'green-pill' : 'amber-pill'}">${c.status}</span></td>
        <td style="max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${c.facts}${c.semanticConfidence != null ? ` <span class="status-pill blue-pill">Semantic ${c.semanticConfidence}%</span>` : ''}</td>
        <td>
          <div style="display:flex; gap:6px; flex-wrap:wrap;">
            <button class="btn btn-secondary btn-sm" onclick="loadCaseMO('${c.id}')">Find MO Links</button>
            <button class="btn btn-primary btn-sm" onclick="loadIncidentReconstruction('${c.id}')">Reconstruct</button>
          </div>
        </td>
      `;
      casesBody.appendChild(row);
    });
  } else {
    casesSec.style.display = "none";
  }
}

async function loadCaseMO(caseId) {
  try {
    const res = await fetch(`${API_BASE}/cases/${encodeURIComponent(caseId)}/links`);
    if (!res.ok) throw new Error(`Case link request failed: ${res.status}`);
    const data = await res.json();
    const source = data.sourceCase;
    const related = data.relatedCases;
    const districts = [...new Set(related.map(item => item.district))];
    const bestScore = related.length ? related[0].connectionScore : 0;
    const dynamicAlert = {
      id: `case-links-${source.caseId}`,
      severity: bestScore >= 80 ? "urgent" : "watch",
      title: `${related.length} explainable links for FIR ${source.crimeNo}`,
      timeText: "Computed on demand · Explainable ML Case Similarity",
      description: `${related.length} related cases across ${districts.length} district(s); strongest evidence connection score ${bestScore}/100.`,
      whatHappened: `Drishti compared the FIR narrative and relational records against 50,460 indexed cases. ML similarity confidence is ranked using FIR narrative / MO, offence type, location, time-of-day, and known cross-case links. It is an investigative lead, not proof.`,
      cases: related,
      evidence: related.slice(0, 5).map(item => ({
        label: `${item.crimeNo} · ${item.district} · ML similarity confidence ${item.similarityConfidence ?? item.mlConfidence ?? '—'}%`,
        value: `${item.similaritySignals?.map(signal => `${signal.label}: ${signal.value}`).join(" · ") || item.evidence.map(e => e.value).join("; ")} · Evidence connection ${item.connectionScore}/100`
      })),
      recommendedAction: "Suggested response: Review the evidence for the highest-scoring links and validate the associated FIRs before merging or coordinating investigations."
    };

    activeAlertsList = [dynamicAlert, ...activeAlertsList.filter(item => item.id !== dynamicAlert.id)];
    renderAlertsSidebarFeed(activeAlertsList);
    triggerNav("alerts");
    loadAlertDetails(dynamicAlert.id);
  } catch (err) {
    console.error("Unable to compute MO links:", err);
  }
}

// ─── SCREEN: INCIDENT RECONSTRUCTION ─────────────────────────────────────
function initReconstruction() {
  const slider = document.getElementById("reconstruction-slider");
  const playButton = document.getElementById("reconstruction-play");
  slider.addEventListener("input", () => renderReconstructionStep(parseInt(slider.value)));
  playButton.addEventListener("click", toggleReconstructionPlayback);
  document.getElementById("btn-request-review").addEventListener("click", () => submitOperationalAction(false));
  document.getElementById("btn-approve-coordination").addEventListener("click", () => submitOperationalAction(true));
}

async function loadIncidentReconstruction(caseId) {
  try {
    labLoaded.add("reconstruction");
    reconstructionData = await fetchJson(`/cases/${encodeURIComponent(caseId)}/reconstruction`);
    const aiBrief = await fetchJson(`/cases/${encodeURIComponent(caseId)}/ai-brief`);
    const pdfButton = document.getElementById("btn-case-pdf");
    pdfButton.href = `${API_BASE}/cases/${encodeURIComponent(caseId)}/brief.pdf`;
    pdfButton.classList.remove("disabled-link");
    pdfButton.removeAttribute("aria-disabled");
    if (activePanel !== "reconstruction") triggerNav("reconstruction");
    renderReconstructionSummary();
    renderAIFIRBrief(aiBrief);
    window.setTimeout(() => {
      initializeReconstructionMap();
      renderReconstructionStep(0);
      reconstructionMap.invalidateSize(true);
    }, 120);

    const slider = document.getElementById("reconstruction-slider");
    slider.min = 0;
    slider.max = Math.max(0, reconstructionData.events.length - 1);
    slider.value = 0;
  } catch (error) {
    console.error("Unable to reconstruct incident:", error);
    document.getElementById("reconstruction-title").textContent = "Unable to load reconstruction";
    document.getElementById("reconstruction-summary").textContent = error.message;
  }
}

function renderAIFIRBrief(brief) {
  const container = document.getElementById("ai-fir-brief");
  container.innerHTML = `<p class="mo-paragraph">${escapeLab(brief.summary)}</p><div class="term-row">${brief.keywords.map(keyword => `<span class="term-pill">${escapeLab(keyword)}</span>`).join('') || '<span class="term-pill">No keywords available</span>'}</div><div class="details-list" style="margin-top:14px;">${brief.entities.map(entity => `<div class="details-item"><span class="details-label">${escapeLab(entity.type)} · ${entity.confidence}%</span><span class="details-value">${escapeLab(entity.value)}<small style="display:block;color:var(--text-muted)">${escapeLab(entity.source)}</small></span></div>`).join('') || '<div class="details-item"><span class="details-value">No extractable entities found.</span></div>'}</div><div class="human-review-note" style="margin-top:12px;">${escapeLab(brief.caveat)}</div>`;
}

function initializeReconstructionMap() {
  if (reconstructionMap) {
    reconstructionMap.remove();
    reconstructionMap = null;
  }
  const incident = reconstructionData.events.find(event => event.type === "incident") || reconstructionData.events[0];
  reconstructionMap = L.map("reconstruction-map", {
    center: [incident.lat, incident.lng],
    zoom: 14,
    zoomControl: true,
    attributionControl: false
  });
  L.tileLayer(mapTilesUrl).addTo(reconstructionMap);
  reconstructionLayer = L.layerGroup().addTo(reconstructionMap);

  if (reconstructionData.routeCoordinates.length > 1) {
    L.polyline(
      reconstructionData.routeCoordinates.map(point => [point.lat, point.lng]),
      { color: "#D29922", weight: 2, dashArray: "7 7", opacity: 0.75 }
    ).addTo(reconstructionMap).bindTooltip("Illustrative route — exact movement evidence missing");
  }
}

function renderReconstructionSummary() {
  const currentCase = reconstructionData.case;
  document.getElementById("reconstruction-title").textContent = `${currentCase.crimeType} · FIR ${currentCase.crimeNo}`;
  document.getElementById("reconstruction-summary").textContent = currentCase.briefFacts;
  const completeness = document.getElementById("reconstruction-completeness");
  completeness.textContent = `${reconstructionData.dataCompleteness}% DATA COMPLETE`;
  completeness.className = `status-pill ${reconstructionData.dataCompleteness >= 70 ? 'green-pill' : 'amber-pill'} large`;

  const missingContainer = document.getElementById("reconstruction-missing-links");
  missingContainer.innerHTML = "";
  reconstructionData.missingLinks.forEach(link => {
    const item = document.createElement("div");
    item.className = `missing-link-item ${link.status}`;
    item.innerHTML = `
      <div class="missing-link-heading"><span>${link.field}</span><span class="status-pill ${link.status === 'conflict' ? 'red-pill' : 'amber-pill'}">${link.status}</span></div>
      <div>${link.impact}</div>
      <small>Next: ${link.nextStep}</small>
    `;
    missingContainer.appendChild(item);
  });

  const decision = reconstructionData.decisionSupport;
  document.getElementById("reconstruction-decision").innerHTML = `
    <div class="decision-score-row">
      <span class="status-pill ${decision.priority === 'HIGH REVIEW' ? 'red-pill' : 'blue-pill'}">${decision.priority}</span>
      <strong>Strongest case link: ${decision.strongestLinkScore}/100</strong>
    </div>
    <div class="header-muted-label" style="margin:10px 0;">Affected districts: ${decision.affectedDistricts.join(', ') || 'Current district only'}</div>
    <ol class="decision-list">${decision.recommendedActions.map(action => `<li>${action}</li>`).join('')}</ol>
    <div class="human-review-note">Human approval is mandatory before any operational action.</div>
  `;
  document.getElementById("btn-request-review").disabled = false;
  document.getElementById("btn-approve-coordination").disabled = false;
  document.getElementById("reconstruction-audit-result").textContent = "";
}

function renderReconstructionStep(index) {
  if (!reconstructionData || !reconstructionLayer) return;
  const events = reconstructionData.events;
  const currentEvent = events[index];
  reconstructionLayer.clearLayers();

  events.slice(0, index + 1).forEach((event, eventIndex) => {
    const marker = L.marker([event.lat, event.lng], {
      icon: L.divIcon({
        className: `reconstruction-marker ${event.confidence === 'inferred' ? 'inferred' : 'recorded'} ${eventIndex === index ? 'current' : ''}`,
        html: `<span>${event.icon}</span>`,
        iconSize: [30, 30],
        iconAnchor: [15, 15]
      })
    }).addTo(reconstructionLayer);
    marker.bindPopup(`<strong>${event.label}</strong><br>${formatReconstructionTime(event)}<br><small>${event.source}</small>`);
  });

  reconstructionMap.panTo([currentEvent.lat, currentEvent.lng]);
  document.getElementById("reconstruction-time").textContent = formatReconstructionTime(currentEvent);
  document.getElementById("reconstruction-event-label").textContent = `${currentEvent.icon} ${currentEvent.label}`;
  document.getElementById("reconstruction-event-source").textContent = `${currentEvent.confidence.toUpperCase()} · ${currentEvent.source}`;
}

function formatReconstructionTime(event) {
  if (event.displayTime) return event.displayTime;
  return new Date(event.timestamp).toLocaleString("en-IN", {
    day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit"
  });
}

function toggleReconstructionPlayback() {
  if (!reconstructionData) return;
  const slider = document.getElementById("reconstruction-slider");
  if (reconstructionInterval) {
    clearInterval(reconstructionInterval);
    reconstructionInterval = null;
    return;
  }
  reconstructionInterval = setInterval(() => {
    const next = parseInt(slider.value) + 1;
    if (next > parseInt(slider.max)) {
      clearInterval(reconstructionInterval);
      reconstructionInterval = null;
      return;
    }
    slider.value = next;
    renderReconstructionStep(next);
  }, 1400);
}

async function submitOperationalAction(approved) {
  if (!reconstructionData) return;
  const decision = reconstructionData.decisionSupport;
  const payload = {
    caseId: reconstructionData.case.caseId,
    actionType: approved ? "district-coordination" : "analyst-review",
    rationale: approved
      ? `Coordinate evidence review across ${decision.affectedDistricts.join(', ') || reconstructionData.case.district}`
      : `Validate ${reconstructionData.missingLinks.length} missing or partial evidence links`,
    approved
  };
  const response = await fetch(`${API_BASE}/actions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const result = await response.json();
  document.getElementById("reconstruction-audit-result").textContent = response.ok
    ? `Audit #${result.actionId}: ${result.status} · ${result.timestamp}`
    : `Action could not be recorded: ${result.detail || response.status}`;
}

// ─── SCREEN 4: INTELLIGENCE PROFILES ──────────────────────────────────────
async function loadSuspectProfile(name) {
  try {
    labLoaded.add("profile");
    const state = document.getElementById("profile-load-state");
    state.className = "analysis-note";
    state.textContent = `Loading evidence linked to ${name}…`;
    const data = await fetchJson(`/profile/${encodeURIComponent(name)}`);
    currentProfile = data;
    
    // Render text data
    document.getElementById("profile-name").textContent = data.name;
    document.getElementById("profile-alias").textContent = data.alias ? `alias ${data.alias}` : '';
    document.getElementById("profile-demographics").textContent = `${data.age == null ? "Age unavailable" : `Age ${data.age}`} · Gender ${data.gender} · Last linked FIR: ${data.lastSeen}`;
    
    // Status badges
    const riskPill = document.getElementById("profile-risk-pill");
    riskPill.textContent = data.pills[0] || "SUSPECT PROFILE";
    riskPill.className = `status-pill ${riskPill.textContent.includes('PRIORITY') ? 'red-pill' : 'amber-pill'} large`;
    const statusPill = document.getElementById("profile-status-pill");
    statusPill.textContent = data.status;
    statusPill.className = `status-pill ${data.status === 'NO ARREST RECORD' ? 'amber-pill' : 'blue-pill'} large`;
    
    // Detail counts
    document.getElementById("prof-aadhaar").textContent = data.contactInfo.aadhaar;
    document.getElementById("prof-phones").textContent = data.contactInfo.phone;
    document.getElementById("prof-address").textContent = data.contactInfo.address;
    document.getElementById("prof-vehicle").textContent = data.contactInfo.vehicle;
    
    document.getElementById("prof-father").textContent = data.family.father;
    document.getElementById("prof-brother").textContent = data.family.brother;
    document.getElementById("prof-mo-desc").textContent = data.moDescription;
    
    // Co-accused associates chips
    const associatesList = document.getElementById("prof-associates-list");
    associatesList.innerHTML = "";
    data.family.associates.forEach(assoc => {
      const chip = document.createElement("span");
      chip.className = "detail-chip";
      chip.textContent = `${assoc.name} (${assoc.casesShared} shared cases)`;
      chip.addEventListener("click", () => {
        loadSuspectProfile(assoc.name);
      });
      associatesList.appendChild(chip);
    });
    
    // Draw Timeline
    const timeline = document.getElementById("profile-timeline");
    timeline.innerHTML = "";
    data.timeline.forEach((t, i) => {
      const block = document.createElement("div");
      block.className = `timeline-block ${i === 0 ? 'active' : ''}`;
      block.innerHTML = `
        <div class="timeline-dot"></div>
        <div class="timeline-date">${t.date}</div>
        <div class="timeline-title">${t.type} · FIR #${t.crimeNo.slice(-5)}</div>
        <div class="timeline-meta">${t.district} · ${t.status}</div>
        <div class="timeline-desc">${t.briefFacts}</div>
      `;
      timeline.appendChild(block);
    });
    
    // Switch to profile tab
    if (activePanel !== "profile") triggerNav("profile");
    profileLoaded = true;
    window.setTimeout(() => {
      renderProfilePathMap(data.movement);
      profileMap?.invalidateSize(true);
    }, 120);
    state.className = "analysis-note";
    state.textContent = `${data.timeline.length} linked FIRs and ${data.movement.length} mapped incident coordinates loaded from Catalyst.`;

    const nextActions = document.getElementById("profile-next-actions");
    const networkButton = document.getElementById("profile-open-network");
    const reconstructionButton = document.getElementById("profile-open-reconstruction");
    networkButton.disabled = false;
    reconstructionButton.disabled = !data.timeline.length;
    const linkedGroup = /snatch/i.test(data.moDescription || "")
      ? "Indiranagar Chain Snatching Group"
      : "Drill & Enter Group";
    networkButton.onclick = () => {
      triggerNav("networks");
      window.setTimeout(() => fetchNetworkGroupGraph(linkedGroup), 140);
    };
    reconstructionButton.onclick = () => {
      if (data.timeline[0]?.id) loadIncidentReconstruction(data.timeline[0].id);
    };
    
  } catch (err) {
    console.error("Failed loading suspect profile:", err);
    const state = document.getElementById("profile-load-state");
    state.className = "analysis-note warning";
    state.textContent = `Profile unavailable: ${err.message}`;
    document.getElementById("profile-name").textContent = "Profile could not be loaded";
    document.getElementById("profile-timeline").innerHTML = `<div class="empty-state-detail"><p>${escapeLab(err.message)}</p></div>`;
    document.getElementById("profile-open-network").disabled = true;
    document.getElementById("profile-open-reconstruction").disabled = true;
  }
}

let profilePolyline = null;
let profileMarkers = [];

function renderProfilePathMap(coords) {
  if (!profileMap) {
    profileMap = L.map("profile-movement-map", {
      center: [15.3, 76.2],
      zoom: 6,
      zoomControl: true,
      attributionControl: false
    });
    L.tileLayer(mapTilesUrl).addTo(profileMap);
  }
  
  // Clear old markings
  if (profilePolyline) profileMap.removeLayer(profilePolyline);
  profileMarkers.forEach(m => profileMap.removeLayer(m));
  profileMarkers = [];
  
  if (coords.length === 0) return;
  
  const points = coords.map(c => [c.lat, c.lng]);
  
  // Draw line
  profilePolyline = L.polyline(points, {
    color: '#F85149',
    weight: 2,
    dashArray: '5, 10'
  }).addTo(profileMap);
  
  // Draw markers
  coords.forEach((c, idx) => {
    const marker = L.circleMarker([c.lat, c.lng], {
      radius: idx === 0 ? 6 : 4,
      fillColor: idx === 0 ? '#F85149' : '#8B949E',
      color: '#fff',
      weight: 1
    }).addTo(profileMap);
    
    marker.bindTooltip(`${c.date}: ${c.district}`, { className: 'map-tooltip' });
    profileMarkers.push(marker);
  });
  
  // Pan to fit path bounds
  profileMap.fitBounds(profilePolyline.getBounds(), { padding: [20, 20] });
}

// ─── SCREEN 5: CRIME NETWORKS (Vis.js Node Graph) ─────────────────────────
async function fetchNetworkGroups() {
  try {
    const res = await fetch(`${API_BASE}/networks`);
    const data = await res.json();
    
    renderNetworkGroupsSidebar(data.groups);
    document.getElementById("network-title").textContent = `${data.groups[0].name} Network Link`;
    document.getElementById("network-explanation").textContent = data.selectedGroup.explanation;
    renderNetworkCanvas(data.selectedGroup);
  } catch (err) {
    console.error("Error fetching network groups:", err);
  }
}

function renderNetworkGroupsSidebar(groups) {
  const feed = document.getElementById("networks-groups-feed");
  feed.innerHTML = "";
  
  groups.forEach((g, idx) => {
    const card = document.createElement("div");
    card.className = `network-group-card ${idx === 0 ? 'active' : ''}`;
    card.innerHTML = `
      <div class="net-group-title">${g.name}</div>
      <div class="net-group-sub">${g.size} suspects · ${g.cases} cases · ${g.districts}</div>
      <div class="net-group-status" style="color:${g.status.includes('AT LARGE') ? 'var(--alert-red)' : 'var(--success-green)'}">${g.status}</div>
    `;
    card.addEventListener("click", () => {
      document.querySelectorAll(".network-group-card").forEach(c => c.classList.remove("active"));
      card.classList.add("active");
      
      // Load details
      fetchNetworkGroupGraph(g.name);
    });
    feed.appendChild(card);
  });
}

async function fetchNetworkGroupGraph(groupName) {
  try {
    const res = await fetch(`${API_BASE}/networks?groupName=${encodeURIComponent(groupName)}`);
    const data = await res.json();
    
    document.getElementById("network-title").textContent = `${groupName} Network Link`;
    document.getElementById("network-explanation").textContent = data.selectedGroup.explanation;
    
    renderNetworkCanvas(data.selectedGroup);
  } catch (err) {
    console.error("Failed loading group graph nodes:", err);
  }
}

function renderNetworkCanvas(graphData) {
  const container = document.getElementById("network-graph-canvas");
  activeNetworkGraph = graphData;
  if (!container.offsetWidth || !container.offsetHeight) return;
  if (networkInstance) {
    networkInstance.destroy();
    networkInstance = null;
  }
  // Use the deterministic SVG renderer in production. It cannot disappear
  // because of canvas sizing, CDN timing, or physics stabilization.
  renderNetworkFallback(container, graphData);
  return;

  // Vis.js formats
  const nodeCount = graphData.nodes.length;
  const nodes = new vis.DataSet(graphData.nodes.map((n, index) => {
    let shape = "dot";
    let iconLabel = n.label;
    
    // Choose styling based on node group
    if (n.group === "asset") {
      shape = "box";
    }
    
    return {
      id: n.id,
      label: n.label,
      shape: shape,
      size: n.size || 15,
      color: {
        background: n.color,
        border: '#21262D',
        highlight: { background: '#58A6FF', border: '#FFF' }
      },
      font: { color: '#E6EDF3', face: 'Manrope', size: 14, strokeWidth: 3, strokeColor: '#08111c' },
      title: n.title,
      group: n.group,
      x: Math.cos((index / Math.max(1,nodeCount)) * Math.PI * 2) * (180 + (index % 3) * 35),
      y: Math.sin((index / Math.max(1,nodeCount)) * Math.PI * 2) * (135 + (index % 2) * 30)
    };
  }));
  
  const edges = new vis.DataSet(graphData.edges.map(e => ({
    from: e.from,
    to: e.to,
    label: e.label,
    font: { color: '#AFC4D8', size: 10, face: 'Manrope', align: 'horizontal', strokeWidth: 2, strokeColor: '#08111c' },
    color: { color: e.color || '#21262D', highlight: '#58A6FF' },
    width: e.width || 1
  })));
  
  const data = { nodes, edges };
  
  const options = {
    layout: {
      improvedLayout: true,
      randomSeed: 12
    },
    physics: false,
    interaction: {
      hover: true,
      tooltipDelay: 100,
      zoomView: true,
      dragView: true,
      navigationButtons: true,
      keyboard: { enabled: true, bindToWindow: false }
    },
    nodes: { borderWidth: 2, shadow: { enabled:true, color:'rgba(0,0,0,.35)', size:8, x:0, y:3 } },
    edges: { smooth: { enabled:true, type:'dynamic', roundness:.18 }, selectionWidth:2 }
  };
  
  networkInstance = new vis.Network(container, data, options);
  networkInstance.fit({ animation: { duration:350, easingFunction:"easeInOutQuad" } });
  
  // Double-click accused node to open profile
  networkInstance.on("doubleClick", (params) => {
    if (params.nodes.length > 0) {
      const nodeId = params.nodes[0];
      const clickedNode = nodes.get(nodeId);
      if (clickedNode && clickedNode.group === "suspect") {
        loadSuspectProfile(nodeId);
      }
    }
  });
}

function renderNetworkFallback(container, graphData) {
  const width = Math.max(container.clientWidth, 720);
  const height = Math.max(container.clientHeight, 480);
  const positions = new Map(graphData.nodes.map((node,index) => {
    const angle = index / Math.max(1,graphData.nodes.length) * Math.PI * 2 - Math.PI/2;
    return [node.id, { x:width/2 + Math.cos(angle)*width*.31, y:height/2 + Math.sin(angle)*height*.3 }];
  }));
  const edges = graphData.edges.map(edge => {
    const from=positions.get(edge.from), to=positions.get(edge.to);
    return `<line x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}" stroke="${edge.color || "#527da3"}" stroke-width="${Math.max(1,edge.width||1)}" opacity=".8"/>`;
  }).join("");
  const nodes = graphData.nodes.map(node => {
    const point=positions.get(node.id), label=escapeLab(node.label).replace(/\n/g," ");
    const box=node.group==="asset";
    return `<g class="fallback-network-node" data-profile="${node.group==="suspect" ? escapeLab(node.id):""}">
      ${box ? `<rect x="${point.x-65}" y="${point.y-24}" width="130" height="48" rx="8" fill="${node.color}" stroke="#d9eeff" stroke-width="2"/>` : `<circle cx="${point.x}" cy="${point.y}" r="${Math.max(16,node.size||15)}" fill="${node.color}" stroke="#d9eeff" stroke-width="2"/>`}
      <text x="${point.x}" y="${point.y + (box ? 4 : (node.size||15)+19)}" fill="#eef7ff" text-anchor="middle" font-size="12" font-family="Manrope">${label}</text>
    </g>`;
  }).join("");
  container.innerHTML = `<svg class="fallback-network-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Crime relationship network">${edges}${nodes}</svg>`;
  document.getElementById("network-graph-status").textContent = `${graphData.nodes.length} entities and ${graphData.edges.length} evidence links shown. Double-click a suspect node to open their profile.`;
  container.querySelectorAll("[data-profile]:not([data-profile=''])").forEach(node =>
    node.addEventListener("dblclick", () => loadSuspectProfile(node.dataset.profile))
  );
}

// ─── SCREEN 6: SITUATIONS (ALERTS FEED) ───────────────────────────────────
async function fetchSituationsData() {
  try {
    const res = await fetch(`${API_BASE}/alerts`);
    const data = await res.json();
    
    activeAlertsList = data.alerts;
    renderAlertsSidebarFeed(data.alerts);
    document.getElementById("floating-badge-text").textContent = `${data.alerts.length} Situations Active`;
    if (data.alerts.length > 0) {
      document.getElementById("map-alert-title").textContent = data.alerts[0].title;
      document.getElementById("map-alert-desc").textContent = data.alerts[0].description;
    }
    
    // Auto load first alert details
    if (data.alerts.length > 0) {
      loadAlertDetails(data.alerts[0].id);
    }
  } catch (err) {
    console.error("Error loading alerts:", err);
  }
}

function renderAlertsSidebarFeed(alerts) {
  const container = document.getElementById("situations-list-feed");
  container.innerHTML = "";
  
  alerts.forEach((alert, index) => {
    const card = document.createElement("div");
    card.className = `alert-feed-card ${alert.severity} ${index === 0 ? 'active' : ''}`;
    card.id = `alert-card-${alert.id}`;
    
    card.innerHTML = `
      <div class="alert-header-row">
        <span class="alert-item-title">${alert.title}</span>
        <span class="status-pill ${alert.severity === 'urgent' ? 'red-pill' : 'amber-pill'}">${alert.severity}</span>
      </div>
      <div style="font-size:11px; color:var(--text-muted); margin-bottom:6px;">${alert.timeText}</div>
      <p class="alert-item-desc">${alert.description}</p>
    `;
    card.addEventListener("click", () => {
      document.querySelectorAll(".alert-feed-card").forEach(c => c.classList.remove("active"));
      card.classList.add("active");
      
      loadAlertDetails(alert.id);
    });
    container.appendChild(card);
  });
}

let alertMap = null;
let alertMarkersGroup = L.layerGroup();

function loadAlertDetails(alertId) {
  const alert = activeAlertsList.find(a => a.id === alertId);
  if (!alert) return;
  
  const container = document.getElementById("situation-detail-container");
  
  // Render structure
  container.innerHTML = `
    <div class="situation-detail-header">
      <div class="situation-detail-title">
        <span>${alert.title}</span>
        <span class="status-pill ${alert.severity === 'urgent' ? 'red-pill' : 'amber-pill'} large">${alert.severity}</span>
      </div>
      <div class="situation-detail-meta">${alert.timeText} · SCRB Watchdog Engine</div>
    </div>
    
    <p class="alert-paragraph">${alert.whatHappened}</p>
    
    <!-- Row of 3 cases if available -->
    <div class="alert-side-cases" id="alert-detail-cases">
      <!-- Injected cases -->
    </div>

    <div class="panel-card" id="alert-evidence-panel" style="margin-bottom:20px; padding:14px;">
      <h4 style="font-size:11px; text-transform:uppercase; color:var(--text-muted); margin-bottom:10px;">Why Drishti flagged this</h4>
      <div id="alert-evidence-list" class="details-list"></div>
    </div>
    
    <!-- Mini Map -->
    <div class="panel-card" style="margin-bottom: 20px; padding: 12px;">
      <h4 style="font-size:11px; text-transform:uppercase; color:var(--text-muted); margin-bottom:8px;">Geographic Cluster Coordinates</h4>
      <div id="alert-incident-map" style="height: 180px; width:100%; border-radius:6px; background:#000;"></div>
    </div>
    
    <!-- Suggested Actions -->
    <div class="alert-action-box">
      <div class="action-box-header">Recommended Response Guidelines</div>
      <div class="action-box-text">${alert.recommendedAction}</div>
    </div>
    
    <div class="flex-actions-row" style="display:flex; gap:10px;">
      <button class="btn btn-primary" id="alert-dispatch-action" ${alert.cases?.length ? "" : "disabled"}>Record SP Review Request</button>
      <a class="btn btn-secondary ${alert.cases?.length ? "" : "disabled-link"}" id="alert-export-report" ${alert.cases?.length ? "" : 'href="#" aria-disabled="true"'}>Open FIR Intelligence Brief</a>
    </div>
    <div id="alert-action-status" class="audit-result"></div>
  `;
  
  // 1. Render case cards
  const casesBox = document.getElementById("alert-detail-cases");
  if (alert.cases && alert.cases.length > 0) {
    alert.cases.forEach(c => {
      const box = document.createElement("div");
      box.className = "alert-case-box";
      box.innerHTML = `
        <div class="ac-box-title">FIR #${c.crimeNo.slice(-5)}</div>
        <div class="ac-box-date">${c.date}</div>
        <div class="ac-box-desc" style="max-height: 80px; overflow:hidden; text-overflow:ellipsis;">${c.facts}</div>
      `;
      casesBox.appendChild(box);
    });
  } else {
    casesBox.style.display = "none";
  }

  const evidencePanel = document.getElementById("alert-evidence-panel");
  const evidenceList = document.getElementById("alert-evidence-list");
  if (alert.evidence && alert.evidence.length > 0) {
    alert.evidence.forEach(item => {
      const row = document.createElement("div");
      row.className = "details-item";
      row.innerHTML = `<span class="details-label">${item.label}</span><span class="details-value">${item.value}</span>`;
      evidenceList.appendChild(row);
    });
  } else {
    evidencePanel.style.display = "none";
  }

  const primaryCase = alert.cases?.[0];
  if (primaryCase) {
    document.getElementById("alert-export-report").href = `${API_BASE}/cases/${encodeURIComponent(primaryCase.id || primaryCase.caseId)}/brief.pdf`;
    document.getElementById("alert-export-report").target = "_blank";
    document.getElementById("alert-dispatch-action").addEventListener("click", async () => {
      const status = document.getElementById("alert-action-status");
      status.textContent = "Recording request…";
      try {
        const response = await fetch(`${API_BASE}/actions`, {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({
            caseId:Number(primaryCase.id || primaryCase.caseId),
            actionType:"sp-review-request",
            rationale:`Review situation: ${alert.title}`,
            approved:false
          })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Unable to record action");
        status.textContent = `Recorded as action ${result.actionId} · ${result.status}.`;
      } catch (error) {
        status.textContent = `Action failed: ${error.message}`;
      }
    });
  }
  
  // 2. Render Map coordinates for these alerts
  setTimeout(() => {
    // Initialise alert map
    if (alertMap) {
      alertMap.remove();
      alertMap = null;
    }
    
    alertMap = L.map("alert-incident-map", {
      center: [15.3, 76.2],
      zoom: 6,
      zoomControl: true,
      attributionControl: false
    });
    L.tileLayer(mapTilesUrl).addTo(alertMap);
    alertMarkersGroup.addTo(alertMap);
    alertMarkersGroup.clearLayers();
    
    if (alert.cases && alert.cases.length > 0) {
      const markers = [];
      alert.cases.forEach(c => {
        const marker = L.circleMarker([c.lat, c.lng], {
          radius: 6,
          fillColor: "#F85149",
          color: "#fff",
          weight: 1
        }).addTo(alertMap);
        
        marker.bindTooltip(c.crimeNo, { className: 'map-tooltip' });
        alertMarkersGroup.addLayer(marker);
        markers.push(marker);
      });
      
      // Fit bounds
      const group = new L.featureGroup(markers);
      alertMap.fitBounds(group.getBounds(), { padding: [30, 30] });
    }
    window.setTimeout(() => alertMap?.invalidateSize(true), 80);
  }, 100);
}

// ─── SCREEN 7: DISTRICT DRILL DOWN ────────────────────────────────────────
function initDistrictDrilldown() {
  const selector = document.getElementById("select-drilldown-district");
  
  // List all 31 districts dynamically in selectors
  const karnatakaDistricts = [
    {id: 1, name: "Bangalore Urban"},
    {id: 2, name: "Bangalore Rural"},
    {id: 3, name: "Mysuru"},
    {id: 4, name: "Belagavi"},
    {id: 5, name: "Kalaburagi"},
    {id: 6, name: "Dakshina Kannada"},
    {id: 7, name: "Tumakuru"},
    {id: 8, name: "Shivamogga"},
    {id: 9, name: "Dharwad"},
    {id: 10, name: "Vijayapura"},
    {id: 11, name: "Ballari"},
    {id: 12, name: "Raichur"},
    {id: 13, name: "Hassan"},
    {id: 14, name: "Mandya"},
    {id: 15, name: "Udupi"},
    {id: 16, name: "Uttara Kannada"},
    {id: 17, name: "Chikkamagaluru"},
    {id: 18, name: "Kodagu"},
    {id: 19, name: "Chitradurga"},
    {id: 20, name: "Davangere"},
    {id: 21, name: "Gadag"},
    {id: 22, name: "Haveri"},
    {id: 23, name: "Koppal"},
    {id: 24, name: "Bagalkote"},
    {id: 25, name: "Chamarajanagara"},
    {id: 26, name: "Chikkaballapura"},
    {id: 27, name: "Kolar"},
    {id: 28, name: "Ramanagara"},
    {id: 29, name: "Yadgir"},
    {id: 30, name: "Vijayanagara"},
    {id: 31, name: "Bidar"}
  ];
  
  // Populate dropdowns
  const mapSelect = document.getElementById("map-filter-district");
  
  karnatakaDistricts.forEach(d => {
    const opt1 = document.createElement("option");
    opt1.value = d.id;
    opt1.textContent = d.name;
    selector.appendChild(opt1);
    
    const opt2 = document.createElement("option");
    opt2.value = d.id;
    opt2.textContent = d.name;
    mapSelect.appendChild(opt2);
  });
  
  // Change trigger
  selector.addEventListener("change", (e) => {
    loadDistrictDrilldown(e.target.value);
  });
  
  // Load default district (Mysuru id=3)
  loadDistrictDrilldown(3);
}

async function loadDistrictDrilldown(districtId) {
  try {
    const res = await fetch(`${API_BASE}/districts/${districtId}`);
    const data = await res.json();
    
    // Header summary
    document.getElementById("district-drill-title").textContent = `${data.districtName} District Analysis`;
    document.getElementById("district-brief-summary").innerHTML = `
      <strong>${data.districtName}</strong> logged <strong>${data.periodCasesCount}</strong> incidents in ${data.analysisPeriod}
      (<strong>${data.percentageIncrease}</strong>). Across the full dataset, ${data.casesCount} incidents are linked to this district.
      The most frequent current category is <strong>${data.topCrimeType}</strong>.
    `;
    
    // Select dropdown matching state
    document.getElementById("select-drilldown-district").value = districtId;
    
    // Stations breakdown Table
    const tableBody = document.getElementById("table-stations-body");
    tableBody.innerHTML = "";
    
    data.stations.forEach(s => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td style="font-weight:600;">${s.stationName}</td>
        <td style="text-align:right;">${s.cases}</td>
        <td>
          <span style="display:inline-block; width: 60px; font-weight:700;">${s.resolved}</span>
          <div style="display:inline-block; width: 80px; height: 6px; background:#21262D; border-radius:3px; overflow:hidden; vertical-align:middle; margin-left:10px;">
            <div style="width:${s.resolved.split('(')[1].split('%')[0]}%; height:100%; background:var(--accent-blue);"></div>
          </div>
        </td>
        <td style="text-align:right; font-family:monospace; font-size:12px;">${s.pending}</td>
        <td><span class="status-pill ${s.status.includes('⚠️') ? 'amber-pill' : s.status.includes('Good') ? 'green-pill' : 'blue-pill'}">${s.status}</span></td>
      `;
      tableBody.appendChild(row);
    });
    
    // Top Offenders list sidebar
    const offendersList = document.getElementById("district-offenders-list");
    offendersList.innerHTML = "";
    
    data.topOffenders.forEach(off => {
      const row = document.createElement("div");
      row.className = "offender-row";
      row.innerHTML = `
        <span class="off-name" style="cursor:pointer; color:var(--accent-blue-lt);" onclick="loadSuspectProfile('${off.name.replace(/'/g, "\\'")}')">${off.name}</span>
        <div style="text-align:right;">
          <span class="off-count">${off.cases} Cases</span><br/>
          <span class="status-pill ${off.status === 'NO ARREST RECORD' ? 'amber-pill' : 'blue-pill'}" style="font-size:8px; margin-top:2px;">${off.status}</span>
        </div>
      `;
      offendersList.appendChild(row);
    });
    
  } catch (err) {
    console.error("Error loading district drill details:", err);
  }
}
