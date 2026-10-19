"""zhaw — Zero-Hallucination Academic Workflow.

A thin, stable CLI over the executable quality gates that live in
``.agents/skills/``. The gates themselves stay plain scripts (easy to read,
easy to audit, no framework); this package only gives them one discoverable
entry point and one exit-code contract.
"""

__version__ = "0.2.0"

from ._paths import repo_root, script, skills_dir  # noqa: F401

__all__ = ["__version__", "repo_root", "skills_dir", "script"]
