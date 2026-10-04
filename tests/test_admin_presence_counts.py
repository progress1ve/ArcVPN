from bot.services.admin_presence import unique_customer_presence

def test_main_lte_multiple_keys_and_missing_telegram_id_count_once():
    customers = [{"id":1,"telegram_id":11,"panel_email":"main1","lte_panel_username":"lte1"}, {"id":1,"telegram_id":11,"panel_email":"main2","lte_panel_username":"lte1"}, {"id":2,"telegram_id":22,"panel_email":"main3"}]
    rows = [{"telegram_id":11,"username":"main1","online_at":"2026-10-04T10:00:00Z"}, {"telegram_id":11,"username":"lte1","online_at":"2026-10-04T10:01:00Z"}, {"telegram_id":None,"username":"main2","online_at":"2026-10-04T10:00:00Z"}, {"telegram_id":None,"username":"main3","online_at":"2026-10-04T10:00:00Z"}, {"telegram_id":None,"username":"unknown","online_at":"2026-10-04T10:00:00Z"}]
    result=unique_customer_presence(rows,customers)
    assert len(result)==2
    assert result[0]["username"]=="lte1"
    assert result[1]["username"]=="main3"
