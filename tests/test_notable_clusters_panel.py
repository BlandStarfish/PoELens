"""Tests for Passive Tree Notable Cluster Reference data and panel logic."""

import json
import os
import pytest

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "notable_clusters.json")


@pytest.fixture(scope="module")
def data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def clusters(data):
    return data["clusters"]


# ── Data integrity ──────────────────────────────────────────────────────────────

def test_data_file_exists():
    assert os.path.exists(DATA_PATH)


def test_has_required_top_level_keys(data):
    for key in ("clusters", "how_it_works", "tips", "categories"):
        assert key in data, f"Missing top-level key: {key}"


def test_clusters_non_empty(clusters):
    assert len(clusters) >= 12, f"Expected at least 12 clusters, got {len(clusters)}"


def test_all_clusters_have_required_fields(clusters):
    required = ("name", "category", "notables", "effect", "build_types", "notes")
    for cluster in clusters:
        for field in required:
            assert field in cluster, f"Cluster '{cluster.get('name')}' missing field: {field}"


def test_cluster_names_unique(clusters):
    names = [c["name"] for c in clusters]
    assert len(names) == len(set(names)), "Duplicate cluster names found"


def test_valid_categories(clusters, data):
    valid = set(data.get("categories", []))
    for cluster in clusters:
        assert cluster["category"] in valid, \
            f"Cluster '{cluster['name']}' has invalid category: '{cluster['category']}'"


def test_effect_non_empty(clusters):
    for cluster in clusters:
        assert cluster["effect"].strip(), \
            f"Cluster '{cluster['name']}' has empty effect"


def test_notables_list_non_empty(clusters):
    for cluster in clusters:
        assert len(cluster["notables"]) >= 1, \
            f"Cluster '{cluster['name']}' has empty notables list"


def test_build_types_non_empty(clusters):
    for cluster in clusters:
        assert len(cluster["build_types"]) >= 1, \
            f"Cluster '{cluster['name']}' has empty build_types list"


# ── Category coverage ───────────────────────────────────────────────────────────

def test_has_offense_clusters(clusters):
    off = [c for c in clusters if c["category"] == "Offense"]
    assert len(off) >= 2, f"Expected at least 2 Offense clusters, got {len(off)}"


def test_has_defense_clusters(clusters):
    def_ = [c for c in clusters if c["category"] == "Defense"]
    assert len(def_) >= 2, f"Expected at least 2 Defense clusters, got {len(def_)}"


def test_has_keystone_clusters(clusters):
    ks = [c for c in clusters if c["category"] == "Keystones"]
    assert len(ks) >= 4, f"Expected at least 4 Keystone clusters, got {len(ks)}"


# ── Key clusters present ────────────────────────────────────────────────────────

def test_key_keystones_present(clusters):
    names = {c["name"] for c in clusters}
    expected = {"Resolute Technique", "Chaos Inoculation", "Vaal Pact", "Acrobatics + Phase Acrobatics"}
    for name in expected:
        assert name in names, f"Expected cluster '{name}' not found"


def test_chaos_inoculation_effect(clusters):
    by_name = {c["name"]: c for c in clusters}
    ci = by_name.get("Chaos Inoculation")
    assert ci is not None
    assert "1" in ci["effect"] or "immune" in ci["effect"].lower(), \
        "Chaos Inoculation effect should mention life = 1 or chaos immunity"


# ── Search logic (data-level) ───────────────────────────────────────────────────

def _matches(cluster: dict, query: str) -> bool:
    """Mirror of panel search logic for data-level testing."""
    if not query:
        return True
    searchable = " ".join([
        cluster.get("name", ""),
        cluster.get("category", ""),
        cluster.get("location", ""),
        " ".join(cluster.get("notables", [])),
        cluster.get("effect", ""),
        " ".join(cluster.get("build_types", [])),
        cluster.get("point_cost", ""),
        cluster.get("notes", ""),
    ]).lower()
    return query in searchable


def test_panel_module_importable():
    """Verify the panel module can be imported without a QApplication."""
    import importlib
    mod = importlib.import_module("ui.widgets.notable_clusters_panel")
    assert hasattr(mod, "NotableClustersPanel")


def test_search_matches_name(clusters):
    results = [c for c in clusters if _matches(c, "vaal pact")]
    assert len(results) > 0


def test_search_matches_effect(clusters):
    results = [c for c in clusters if _matches(c, "leech")]
    assert len(results) > 0


def test_search_matches_build_type(clusters):
    results = [c for c in clusters if _matches(c, "occultist")]
    assert len(results) > 0


def test_search_empty_returns_all(clusters):
    results = [c for c in clusters if _matches(c, "")]
    assert len(results) == len(clusters)


def test_search_no_match(clusters):
    results = [c for c in clusters if _matches(c, "xyzxyzxyz_no_match")]
    assert len(results) == 0


def test_filter_keystones(clusters):
    keystones = [c for c in clusters if c["category"] == "Keystones"]
    assert all(c["category"] == "Keystones" for c in keystones)


def test_tips_non_empty(data):
    tips = data.get("tips", [])
    assert len(tips) >= 2, "Expected at least 2 tips"


def test_how_it_works_non_empty(data):
    how = data.get("how_it_works", "")
    assert how.strip(), "how_it_works should not be empty"
