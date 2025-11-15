from automation.pipelines.stage_map import lane_packages


def test_lane_qa_contracts_defined() -> None:
    for lane in lane_packages():
        assert lane.qa_contracts, f"Lane {lane.lane_id} must define QA contract IDs"


def test_lane_cost_ceiling_positive() -> None:
    for lane in lane_packages():
        assert lane.cost_ceiling_tokens > 0
