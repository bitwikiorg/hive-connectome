from hive_connectome.brains.synthetic import DeterministicMiniBrain
from hive_connectome.schemas import BrainKind

def test_brain_is_stateful_and_resettable():
    b=DeterministicMiniBrain("x",BrainKind.WORM_LINK,8);a=b.step({"x":1});c=b.step({"x":1})
    assert a.state_vector!=c.state_vector
    b.reset();assert b.step({"x":1}).state_vector==a.state_vector

def test_feedback_changes_next_state():
    a=DeterministicMiniBrain("x",BrainKind.FLY_CORE,8);b=DeterministicMiniBrain("x",BrainKind.FLY_CORE,8)
    a.step("same");b.step("same");a.feedback(1.0)
    assert a.step("same").state_vector!=b.step("same").state_vector
