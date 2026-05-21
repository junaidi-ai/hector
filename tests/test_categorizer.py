from hector.categorizer import (
    _is_healthcare_relevant,
    _phrase_in_text,
    categorize_repository,
)

# Task 10: Comprehensive categorizer tests


# Subtask 1: Known-good healthcare repos → correctly categorized
def test_categorize_healthcare_ehr_system():
    """EHR system should be categorized as EHR & Clinical Systems."""
    name = "awesome-ehr"
    desc = "Open source electronic health record system"
    cats = ["EHR & Clinical Systems", "Telemedicine"]
    matched = categorize_repository(name, desc, cats)
    assert "EHR & Clinical Systems" in matched


def test_categorize_healthcare_telemedicine():
    """Telemedicine platform should be categorized correctly."""
    name = "telehealth-platform"
    desc = "Remote patient consultation and telehealth services"
    cats = ["Telemedicine", "EHR & Clinical Systems"]
    matched = categorize_repository(name, desc, cats)
    assert "Telemedicine" in matched


def test_categorize_healthcare_imaging():
    """DICOM and medical imaging tools → Imaging & Radiology."""
    name = "dicom-viewer"
    desc = "Medical image analysis using DICOM and radiomics"
    cats = ["Imaging & Radiology", "AI Diagnostics"]
    matched = categorize_repository(name, desc, cats)
    assert "Imaging & Radiology" in matched


def test_categorize_healthcare_ai_diagnostics():
    """AI diagnostics tools should be categorized correctly."""
    name = "clinical-decision-support"
    desc = "Machine learning model for clinical diagnosis support"
    cats = ["AI Diagnostics", "EHR & Clinical Systems"]
    matched = categorize_repository(name, desc, cats)
    assert "AI Diagnostics" in matched


# Subtask 2: ROS2/robotics repos → Uncategorized (not misclassified)
def test_categorize_ros2_robotics_excluded():
    """ROS2 robotics repos should be Uncategorized, not misclassified."""
    name = "ros2-manipulation"
    desc = "ROS2 robot manipulation package for industrial robots"
    cats = ["AI Diagnostics", "Robotics & Surgical Systems", "Telemedicine"]
    matched = categorize_repository(name, desc, cats)
    # Should be empty, not misclassified
    assert matched == []


def test_categorize_autonomous_driving_excluded():
    """Autonomous driving should be excluded, not categorized."""
    name = "autonomous-nav"
    desc = "Autonomous driving navigation stack for self-driving cars"
    cats = ["AI Diagnostics", "Robotics & Surgical Systems"]
    matched = categorize_repository(name, desc, cats)
    assert matched == []


# Subtask 3: arxiv paper tracker → Uncategorized
def test_categorize_arxiv_papers_excluded():
    """ArXiv paper trackers should be Uncategorized."""
    name = "arxiv-paper-tracker"
    desc = "An awesome list of papers on machine learning from arXiv"
    cats = ["AI Diagnostics", "Data Platforms & ETL"]
    matched = categorize_repository(name, desc, cats)
    assert matched == []


# Subtask 4: DICOM/PACS tool → Imaging & Radiology
def test_categorize_pacs_system():
    """PACS system should be in Imaging & Radiology."""
    name = "dicom-pacs"
    desc = "Picture Archiving and Communication System (PACS) for medical imaging"
    cats = ["Imaging & Radiology", "EHR & Clinical Systems"]
    matched = categorize_repository(name, desc, cats)
    assert "Imaging & Radiology" in matched


# Subtask 5: _phrase_in_text boundary conditions
def test_phrase_in_text_short_token():
    """Short tokens should match with word boundaries."""
    # "ai" should not match "scare" or "chain"
    assert _phrase_in_text("ai", "scare ai care")
    assert not _phrase_in_text("ai", "chain")


def test_phrase_in_text_multiword_phrase():
    """Multi-word phrases should match as complete phrases."""
    # "clinical nlp" should match as a phrase
    assert _phrase_in_text("clinical nlp", "Uses clinical nlp for notes")
    # But should not match if split
    assert not _phrase_in_text("clinical nlp", "clinical text and nlp")


def test_phrase_in_text_case_insensitive():
    """Phrase matching should be case-insensitive."""
    assert _phrase_in_text("HEALTH", "healthcare system")
    assert _phrase_in_text("Health", "HEALTHCARE SYSTEM")


def test_phrase_in_text_normalized():
    """Should handle special characters in text."""
    assert _phrase_in_text("health", "health-tech tools")
    assert _phrase_in_text("clinical", "clinical, AI diagnostics")


# Subtask 6: _is_healthcare_relevant allowlist (Task 3)
def test_is_healthcare_relevant_basic():
    """Healthcare anchors should be detected."""
    assert _is_healthcare_relevant("health")
    assert _is_healthcare_relevant("medical")
    assert _is_healthcare_relevant("clinical")
    assert _is_healthcare_relevant("patient")
    assert _is_healthcare_relevant("hospital")


def test_is_healthcare_relevant_in_context():
    """Healthcare keywords in real text should be detected."""
    assert _is_healthcare_relevant("electronic health record system")
    assert _is_healthcare_relevant("clinical decision support")
    assert _is_healthcare_relevant("patient monitoring system")


def test_is_healthcare_relevant_false_positives():
    """Non-healthcare content should not match."""
    assert not _is_healthcare_relevant("care for your plants")  # "care" was removed from anchors
    assert not _is_healthcare_relevant("machine learning framework")
    assert not _is_healthcare_relevant("python web framework")


def test_is_healthcare_relevant_word_boundaries():
    """Short anchors need proper word boundaries."""
    # "care" in "scare" should not match
    assert not _is_healthcare_relevant("scare them away")
    # But standalone "care" should match... wait, we removed "care" from anchors
    # Let's test with "patient" instead
    assert _is_healthcare_relevant("patient care")


# Original basic tests
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
