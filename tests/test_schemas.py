import pytest
from hive_connectome.schemas import DataSourceSpec, EventEnvelope, JevQuestion, DecisionType

def test_event_defaults():
    e=EventEnvelope(payload={"x":1})
    assert e.id and e.source_id=="manual"

def test_jev_question_shapes():
    q=JevQuestion(type=DecisionType.CHOICE,instructions="route",criteria={"a":"A","b":"B"})
    assert q.type=="choice"

def test_file_drop_requires_path():
    with pytest.raises(ValueError):
        DataSourceSpec(id="x",name="x",kind="file_drop")

from hive_connectome.schemas import BrainStageSpec, BeeUnitSpec, HivemindSpec, BrainKind

def test_generic_brain_chain_schema():
    bee=BeeUnitSpec(id="x",role="test",brain_chain=[
        BrainStageSpec(id="w",kind=BrainKind.WORM_LINK,engine="synthetic",state_size=16),
        BrainStageSpec(id="l",kind=BrainKind.LARVAL_MB,engine="planned",enabled=False,input_from=["w"]),
        BrainStageSpec(id="f",kind=BrainKind.FLY_CORE,engine="synthetic",state_size=64,input_from=["w","l"]),
    ])
    hive=HivemindSpec(bee_units=[bee],default_chain=["x"])
    assert hive.bee_units[0].brain_chain[1].kind==BrainKind.LARVAL_MB
