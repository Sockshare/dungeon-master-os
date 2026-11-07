"""Configuration and LLM provider settings for Dungeon Master OS."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    custom = os.environ.get("DMOS_DATA_DIR", "").strip()
    p = Path(custom) if custom else (PROJECT_ROOT / "data")
    p.mkdir(parents=True, exist_ok=True)
    return p


def campaigns_dir() -> Path:
    p = data_dir() / "campaigns"
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_path() -> Path:
    return data_dir() / "settings.json"


def display_path(p: Path) -> str:
    """Return a clean relative path string so absolute system paths are never exposed."""
    try:
        rel = p.resolve().relative_to(PROJECT_ROOT.resolve())
        return f"./{rel.as_posix()}"
    except Exception:
        return f"./data/{p.name}"


class DMOSSettings(BaseModel):
    provider: Literal["auto", "offline", "ollama", "openai", "anthropic"] = Field(default="auto")
    ollama_url: str = Field(default="http://127.0.0.1:11434")
    ollama_model: str = Field(default="llama3.2:latest")
    openai_base_url: str = Field(default="https://api.openai.com/v1")
    openai_model: str = Field(default="gpt-4o-mini")
    openai_api_key: str = Field(default="")
    anthropic_model: str = Field(default="claude-3-5-haiku-latest")
    anthropic_api_key: str = Field(default="")
    default_dice_mode: Literal["normal", "adv", "dis"] = Field(default="normal")
    auto_roll_checks: bool = Field(default=True)
    sound_enabled: bool = Field(default=True)
    fog_of_war_enabled: bool = Field(default=True)

    def effective_provider(self) -> str:
        env_prov = os.environ.get("DMOS_PROVIDER", "").strip().lower()
        if env_prov in ("offline", "ollama", "openai", "anthropic"):
            return env_prov
        if self.provider != "auto":
            return self.provider
        if self.openai_api_key or os.environ.get("OPENAI_API_KEY"):
            return "openai"
        if self.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY"):
            return "anthropic"
        return "offline"

    def effective_model(self) -> str:
        eff = self.effective_provider()
        if eff == "ollama":
            return self.ollama_model
        if eff == "openai":
            return self.openai_model
        if eff == "anthropic":
            return self.anthropic_model
        return "dmos-procedural-gm-v1"

    def public_dict(self) -> dict:
        return {
            "provider": self.provider,
            "effective_provider": self.effective_provider(),
            "effective_model": self.effective_model(),
            "ollama_url": self.ollama_url,
            "ollama_model": self.ollama_model,
            "openai_base_url": self.openai_base_url,
            "openai_model": self.openai_model,
            "has_openai_key": bool(self.openai_api_key or os.environ.get("OPENAI_API_KEY")),
            "anthropic_model": self.anthropic_model,
            "has_anthropic_key": bool(self.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")),
            "default_dice_mode": self.default_dice_mode,
            "auto_roll_checks": self.auto_roll_checks,
            "sound_enabled": self.sound_enabled,
            "fog_of_war_enabled": self.fog_of_war_enabled,
            "data_dir": display_path(data_dir()),
            "settings_file": display_path(config_path()),
        }


def load_settings() -> DMOSSettings:
    path = config_path()
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return DMOSSettings(**raw)
        except Exception:
            pass
    return DMOSSettings()


def save_settings(settings: DMOSSettings) -> DMOSSettings:
    path = config_path()
    path.write_text(json.dumps(settings.model_dump(), indent=2), encoding="utf-8")
    return settings
