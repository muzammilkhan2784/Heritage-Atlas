import pytest

from heritage.validation import InvalidSearch, parse_search


@pytest.mark.parametrize(
    "params",
    [
        {"lat": "NaN", "lon": "0", "radius": "1"},
        {"lat": "0", "lon": "Infinity", "radius": "1"},
        {"lat": "91", "lon": "0", "radius": "1"},
        {"lat": "0", "lon": "-181", "radius": "1"},
        {"lat": "0", "lon": "0", "radius": "0"},
        {"lat": "0", "lon": "0", "radius": "20001"},
        {"lat": "0"},
        {"lat": "bad", "lon": "0", "radius": "1"},
        {"page": "0"},
        {"page": "1001"},
        {"page": "a"},
        {"per_page": "49"},
        {"language": "$ne"},
        {"category": "bad"},
        {"q": "a" * 121},
    ],
)
def test_reject_invalid_search(params):
    with pytest.raises(InvalidSearch):
        parse_search(params)


def test_accept_zero_coordinates_and_preserve_filters():
    search = parse_search(
        {"lat": "0", "lon": "0", "radius": "1", "q": "  temple ", "language": "Hindi"}
    )
    assert search.lat == 0
    assert search.params()["lon"] == 0
    assert search.q == "temple"
    assert search.language == "Hindi"
