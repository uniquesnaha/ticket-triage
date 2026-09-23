"""Versioned prompt templates, stored as TOML files next to this module.

Prompts are data, not code: they are reviewed as plain-text diffs, carry an explicit
version, and are fingerprinted so every result records the exact text that produced it.
Switching prompts (for an A/B test or an eval) is a settings change (``TRIAGE_PROMPT``),
not a code change.
"""

from __future__ import annotations

import hashlib
import re
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent

_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
_NAME = re.compile(r"^[a-z0-9_-]+$")
# Single braces are template variables in LangChain f-string templates.
_VARIABLE = re.compile(r"(?<!\{)\{([a-z_]+)\}(?!\})")


class PromptError(ValueError):
    """A prompt file is missing or malformed."""


@dataclass(frozen=True)
class PromptTemplate:
    name: str
    version: str
    description: str
    system: str
    human: str

    @property
    def fingerprint(self) -> str:
        """Short content hash; changes whenever the prompt text changes."""
        digest = hashlib.sha256(f"{self.system}\x00{self.human}".encode()).hexdigest()
        return digest[:12]

    @property
    def ref(self) -> str:
        """Identifier recorded on every result, e.g. ``triage@1.0.0#3f2a9c1b7d4e``."""
        return f"{self.name}@{self.version}#{self.fingerprint}"


def _require_str(table: dict[str, object], key: str, where: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PromptError(f"{where}: '{key}' must be a non-empty string")
    return value


@lru_cache
def load_prompt(name: str, required_variables: frozenset[str] = frozenset()) -> PromptTemplate:
    """Load and validate ``<name>.toml``. Cached: prompt files are read once per process."""
    if not _NAME.match(name):
        raise PromptError(f"Invalid prompt name: {name!r}")
    path = PROMPTS_DIR / f"{name}.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PromptError(f"Prompt file not found: {path.name}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise PromptError(f"{path.name}: invalid TOML ({exc})") from exc

    meta, prompt = data.get("meta"), data.get("prompt")
    if not isinstance(meta, dict) or not isinstance(prompt, dict):
        raise PromptError(f"{path.name}: needs [meta] and [prompt] tables")

    template = PromptTemplate(
        name=_require_str(meta, "name", path.name),
        version=_require_str(meta, "version", path.name),
        description=_require_str(meta, "description", path.name),
        system=_require_str(prompt, "system", path.name),
        human=_require_str(prompt, "human", path.name),
    )
    if template.name != name:
        raise PromptError(f"{path.name}: meta.name is {template.name!r}, expected {name!r}")
    if not _SEMVER.match(template.version):
        raise PromptError(f"{path.name}: version must be MAJOR.MINOR.PATCH")
    if _VARIABLE.search(template.system):
        raise PromptError(f"{path.name}: system prompt must not contain template variables")
    found = set(_VARIABLE.findall(template.human))
    if missing := required_variables - found:
        raise PromptError(f"{path.name}: human template is missing {sorted(missing)}")
    if extra := found - required_variables:
        raise PromptError(f"{path.name}: human template has unknown variables {sorted(extra)}")
    return template
