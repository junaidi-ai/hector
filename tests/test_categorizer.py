from hector.categorizer import categorize_repository


def test_categorize_repository_keyword_match():
    name = "awesome-telemedicine-platform"
    desc = "A modern AI diagnostics and telemedicine toolkit."
    cats = ["AI Diagnostics", "Telemedicine", "Health Data"]
    matched = categorize_repository(name, desc, cats)
    assert "Telemedicine" in matched
    assert "AI Diagnostics" in matched


def test_categorize_repository_no_match():
    matched = categorize_repository("repo", "some description", ["Oncology"])
    assert matched == []
