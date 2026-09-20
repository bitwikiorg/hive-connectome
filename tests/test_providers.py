import json, httpx, pytest
from hive_connectome.providers.venice import VeniceJev
from hive_connectome.providers.lmstudio import LMStudio
from hive_connectome.schemas import JevQuestion, DecisionType

@pytest.mark.asyncio
async def test_venice_payload_and_response():
    def handler(req):
        assert req.url.path.endswith("/decisions")
        data=json.loads(req.content); assert data["model"]=="jev-latest"
        return httpx.Response(200,json={"model":"jev-latest","answers":{"x":{"type":"noul","noul":0.9}},"usage":{}})
    v=VeniceJev("https://example.test","k",transport=httpx.MockTransport(handler))
    out=await v.decide({"a":1},{"x":JevQuestion(type=DecisionType.NOUL,instructions="x?")})
    assert out.answers["x"]["noul"]==0.9
    assert out.transport["provider"]=="venice"
    assert out.transport["capability"]=="decisions"
    assert out.transport["http_status"]==200
    assert out.transport["request_hash"] and out.transport["response_hash"]

@pytest.mark.asyncio
async def test_lmstudio_chat():
    lm=LMStudio("http://lm.test/v1",transport=httpx.MockTransport(lambda req:httpx.Response(200,json={"choices":[{"message":{"content":"ok"}}]})))
    out=await lm.chat("model","task",{"x":1})
    assert out.text=="ok"
    assert out.transport["provider"]=="lmstudio" and out.transport["http_status"]==200

@pytest.mark.asyncio
async def test_lmstudio_temperature_auth_and_models():
    def handler(req):
        if req.url.path.endswith('/models'): return httpx.Response(200, json={"data":[{"id":"tiny"}]})
        payload=json.loads(req.content); assert payload["temperature"]==0.7; assert req.headers["Authorization"]=="Bearer secret"
        return httpx.Response(200,json={"choices":[{"message":{"content":"warm"}}]})
    lm=LMStudio("http://lm.test/v1",api_token="secret",transport=httpx.MockTransport(handler))
    assert (await lm.list_models())["data"][0]["id"]=="tiny"
    assert (await lm.chat("model","task",{"x":1},temperature=0.7)).text=="warm"

@pytest.mark.asyncio
async def test_venice_chat_completions():
    from hive_connectome.providers.venice import VeniceChat
    def handler(req):
        payload=json.loads(req.content); assert req.url.path.endswith('/chat/completions') and payload["model"]=="chat-model" and payload["temperature"]==0.4
        return httpx.Response(200,json={"choices":[{"message":{"content":"ok-chat"}}]})
    chat=VeniceChat("https://api.venice.test/api/v1","vk",transport=httpx.MockTransport(handler))
    out=await chat.chat("chat-model","task",{"x":1},temperature=0.4)
    assert out.provider=="venice" and out.text=="ok-chat"
    assert out.transport["capability"]=="chat" and out.transport["http_status"]==200
