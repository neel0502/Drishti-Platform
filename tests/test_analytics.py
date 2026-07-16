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
