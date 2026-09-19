import json,httpx,pytest
from hive_connectome.providers.venice import VeniceJev
from hive_connectome.providers.lmstudio import LMStudio
from hive_connectome.schemas import JevQuestion,DecisionType

@pytest.mark.asyncio
async def test_venice_payload_and_response():
    def handler(req):
        assert req.url.path.endswith("/decisions");data=json.loads(req.content);assert data["model"]=="jev-latest"
        return httpx.Response(200,json={"model":"jev-latest","answers":{"x":{"type":"noul","noul":0.9}},"usage":{}})
    v=VeniceJev("https://example.test","k",transport=httpx.MockTransport(handler))
    out=await v.decide({"a":1},{"x":JevQuestion(type=DecisionType.NOUL,instructions="x?")})
    assert out.answers["x"]["noul"]==0.9

@pytest.mark.asyncio
async def test_lmstudio_chat():
    lm=LMStudio("http://lm.test/v1",transport=httpx.MockTransport(lambda req:httpx.Response(200,json={"choices":[{"message":{"content":"ok"}}]})))
    out=await lm.chat("model","task",{"x":1});assert out.text=="ok"
