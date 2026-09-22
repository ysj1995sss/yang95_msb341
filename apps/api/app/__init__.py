"""
Puts the existing product/resume_tailorer engine (parsers, analyzers,
tailorer, PDF generation, candidate fit scoring) on sys.path so this API
can import it as `resume_tailorer` without duplicating or vendoring it.
That engine is the more complete implementation in this repo -- this
package is a thin multi-user API surface (auth, persistence, an HTTP
contract) around it, modeled on job-copilot's FastAPI backend.
"""

import sys
from pathlib import Path

_PRODUCT_ROOT = Path(__file__).resolve().parents[3] / "product"
if str(_PRODUCT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PRODUCT_ROOT))
