import pytest
from unittest.mock import AsyncMock, patch
from src.config import NotifyConfig, WecomConfig, DingtalkConfig
from src.notifier.dispatcher import NotifyDispatcher
from src.notifier.console import ConsoleNotifier
from src.notifier.wecom import WecomNotifier
from src.notifier.dingtalk import DingtalkNotifier

@pytest.fixture
def notify_config():
    config = NotifyConfig()
    config.channels = ["console", "wecom", "dingtalk"]
    config.wecom = WecomConfig(webhook_url="http://test.wecom")
    config.dingtalk = DingtalkConfig(webhook_url="http://test.dingtalk", secret="secret")
    return config

@pytest.mark.asyncio
async def test_notify_dispatcher(notify_config):
    dispatcher = NotifyDispatcher(notify_config)
    assert len(dispatcher.notifiers) == 3
    
    # Should not raise exception
    await dispatcher.dispatch("Test Title", "Test Content")

@pytest.mark.asyncio
async def test_console_notifier():
    notifier = ConsoleNotifier()
    result = await notifier.send("Title", "Content")
    assert result is True

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_wecom_notifier(mock_post):
    class MockResponse:
        def json(self):
            return {"errcode": 0}
        def raise_for_status(self): pass
    mock_post.return_value = MockResponse()
    notifier = WecomNotifier("http://test.wecom")
    result = await notifier.send("Title", "Content")
    assert result is True

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_dingtalk_notifier(mock_post):
    class MockResponse:
        def json(self):
            return {"errcode": 0}
        def raise_for_status(self): pass
    mock_post.return_value = MockResponse()
    notifier = DingtalkNotifier("http://test.dingtalk", secret="secret")
    result = await notifier.send("Title", "Content")
    assert result is True
