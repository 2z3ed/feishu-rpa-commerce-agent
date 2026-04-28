from app.services.feishu.longconn import _can_mark_task_queued


def test_p15b_can_mark_task_queued_for_received_or_queued():
    assert _can_mark_task_queued("received") is True
    assert _can_mark_task_queued("queued") is True


def test_p15b_cannot_overwrite_terminal_or_processing_status():
    assert _can_mark_task_queued("processing") is False
    assert _can_mark_task_queued("succeeded") is False
    assert _can_mark_task_queued("failed") is False
    assert _can_mark_task_queued("awaiting_confirmation") is False
