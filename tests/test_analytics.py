import backend.app as analytics


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
