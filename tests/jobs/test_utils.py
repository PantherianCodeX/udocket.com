from apps.platform.jobs.utils import unique_title


def test_unique_title_first_available():
    assert unique_title("Transcript", []) == "Transcript"


def test_unique_title_when_exists_without_suffix():
    existing = ["Transcript"]
    assert unique_title("Transcript", existing) == "Transcript(1)"


def test_unique_title_takes_highest_suffix():
    existing = ["Transcript", "Transcript(1)", "Transcript(4)"]
    assert unique_title("Transcript", existing) == "Transcript(5)"


def test_unique_title_preserves_other_titles():
    existing = ["Summary", "Transcript(2)"]
    assert unique_title("Transcript", existing) == "Transcript"
