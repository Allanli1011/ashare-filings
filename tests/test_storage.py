import pytest
from datetime import datetime
from src.models.announcement import Announcement, AnnouncementCategory
from src.models.signal import Signal, SignalAction, SignalStrength
from src.storage.database import Database

@pytest.fixture
async def temp_db(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.init()
    return db

@pytest.mark.asyncio
async def test_database_init(temp_db):
    assert temp_db is not None

@pytest.mark.asyncio
async def test_save_and_check_announcement(temp_db):
    announcement = Announcement(
        id="test_ann_1",
        stock_code="000001",
        stock_name="Test Bank",
        title="Test Announcement",
        category=AnnouncementCategory.ANNUAL_REPORT,
        publish_time=datetime.now(),
        source="cninfo",
        url="http://test.com"
    )
    
    # Not processed initially
    assert not await temp_db.is_processed(announcement.id)
    
    # Save announcement
    await temp_db.save_announcement(announcement)
    
    # Now it should be processed
    assert await temp_db.is_processed(announcement.id)

@pytest.mark.asyncio
async def test_filter_new(temp_db):
    ann1 = Announcement(
        id="test_ann_1", stock_code="000001", stock_name="Test Bank",
        title="Test 1", category=AnnouncementCategory.ANNUAL_REPORT,
        publish_time=datetime.now(), source="cninfo", url="http://test1.com"
    )
    ann2 = Announcement(
        id="test_ann_2", stock_code="000002", stock_name="Test Tech",
        title="Test 2", category=AnnouncementCategory.OTHER,
        publish_time=datetime.now(), source="cninfo", url="http://test2.com"
    )
    
    # Both are new
    new_anns = await temp_db.filter_new([ann1, ann2])
    assert len(new_anns) == 2
    
    # Save one
    await temp_db.save_announcement(ann1)
    
    # Now only one is new
    new_anns = await temp_db.filter_new([ann1, ann2])
    assert len(new_anns) == 1
    assert new_anns[0].id == "test_ann_2"

@pytest.mark.asyncio
async def test_save_signal(temp_db):
    announcement = Announcement(
        id="test_ann_1", stock_code="000001", stock_name="Test Bank",
        title="Test 1", category=AnnouncementCategory.ANNUAL_REPORT,
        publish_time=datetime.now(), source="cninfo", url="http://test1.com"
    )
    await temp_db.save_announcement(announcement)
    
    signal = Signal(
        announcement_id=announcement.id,
        stock_code="000001",
        stock_name="Test Bank",
        action=SignalAction.BUY,
        strength=SignalStrength.HIGH,
        reason="Good earnings",
        key_data={"profit": "100M"}
    )
    
    # Save signal shouldn't raise exception
    await temp_db.save_signal(signal)
