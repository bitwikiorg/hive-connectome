from hive_connectome.evals import DEFAULT_TOGGLES, summarize_eval


def test_default_toggles_are_complete_matrix():
    assert {(x.jev, x.llm) for x in DEFAULT_TOGGLES} == {(False, False), (True, False), (False, True), (True, True)}


def test_summarize_eval():
    rows = [
        {"toggle_case":"a","route_correct":True,"latency_ms":10,"llm_called":False,"jev_called":True,"error":None},
        {"toggle_case":"a","route_correct":False,"latency_ms":30,"llm_called":True,"jev_called":True,"error":"x"},
        {"toggle_case":"b","route_correct":None,"latency_ms":5,"llm_called":False,"jev_called":False,"error":None},
    ]
    out = summarize_eval(rows)
    assert out["a"]["route_accuracy"] == 0.5
    assert out["a"]["mean_latency_ms"] == 20
    assert out["a"]["llm_calls"] == 1
    assert out["a"]["failures"] == 1
    assert out["b"]["route_accuracy"] is None
