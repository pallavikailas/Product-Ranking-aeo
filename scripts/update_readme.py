"""Replace the static Streamlit badge in README.md with a live shields.io badge."""

import re
import sys

from scripts.badge_status import APP_URL, get_app_status, get_badge_url

README_PATH = "README.md"

# Matches the existing Open in Streamlit badge line
_STREAMLIT_BADGE_RE = re.compile(
    r"\[!\[Open in Streamlit\]\(https://static\.streamlit\.io/badges/[^)]+\)\]\([^)]+\)"
)


def update_readme() -> int:
    try:
        with open(README_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        status = get_app_status(APP_URL)
        badge_url = get_badge_url(status)
        new_badge = f"[![App Status]({badge_url})]({APP_URL})"

        updated, count = _STREAMLIT_BADGE_RE.subn(new_badge, content)
        if count == 0:
            print("No Streamlit badge found in README.md", file=sys.stderr)
            return 1

        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(updated)

        print(f"Updated README.md badge to status: {status}")
        return 0
    except Exception as exc:
        print(f"Error updating README.md: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(update_readme())
