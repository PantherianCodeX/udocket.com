from automation.langgraph import runtime


def test_execution_order_has_all_lanes() -> None:
    order = runtime.execution_order()
    assert len(order) == len(runtime.load_lane_packages())
    seen = set(pkg.lane_id for pkg in order)
    assert seen == set(pkg.lane_id for pkg in runtime.load_lane_packages())


def test_lane_profiles_register_both() -> None:
    profiles = runtime.lane_profiles()
    assert profiles, "Runtime profiles must map to lane packages"
    assert all(len(pkg.stage_keys) for pkg in profiles.values())
