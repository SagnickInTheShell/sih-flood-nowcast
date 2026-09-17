from fastapi.testclient import TestClient

from app.main import app


def test_full_api_flow():
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200

        scenarios_resp = client.get("/api/scenarios")
        assert scenarios_resp.status_code == 200
        scenario_list = scenarios_resp.json()
        assert len(scenario_list) == 3
        scenario_id = scenario_list[0]["scenario_id"]

        infra_resp = client.get("/api/critical-infrastructure")
        assert infra_resp.status_code == 200
        infra_list = infra_resp.json()
        assert len(infra_list) == 3

        sim_resp = client.post("/api/simulate", json={"rainfall_intensity_mm_hr": 60, "duration_min": 90})
        assert sim_resp.status_code == 200
        sim_body = sim_resp.json()
        assert "scenario_id" in sim_body
        assert "node_predictions" in sim_body and len(sim_body["node_predictions"]) > 0
        assert "road_segments" in sim_body and len(sim_body["road_segments"]) > 0
        assert sim_body["model_caveat"]
        assert sim_body["is_synthetic_ward"] is True

        start, end = infra_list[0], infra_list[1]
        route_resp = client.post("/api/route", json={
            "start": {"lat": start["lat"], "lng": start["lng"]},
            "end": {"lat": end["lat"], "lng": end["lng"]},
            "scenario_id": scenario_id,
            "algorithm": "astar",
        })
        assert route_resp.status_code == 200
        route_body = route_resp.json()
        assert "route_geometry" in route_body
        assert "baseline_route_geometry" in route_body
        assert "eta_seconds" in route_body
        assert "avoided_flooded_segments" in route_body

        backtest_resp = client.get("/api/backtest/nonexistent")
        assert backtest_resp.status_code == 501
