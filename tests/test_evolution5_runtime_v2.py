from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_v2_has_active_tactical_arbitration():
    h = (ROOT / 'competition/agents/juraj_v35_cpp/evolution5_behavior.hpp').read_text()
    assert 'enum class TacticalMode {EXPAND,DEFEND,MUSTER,ATTACK}' in h
    assert 'anti_rush_' in h
    assert 'void tune(v35::Candidate&q,int turn)' in h
    assert 'REAR_EVACUATION' in h
    assert 'FREE_SURPLUS_RELOCATION' in h
    assert '[e5_behavior_v2]' in h


def test_apply_cpp_wires_runtime_v2_before_scheduling():
    s = (ROOT / 'tools/evolution5/apply_cpp.py').read_text()
    assert 'e5_.update(' in s
    assert 'e5_.allow(q)' in s
    assert 'e5_.tune(q,o.turn)' in s
    assert 'o.my_land,o.opp_land,o.my_army,o.opp_army' in s
