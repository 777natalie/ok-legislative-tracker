from update_bills import find_changed_bills


def bill(bill_id, change_hash):
    return {"bill_id": bill_id, "change_hash": change_hash}


def test_unchanged_bill_is_skipped():
    assert find_changed_bills([bill(1, "aaa")], {1: "aaa"}) == []


def test_changed_hash_is_fetched():
    assert find_changed_bills([bill(1, "bbb")], {1: "aaa"}) == [bill(1, "bbb")]


def test_new_bill_is_fetched():
    assert find_changed_bills([bill(2, "ccc")], {}) == [bill(2, "ccc")]


def test_sorted_by_bill_id():
    master = [bill(30, "x"), bill(10, "y"), bill(20, "z")]
    assert [b["bill_id"] for b in find_changed_bills(master, {})] == [10, 20, 30]
