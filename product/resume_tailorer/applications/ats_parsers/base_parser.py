"""Abstract base class for ATS form parsers.

All supported platforms (Greenhouse, Lever, Ashby) share the same generic
HTML form-extraction logic, implemented once here via `_extract_fields()`.
Platform-specific subclasses exist to name themselves correctly and as an
extension point for future platform-specific refinements — the shared
logic is sufficient for this MVP because these three platforms use
conventional HTML form markup (input/select/textarea with name attributes).
"""

from abc import ABC, abstractmethod
from typing import List

from bs4 import BeautifulSoup

from resume_tailorer.applications.models import ATSCapability, FormField

# Input types we never treat as a user-fillable field.
_IGNORED_INPUT_TYPES = {"hidden", "submit", "button", "image", "reset"}

# Maps an HTML <input type="..."> value to our FormField.field_type vocabulary.
_INPUT_TYPE_MAP = {
    "text": "text",
    "email": "email",
    "tel": "phone",
    "date": "date",
    "checkbox": "checkbox",
    "file": "file",
}


class BaseATSParser(ABC):
    """Abstract interface every ATS parser must implement."""

    @abstractmethod
    def get_platform_name(self) -> str:
        """Return the lowercase platform identifier, e.g. 'greenhouse'."""
        raise NotImplementedError

    @abstractmethod
    def is_supported(self) -> bool:
        """Whether this platform's forms can actually be parsed from static HTML.

        Kept for backward compatibility with existing callers/tests.
        get_capability() (spec 003 Step 21) is the richer, authoritative
        source of truth going forward -- it can express "manual works but
        real submission doesn't," which a single bool cannot.
        """
        raise NotImplementedError

    @abstractmethod
    def get_capability(self) -> ATSCapability:
        """Declare what this platform's integration can actually do."""
        raise NotImplementedError

    @abstractmethod
    def parse_form(self, form_html: str) -> List[FormField]:
        """Extract fillable fields from a job application form's HTML."""
        raise NotImplementedError

    def _extract_fields(self, form_html: str) -> List[FormField]:
        """Shared generic extraction logic used by all supported subclasses.

        Finds <input>, <select>, and <textarea> elements with a `name`
        attribute, skips non-fillable input types (hidden/submit/etc.),
        and maps each to a FormField with its type and required flag.
        Fields always start unfilled (value="", prefilled=False) — filling
        is the FormFiller's job (Task 3), not the parser's.
        """
        if not form_html or not form_html.strip():
            return []

        soup = BeautifulSoup(form_html, "html.parser")
        fields: List[FormField] = []

        for input_tag in soup.find_all("input"):
            name = input_tag.get("name")
            if not name:
                continue
            input_type = (input_tag.get("type") or "text").lower()
            if input_type in _IGNORED_INPUT_TYPES:
                continue
            field_type = _INPUT_TYPE_MAP.get(input_type, "text")
            fields.append(FormField(
                field_name=name,
                field_type=field_type,
                required=input_tag.has_attr("required"),
                label=_label_for(input_tag, soup),
            ))

        for select_tag in soup.find_all("select"):
            name = select_tag.get("name")
            if not name:
                continue
            fields.append(FormField(
                field_name=name,
                field_type="select",
                required=select_tag.has_attr("required"),
                label=_label_for(select_tag, soup),
            ))

        for textarea_tag in soup.find_all("textarea"):
            name = textarea_tag.get("name")
            if not name:
                continue
            fields.append(FormField(
                field_name=name,
                field_type="textarea",
                required=textarea_tag.has_attr("required"),
                label=_label_for(textarea_tag, soup),
            ))

        return fields


def _label_for(tag, soup) -> str:
    """The visible question for a form control: its <label>, aria-label, or placeholder."""
    label = None
    if tag.get("id"):
        label = soup.find("label", attrs={"for": tag["id"]})
    if label is None:
        label = tag.find_parent("label")
    text = label.get_text(" ", strip=True) if label is not None else ""
    return " ".join((text or tag.get("aria-label") or tag.get("placeholder") or "").split())
