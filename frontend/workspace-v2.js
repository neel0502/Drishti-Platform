// Drishti officer workspace controller. Reuses the existing governed APIs.
(function () {
  const workspaceState = {
    cases: [],
    priorityCases: [],
    actions: [],
    activeCaseId: null,
    activeCase: null,
    activeCaseData: null,
    activeTab: "overview",
    caseFilter: "all",
    language: localStorage.getItem("drishti-language") || "en"
  };

  const voiceBriefingState = { status: "idle", utterance: null, aiText: null, aiAgentId: null };

  const translations = {
    en: {
      myWork: "My work", today: "Today", myCases: "My Cases", reviewQueue: "Review Queue",
      skipToContent: "Skip to main content",
      policeCaseWorkspace: "Police Case Workspace", operationalWorkspace: "Operational workspace", investigatingOfficer: "Investigating Officer",
      statePoliceChief: "State Police Chief", districtSuperintendent: "District Superintendent", patrolSupervisor: "Patrol Supervisor", crimeAnalyst: "Crime Analyst",
      roleCommand: "State Command · DGP", roleDistrict: "District Command · SP", roleStation: "Station Officer · Indiranagar PS",
      rolePatrol: "Patrol Supervisor", roleAnalyst: "Crime Analyst", globalSearchPlaceholder: "FIR, person, phone or vehicle",
      investigateAction: "Search",
      logoutAria: "Logout",
      roleGuidanceCommand: "Statewide oversight, cross-district approvals, and resource coordination.",
      roleGuidanceDistrict: "District supervision, station performance, investigations, and coordination requests.",
      roleGuidanceStation: "Review assigned cases, evidence gaps, investigation steps, and supervisor handoffs.",
      roleGuidancePatrol: "Review shift priorities, locations requiring attention, and allocated patrol work.",
      roleGuidanceAnalyst: "Review links, evidence, hypotheses, and intelligence-support requests.",
      identityBoundary: "Prototype role simulation—not authentication. Production permissions come from verified Catalyst identity.",
      moreTools: "More tools", specialistTools: "Specialist tools", shiftBriefing: "SHIFT BRIEFING",
      greeting: "Good morning, Inspector", priority: "PRIORITY", needsAttention: "Needs your attention",
      openReviewQueue: "Open review queue", continueLabel: "CONTINUE", recentCases: "Recent cases",
      handoffs: "HANDOFFS", waitingReview: "Waiting on review", investigation: "INVESTIGATION",
      myCasesIntro: "Open a case to review its facts, evidence, timeline and next action.", registerFir: "Register FIR",
      searchCases: "Search cases", caseSearchPlaceholder: "FIR number, offence or district", allCases: "All cases",
      recentlyRegistered: "Recently registered", backToCases: "← Back to My Cases", selectCase: "Select a case",
      requestReview: "Request review", askDrishti: "Ask Drishti", overview: "Overview", timeline: "Timeline",
      evidence: "Evidence", linkedCases: "Linked Cases", reviews: "Reviews", supervision: "SUPERVISION",
      reviewQueueIntro: "Cases and officer requests requiring a recorded human decision.", humanApprovalRequired: "Human approval required",
      prioritised: "PRIORITISED", casesRequiringReview: "Cases requiring review", buildingReviewQueue: "Building the review queue…",
      requests: "REQUESTS", officerHandoffs: "Officer handoffs", sourceLinkedAssistant: "SOURCE-LINKED ASSISTANT",
      drishtiIntro: "Drishti can review this case and prepare suggestions. It cannot alter a record or approve an action.",
      promptAttention: "What needs attention in this case?", promptEvidence: "Which evidence is still missing?",
      promptConflicts: "Are there conflicting records?", yourQuestion: "Your question", reviewWithDrishti: "Review case with Drishti",
      languageSwitchAria: "Switch interface language", todaySummaryAria: "Today's work summary", filterCasesAria: "Filter cases",
      caseSectionsAria: "Case sections", closeDrishtiAria: "Close Drishti", loadingAttention: "Loading the work that needs your attention…",
      checkingRecords: "Checking current case records…", loadingCases: "Loading cases…", chooseCase: "Choose a case from My Cases.",
      itemsNeedAction: "{count} items need a recorded decision or follow-up.", noUrgentHandoffs: "No urgent handoffs are pending. Continue your active investigations.",
      urgentReview: "Urgent review", priorityCases: "Priority cases", awaitingDecision: "Awaiting decision",
      activeCases: "Active cases", availableToReview: "Available to review", recordedDecisions: "Recorded decisions", auditEntries: "Audit entries",
      noPriorityThreshold: "No case currently meets the priority-review threshold.", noHandoffs: "No officer handoffs are waiting.",
      review: "Review", openCase: "Open case", daysOpen: "days open", registered: "Registered", processDelay: "process-delay priority",
      investigationAvailable: "Investigation record available", noCaseMatch: "No cases match this search and filter.",
      assemblingCase: "Assembling the verified case record…", caseOpenFailed: "The case could not be opened", caseWorkspace: "CASE WORKSPACE",
      reviewPriority: "Review priority", evidenceReadiness: "Evidence readiness", linkedFirs: "Linked FIRs", incident: "Incident",
      humanControl: "Human control", required: "Required", standardReview: "Standard review", recordedSummary: "Recorded FIR summary",
      source: "Source", investigationChecklist: "Investigation checklist", step: "Step", noReviewSteps: "No additional review steps.",
      nextRecommendedAction: "Next recommended action", recommendation: "Recommendation", noSuggestedAction: "No action is currently suggested.",
      complete: "complete", linksRequireVerification: "missing, partial or conflicting links require verification.", caseTimeline: "Case timeline",
      evidenceAttention: "Evidence requiring attention", next: "Next", recorded: "Recorded", evidenceRecord: "Evidence record",
      uploadedEvidence: "Uploaded evidence", developmentRecord: "Development record", noMissingEvidence: "No missing evidence links identified.",
      recordedEvidence: "Recorded evidence", noUploadedEvidence: "No development evidence uploads are linked to this FIR.",
      candidateLinkedFirs: "Candidate linked FIRs", candidate: "Candidate", candidateCaveat: "Connections are investigative leads and must be verified against source records.",
      recordedLinkSignals: "Recorded link signals", noCandidateLinks: "No candidate links meet the current review threshold.",
      humanReviewHistory: "Human review history", noReviewHistory: "No review decisions have been recorded for this case.",
      recordingRequest: "Recording request…", reviewRequested: "Review requested", requestFailed: "Request failed",
      noReviewCases: "No cases meet the prioritisation threshold.", pending: "Pending", approveReview: "Approve review",
      returnOfficer: "Return to officer", reviewApproved: "Review approved", returnedOfficer: "Returned to officer",
      auditRecorded: "Decision added to the audit record.", tryAgain: "Try again", reviewingSources: "Reviewing recorded facts, evidence gaps and source links…",
      answer: "Answer", recordedFacts: "Recorded facts and checks", recommendedActions: "Recommended next actions", sourcesUsed: "Sources used",
      suggestionsOnly: "Suggestions only · Officer verification and approval required", whySuggested: "Why did Drishti suggest this?",
      drishtiUnavailable: "Drishti review unavailable", recordUnchanged: "The case record remains available and unchanged.",
      workspaceUnavailable: "Workspace data is temporarily unavailable",
      listenBriefing: "Listen to briefing", pauseBriefing: "Pause", resumeBriefing: "Resume",
      stopBriefing: "Stop", briefingPlaying: "Reading the role-scoped briefing.", briefingPaused: "Briefing paused.",
      briefingStopped: "Briefing stopped.", voiceBriefingUnavailable: "Voice briefing is not supported in this browser.",
      briefingBoundary: "This is decision support. Verify the cited records before taking action.",
      generateAiBriefing: "Generate detailed AI briefing", generatingAiBriefing: "Generating AI briefing…",
      aiBriefingTitle: "Detailed AI shift briefing", aiBriefingFailed: "The detailed AI briefing could not be generated.",
      aiBriefingFallback: "Validated fallback", aiBriefingSources: "Sources reviewed", listenAiBriefing: "Listen to AI briefing",
      openAgentCentre: "Open full agent review", aiBriefingDraft: "Draft only · officer decides"
    },
    kn: {
      myWork: "ನನ್ನ ಕೆಲಸ", today: "ಇಂದು", myCases: "ನನ್ನ ಪ್ರಕರಣಗಳು", reviewQueue: "ಪರಿಶೀಲನಾ ಸರತಿ",
      skipToContent: "ಮುಖ್ಯ ವಿಷಯಕ್ಕೆ ಹೋಗಿ",
      policeCaseWorkspace: "ಪೊಲೀಸ್ ಪ್ರಕರಣ ಕಾರ್ಯಸ್ಥಳ", operationalWorkspace: "ಕಾರ್ಯಾಚರಣಾ ಕಾರ್ಯಸ್ಥಳ", investigatingOfficer: "ತನಿಖಾಧಿಕಾರಿ",
      statePoliceChief: "ರಾಜ್ಯ ಪೊಲೀಸ್ ಮುಖ್ಯಸ್ಥ", districtSuperintendent: "ಜಿಲ್ಲಾ ಪೊಲೀಸ್ ಅಧೀಕ್ಷಕ", patrolSupervisor: "ಗಸ್ತು ಮೇಲ್ವಿಚಾರಕ", crimeAnalyst: "ಅಪರಾಧ ವಿಶ್ಲೇಷಕ",
      roleCommand: "ರಾಜ್ಯ ಕಮಾಂಡ್ · ಡಿಜಿಪಿ", roleDistrict: "ಜಿಲ್ಲಾ ಕಮಾಂಡ್ · ಎಸ್ಪಿ", roleStation: "ಠಾಣಾ ಅಧಿಕಾರಿ · ಇಂದಿರಾನಗರ ಪಿಎಸ್",
      rolePatrol: "ಗಸ್ತು ಮೇಲ್ವಿಚಾರಕ", roleAnalyst: "ಅಪರಾಧ ವಿಶ್ಲೇಷಕ", globalSearchPlaceholder: "ಎಫ್‌ಐಆರ್, ವ್ಯಕ್ತಿ, ಫೋನ್ ಅಥವಾ ವಾಹನ",
      investigateAction: "ಹುಡುಕಿ",
      logoutAria: "ಲಾಗ್ ಔಟ್",
      roleGuidanceCommand: "ರಾಜ್ಯವ್ಯಾಪಿ ಮೇಲ್ವಿಚಾರಣೆ, ಅಂತರ-ಜಿಲ್ಲಾ ಅನುಮೋದನೆಗಳು ಮತ್ತು ಸಂಪನ್ಮೂಲ ಸಮನ್ವಯ.",
      roleGuidanceDistrict: "ಜಿಲ್ಲಾ ಮೇಲ್ವಿಚಾರಣೆ, ಠಾಣಾ ಕಾರ್ಯಕ್ಷಮತೆ, ತನಿಖೆಗಳು ಮತ್ತು ಸಮನ್ವಯ ವಿನಂತಿಗಳು.",
      roleGuidanceStation: "ನಿಯೋಜಿತ ಪ್ರಕರಣಗಳು, ಸಾಕ್ಷ್ಯ ಕೊರತೆಗಳು, ತನಿಖಾ ಹಂತಗಳು ಮತ್ತು ಮೇಲ್ವಿಚಾರಕರ ಹಸ್ತಾಂತರಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.",
      roleGuidancePatrol: "ಪಾಳಿ ಆದ್ಯತೆಗಳು, ಗಮನ ಅಗತ್ಯವಿರುವ ಸ್ಥಳಗಳು ಮತ್ತು ನಿಯೋಜಿತ ಗಸ್ತು ಕೆಲಸವನ್ನು ಪರಿಶೀಲಿಸಿ.",
      roleGuidanceAnalyst: "ಸಂಪರ್ಕಗಳು, ಸಾಕ್ಷ್ಯ, ಊಹೆಗಳು ಮತ್ತು ಗುಪ್ತಚರ ಸಹಾಯ ವಿನಂತಿಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.",
      identityBoundary: "ಇದು ಮಾದರಿ ಪಾತ್ರ ಅನುಕರಣ—ದೃಢೀಕರಣವಲ್ಲ. ಉತ್ಪಾದನಾ ಅನುಮತಿಗಳು ಪರಿಶೀಲಿತ Catalyst ಗುರುತಿನಿಂದ ಬರಬೇಕು.",
      moreTools: "ಹೆಚ್ಚಿನ ಸಾಧನಗಳು", specialistTools: "ವಿಶೇಷ ಸಾಧನಗಳು", shiftBriefing: "ಪಾಳಿ ಮಾಹಿತಿ",
      greeting: "ಶುಭೋದಯ, ಇನ್ಸ್‌ಪೆಕ್ಟರ್", priority: "ಆದ್ಯತೆ", needsAttention: "ನಿಮ್ಮ ಗಮನ ಅಗತ್ಯ",
      openReviewQueue: "ಪರಿಶೀಲನಾ ಸರತಿ ತೆರೆಯಿರಿ", continueLabel: "ಮುಂದುವರಿಸಿ", recentCases: "ಇತ್ತೀಚಿನ ಪ್ರಕರಣಗಳು",
      handoffs: "ಹಸ್ತಾಂತರಗಳು", waitingReview: "ಪರಿಶೀಲನೆಗಾಗಿ ಕಾಯುತ್ತಿದೆ", investigation: "ತನಿಖೆ",
      myCasesIntro: "ವಾಸ್ತವಾಂಶಗಳು, ಸಾಕ್ಷ್ಯ, ಕಾಲಕ್ರಮ ಮತ್ತು ಮುಂದಿನ ಕ್ರಮ ಪರಿಶೀಲಿಸಲು ಪ್ರಕರಣ ತೆರೆಯಿರಿ.", registerFir: "ಎಫ್‌ಐಆರ್ ದಾಖಲಿಸಿ",
      searchCases: "ಪ್ರಕರಣ ಹುಡುಕಿ", caseSearchPlaceholder: "ಎಫ್‌ಐಆರ್ ಸಂಖ್ಯೆ, ಅಪರಾಧ ಅಥವಾ ಜಿಲ್ಲೆ", allCases: "ಎಲ್ಲ ಪ್ರಕರಣಗಳು",
      recentlyRegistered: "ಇತ್ತೀಚೆಗೆ ದಾಖಲಾಗಿದೆ", backToCases: "← ನನ್ನ ಪ್ರಕರಣಗಳಿಗೆ ಹಿಂದಿರುಗಿ", selectCase: "ಪ್ರಕರಣ ಆಯ್ಕೆಮಾಡಿ",
      requestReview: "ಪರಿಶೀಲನೆ ಕೋರಿರಿ", askDrishti: "ದೃಷ್ಟಿಯನ್ನು ಕೇಳಿ", overview: "ಸಾರಾಂಶ", timeline: "ಕಾಲಕ್ರಮ",
      evidence: "ಸಾಕ್ಷ್ಯ", linkedCases: "ಸಂಬಂಧಿತ ಪ್ರಕರಣಗಳು", reviews: "ಪರಿಶೀಲನೆಗಳು", supervision: "ಮೇಲ್ವಿಚಾರಣೆ",
      reviewQueueIntro: "ದಾಖಲಿತ ಮಾನವ ನಿರ್ಧಾರ ಅಗತ್ಯವಿರುವ ಪ್ರಕರಣಗಳು ಮತ್ತು ಅಧಿಕಾರಿ ವಿನಂತಿಗಳು.", humanApprovalRequired: "ಮಾನವ ಅನುಮೋದನೆ ಅಗತ್ಯ",
      prioritised: "ಆದ್ಯತೆಯವು", casesRequiringReview: "ಪರಿಶೀಲನೆ ಅಗತ್ಯವಿರುವ ಪ್ರಕರಣಗಳು", buildingReviewQueue: "ಪರಿಶೀಲನಾ ಸರತಿ ಸಿದ್ಧವಾಗುತ್ತಿದೆ…",
      requests: "ವಿನಂತಿಗಳು", officerHandoffs: "ಅಧಿಕಾರಿ ಹಸ್ತಾಂತರಗಳು", sourceLinkedAssistant: "ಮೂಲ-ಸಂಬಂಧಿತ ಸಹಾಯಕ",
      drishtiIntro: "ದೃಷ್ಟಿ ಈ ಪ್ರಕರಣವನ್ನು ಪರಿಶೀಲಿಸಿ ಸಲಹೆಗಳನ್ನು ಸಿದ್ಧಪಡಿಸಬಹುದು. ಅದು ದಾಖಲೆಯನ್ನು ಬದಲಾಯಿಸಲು ಅಥವಾ ಕ್ರಮವನ್ನು ಅನುಮೋದಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ.",
      promptAttention: "ಈ ಪ್ರಕರಣದಲ್ಲಿ ಯಾವುದಕ್ಕೆ ಗಮನ ಬೇಕು?", promptEvidence: "ಯಾವ ಸಾಕ್ಷ್ಯ ಇನ್ನೂ ಬಾಕಿಯಿದೆ?",
      promptConflicts: "ಪರಸ್ಪರ ವಿರೋಧಿ ದಾಖಲೆಗಳಿವೆಯೇ?", yourQuestion: "ನಿಮ್ಮ ಪ್ರಶ್ನೆ", reviewWithDrishti: "ದೃಷ್ಟಿಯೊಂದಿಗೆ ಪ್ರಕರಣ ಪರಿಶೀಲಿಸಿ",
      languageSwitchAria: "ಇಂಟರ್ಫೇಸ್ ಭಾಷೆ ಬದಲಾಯಿಸಿ", todaySummaryAria: "ಇಂದಿನ ಕೆಲಸದ ಸಾರಾಂಶ", filterCasesAria: "ಪ್ರಕರಣಗಳನ್ನು ಶೋಧಿಸಿ",
      caseSectionsAria: "ಪ್ರಕರಣದ ವಿಭಾಗಗಳು", closeDrishtiAria: "ದೃಷ್ಟಿಯನ್ನು ಮುಚ್ಚಿ", loadingAttention: "ನಿಮ್ಮ ಗಮನ ಅಗತ್ಯವಿರುವ ಕೆಲಸ ಲೋಡ್ ಆಗುತ್ತಿದೆ…",
      checkingRecords: "ಪ್ರಸ್ತುತ ಪ್ರಕರಣ ದಾಖಲೆಗಳನ್ನು ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ…", loadingCases: "ಪ್ರಕರಣಗಳು ಲೋಡ್ ಆಗುತ್ತಿವೆ…", chooseCase: "ನನ್ನ ಪ್ರಕರಣಗಳಿಂದ ಒಂದು ಪ್ರಕರಣ ಆಯ್ಕೆಮಾಡಿ.",
      itemsNeedAction: "{count} ವಿಷಯಗಳಿಗೆ ದಾಖಲಿತ ನಿರ್ಧಾರ ಅಥವಾ ಮುಂದಿನ ಕ್ರಮ ಅಗತ್ಯ.", noUrgentHandoffs: "ತುರ್ತು ಹಸ್ತಾಂತರಗಳು ಬಾಕಿಯಿಲ್ಲ. ಸಕ್ರಿಯ ತನಿಖೆಗಳನ್ನು ಮುಂದುವರಿಸಿ.",
      urgentReview: "ತುರ್ತು ಪರಿಶೀಲನೆ", priorityCases: "ಆದ್ಯತೆಯ ಪ್ರಕರಣಗಳು", awaitingDecision: "ನಿರ್ಧಾರಕ್ಕಾಗಿ ಕಾಯುತ್ತಿದೆ",
      activeCases: "ಸಕ್ರಿಯ ಪ್ರಕರಣಗಳು", availableToReview: "ಪರಿಶೀಲನೆಗೆ ಲಭ್ಯ", recordedDecisions: "ದಾಖಲಿತ ನಿರ್ಧಾರಗಳು", auditEntries: "ಲೆಕ್ಕಪರಿಶೋಧನಾ ನಮೂದುಗಳು",
      noPriorityThreshold: "ಯಾವ ಪ್ರಕರಣವೂ ಪ್ರಸ್ತುತ ಆದ್ಯತಾ ಪರಿಶೀಲನಾ ಮಿತಿಯನ್ನು ತಲುಪಿಲ್ಲ.", noHandoffs: "ಯಾವ ಅಧಿಕಾರಿ ಹಸ್ತಾಂತರವೂ ಬಾಕಿಯಿಲ್ಲ.",
      review: "ಪರಿಶೀಲನೆ", openCase: "ಪ್ರಕರಣ ತೆರೆಯಿರಿ", daysOpen: "ದಿನಗಳಿಂದ ತೆರೆದಿದೆ", registered: "ದಾಖಲಾದ ದಿನ", processDelay: "ಪ್ರಕ್ರಿಯೆ-ವಿಳಂಬ ಆದ್ಯತೆ",
      investigationAvailable: "ತನಿಖಾ ದಾಖಲೆ ಲಭ್ಯ", noCaseMatch: "ಈ ಹುಡುಕಾಟ ಮತ್ತು ಶೋಧಕಕ್ಕೆ ಯಾವುದೇ ಪ್ರಕರಣ ಹೊಂದಿಕೆಯಾಗಿಲ್ಲ.",
      assemblingCase: "ಪರಿಶೀಲಿತ ಪ್ರಕರಣ ದಾಖಲೆ ಸಿದ್ಧವಾಗುತ್ತಿದೆ…", caseOpenFailed: "ಪ್ರಕರಣ ತೆರೆಯಲಾಗಲಿಲ್ಲ", caseWorkspace: "ಪ್ರಕರಣ ಕಾರ್ಯಸ್ಥಳ",
      reviewPriority: "ಪರಿಶೀಲನಾ ಆದ್ಯತೆ", evidenceReadiness: "ಸಾಕ್ಷ್ಯ ಸಿದ್ಧತೆ", linkedFirs: "ಸಂಬಂಧಿತ ಎಫ್‌ಐಆರ್‌ಗಳು", incident: "ಘಟನೆ",
      humanControl: "ಮಾನವ ನಿಯಂತ್ರಣ", required: "ಅಗತ್ಯ", standardReview: "ಸಾಮಾನ್ಯ ಪರಿಶೀಲನೆ", recordedSummary: "ದಾಖಲಿತ ಎಫ್‌ಐಆರ್ ಸಾರಾಂಶ",
      source: "ಮೂಲ", investigationChecklist: "ತನಿಖಾ ಪರಿಶೀಲನಾ ಪಟ್ಟಿ", step: "ಹಂತ", noReviewSteps: "ಹೆಚ್ಚುವರಿ ಪರಿಶೀಲನಾ ಹಂತಗಳಿಲ್ಲ.",
      nextRecommendedAction: "ಶಿಫಾರಸು ಮಾಡಿದ ಮುಂದಿನ ಕ್ರಮ", recommendation: "ಶಿಫಾರಸು", noSuggestedAction: "ಪ್ರಸ್ತುತ ಯಾವುದೇ ಕ್ರಮ ಸೂಚಿಸಲಾಗಿಲ್ಲ.",
      complete: "ಪೂರ್ಣ", linksRequireVerification: "ಕಾಣೆಯಾದ, ಭಾಗಶಃ ಅಥವಾ ವಿರೋಧಿ ಸಂಪರ್ಕಗಳಿಗೆ ಪರಿಶೀಲನೆ ಅಗತ್ಯ.", caseTimeline: "ಪ್ರಕರಣ ಕಾಲಕ್ರಮ",
      evidenceAttention: "ಗಮನ ಅಗತ್ಯವಿರುವ ಸಾಕ್ಷ್ಯ", next: "ಮುಂದೆ", recorded: "ದಾಖಲಾಗಿದೆ", evidenceRecord: "ಸಾಕ್ಷ್ಯ ದಾಖಲೆ",
      uploadedEvidence: "ಅಪ್‌ಲೋಡ್ ಮಾಡಿದ ಸಾಕ್ಷ್ಯ", developmentRecord: "ಅಭಿವೃದ್ಧಿ ದಾಖಲೆ", noMissingEvidence: "ಕಾಣೆಯಾದ ಸಾಕ್ಷ್ಯ ಸಂಪರ್ಕಗಳು ಕಂಡುಬಂದಿಲ್ಲ.",
      recordedEvidence: "ದಾಖಲಿತ ಸಾಕ್ಷ್ಯ", noUploadedEvidence: "ಈ ಎಫ್‌ಐಆರ್‌ಗೆ ಯಾವುದೇ ಅಭಿವೃದ್ಧಿ ಸಾಕ್ಷ್ಯ ಅಪ್‌ಲೋಡ್ ಸಂಪರ್ಕಿಸಿಲ್ಲ.",
      candidateLinkedFirs: "ಸಂಭಾವ್ಯ ಸಂಬಂಧಿತ ಎಫ್‌ಐಆರ್‌ಗಳು", candidate: "ಸಂಭಾವ್ಯ", candidateCaveat: "ಸಂಪರ್ಕಗಳು ತನಿಖಾ ಸುಳಿವುಗಳು; ಮೂಲ ದಾಖಲೆಗಳಿಂದ ಪರಿಶೀಲಿಸಬೇಕು.",
      recordedLinkSignals: "ದಾಖಲಿತ ಸಂಪರ್ಕ ಸೂಚನೆಗಳು", noCandidateLinks: "ಪ್ರಸ್ತುತ ಪರಿಶೀಲನಾ ಮಿತಿಗೆ ಯಾವುದೇ ಸಂಭಾವ್ಯ ಸಂಪರ್ಕ ತಲುಪಿಲ್ಲ.",
      humanReviewHistory: "ಮಾನವ ಪರಿಶೀಲನಾ ಇತಿಹಾಸ", noReviewHistory: "ಈ ಪ್ರಕರಣಕ್ಕೆ ಯಾವುದೇ ಪರಿಶೀಲನಾ ನಿರ್ಧಾರ ದಾಖಲಾಗಿಲ್ಲ.",
      recordingRequest: "ವಿನಂತಿ ದಾಖಲಾಗುತ್ತಿದೆ…", reviewRequested: "ಪರಿಶೀಲನೆ ಕೋರಲಾಗಿದೆ", requestFailed: "ವಿನಂತಿ ವಿಫಲವಾಗಿದೆ",
      noReviewCases: "ಯಾವ ಪ್ರಕರಣವೂ ಆದ್ಯತಾ ಮಿತಿಯನ್ನು ತಲುಪಿಲ್ಲ.", pending: "ಬಾಕಿ", approveReview: "ಪರಿಶೀಲನೆ ಅನುಮೋದಿಸಿ",
      returnOfficer: "ಅಧಿಕಾರಿಗೆ ಹಿಂತಿರುಗಿಸಿ", reviewApproved: "ಪರಿಶೀಲನೆ ಅನುಮೋದಿಸಲಾಗಿದೆ", returnedOfficer: "ಅಧಿಕಾರಿಗೆ ಹಿಂತಿರುಗಿಸಲಾಗಿದೆ",
      auditRecorded: "ನಿರ್ಧಾರವನ್ನು ಲೆಕ್ಕಪರಿಶೋಧನಾ ದಾಖಲೆಗೆ ಸೇರಿಸಲಾಗಿದೆ.", tryAgain: "ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ", reviewingSources: "ದಾಖಲಿತ ವಾಸ್ತವಾಂಶಗಳು, ಸಾಕ್ಷ್ಯ ಕೊರತೆಗಳು ಮತ್ತು ಮೂಲ ಸಂಪರ್ಕಗಳನ್ನು ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ…",
      answer: "ಉತ್ತರ", recordedFacts: "ದಾಖಲಿತ ವಾಸ್ತವಾಂಶಗಳು ಮತ್ತು ಪರಿಶೀಲನೆಗಳು", recommendedActions: "ಶಿಫಾರಸು ಮಾಡಿದ ಮುಂದಿನ ಕ್ರಮಗಳು", sourcesUsed: "ಬಳಸಿದ ಮೂಲಗಳು",
      suggestionsOnly: "ಸಲಹೆಗಳು ಮಾತ್ರ · ಅಧಿಕಾರಿ ಪರಿಶೀಲನೆ ಮತ್ತು ಅನುಮೋದನೆ ಅಗತ್ಯ", whySuggested: "ದೃಷ್ಟಿ ಇದನ್ನು ಏಕೆ ಸೂಚಿಸಿತು?",
      drishtiUnavailable: "ದೃಷ್ಟಿ ಪರಿಶೀಲನೆ ಲಭ್ಯವಿಲ್ಲ", recordUnchanged: "ಪ್ರಕರಣ ದಾಖಲೆ ಲಭ್ಯವಿದೆ ಮತ್ತು ಬದಲಾಗಿಲ್ಲ.",
      workspaceUnavailable: "ಕಾರ್ಯಸ್ಥಳದ ಡೇಟಾ ತಾತ್ಕಾಲಿಕವಾಗಿ ಲಭ್ಯವಿಲ್ಲ",
      listenBriefing: "ಪಾಳಿ ಮಾಹಿತಿ ಆಲಿಸಿ", pauseBriefing: "ವಿರಾಮ", resumeBriefing: "ಮುಂದುವರಿಸಿ",
      stopBriefing: "ನಿಲ್ಲಿಸಿ", briefingPlaying: "ಪಾತ್ರಕ್ಕೆ ಅನುಗುಣವಾದ ಪಾಳಿ ಮಾಹಿತಿಯನ್ನು ಓದುತ್ತಿದೆ.", briefingPaused: "ಪಾಳಿ ಮಾಹಿತಿ ವಿರಾಮದಲ್ಲಿದೆ.",
      briefingStopped: "ಪಾಳಿ ಮಾಹಿತಿ ನಿಲ್ಲಿಸಲಾಗಿದೆ.", voiceBriefingUnavailable: "ಈ ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಧ್ವನಿ ಪಾಳಿ ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ.",
      briefingBoundary: "ಇದು ನಿರ್ಧಾರ ಸಹಾಯ ಮಾತ್ರ. ಕ್ರಮ ಕೈಗೊಳ್ಳುವ ಮೊದಲು ಉಲ್ಲೇಖಿತ ದಾಖಲೆಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.",
      generateAiBriefing: "ವಿವರವಾದ ಎಐ ಪಾಳಿ ಮಾಹಿತಿ ಸಿದ್ಧಪಡಿಸಿ", generatingAiBriefing: "ಎಐ ಪಾಳಿ ಮಾಹಿತಿ ಸಿದ್ಧವಾಗುತ್ತಿದೆ…",
      aiBriefingTitle: "ವಿವರವಾದ ಎಐ ಪಾಳಿ ಮಾಹಿತಿ", aiBriefingFailed: "ವಿವರವಾದ ಎಐ ಪಾಳಿ ಮಾಹಿತಿ ಸಿದ್ಧಪಡಿಸಲಾಗಲಿಲ್ಲ.",
      aiBriefingFallback: "ಪರಿಶೀಲಿತ ಪರ್ಯಾಯ", aiBriefingSources: "ಪರಿಶೀಲಿಸಿದ ಮೂಲಗಳು", listenAiBriefing: "ಎಐ ಪಾಳಿ ಮಾಹಿತಿ ಆಲಿಸಿ",
      openAgentCentre: "ಪೂರ್ಣ ಏಜೆಂಟ್ ಪರಿಶೀಲನೆ ತೆರೆಯಿರಿ", aiBriefingDraft: "ಕರಡು ಮಾತ್ರ · ಅಧಿಕಾರಿ ನಿರ್ಧರಿಸುತ್ತಾರೆ"
    }
  };

  function tr(key, variables = {}) {
    let value = translations[workspaceState.language]?.[key] || translations.en[key] || key;
    Object.entries(variables).forEach(([name, replacement]) => { value = value.replaceAll(`{${name}}`, String(replacement)); });
    return value;
  }

  function dateLocale() {
    return workspaceState.language === "kn" ? "kn-IN" : "en-IN";
  }

  const roleTodayCopy = {
    en: {
      command: { kicker:"STATE COMMAND", greeting:"State priorities requiring command attention", primaryKicker:"STATE REVIEW", primary:"Cross-district and delayed cases", secondaryKicker:"DISTRICTS", secondary:"Where attention is concentrated", handoffKicker:"DECISIONS", handoff:"Waiting for command review" },
      district: { kicker:"DISTRICT COMMAND", greeting:"District investigations requiring your decision", primaryKicker:"DISTRICT REVIEW", primary:"Cases requiring supervision", secondaryKicker:"WORKLOAD", secondary:"Offence groups needing attention", handoffKicker:"OFFICER REQUESTS", handoff:"Waiting for your decision" },
      station: { kicker:"MY STATION", greeting:"Good morning, Inspector", primaryKicker:"MY INVESTIGATIONS", primary:"Cases needing action today", secondaryKicker:"CONTINUE", secondary:"Recently assigned FIRs", handoffKicker:"SUPERVISOR HANDOFFS", handoff:"Waiting for review" },
      patrol: { kicker:"THIS SHIFT", greeting:"Patrol priorities for the current shift", primaryKicker:"RECORDED INCIDENTS", primary:"Locations requiring attention", secondaryKicker:"AREA VIEW", secondary:"Where incidents are concentrated", handoffKicker:"DEPLOYMENT BOUNDARY", handoff:"Command confirmation required" },
      analyst: { kicker:"ANALYSIS QUEUE", greeting:"Intelligence checks requiring analysis", primaryKicker:"VERIFY", primary:"Patterns and records needing review", secondaryKicker:"ANALYTICAL SCOPE", secondary:"Districts represented in the queue", handoffKicker:"FINDINGS", handoff:"Waiting for officer verification" }
    },
    kn: {
      command: { kicker:"ರಾಜ್ಯ ಕಮಾಂಡ್", greeting:"ಕಮಾಂಡ್ ಗಮನ ಅಗತ್ಯವಿರುವ ರಾಜ್ಯ ಆದ್ಯತೆಗಳು", primaryKicker:"ರಾಜ್ಯ ಪರಿಶೀಲನೆ", primary:"ಅಂತರ-ಜಿಲ್ಲಾ ಮತ್ತು ವಿಳಂಬಿತ ಪ್ರಕರಣಗಳು", secondaryKicker:"ಜಿಲ್ಲೆಗಳು", secondary:"ಗಮನ ಕೇಂದ್ರೀಕೃತವಾಗಿರುವ ಸ್ಥಳಗಳು", handoffKicker:"ನಿರ್ಧಾರಗಳು", handoff:"ಕಮಾಂಡ್ ಪರಿಶೀಲನೆಗಾಗಿ ಕಾಯುತ್ತಿದೆ" },
      district: { kicker:"ಜಿಲ್ಲಾ ಕಮಾಂಡ್", greeting:"ನಿಮ್ಮ ನಿರ್ಧಾರ ಅಗತ್ಯವಿರುವ ಜಿಲ್ಲಾ ತನಿಖೆಗಳು", primaryKicker:"ಜಿಲ್ಲಾ ಪರಿಶೀಲನೆ", primary:"ಮೇಲ್ವಿಚಾರಣೆ ಅಗತ್ಯವಿರುವ ಪ್ರಕರಣಗಳು", secondaryKicker:"ಕೆಲಸದ ಹೊರೆ", secondary:"ಗಮನ ಅಗತ್ಯವಿರುವ ಅಪರಾಧ ಗುಂಪುಗಳು", handoffKicker:"ಅಧಿಕಾರಿ ವಿನಂತಿಗಳು", handoff:"ನಿಮ್ಮ ನಿರ್ಧಾರಕ್ಕಾಗಿ ಕಾಯುತ್ತಿದೆ" },
      station: { kicker:"ನನ್ನ ಠಾಣೆ", greeting:"ಶುಭೋದಯ, ಇನ್ಸ್‌ಪೆಕ್ಟರ್", primaryKicker:"ನನ್ನ ತನಿಖೆಗಳು", primary:"ಇಂದು ಕ್ರಮ ಅಗತ್ಯವಿರುವ ಪ್ರಕರಣಗಳು", secondaryKicker:"ಮುಂದುವರಿಸಿ", secondary:"ಇತ್ತೀಚೆಗೆ ನಿಯೋಜಿಸಲಾದ ಎಫ್‌ಐಆರ್‌ಗಳು", handoffKicker:"ಮೇಲ್ವಿಚಾರಕ ಹಸ್ತಾಂತರಗಳು", handoff:"ಪರಿಶೀಲನೆಗಾಗಿ ಕಾಯುತ್ತಿದೆ" },
      patrol: { kicker:"ಈ ಪಾಳಿ", greeting:"ಪ್ರಸ್ತುತ ಪಾಳಿಯ ಗಸ್ತು ಆದ್ಯತೆಗಳು", primaryKicker:"ದಾಖಲಿತ ಘಟನೆಗಳು", primary:"ಗಮನ ಅಗತ್ಯವಿರುವ ಸ್ಥಳಗಳು", secondaryKicker:"ಪ್ರದೇಶ ನೋಟ", secondary:"ಘಟನೆಗಳು ಕೇಂದ್ರೀಕೃತವಾಗಿರುವ ಸ್ಥಳಗಳು", handoffKicker:"ನಿಯೋಜನೆ ಮಿತಿ", handoff:"ಕಮಾಂಡ್ ದೃಢೀಕರಣ ಅಗತ್ಯ" },
      analyst: { kicker:"ವಿಶ್ಲೇಷಣಾ ಸರತಿ", greeting:"ವಿಶ್ಲೇಷಣೆ ಅಗತ್ಯವಿರುವ ಗುಪ್ತಚರ ಪರಿಶೀಲನೆಗಳು", primaryKicker:"ಪರಿಶೀಲಿಸಿ", primary:"ಪರಿಶೀಲನೆ ಅಗತ್ಯವಿರುವ ಮಾದರಿಗಳು ಮತ್ತು ದಾಖಲೆಗಳು", secondaryKicker:"ವಿಶ್ಲೇಷಣಾ ವ್ಯಾಪ್ತಿ", secondary:"ಸರತಿಯಲ್ಲಿ ಪ್ರತಿನಿಧಿಸಲಾದ ಜಿಲ್ಲೆಗಳು", handoffKicker:"ಕಂಡುಹಿಡಿಕೆಗಳು", handoff:"ಅಧಿಕಾರಿ ಪರಿಶೀಲನೆಗಾಗಿ ಕಾಯುತ್ತಿದೆ" }
    }
  };

  function currentRole() {
    return document.getElementById("role-select")?.value || "station";
  }

  function roleCopy() {
    const language = workspaceState.language === "kn" ? "kn" : "en";
    return roleTodayCopy[language][currentRole()] || roleTodayCopy[language].station;
  }

  function groupedCompactRows(items, field, detailLabel) {
    const counts = new Map();
    items.forEach(item => {
      const key = String(item[field] || "Not recorded");
      counts.set(key, (counts.get(key) || 0) + 1);
    });
    return [...counts.entries()].sort((a,b) => b[1] - a[1]).slice(0,5).map(([label,count]) =>
      `<div class="compact-case compact-summary"><strong>${escapeLab(label)}</strong><span>${count} ${escapeLab(detailLabel)}</span></div>`
    ).join("");
  }

  document.addEventListener("DOMContentLoaded", () => {
    activePanel = "today";
    updateWorkspaceHeader("today");
    initWorkspaceNavigation();
    initCaseWorkspaceControls();
    initDrishtiDrawer();
    initLanguageSwitch();
    initVoiceBriefing();
    initDetailedAiBriefing();
    initPeripheralTranslations();
    loadOfficerWorkspace();
    updateTodayDate();
    window.DrishtiWorkspace = {
      getActiveCaseId: () => workspaceState.activeCaseId,
      getLanguage: () => workspaceState.language,
      getCases: () => workspaceState.cases.map(item => ({ ...item })),
      openCase: caseId => openCaseWorkspace(Number(caseId)),
      openPanel: target => openWorkspacePanel(target)
    };
  });

  function initWorkspaceNavigation() {
    document.querySelectorAll(".primary-nav").forEach(link => link.addEventListener("click", () => {
      document.querySelectorAll(".primary-nav").forEach(item => item.removeAttribute("aria-current"));
      link.setAttribute("aria-current", "page");
    }));
    document.querySelector('.primary-nav[data-target="today"]')?.setAttribute("aria-current", "page");
    document.getElementById("more-tools-toggle").addEventListener("click", event => {
      const expanded = document.body.classList.toggle("show-advanced-nav");
      event.currentTarget.setAttribute("aria-expanded", String(expanded));
      event.currentTarget.querySelector(".more-tools-chevron").textContent = expanded ? "⌃" : "⌄";
    });
    document.querySelectorAll("[data-open-workspace]").forEach(button => {
      button.addEventListener("click", () => openWorkspacePanel(button.dataset.openWorkspace));
    });
    document.getElementById("case-back-button").addEventListener("click", () => openWorkspacePanel("cases"));
    document.getElementById("case-list-search").addEventListener("input", renderCaseList);
    document.querySelectorAll("[data-case-filter]").forEach(button => {
      button.addEventListener("click", () => {
        workspaceState.caseFilter = button.dataset.caseFilter;
        document.querySelectorAll("[data-case-filter]").forEach(item => item.classList.toggle("active", item === button));
        renderCaseList();
      });
    });
  }

  function openWorkspacePanel(target) {
    if (target === "reviews" && !["command", "district"].includes(document.getElementById("role-select").value)) return;
    const nav = document.querySelector(`.nav-link[data-target="${target}"]`);
    if (nav) {
      nav.click();
      updateOfficerHeader(target);
      return;
    }
    document.querySelectorAll(".content-panel").forEach(panel => panel.classList.remove("active"));
    document.getElementById(`${target}-panel`)?.classList.add("active");
    document.querySelectorAll(".nav-link").forEach(link => link.classList.remove("active"));
    activePanel = target;
    updateWorkspaceHeader(target);
    updateOfficerHeader(target);
  }

  async function loadOfficerWorkspace() {
    try {
      const [caseResponse, actionResponse] = await Promise.all([
        fetchJson("/reconstruction-options?limit=40"),
        fetchJson("/actions")
      ]);
      workspaceState.cases = caseResponse.cases || [];
      workspaceState.actions = actionResponse.actions || [];
      try {
        const priorityResponse = await fetchJson("/lifecycle/priority?limit=8");
        workspaceState.priorityCases = priorityResponse.cases || [];
      } catch (error) {
        workspaceState.priorityCases = [];
      }
      renderToday();
      renderCaseList();
      renderReviewQueue();
    } catch (error) {
      const safe = escapeLab(error.message);
      ["today-priority-list", "case-list", "review-case-list"].forEach(id => {
        document.getElementById(id).innerHTML = `<div class="workspace-empty">${tr("workspaceUnavailable")}: ${safe}</div>`;
      });
    }
  }

  function findCase(caseId) {
    return workspaceState.cases.find(item => Number(item.caseId) === Number(caseId));
  }

  function renderToday() {
    const role = currentRole();
    const copy = roleCopy();
    const allPriority = workspaceState.priorityCases;
    const districtScoped = allPriority.filter(item => String(item.district).toLowerCase().includes("bangalore"));
    const priority = ["district", "station"].includes(role) && districtScoped.length ? districtScoped : allPriority;
    const pendingActions = workspaceState.actions.filter(item => String(item.status).includes("pending"));
    const highReview = priority.filter(item => Number(item.delayRisk) >= 70);
    const districts = new Set(priority.map(item => item.district).filter(Boolean));
    document.getElementById("today-kicker").textContent = copy.kicker;
    document.getElementById("today-greeting").textContent = copy.greeting;
    document.getElementById("today-primary-kicker").textContent = copy.primaryKicker;
    document.getElementById("today-primary-title").textContent = copy.primary;
    document.getElementById("today-secondary-kicker").textContent = copy.secondaryKicker;
    document.getElementById("today-secondary-title").textContent = copy.secondary;
    document.getElementById("today-handoff-kicker").textContent = copy.handoffKicker;
    document.getElementById("today-handoff-title").textContent = copy.handoff;
    document.getElementById("today-nav-count").textContent = highReview.length + pendingActions.length;
    document.getElementById("review-nav-count").textContent = priority.length + pendingActions.length;
    const totalAttention = highReview.length + (role === "patrol" ? 0 : pendingActions.length);
    document.getElementById("today-summary").textContent = totalAttention
      ? `${totalAttention} ${role === "patrol" ? "recorded location priorities" : "items need a recorded decision or follow-up"}.`
      : tr("noUrgentHandoffs");
    const metrics = {
      command: [["urgent",highReview.length,"High-priority FIRs","State review"],["review",districts.size,"Districts flagged","Cross-district scope"],["",pendingActions.length,"Decisions waiting","Human approval"],["complete",workspaceState.actions.length,"Audit entries","Recorded actions"]],
      district: [["urgent",highReview.length,"Urgent district FIRs","Supervisor review"],["review",priority.length,"Cases in review","Bengaluru scope"],["",pendingActions.length,"Officer requests","Awaiting decision"],["complete",workspaceState.actions.length - pendingActions.length,"Recorded decisions","District audit"]],
      station: [["urgent",highReview.length,"Cases needing action","Assigned review"],["review",pendingActions.length,"Supervisor handoffs","Waiting"],["",workspaceState.cases.filter(item=>String(item.district).toLowerCase().includes("bangalore")).length,"Station FIRs","Available to work"],["complete",workspaceState.actions.length - pendingActions.length,"Recorded steps","Audit entries"]],
      patrol: [["urgent",highReview.length,"Priority incidents","Recorded signals"],["review",districts.size,"Areas represented","Location review"],["",priority.length,"Incident records","Current briefing"],["complete",0,"Automatic deployments","Officer-controlled"]],
      analyst: [["urgent",priority.length,"Records to analyse","Intelligence queue"],["review",districts.size,"Districts represented","Cross-district scope"],["",priority.filter(item=>(item.signals||[]).length).length,"Explained signals","Source-linked"],["complete",pendingActions.length,"Findings waiting","Officer verification"]]
    }[role] || [];
    document.getElementById("today-attention-summary").innerHTML = metrics.map(([type,value,label,detail], index) => `<article class="attention-tile ${type} ${index === 0 ? "primary" : ""}"><span class="tile-label">${escapeLab(label)}</span><strong>${value}</strong><span>${escapeLab(detail)}</span></article>`).join("");

    const priorityItems = priority.slice(0, 5);
    document.getElementById("today-priority-list").innerHTML = priorityItems.length
      ? priorityItems.map(item => role === "patrol" ? renderPatrolPriority(item) : renderOperationalItem(item)).join("")
      : `<div class="workspace-empty">${tr("noPriorityThreshold")}</div>`;
    const scopedCases = ["district","station"].includes(role)
      ? workspaceState.cases.filter(item => String(item.district).toLowerCase().includes("bangalore"))
      : workspaceState.cases;
    document.getElementById("today-recent-cases").innerHTML = role === "station"
      ? scopedCases.slice(0,5).map(item => `<button class="compact-case" type="button" data-open-case="${item.caseId}"><strong>FIR ${escapeLab(item.crimeNo)}</strong><span>${escapeLab(item.crimeType)} · ${escapeLab(item.district)}</span></button>`).join("")
      : groupedCompactRows(priority, role === "district" ? "crimeType" : "district", role === "district" ? "cases" : "priority records");
    document.getElementById("today-handoffs").innerHTML = role === "patrol"
      ? `<span class="workspace-empty">Locations are decision support only. A patrol supervisor confirms every deployment.</span>`
      : pendingActions.length
      ? pendingActions.slice(0, 6).map(item => `<span class="handoff-pill">FIR ${escapeLab(findCase(item.caseId)?.crimeNo || item.caseId)} · ${escapeLab(humaniseAction(item.actionType))}</span>`).join("")
      : `<span class="workspace-empty">${tr("noHandoffs")}</span>`;
    bindOpenCaseButtons(document.getElementById("today-panel"));
    document.querySelectorAll("[data-open-patrol-map]").forEach(button => button.addEventListener("click", () => document.querySelector('.nav-link[data-target="map"]')?.click()));
  }

  function initVoiceBriefing() {
    const toggle = document.getElementById("today-voice-toggle");
    const stop = document.getElementById("today-voice-stop");
    if (!("speechSynthesis" in window) || typeof window.SpeechSynthesisUtterance !== "function") {
      toggle.disabled = true;
      document.getElementById("today-voice-status").textContent = tr("voiceBriefingUnavailable");
      return;
    }
    toggle.addEventListener("click", () => {
      if (voiceBriefingState.status === "speaking") {
        window.speechSynthesis.pause();
        voiceBriefingState.status = "paused";
        updateVoiceBriefingControls(tr("briefingPaused"));
        return;
      }
      if (voiceBriefingState.status === "paused") {
        window.speechSynthesis.resume();
        voiceBriefingState.status = "speaking";
        updateVoiceBriefingControls(tr("briefingPlaying"));
        return;
      }
      startVoiceBriefing();
    });
    stop.addEventListener("click", () => stopVoiceBriefing(true));
    window.addEventListener("beforeunload", () => stopVoiceBriefing(false));
    updateVoiceBriefingControls("");
  }

  function initDetailedAiBriefing() {
    document.getElementById("today-ai-briefing-button").addEventListener("click", generateDetailedAiBriefing);
    updateDetailedAiBriefingButton();
  }

  async function generateDetailedAiBriefing() {
    const button = document.getElementById("today-ai-briefing-button");
    const panel = document.getElementById("today-ai-briefing");
    const agentId = currentRole() === "patrol" ? "patrol-shift-briefing" : "shift-briefing";
    const query = workspaceState.language === "kn"
      ? "ಪ್ರಸ್ತುತ ಪಾಳಿಗೆ ವಿವರವಾದ ಮೂಲ-ಸಂಬಂಧಿತ ಮಾಹಿತಿ ಸಿದ್ಧಪಡಿಸಿ. ಆದ್ಯತೆಗಳು, ಬಾಕಿ ಮಾನವ ಪರಿಶೀಲನೆಗಳು, ಅನಿಶ್ಚಿತತೆ ಮತ್ತು ಸುರಕ್ಷಿತ ಮುಂದಿನ ಹಂತಗಳನ್ನು ಪ್ರತ್ಯೇಕಿಸಿ."
      : "Prepare a detailed source-linked briefing for the current shift. Separate priorities, pending human reviews, uncertainty, and the safest next verification steps.";
    stopVoiceBriefing(false);
    voiceBriefingState.aiText = null;
    voiceBriefingState.aiAgentId = agentId;
    button.disabled = true;
    document.getElementById("today-ai-briefing-label").textContent = tr("generatingAiBriefing");
    panel.hidden = false;
    panel.innerHTML = `<div class="ai-briefing-progress"><span aria-hidden="true">✦</span><div><strong>${escapeLab(tr("generatingAiBriefing"))}</strong><p>${workspaceState.language === "kn" ? "ಅನುಮೋದಿತ ಪಾಳಿ ದಾಖಲೆಗಳನ್ನು ಓದಿ, ದುರ್ಬಲ ಕಂಡುಹಿಡಿಕೆಗಳನ್ನು ಪ್ರಶ್ನಿಸಿ ಮತ್ತು ಮೂಲಗಳನ್ನು ಜೋಡಿಸುತ್ತಿದೆ." : "Reading approved shift records, challenging weak findings, and attaching sources."}</p></div></div>`;
    let timeout;
    try {
      const controller = new AbortController();
      timeout = window.setTimeout(() => controller.abort(), 65000);
      const response = await fetch("/api/agents/run", {
        method: "POST", headers: { "Content-Type": "application/json" }, signal: controller.signal,
        body: JSON.stringify({ agentId, caseId: null, role: currentRole(), language: workspaceState.language, query })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
      renderDetailedAiBriefing(data);
    } catch (error) {
      voiceBriefingState.aiText = null;
      const detail = error.name === "AbortError" ? "The agent response window expired." : error.message;
      panel.innerHTML = `<div class="ai-briefing-error"><strong>${escapeLab(tr("aiBriefingFailed"))}</strong><p>${escapeLab(detail)}</p><span>${escapeLab(tr("listenBriefing"))} remains available without AI.</span></div>`;
    } finally {
      window.clearTimeout(timeout);
      button.disabled = false;
      updateDetailedAiBriefingButton();
    }
  }

  function renderDetailedAiBriefing(data) {
    const panel = document.getElementById("today-ai-briefing");
    const fallback = data.run?.aiProvider === "deterministic-fallback";
    const model = fallback ? tr("aiBriefingFallback") : `OpenAI · ${data.run?.aiModel || "gpt-5-mini"}`;
    const citations = (data.citations || []).slice(0, 4);
    const claims = (data.claims || []).slice(0, 3);
    voiceBriefingState.aiText = String(data.answer || "");
    panel.innerHTML = `<div class="ai-briefing-head"><div><span class="eyebrow">${escapeLab(tr("aiBriefingDraft"))}</span><h3>${escapeLab(tr("aiBriefingTitle"))}</h3></div><span class="ai-briefing-model ${fallback ? "fallback" : ""}">${escapeLab(model)}</span></div>
      <p class="ai-briefing-answer">${escapeLab(data.answer)}</p>
      ${claims.length ? `<div class="ai-briefing-findings">${claims.map(claim => `<article><span>${escapeLab(claim.recordStatus)}</span><strong>${escapeLab(claim.statement)}</strong><small>${Number(claim.confidenceBeforeReview || 0)}% · ${(claim.supportingSourceIds || []).map(escapeLab).join(" · ")}</small></article>`).join("")}</div>` : ""}
      <details class="ai-briefing-sources"><summary>${escapeLab(tr("aiBriefingSources"))} · ${citations.length}</summary>${citations.map(citation => `<p><strong>${escapeLab(citation.id)} · ${escapeLab(citation.label)}</strong><span>${escapeLab(citation.source)}</span></p>`).join("")}</details>
      <div class="ai-briefing-actions"><button type="button" id="today-ai-listen">▶ ${escapeLab(tr("listenAiBriefing"))}</button><button type="button" id="today-ai-open-agent">${escapeLab(tr("openAgentCentre"))}</button></div>
      <p class="ai-briefing-boundary">${escapeLab(tr("briefingBoundary"))}</p>`;
    document.getElementById("today-ai-listen").addEventListener("click", startVoiceBriefing);
    document.getElementById("today-ai-open-agent").addEventListener("click", () => window.DrishtiAgents?.open(voiceBriefingState.aiAgentId, null));
    updateVoiceBriefingControls("");
  }

  function updateDetailedAiBriefingButton() {
    const label = document.getElementById("today-ai-briefing-label");
    if (label && !document.getElementById("today-ai-briefing-button")?.disabled) label.textContent = tr("generateAiBriefing");
  }

  function clearDetailedAiBriefing() {
    voiceBriefingState.aiText = null;
    voiceBriefingState.aiAgentId = null;
    const panel = document.getElementById("today-ai-briefing");
    if (panel) { panel.hidden = true; panel.innerHTML = ""; }
  }

  function buildVoiceBriefingText() {
    if (voiceBriefingState.aiText) return `${voiceBriefingState.aiText} ${tr("briefingBoundary")}`;
    const parts = [
      document.getElementById("today-greeting").textContent.trim(),
      document.getElementById("today-summary").textContent.trim()
    ];
    document.querySelectorAll("#today-attention-summary .attention-tile").forEach(tile => {
      const label = tile.querySelector(".tile-label")?.textContent.trim();
      const value = tile.querySelector("strong")?.textContent.trim();
      const detail = [...tile.querySelectorAll("span")].at(-1)?.textContent.trim();
      if (label && value) parts.push(`${label}: ${value}${detail ? `. ${detail}` : ""}.`);
    });
    const priorities = [...document.querySelectorAll("#today-priority-list .operational-item")].slice(0, 3);
    if (priorities.length) parts.push(workspaceState.language === "kn" ? "ಮುಖ್ಯ ಆದ್ಯತೆಗಳು." : "Top priorities.");
    priorities.forEach(item => {
      const meta = item.querySelector(".operational-meta")?.textContent.trim();
      const title = item.querySelector("h4")?.textContent.trim();
      const detail = item.querySelector("p")?.textContent.trim();
      parts.push([meta, title, detail].filter(Boolean).join(". "));
    });
    const handoffs = document.querySelectorAll("#today-handoffs .handoff-pill").length;
    if (handoffs) parts.push(workspaceState.language === "kn" ? `${handoffs} ಹಸ್ತಾಂತರಗಳು ಮಾನವ ಪರಿಶೀಲನೆಗಾಗಿ ಕಾಯುತ್ತಿವೆ.` : `${handoffs} handoffs are waiting for human review.`);
    parts.push(tr("briefingBoundary"));
    return parts.filter(Boolean).join(" ");
  }

  function startVoiceBriefing() {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(buildVoiceBriefingText());
    utterance.lang = workspaceState.language === "kn" ? "kn-IN" : "en-IN";
    utterance.rate = .92;
    const languagePrefix = workspaceState.language === "kn" ? "kn" : "en";
    const matchingVoice = window.speechSynthesis.getVoices().find(voice => String(voice.lang || "").toLowerCase().startsWith(languagePrefix));
    if (matchingVoice) utterance.voice = matchingVoice;
    utterance.onend = () => finishVoiceBriefing("");
    utterance.onerror = event => finishVoiceBriefing(event.error === "canceled" ? "" : tr("voiceBriefingUnavailable"));
    voiceBriefingState.utterance = utterance;
    voiceBriefingState.status = "speaking";
    updateVoiceBriefingControls(tr("briefingPlaying"));
    window.speechSynthesis.speak(utterance);
  }

  function stopVoiceBriefing(announce) {
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    finishVoiceBriefing(announce ? tr("briefingStopped") : "");
  }

  function finishVoiceBriefing(statusText) {
    voiceBriefingState.status = "idle";
    voiceBriefingState.utterance = null;
    updateVoiceBriefingControls(statusText);
  }

  function updateVoiceBriefingControls(statusText) {
    const toggle = document.getElementById("today-voice-toggle");
    const stop = document.getElementById("today-voice-stop");
    const label = document.getElementById("today-voice-label");
    const status = document.getElementById("today-voice-status");
    if (!toggle || !stop || !label || !status) return;
    const key = voiceBriefingState.status === "speaking" ? "pauseBriefing" : voiceBriefingState.status === "paused" ? "resumeBriefing" : "listenBriefing";
    label.textContent = tr(key);
    toggle.querySelector("span[aria-hidden]").textContent = voiceBriefingState.status === "speaking" ? "Ⅱ" : "▶";
    toggle.setAttribute("aria-label", tr(key));
    toggle.setAttribute("aria-pressed", String(voiceBriefingState.status !== "idle"));
    stop.hidden = voiceBriefingState.status === "idle";
    stop.setAttribute("aria-label", tr("stopBriefing"));
    status.textContent = statusText || "";
  }

  function renderPatrolPriority(item) {
    return `<article class="operational-item high"><span class="priority-rail" aria-hidden="true"></span><div class="operational-copy"><span class="operational-meta">RECORDED INCIDENT · ${escapeLab(item.district)}</span><h4>${escapeLab(item.crimeType)}</h4><p>Confirm location, time, recency, and current operational relevance before allocating a unit.</p></div><button class="open-case-button" type="button" data-open-patrol-map>View area</button></article>`;
  }

  function renderOperationalItem(item) {
    const high = Number(item.delayRisk) >= 70;
    const signals = (item.signals || []).slice(0, 2).join(" · ");
    return `<article class="operational-item ${high ? "high" : ""}"><span class="priority-rail" aria-hidden="true"></span><div class="operational-copy"><span class="operational-meta">${high ? tr("urgentReview") : tr("review")} · FIR ${escapeLab(item.crimeNo)}</span><h4>${escapeLab(item.crimeType)}</h4><p>${escapeLab(signals || `${item.district} · ${item.ageDays} ${tr("daysOpen")}`)}</p></div><button class="open-case-button" type="button" data-open-case="${item.caseId}">${tr("openCase")}</button></article>`;
  }

  function renderCaseList() {
    const container = document.getElementById("case-list");
    const query = document.getElementById("case-list-search").value.trim().toLowerCase();
    const priorityIds = new Set(workspaceState.priorityCases.map(item => Number(item.caseId)));
    let cases = workspaceState.cases.filter(item => !query || [item.crimeNo, item.crimeType, item.district].some(value => String(value).toLowerCase().includes(query)));
    if (workspaceState.caseFilter === "attention") cases = cases.filter(item => priorityIds.has(Number(item.caseId)));
    if (workspaceState.caseFilter === "recent") cases = cases.slice(0, 12);
    container.innerHTML = cases.length ? cases.map(item => {
      const priority = workspaceState.priorityCases.find(row => Number(row.caseId) === Number(item.caseId));
      return `<article class="case-list-card"><div><span class="eyebrow">FIR ${escapeLab(item.crimeNo)}</span><h3>${escapeLab(item.crimeType)}</h3><p>${escapeLab(item.district)} · ${tr("registered")} ${formatDate(item.date)}</p><div class="status-line"><span class="status-dot ${priority ? "attention" : ""}" aria-hidden="true"></span>${priority ? `${tr("needsAttention")} · ${Math.round(priority.delayRisk)}% ${tr("processDelay")}` : tr("investigationAvailable")}</div></div><button class="open-case-button" type="button" data-open-case="${item.caseId}">${tr("openCase")}</button></article>`;
    }).join("") : `<div class="workspace-empty">${tr("noCaseMatch")}</div>`;
    bindOpenCaseButtons(container);
  }

  function bindOpenCaseButtons(scope) {
    scope.querySelectorAll("[data-open-case]").forEach(button => button.addEventListener("click", () => openCaseWorkspace(Number(button.dataset.openCase))));
  }

  async function openCaseWorkspace(caseId) {
    if (currentRole() === "patrol") {
      document.querySelector('.nav-link[data-target="map"]')?.click();
      return;
    }
    workspaceState.activeCaseId = caseId;
    document.dispatchEvent(new CustomEvent("drishti:case-opened", { detail: { caseId } }));
    workspaceState.activeCase = findCase(caseId);
    document.getElementById("case-panel").dataset.caseId = String(caseId);
    workspaceState.activeTab = "overview";
    document.querySelectorAll(".case-tab").forEach(tab => {
      const selected = tab.dataset.caseTab === "overview";
      tab.classList.toggle("active", selected);
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
    openWorkspacePanel("case");
    const pendingCase = workspaceState.activeCase || {};
    document.getElementById("case-workspace-jurisdiction").textContent = `${pendingCase.district || ""}${pendingCase.district ? " · " : ""}${tr("caseWorkspace")}`;
    document.getElementById("case-workspace-title").textContent = pendingCase.crimeNo ? `FIR ${pendingCase.crimeNo}` : tr("caseWorkspace");
    document.getElementById("case-workspace-subtitle").textContent = pendingCase.crimeType || "";
    document.getElementById("case-facts-bar").innerHTML = `<div class="case-loading-fact"><strong>${tr("assemblingCase")}</strong><span>Checking the latest recorded facts and evidence.</span></div>`;
    document.getElementById("case-role-journey").innerHTML = "";
    document.getElementById("case-workspace-body").innerHTML = `<div class="workspace-loading">${tr("assemblingCase")}</div>`;
    try {
      const [plan, reconstruction, brief, evidence, actions] = await Promise.all([
        fetchJson(`/cases/${caseId}/command-plan`),
        fetchJson(`/cases/${caseId}/reconstruction`),
        fetchJson(`/cases/${caseId}/ai-brief`),
        fetchJson(`/evidence?caseId=${caseId}`),
        fetchJson(`/actions?caseId=${caseId}`)
      ]);
      workspaceState.activeCaseData = { plan, reconstruction, brief, evidence: evidence.records || [], actions: actions.actions || [] };
      renderCaseHeader();
      renderCaseTab("overview");
      document.getElementById("case-workspace-title").focus();
    } catch (error) {
      document.getElementById("case-workspace-body").innerHTML = `<div class="workspace-empty">${tr("caseOpenFailed")}: ${escapeLab(error.message)}</div>`;
    }
  }

  function renderCaseHeader() {
    const { plan, reconstruction } = workspaceState.activeCaseData;
    const caseRecord = reconstruction.case;
    document.getElementById("case-workspace-jurisdiction").textContent = `${caseRecord.district} · ${tr("caseWorkspace")}`;
    document.getElementById("case-workspace-title").textContent = `FIR ${caseRecord.crimeNo}`;
    document.getElementById("case-workspace-subtitle").textContent = caseRecord.crimeType;
    document.getElementById("case-facts-bar").innerHTML = [
      [tr("reviewPriority"), plan.priority === "HIGH REVIEW" ? tr("urgentReview") : tr("standardReview")],
      [tr("evidenceReadiness"), `${plan.evidenceCompleteness}%`],
      [tr("linkedFirs"), plan.linkedCases.length],
      [tr("incident"), formatDate(caseRecord.incidentTime)],
      [tr("humanControl"), tr("required")]
    ].map(([label,value]) => `<div class="case-fact"><span>${escapeLab(label)}</span><strong>${escapeLab(value)}</strong></div>`).join("");
    const actions = workspaceState.activeCaseData.actions || [];
    const supervisorApproved = actions.some(item => String(item.actionType).includes("approved") || item.approved === true);
    const journey = [
      ["Station", "FIR and evidence", "recorded"],
      ["Analyst", "Verify candidate links", plan.linkedCases.length ? "attention" : "clear"],
      ["SP", "Human review", supervisorApproved ? "recorded" : "waiting"],
      ["Patrol", "Approved location brief", supervisorApproved ? "eligible" : "not released"],
      ["DGP", "State oversight", actions.length ? "audit visible" : "no escalation"]
    ];
    document.getElementById("case-role-journey").innerHTML = `<div><span class="eyebrow">FIR TO DECISION</span><strong>Case decision path</strong></div>${journey.map(([role,label,status]) => `<article class="journey-step ${escapeLab(status.replaceAll(" ","-"))}"><span>${escapeLab(role)}</span><b>${escapeLab(label)}</b><small>${escapeLab(status)}</small></article>`).join("")}`;
  }

  function initCaseWorkspaceControls() {
    document.querySelectorAll(".case-tab").forEach((tab, index) => {
      tab.tabIndex = index === 0 ? 0 : -1;
      tab.addEventListener("click", () => {
      workspaceState.activeTab = tab.dataset.caseTab;
      document.querySelectorAll(".case-tab").forEach(item => {
        const selected = item === tab;
        item.classList.toggle("active", selected);
        item.setAttribute("aria-selected", String(selected));
        item.tabIndex = selected ? 0 : -1;
      });
      document.getElementById("case-workspace-body").setAttribute("aria-labelledby", tab.id);
      renderCaseTab(workspaceState.activeTab);
      });
    });
    document.getElementById("case-request-review").addEventListener("click", requestCaseReview);
    document.querySelector(".case-tabs").addEventListener("keydown", event => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      const tabs = [...document.querySelectorAll(".case-tab")];
      const current = tabs.indexOf(document.activeElement);
      if (current < 0) return;
      event.preventDefault();
      const nextIndex = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 :
        (current + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
      tabs[nextIndex].focus();
      tabs[nextIndex].click();
    });
  }

  function renderCaseTab(tab) {
    if (!workspaceState.activeCaseData) return;
    const body = document.getElementById("case-workspace-body");
    const data = workspaceState.activeCaseData;
    if (tab === "overview") {
      const next = data.plan.steps[0];
      body.innerHTML = `<section class="case-priority-action"><div><span class="eyebrow">${tr("nextRecommendedAction")}</span>${next ? `<h3>${escapeLab(next.title)}</h3><p>${escapeLab(next.nextStep)}</p>` : `<h3>${tr("noSuggestedAction")}</h3>`}</div><div class="case-readiness"><span>${tr("evidenceReadiness")}</span><strong>${data.plan.evidenceCompleteness}%</strong><div class="evidence-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${data.plan.evidenceCompleteness}"><span style="width:${data.plan.evidenceCompleteness}%"></span></div><small>${data.reconstruction.missingLinks.length} ${tr("linksRequireVerification")}</small></div></section><div class="case-overview-grid"><section class="case-section-card"><h3>${tr("investigationChecklist")}</h3>${data.plan.steps.map((step,index) => `<div class="workspace-step ${index === 0 ? "current" : ""}"><span class="record-state">${tr("step")} ${index + 1}</span><strong>${escapeLab(step.title)}</strong><p>${escapeLab(step.nextStep)}</p></div>`).join("") || `<p>${tr("noReviewSteps")}</p>`}</section><aside><section class="case-section-card case-summary-card"><h3>${tr("recordedSummary")}</h3><p>${escapeLab(data.brief.summary)}</p><div class="source-tag">${tr("source")}: CaseMaster.BriefFacts</div></section></aside></div>`;
    } else if (tab === "timeline") {
      body.innerHTML = `<section class="case-section-card"><h3>${tr("caseTimeline")}</h3>${data.reconstruction.events.map(event => `<article class="timeline-event"><span class="record-state ${event.confidence === "inferred" ? "inferred" : ""}">${escapeLab(statusLabel(event.confidence))}</span><strong>${escapeLab(event.displayTime || formatDateTime(event.timestamp))}</strong><p>${escapeLab(event.label)}</p><span class="source-tag">${tr("source")}: ${escapeLab(event.source)}</span></article>`).join("")}</section>`;
    } else if (tab === "evidence") {
      const missing = data.reconstruction.missingLinks.map(item => `<article class="evidence-row"><span class="record-state inferred">${escapeLab(statusLabel(item.status))}</span><strong>${escapeLab(item.field)}</strong><p>${escapeLab(item.impact)} ${tr("next")}: ${escapeLab(item.nextStep)}</p></article>`).join("");
      const uploaded = data.evidence.map(item => `<article class="evidence-row"><span class="record-state">${tr("recorded")}</span><strong>${escapeLab(item.filename || item.category || tr("evidenceRecord"))}</strong><p>${escapeLab(item.category || tr("uploadedEvidence"))} · ${escapeLab(item.timestamp || tr("developmentRecord"))}</p></article>`).join("");
      body.innerHTML = `<section class="case-section-card"><h3>${tr("evidenceAttention")}</h3>${missing || `<p>${tr("noMissingEvidence")}</p>`}<h3 style="margin-top:22px">${tr("recordedEvidence")}</h3>${uploaded || `<p>${tr("noUploadedEvidence")}</p>`}</section>`;
    } else if (tab === "links") {
      body.innerHTML = `<section class="case-section-card"><div class="link-review-heading"><div><h3>${tr("candidateLinkedFirs")}</h3><p>${tr("candidateCaveat")}</p></div><span class="human-control-badge">Compare evidence before coordination</span></div>${data.plan.linkedCases.map(item => {
        const evidence = item.evidence || [];
        const evidenceTypes = evidence.map(source => String(source.type || "").toLowerCase());
        const independent = evidenceTypes.some(type => ["co-accused","shared phone","shared vehicle"].includes(type));
        const evidenceText = evidence.map(source => `${source.type || "Signal"}: ${source.value || "recorded"}`).join(" · ");
        return `<article class="linked-case-row link-verification-card ${independent ? "supported" : "narrative-only"}"><div class="link-verification-state"><span class="record-state inferred">${tr("candidate")} · ${item.connectionScore}/100</span><strong>${independent ? "Independent identifier recorded" : "Narrative similarity only"}</strong></div><h4>FIR ${escapeLab(item.crimeNo)} · ${escapeLab(item.crimeType)}</h4><p>${escapeLab(item.district)} · ${escapeLab(evidenceText || tr("recordedLinkSignals"))}</p><div class="link-officer-check">${independent ? "Officer check: verify each identifier in both source FIRs before coordination." : "Do not merge or attribute a common offender without an independent person, phone, vehicle, forensic, or CCTV signal."}</div></article>`;
      }).join("") || `<p>${tr("noCandidateLinks")}</p>`}</section>`;
    } else {
      body.innerHTML = `<section class="case-section-card"><h3>${tr("humanReviewHistory")}</h3>${data.actions.map(item => `<article class="review-row"><span class="record-state ${String(item.status).includes("pending") ? "inferred" : ""}">${escapeLab(statusLabel(item.status))}</span><strong>${escapeLab(humaniseAction(item.actionType))}</strong><p>${escapeLab(item.rationale)} · ${formatDateTime(item.timestamp)}</p></article>`).join("") || `<p>${tr("noReviewHistory")}</p>`}</section>`;
    }
  }

  async function requestCaseReview() {
    if (!workspaceState.activeCaseId) return;
    const button = document.getElementById("case-request-review");
    button.disabled = true;
    button.textContent = tr("recordingRequest");
    try {
      const response = await fetch(`${API_BASE}/actions`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
        caseId: workspaceState.activeCaseId, actionType: "supervisor-review-request",
        rationale: "Investigating officer requested supervisor review from the case workspace.", officer: "Inspector R. Sharma", approved: false
      }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Review request failed");
      workspaceState.actions.unshift(result);
      workspaceState.activeCaseData.actions.unshift(result);
      button.textContent = tr("reviewRequested");
      renderToday();
      renderReviewQueue();
    } catch (error) {
      button.textContent = tr("requestFailed");
    } finally {
      setTimeout(() => { button.disabled = false; button.textContent = tr("requestReview"); }, 1800);
    }
  }

  function renderReviewQueue() {
    const pending = workspaceState.actions.filter(item => String(item.status).includes("pending"));
    document.getElementById("review-case-list").innerHTML = workspaceState.priorityCases.length
      ? workspaceState.priorityCases.map(renderOperationalItem).join("")
      : `<div class="workspace-empty">${tr("noReviewCases")}</div>`;
    document.getElementById("review-action-list").innerHTML = pending.length ? pending.map(item => `<article class="review-row"><span class="record-state inferred">${tr("pending")}</span><strong>FIR ${escapeLab(findCase(item.caseId)?.crimeNo || item.caseId)} · ${escapeLab(humaniseAction(item.actionType))}</strong><p>${escapeLab(item.rationale)}</p><div class="review-decision-actions"><button class="review-approve" type="button" data-review-decision="approve" data-review-case="${item.caseId}">${tr("approveReview")}</button><button class="review-return" type="button" data-review-decision="return" data-review-case="${item.caseId}">${tr("returnOfficer")}</button></div></article>`).join("") : `<div class="workspace-empty">${tr("noHandoffs")}</div>`;
    bindOpenCaseButtons(document.getElementById("review-case-list"));
    document.querySelectorAll("[data-review-decision]").forEach(button => button.addEventListener("click", () => recordReviewDecision(button)));
  }

  async function recordReviewDecision(button) {
    button.disabled = true;
    const approved = button.dataset.reviewDecision === "approve";
    try {
      const response = await fetch(`${API_BASE}/actions`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
        caseId: Number(button.dataset.reviewCase), actionType: approved ? "supervisor-review-approved" : "supervisor-review-returned",
        rationale: approved ? "Supervisor reviewed and approved the submitted review request." : "Supervisor returned the request for further officer clarification.",
        officer: "Supervising Officer", approved
      }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Decision failed");
      workspaceState.actions.unshift(result);
      button.closest(".review-row").innerHTML = `<span class="record-state">${tr("recorded")}</span><strong>${approved ? tr("reviewApproved") : tr("returnedOfficer")}</strong><p>${tr("auditRecorded")}</p>`;
      renderToday();
    } catch (error) {
      button.disabled = false;
      button.textContent = tr("tryAgain");
    }
  }

  function initDrishtiDrawer() {
    const drawer = document.getElementById("drishti-drawer");
    const scrim = document.getElementById("drawer-scrim");
    let returnFocus = null;
    const open = () => {
      if (!workspaceState.activeCaseId) return;
      returnFocus = document.activeElement;
      drawer.classList.add("open"); drawer.setAttribute("aria-hidden", "false"); scrim.hidden = false;
      document.getElementById("drishti-question").focus();
    };
    const close = () => {
      drawer.classList.remove("open"); drawer.setAttribute("aria-hidden", "true"); scrim.hidden = true;
      if (returnFocus instanceof HTMLElement) returnFocus.focus();
    };
    document.getElementById("case-ask-drishti").addEventListener("click", open);
    document.getElementById("drishti-drawer-close").addEventListener("click", close);
    scrim.addEventListener("click", close);
    document.addEventListener("keydown", event => {
      if (!drawer.classList.contains("open")) return;
      if (event.key === "Escape") { close(); return; }
      if (event.key !== "Tab") return;
      const focusable = [...drawer.querySelectorAll('button:not([disabled]), textarea:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])')];
      if (!focusable.length) return;
      const first = focusable[0]; const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });
    document.querySelectorAll("#drishti-suggested-prompts button").forEach(button => button.addEventListener("click", () => { document.getElementById("drishti-question").value = button.textContent; }));
    document.getElementById("drishti-run").addEventListener("click", runDrishtiReview);
  }

  async function runDrishtiReview() {
    const button = document.getElementById("drishti-run");
    const result = document.getElementById("drishti-result");
    const roleValue = document.getElementById("role-select").value;
    const role = ["command", "district", "station", "analyst"].includes(roleValue) ? roleValue : "station";
    button.disabled = true;
    result.innerHTML = `<div class="workspace-loading">${tr("reviewingSources")}</div>`;
    try {
      const response = await fetch(`${API_BASE}/agent/investigate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
        caseId: workspaceState.activeCaseId, role, query: document.getElementById("drishti-question").value.trim()
      }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Drishti review is unavailable");
      result.innerHTML = `<div class="drishti-answer"><strong>${tr("answer")}</strong><p>${escapeLab(data.answer)}</p></div><section class="drishti-section"><h3>${tr("recordedFacts")}</h3><ul>${data.claims.map(claim => `<li>${escapeLab(claim.statement)} <span class="source-tag">${claim.supportingSourceIds.map(escapeLab).join(", ")}</span></li>`).join("")}</ul></section><section class="drishti-section"><h3>${tr("recommendedActions")}</h3><ol>${data.recommendedActions.map(action => `<li><strong>${escapeLab(action.title)}</strong><br>${escapeLab(action.reason)}</li>`).join("")}</ol></section><section class="drishti-section"><h3>${tr("sourcesUsed")}</h3>${data.citations.map(citation => `<span class="drishti-citation"><strong>${escapeLab(citation.id)} · ${escapeLab(citation.label)}</strong><br>${escapeLab(citation.source)}</span>`).join("")}</section><div class="human-control-badge">${tr("suggestionsOnly")}</div><details class="drishti-audit"><summary>${tr("whySuggested")}</summary><p>Run ${escapeLab(data.run.runId)} · ${escapeLab(data.model?.provider || "fallback")} ${escapeLab(data.model?.name || "")} · Audit ${escapeLab(data.run.auditHash?.slice(0, 16) || "recorded")}</p></details>`;
    } catch (error) {
      result.innerHTML = `<div class="next-action-box"><h4>${tr("drishtiUnavailable")}</h4><p>${escapeLab(error.message)}. ${tr("recordUnchanged")}</p></div>`;
    } finally {
      button.disabled = false;
    }
  }

  function initLanguageSwitch() {
    const button = document.getElementById("language-switch");
    applyLanguage();
    button.addEventListener("click", () => {
      workspaceState.language = workspaceState.language === "en" ? "kn" : "en";
      localStorage.setItem("drishti-language", workspaceState.language);
      applyLanguage();
    });
  }

  function applyLanguage() {
    stopVoiceBriefing(false);
    clearDetailedAiBriefing();
    const kannada = workspaceState.language === "kn";
    document.documentElement.lang = kannada ? "kn" : "en";
    document.body.dataset.language = workspaceState.language;
    const button = document.getElementById("language-switch");
    button.textContent = kannada ? "English" : "ಕನ್ನಡ";
    document.querySelectorAll("[data-i18n]").forEach(element => { element.textContent = tr(element.dataset.i18n); });
    document.querySelectorAll("[data-i18n-placeholder]").forEach(element => { element.placeholder = tr(element.dataset.i18nPlaceholder); });
    document.querySelectorAll("[data-i18n-aria]").forEach(element => { element.setAttribute("aria-label", tr(element.dataset.i18nAria)); });
    updateRoleGuidance();
    updateAdvancedNavigationLabels();
    updateDataSourceLabel();
    const question = document.getElementById("drishti-question");
    const knownPrompts = [translations.en.promptAttention, translations.en.promptEvidence, translations.en.promptConflicts,
      translations.kn.promptAttention, translations.kn.promptEvidence, translations.kn.promptConflicts];
    if (!question.value.trim() || knownPrompts.includes(question.value.trim())) question.value = tr("promptAttention");
    updateTodayDate();
    updateVoiceBriefingControls("");
    updateDetailedAiBriefingButton();
    updateOfficerHeader(activePanel);
    if (workspaceState.cases.length) {
      renderToday();
      renderCaseList();
      renderReviewQueue();
    }
    if (workspaceState.activeCaseData) {
      renderCaseHeader();
      renderCaseTab(workspaceState.activeTab);
    }
  }

  function initPeripheralTranslations() {
    document.getElementById("role-select").addEventListener("change", () => window.setTimeout(applyLanguage));
    const dataStatus = document.getElementById("data-source-status");
    new MutationObserver(() => updateDataSourceLabel()).observe(dataStatus, { childList: true, characterData: true, subtree: true });
  }

  function updateRoleGuidance() {
    const role = document.getElementById("role-select").value;
    const key = { command: "roleGuidanceCommand", district: "roleGuidanceDistrict", station: "roleGuidanceStation", patrol: "roleGuidancePatrol", analyst: "roleGuidanceAnalyst" }[role] || "roleGuidanceCommand";
    document.getElementById("role-guidance").textContent = tr(key);
    document.querySelector('[data-open-workspace="reviews"]').hidden = !["command", "district"].includes(role);
    const identity = {
      command: ["RS", "DGP R. Sharma", "statePoliceChief"], district: ["AK", "SP A. Kumar", "districtSuperintendent"],
      station: ["RS", "Inspector R. Sharma", "investigatingOfficer"], patrol: ["MG", "PSI M. Gowda", "patrolSupervisor"],
      analyst: ["SI", "S. Iyer", "crimeAnalyst"]
    }[role];
    if (identity) {
      document.querySelector(".officer-profile .avatar").textContent = identity[0];
      document.querySelector(".officer-name").textContent = identity[1];
      document.querySelector(".officer-title").textContent = tr(identity[2]);
    }
  }

  function updateAdvancedNavigationLabels() {
    const labels = {
      home: ["Dashboard", "ಮುಖ್ಯ ಫಲಕ"], alerts: ["Alerts", "ಎಚ್ಚರಿಕೆಗಳು"], drilldown: ["Districts", "ಜಿಲ್ಲೆಗಳು"],
      search: ["FIR Search", "ಎಫ್‌ಐಆರ್ ಹುಡುಕಾಟ"], intake: ["FIR Registration & Evidence Intake", "ಎಫ್‌ಐಆರ್ ದಾಖಲು ಮತ್ತು ಸಾಕ್ಷ್ಯ ಸ್ವೀಕಾರ"],
      profile: ["Intelligence Profiles", "ಗುಪ್ತಚರ ಪ್ರೊಫೈಲ್‌ಗಳು"], reconstruction: ["Incident Reconstruction", "ಘಟನೆ ಪುನರ್‌ನಿರ್ಮಾಣ"],
      commander: ["Case Commander", "ಪ್ರಕರಣ ಕಮಾಂಡರ್"], networks: ["Link Analysis", "ಸಂಪರ್ಕ ವಿಶ್ಲೇಷಣೆ"], hypotheses: ["Investigative Hypotheses", "ತನಿಖಾ ಊಹೆಗಳು"],
      map: ["Crime Map", "ಅಪರಾಧ ನಕ್ಷೆ"], patterns: ["Crime Patterns", "ಅಪರಾಧ ಮಾದರಿಗಳು"], lifecycle: ["Case Progress", "ಪ್ರಕರಣ ಪ್ರಗತಿ"],
      forecast: ["Predictive Analysis Validation", "ಮುನ್ಸೂಚನಾ ವಿಶ್ಲೇಷಣೆ ಪರಿಶೀಲನೆ"], ai: ["AI Evidence & Confidence", "ಎಐ ಸಾಕ್ಷ್ಯ ಮತ್ತು ವಿಶ್ವಾಸ"],
      patrol: ["Patrol Plan", "ಗಸ್ತು ಯೋಜನೆ"], quality: ["Data Integrity & Quality", "ಡೇಟಾ ಸಮಗ್ರತೆ ಮತ್ತು ಗುಣಮಟ್ಟ"]
    };
    const languageIndex = workspaceState.language === "kn" ? 1 : 0;
    Object.entries(labels).forEach(([target, values]) => {
      const link = document.querySelector(`.nav-link[data-target="${target}"]`);
      if (!link) return;
      const textNode = [...link.childNodes].find(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
      if (textNode) textNode.textContent = ` ${values[languageIndex]} `;
    });
    const sectionLabels = workspaceState.language === "kn"
      ? ["ಕಮಾಂಡ್ ಮತ್ತು ನಿಯಂತ್ರಣ", "ತನಿಖೆ", "ಅಪರಾಧ ವಿಶ್ಲೇಷಣೆ", "ನಿಯೋಜನೆ", "ಆಡಳಿತ"]
      : ["Command & Control", "Investigation", "Crime Analysis", "Deployment", "Governance"];
    document.querySelectorAll(".nav-section-label:not(.primary-nav-label)").forEach((element, index) => {
      if (sectionLabels[index]) element.textContent = sectionLabels[index];
    });
  }

  function updateDataSourceLabel() {
    const element = document.getElementById("data-source-status");
    const value = element.textContent.trim();
    const groups = [
      ["Live police records", "ನೇರ ಪೊಲೀಸ್ ದಾಖಲೆಗಳು"], ["Demo records", "ಪ್ರಾತ್ಯಕ್ಷಿಕೆ ದಾಖಲೆಗಳು"],
      ["Connecting records", "ದಾಖಲೆಗಳಿಗೆ ಸಂಪರ್ಕಿಸಲಾಗುತ್ತಿದೆ"]
    ];
    const match = groups.find(group => group.includes(value));
    if (!match) return;
    const translated = match[workspaceState.language === "kn" ? 1 : 0];
    if (translated !== value) element.textContent = translated;
  }

  function updateOfficerHeader(target) {
    const meta = {
      today: [tr("myWork"), tr("today")], cases: [tr("investigation"), tr("myCases")],
      agents: [workspaceState.language === "kn" ? "ಸಹಾಯಕ ಪೊಲೀಸ್ ಕೆಲಸ" : "Assisted police work", workspaceState.language === "kn" ? "ಪೊಲೀಸ್ ಕಾರ್ಯಗಳು" : "Police tasks"],
      case: [tr("investigation"), tr("caseWorkspace")], reviews: [tr("supervision"), tr("reviewQueue")]
    }[target];
    if (!meta) return;
    document.getElementById("workspace-group").textContent = meta[0];
    document.getElementById("workspace-title").textContent = meta[1];
    document.title = `${meta[1]} — Drishti`;
  }

  function updateTodayDate() {
    document.getElementById("today-date").textContent = new Intl.DateTimeFormat(dateLocale(), {
      weekday: "long", day: "numeric", month: "long", year: "numeric"
    }).format(new Date());
  }

  function humaniseAction(value) {
    if (workspaceState.language === "kn") {
      const labels = {
        "case-command-review": "ಪ್ರಕರಣ ಆದೇಶ ಪರಿಶೀಲನೆ", "supervisor-review-request": "ಮೇಲ್ವಿಚಾರಕರ ಪರಿಶೀಲನಾ ವಿನಂತಿ",
        "supervisor-review-approved": "ಮೇಲ್ವಿಚಾರಕರ ಪರಿಶೀಲನೆ ಅನುಮೋದಿಸಲಾಗಿದೆ", "supervisor-review-returned": "ಮೇಲ್ವಿಚಾರಕರ ಪರಿಶೀಲನೆ ಹಿಂತಿರುಗಿಸಲಾಗಿದೆ"
      };
      if (labels[value]) return labels[value];
    }
    return String(value || "case review").replaceAll("-", " ").replace(/\b\w/g, letter => letter.toUpperCase());
  }

  function statusLabel(value) {
    const normalized = String(value || "").toLowerCase();
    if (workspaceState.language !== "kn") return value;
    const labels = {
      recorded: "ದಾಖಲಾಗಿದೆ", inferred: "ಊಹಿಸಲಾಗಿದೆ", missing: "ಕಾಣೆಯಾಗಿದೆ", partial: "ಭಾಗಶಃ",
      conflict: "ವಿರೋಧ", "recorded-date": "ದಾಖಲಿತ ದಿನಾಂಕ", "pending human review": "ಮಾನವ ಪರಿಶೀಲನೆ ಬಾಕಿ",
      "approved by human reviewer": "ಮಾನವ ಪರಿಶೀಲಕರಿಂದ ಅನುಮೋದಿಸಲಾಗಿದೆ"
    };
    return labels[normalized] || value;
  }

  function formatDate(value) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value || "—") : new Intl.DateTimeFormat(dateLocale(), { day: "2-digit", month: "short", year: "numeric" }).format(date);
  }

  function formatDateTime(value) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value || "—") : new Intl.DateTimeFormat(dateLocale(), { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(date);
  }
})();
