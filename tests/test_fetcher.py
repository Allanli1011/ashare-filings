import pytest
from unittest.mock import AsyncMock, patch
from src.fetcher.cninfo import CninfoFetcher
from src.models.announcement import AnnouncementCategory

@pytest.mark.asyncio
async def test_cninfo_fetcher_parse_item():
    fetcher = CninfoFetcher()
    item = {
        "secCode": "000001",
        "secName": "Test Bank",
        "announcementTitle": "<em>2023年度报告</em>",
        "announcementId": "12345678",
        "announcementTime": 1700000000000,
        "announcementType": "年度报告"
    }
    ann = fetcher._parse_item(item)
    assert ann is not None
    assert ann.stock_code == "000001"
    assert ann.title == "2023年度报告"
    assert ann.category == AnnouncementCategory.ANNUAL_REPORT
    assert ann.id == "cninfo_12345678"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_cninfo_fetch_announcements(mock_post):
    class MockResponse:
        def json(self):
            return {
                "announcements": [{
                    "secCode": "000001",
                    "secName": "Test Bank",
                    "announcementTitle": "2023年度报告",
                    "announcementId": "12345678",
                    "announcementTime": 1700000000000,
                    "announcementType": "年度报告"
                }],
                "totalpages": 1
            }
        def raise_for_status(self): pass
    mock_post.return_value = MockResponse()
    
    fetcher = CninfoFetcher()
    anns = await fetcher.fetch_announcements()
    assert len(anns) == 1
    assert anns[0].stock_code == "000001"
    assert anns[0].title == "2023年度报告"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
async def test_cninfo_fetch_content(mock_get):
    class MockResponse:
        content = b"fake pdf content"
        def raise_for_status(self): pass
    mock_get.return_value = MockResponse()
    
    fetcher = CninfoFetcher()
    ann = fetcher._parse_item({
        "secCode": "000001", "secName": "Test Bank", "announcementTitle": "Test", 
        "announcementId": "123456", "announcementTime": 1700000000000
    })
    
    content = await fetcher.fetch_content(ann)
    # the PyPDF2 should handle invalid pdf bytes by catching exception and returning ""
    assert content == ""
