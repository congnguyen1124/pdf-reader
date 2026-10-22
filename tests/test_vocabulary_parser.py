from linguapdf.domain.vocabulary_parser import parse_vocabulary


def test_parse_multiple_delimiters() -> None:
    cards, errors = parse_vocabulary(
        "remarkable\tđáng chú ý\nsustainable;bền vững\neventually,cuối cùng\n"
    )

    assert errors == []
    assert cards == [
        ("remarkable", "đáng chú ý"),
        ("sustainable", "bền vững"),
        ("eventually", "cuối cùng"),
    ]


def test_parse_vietnamese_first_and_reports_bad_rows() -> None:
    cards, errors = parse_vocabulary("cân nhắc|take into account\nthiếu cột", english_first=False)

    assert cards == [("take into account", "cân nhắc")]
    assert errors == ["Dòng 2: cần đúng 2 cột"]

