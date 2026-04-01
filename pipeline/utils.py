#!/usr/bin/env python3
from typing import TypedDict


class CarVariant(TypedDict):
  make: str
  model: str
  model_original: str
  index_key: str
  variant_info: str | None
  years: list[int]
  package_requirements: str
  package_key_used: str | None
  match_confidence: str | None
  matching_keywords: list[str] | None
  support_level: dict


def normalize_for_matching(text: str) -> str:
  text = text.lower().strip()
  text = text.replace(",", "").replace("-", " ").replace("_", " ")
  return " ".join(text.split())


def build_index_key(make: str, model: str) -> str:
  normalized_make = normalize_for_matching(make)
  normalized_model = normalize_for_matching(model)
  return f"{normalized_make}_{normalized_model}".replace(" ", "_")
