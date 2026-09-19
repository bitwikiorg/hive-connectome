import pytest
from hive_connectome.schemas import DataSourceSpec,EventEnvelope,JevQuestion,DecisionType
def test_event_defaults():e=EventEnvelope(payload={"x":1});assert e.id and e.source_id=="manual"
def test_jev_question_shapes():q=JevQuestion(type=DecisionType.CHOICE,instructions="route",criteria={"a":"A","b":"B"});assert q.type=="choice"
def test_file_drop_requires_path():
    with pytest.raises(ValueError):DataSourceSpec(id="x",name="x",kind="file_drop")
