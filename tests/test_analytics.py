import json

import backend.app as analytics
from backend import catalyst_store


def setup_module():
    analytics.load_data()
    analytics.build_network_graph()
    analytics.build_nlp_index()


def test_explainable_case_links_are_computed():
    case_id = analytics.pattern_b_case_ids[0]
    payload = analytics.get_case_links(case_id)

    assert payload["sourceCase"]["caseId"] == case_id
    assert payload["relatedCases"]
    assert payload["relatedCases"][0]["connectionScore"] >= 35
    assert payload["relatedCases"][0]["evidence"]


def test_alerts_include_statistical_evidence_and_cases():
    payload = analytics.get_situations()

    assert payload["alerts"]
    assert payload["alerts"][0]["evidence"]
    assert payload["alerts"][0]["cases"]
    assert "baseline" in payload["alerts"][0]["description"]


def test_network_graph_is_derived_from_case_relationships():
    payload = analytics.build_computed_crime_networks("drill-burglary-gang")
    graph = payload["selectedGroup"]

    assert graph["evidence"]["caseCount"] == len(analytics.pattern_b_case_ids)
    assert graph["nodes"]
    assert any("linked FIR" in edge["label"] for edge in graph["edges"])


def test_district_metrics_use_complete_months():
    payload = analytics.get_district_details(3)

    assert payload["analysisPeriod"] == "2024-11"
    assert payload["periodCasesCount"] > 0
    assert "vs 2024-10" in payload["percentageIncrease"]
    assert payload["topCrimeType"] != "No recorded cases"


def test_dashboard_attention_matches_computed_anomalies():
    dashboard = analytics.get_dashboard()
    anomalies = analytics.compute_monthly_anomalies(limit=3)

    assert len(dashboard["alerts"]) == len(anomalies)
    assert dashboard["kpi"]["attentionDistricts"]["value"] == len(anomalies)


def test_narrative_identifier_extraction():
    phone = analytics.extract_first_identifier(
        "Suspect called 98450-12345 after the incident",
        analytics.PHONE_PATTERN,
        lambda value: value,
    )
    vehicle = analytics.extract_first_identifier(
        "CCTV shows vehicle KA-05 MX 1234 leaving the area",
        analytics.VEHICLE_PATTERN,
        lambda value: value,
    )

    assert phone == "98450-12345"
    assert vehicle == "KA-05 MX 1234"


def test_reconstruction_separates_recorded_and_inferred_events():
    payload = analytics.build_incident_reconstruction(50005)
    event_types = [event["type"] for event in payload["events"]]

    assert event_types[:5] == ["vehicle", "incident", "vehicle", "police", "fir"]
    assert payload["events"][0]["confidence"] == "inferred"
    assert payload["events"][1]["confidence"] == "recorded"
    assert any(link["field"] == "Exact vehicle route" for link in payload["missingLinks"])
    assert payload["decisionSupport"]["humanReviewRequired"] is True


def test_reconstruction_reports_absent_identifiers_without_inventing_route():
    payload = analytics.build_incident_reconstruction(1)
    missing_fields = {link["field"] for link in payload["missingLinks"]}

    assert "Phone identifier" in missing_fields
    assert "Vehicle identifier" in missing_fields
    assert not payload["routeCoordinates"] or len(payload["routeCoordinates"]) == 1
    assert all(event["confidence"] != "inferred" for event in payload["events"])


def test_fusion_engine_reports_present_and_missing_signals():
    payload = analytics.get_case_links(50005)
    strongest = payload["relatedCases"][0]

    assert strongest["connectionScore"] >= 50
    assert any(item["type"] == "MO narrative" for item in strongest["evidence"])
    assert "missingSignals" in strongest


def test_operational_action_is_audited_with_human_status():
    analytics.operational_action_log.clear()
    request = analytics.OperationalActionRequest(
        caseId=50005,
        actionType="analyst-review",
        rationale="Validate missing route evidence",
        approved=False,
    )
    result = analytics.record_operational_action(request)

    assert result["actionId"] == 1
    assert result["status"] == "pending human review"
    assert analytics.get_operational_actions(50005)["actions"][0]["rationale"] == request.rationale


def test_investigation_tasks_are_reconstructed_from_append_only_events():
    from fastapi import HTTPException
    analytics.operational_action_log.clear()
    created = analytics.create_investigation_task(analytics.InvestigationTaskRequest(
        caseId=50005, title="Verify CCTV collection", detail="Confirm collection time, source camera, and custody metadata.",
        owner="Inspector R. Sharma", dueDate="2026-08-28", priority="high", sourceIds=["C2"],
        agentId="evidence-gap", agentRunId="AGT-TEST", createdBy="Inspector R. Sharma",
    ))
    assert created["status"] == "open"
    tasks = analytics.get_investigation_tasks(caseId=50005)["tasks"]
    assert tasks[0]["taskId"] == created["taskId"]
    try:
        analytics.update_investigation_task(created["taskId"], analytics.TaskStatusRequest(
            status="completed", officer="Inspector R. Sharma", role="station", note="Done",
        ))
    except HTTPException as error:
        assert error.status_code == 403
    else:
        raise AssertionError("Station role must not complete a supervisor-controlled task")
    analytics.update_investigation_task(created["taskId"], analytics.TaskStatusRequest(
        status="in_progress", officer="Inspector R. Sharma", role="station", note="Work started",
    ))
    analytics.update_investigation_task(created["taskId"], analytics.TaskStatusRequest(
        status="awaiting_supervisor", officer="Inspector R. Sharma", role="station", note="Evidence attached",
    ))
    analytics.update_investigation_task(created["taskId"], analytics.TaskStatusRequest(
        status="completed", officer="SP A. Kumar", role="district", note="Sources verified",
    ))
    completed = analytics.get_investigation_tasks(caseId=50005)["tasks"][0]
    assert completed["status"] == "completed"
    assert len(completed["history"]) == 3


def test_agent_task_requires_citation_and_task_state_cannot_skip_handoff():
    from fastapi import HTTPException
    analytics.operational_action_log.clear()
    try:
        analytics.create_investigation_task(analytics.InvestigationTaskRequest(
            caseId=50005, title="Verify case link", detail="Compare both source FIRs before coordination.",
            owner="Inspector R. Sharma", dueDate="2026-08-28", agentId="linked-case-verification",
        ))
    except HTTPException as error:
        assert error.status_code == 422
    else:
        raise AssertionError("Agent-suggested work must retain a source citation")

    created = analytics.create_investigation_task(analytics.InvestigationTaskRequest(
        caseId=50005, title="Verify case link", detail="Compare both source FIRs before coordination.",
        owner="Inspector R. Sharma", dueDate="2026-08-28", agentId="linked-case-verification",
        sourceIds=["C3"],
    ))
    try:
        analytics.update_investigation_task(created["taskId"], analytics.TaskStatusRequest(
            status="awaiting_supervisor", officer="Inspector R. Sharma", role="station",
        ))
    except HTTPException as error:
        assert error.status_code == 409
    else:
        raise AssertionError("Task handoff must not skip the in-progress state")


def test_evidence_custody_requires_supervisor_verification():
    from fastapi import HTTPException
    analytics.operational_action_log.clear()
    evidence = {
        "id": "DEV-EV-TEST", "caseId": 50005, "fileName": "test.pdf", "receivedAt": "2026-08-25T10:00:00+00:00",
        "sha256": "abc", "custodyStatus": "received", "humanVerified": False,
    }
    analytics._append_workflow_event("evidence-created", 50005, evidence, "received")
    try:
        analytics.verify_evidence_custody("DEV-EV-TEST", analytics.EvidenceVerificationRequest(
            officer="Inspector", role="station", status="verified",
        ))
    except HTTPException as error:
        assert error.status_code == 403
    else:
        raise AssertionError("Station role must not verify custody")
    result = analytics.verify_evidence_custody("DEV-EV-TEST", analytics.EvidenceVerificationRequest(
        officer="SP A. Kumar", role="district", status="verified", note="Checksum and seal checked",
    ))
    assert result["status"] == "verified"
    assert analytics.list_development_evidence(50005)["records"][0]["humanVerified"] is True


def test_pattern_lab_discovers_clusters_with_linked_cases():
    payload = analytics.discover_patterns(
        districtId=1, crimeHeadId=None, dateFrom=None, dateTo=None, clusterCount=3
    )

    assert len(payload["clusters"]) == 3
    assert sum(cluster["size"] for cluster in payload["clusters"]) == payload["sampledCaseCount"]
    assert all(cluster["topTerms"] for cluster in payload["clusters"])
    assert all(cluster["representativeCases"] for cluster in payload["clusters"])
    assert all("uniqueNarrativeRate" in cluster for cluster in payload["clusters"])


def test_case_lifecycle_reconciles_funnel_and_exceptions():
    payload = analytics.case_lifecycle(districtId=1)
    funnel = {stage["stage"]: stage["count"] for stage in payload["funnel"]}

    assert funnel["FIR registered"] > funnel["Arrest recorded"]
    assert funnel["Arrest recorded"] >= funnel["Chargesheet filed"]
    assert payload["timings"]["medianFIRToArrestDays"] >= 0
    assert payload["bottlenecks"]
    assert payload["exceptions"]["chronologyConflicts"] == 0


def test_patrol_plan_allocates_exact_available_units_and_labels_limitations():
    payload = analytics.patrol_plan(
        districtId=1, availableUnits=8, heinousWeight=1.5,
        recencyWeight=0.75, shiftStart=0, shiftEnd=23,
    )

    assert sum(zone["allocatedUnits"] for zone in payload["zones"]) == 8
    assert 0 < payload["coverageIndex"] <= 100
    assert all(zone["rationale"] for zone in payload["zones"])
    assert "does not predict" in payload["caveat"]


def test_data_quality_centre_reports_schema_issues():
    payload = analytics.data_quality_command_centre(districtId=1)

    assert payload["records"] > 0
    assert 0 <= payload["qualityScore"] <= 100
    assert any(check["name"] == "Duplicated narrative text" for check in payload["checks"])
    assert payload["recommendations"]


def test_hypothesis_board_validates_case_links():
    analytics.hypothesis_boards.clear()
    request = analytics.HypothesisBoardRequest(
        title="Chain-snatching working theory",
        hypothesis="The same vehicle may connect the selected FIRs.",
        caseIds=[50005, -1],
        evidence=["Shared vehicle identifier"],
        gaps=["Exact CCTV route"],
    )
    board = analytics.save_hypothesis_board(request)

    assert board["id"] == 1
    assert board["caseIds"] == [50005]
    assert board["evidence"] and board["gaps"]


def test_patrol_what_if_respects_shift_and_weights():
    payload = analytics.patrol_plan(
        districtId=1, availableUnits=5, heinousWeight=2.0,
        recencyWeight=1.0, shiftStart=18, shiftEnd=23,
    )

    assert sum(zone["allocatedUnits"] for zone in payload["zones"]) == 5
    assert payload["scenario"]["shiftStart"] == 18
    assert payload["scenario"]["heinousWeight"] == 2.0
    assert "baselineCoverageIndex" in payload
    assert payload["coverageDelta"] == round(payload["coverageIndex"] - payload["baselineCoverageIndex"], 1)


def test_forecast_backtest_uses_historical_holdout():
    payload = analytics.forecast_backtest(districtId=1, crimeHeadId=None, holdoutMonths=6)

    assert len(payload["series"]) == 6
    assert payload["metrics"]["mae"] >= 0
    assert "retrospective" in payload["caveat"].lower()


def test_case_brief_pdf_is_generated():
    pdf = analytics.case_brief_pdf(50005).read()

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 2000


def test_health_reports_active_data_source():
    payload = analytics.health_check()

    assert payload["dataSource"]["active"] in {"csv", "catalyst"}
    assert "fallback" in payload["dataSource"]


def test_catalyst_zcql_rows_are_flattened():
    nested = {"CaseMaster": {"CaseMasterID": 7, "CrimeNo": "FIR-7"}}

    assert catalyst_store._flatten_zcql_row(nested, "CaseMaster")["CaseMasterID"] == 7


def test_profile_selector_and_profile_contract_are_usable():
    options = analytics.get_profile_options(limit=10)["profiles"]

    assert options
    profile = analytics.get_suspect_profile(options[0]["name"])
    assert profile["name"]
    assert isinstance(profile["timeline"], list)
    assert isinstance(profile["movement"], list)
    assert all({"lat", "lng", "district", "date"} <= point.keys() for point in profile["movement"])


def test_reconstruction_selector_returns_loadable_cases():
    options = analytics.get_reconstruction_options(limit=10)["cases"]

    assert options
    payload = analytics.build_incident_reconstruction(options[0]["caseId"])
    assert payload["case"]["caseId"] == options[0]["caseId"]
    assert payload["events"]


def test_investigation_agent_returns_cited_human_review_draft():
    analytics.agent_run_log.clear()
    result = analytics.run_investigation_agent(analytics.InvestigationAgentRequest(
        caseId=50005,
        role="district",
        query="What evidence should be verified before district coordination?",
    ))

    assert result["run"]["runId"].startswith("AGT-")
    assert result["citations"]
    assert [stage["id"] for stage in result["stages"]] == ["scout", "skeptic", "commander"]
    assert result["claims"]
    assert all(claim["supportingSourceIds"] for claim in result["claims"])
    assert len(result["skepticReviews"]) == len(result["claims"])
    assert result["recommendedActions"]
    assert result["actionDraft"]["approved"] is False
    assert all(action["requiresHumanApproval"] for action in result["recommendedActions"])
    assert result["run"]["auditHash"]
    assert result["privacy"]["mode"] == "minimum necessary output"
    assert result["model"]["provider"] in {"openai", "deterministic-fallback"}
    assert "totalTokens" in result["model"]["tokenUsage"]


def test_agent_output_masks_direct_identifiers_and_chains_audit_runs():
    analytics.agent_run_log.clear()
    masked = analytics.redact_agent_text("Call 9845012345 using KA-05 MX 1234")
    assert "9845012345" not in masked
    assert "KA-05 MX 1234" not in masked
    first = analytics.run_investigation_agent(analytics.InvestigationAgentRequest(
        caseId=50005, role="analyst", query="Review the evidence and prepare a cited verification plan.",
    ))
    second = analytics.run_investigation_agent(analytics.InvestigationAgentRequest(
        caseId=50005, role="analyst", query="Challenge the prior plan against missing evidence.",
    ))
    private_names = analytics.df_accused[analytics.df_accused["CaseMasterID"] == 50005]["AccusedName"].dropna().astype(str).tolist()
    serialized = json.dumps(first)
    assert all(name == "Unknown" or name not in serialized for name in private_names)
    assert first["run"]["previousAuditHash"] == "GENESIS"
    assert second["run"]["previousAuditHash"] == first["run"]["auditHash"]


def test_internal_agent_run_lookup_does_not_treat_query_descriptor_as_filter():
    analytics.agent_run_log.clear()
    result = analytics.run_investigation_agent(analytics.InvestigationAgentRequest(
        caseId=50005, role="analyst", query="Prepare a cited evidence verification plan for supervisor review.",
    ))

    runs = analytics.get_agent_runs()["runs"]

    assert any(run["runId"] == result["run"]["runId"] for run in runs)


def test_investigation_agent_rejects_unauthorized_role():
    from fastapi import HTTPException
    try:
        analytics.run_investigation_agent(analytics.InvestigationAgentRequest(
            caseId=50005, role="guest", query="Review this FIR evidence before proceeding.",
        ))
    except HTTPException as error:
        assert error.status_code == 403
    else:
        raise AssertionError("Unauthorised role should be rejected")


def test_proactive_sentinel_returns_review_only_triggers():
    payload = analytics.get_agent_sentinel(limit=4)

    assert payload["triggers"]
    assert all(item["humanReviewRequired"] for item in payload["triggers"])
    assert all(item["source"] for item in payload["triggers"])
    assert "does not predict individual" in payload["guardrail"]


def test_each_primary_screen_has_nonempty_data_contract():
    contracts = {
        "home": analytics.get_dashboard(),
        "map": analytics.get_map_data(),
        "situations": analytics.get_situations(),
        "district": analytics.get_district_details(1),
        "networks": analytics.build_computed_crime_networks(),
        "lifecycle": analytics.case_lifecycle(districtId=1),
        "patrol": analytics.patrol_plan(
            districtId=1, availableUnits=4, heinousWeight=1.5,
            recencyWeight=0.75, shiftStart=0, shiftEnd=23,
        ),
        "quality": analytics.data_quality_command_centre(districtId=1),
        "forecast": analytics.forecast_backtest(districtId=1, crimeHeadId=None, holdoutMonths=3),
    }

    assert contracts["home"]["kpi"]
    assert contracts["map"]["geojson"]["features"]
    assert contracts["situations"]["alerts"]
    assert contracts["district"]["stations"]
    assert contracts["networks"]["selectedGroup"]["nodes"]
    assert contracts["lifecycle"]["funnel"]
    assert contracts["patrol"]["zones"]
    assert contracts["quality"]["checks"]
    assert contracts["forecast"]["series"]
