"""Geography resolution service (Phase 19 Data Foundation).

Maps NSS / PLFS / DGT / PMKVY spellings to canonical Local Government Directory (LGD)
codes for states and districts. Unmatched names are rejected and logged to
data/processed/geo_rejects.csv. NEVER GUESS (DATA ADDENDUM Rules 3 & 6).
"""
from __future__ import annotations

import csv
import pathlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PROCESSED_DIR = REPO_ROOT / "backend" / "app" / "data" / "processed"
GEO_REJECTS_FILE = PROCESSED_DIR / "geo_rejects.csv"

# Canonical State List: (lgd_state_code, canonical_name, aliases)
CANONICAL_STATES: list[tuple[int, str, list[str]]] = [
    (1, "Jammu and Kashmir", ["jammu & kashmir", "j&k", "jammu and kashmir", "jk"]),
    (2, "Himachal Pradesh", ["himachal pradesh", "hp", "himachal"]),
    (3, "Punjab", ["punjab", "pb"]),
    (4, "Chandigarh", ["chandigarh", "ch"]),
    (5, "Uttarakhand", ["uttarakhand", "uttaranchal", "uk"]),
    (6, "Haryana", ["haryana", "hr"]),
    (
        7,
        "Delhi",
        ["delhi", "nct of delhi", "national capital territory of delhi", "new delhi", "dl"],
    ),
    (8, "Rajasthan", ["rajasthan", "rj", "raj"]),
    (9, "Uttar Pradesh", ["uttar pradesh", "up", "u.p."]),
    (10, "Bihar", ["bihar", "br"]),
    (11, "Sikkim", ["sikkim", "sk"]),
    (12, "Arunachal Pradesh", ["arunachal pradesh", "ar"]),
    (13, "Nagaland", ["nagaland", "nl"]),
    (14, "Manipur", ["manipur", "mn"]),
    (15, "Mizoram", ["mizoram", "mz"]),
    (16, "Tripura", ["tripura", "tr"]),
    (17, "Meghalaya", ["meghalaya", "ml"]),
    (18, "Assam", ["assam", "as"]),
    (19, "West Bengal", ["west bengal", "wb", "paschim banga", "bengal"]),
    (20, "Jharkhand", ["jharkhand", "jh"]),
    (21, "Odisha", ["odisha", "orissa", "or", "od"]),
    (22, "Chhattisgarh", ["chhattisgarh", "chattisgarh", "cg"]),
    (23, "Madhya Pradesh", ["madhya pradesh", "mp", "m.p."]),
    (24, "Gujarat", ["gujarat", "gj"]),
    (25, "Daman and Diu", ["daman and diu", "daman & diu", "dd"]),
    (26, "Dadra and Nagar Haveli and Daman and Diu", ["dadra and nagar haveli", "dnh", "dnhdd"]),
    (27, "Maharashtra", ["maharashtra", "mh", "maha"]),
    (28, "Andhra Pradesh", ["andhra pradesh", "ap", "a.p."]),
    (29, "Karnataka", ["karnataka", "ka"]),
    (30, "Goa", ["goa", "ga"]),
    (31, "Lakshadweep", ["lakshadweep", "ld"]),
    (32, "Kerala", ["kerala", "kl"]),
    (33, "Tamil Nadu", ["tamil nadu", "tn", "tamilnadu"]),
    (34, "Puducherry", ["puducherry", "pondicherry", "py"]),
    (35, "Andaman and Nicobar Islands", ["andaman and nicobar", "andaman & nicobar islands", "an"]),
    (36, "Telangana", ["telangana", "ts", "tg"]),
    (37, "Ladakh", ["ladakh", "la"]),
]

# Canonical Districts: (lgd_state_code, lgd_district_code, canonical_name, aliases)
CANONICAL_DISTRICTS: list[tuple[int, int, str, list[str]]] = [
    # Uttar Pradesh (9)
    (9, 198, "Varanasi", ["varanasi", "benaras", "benares", "kashi"]),
    (9, 178, "Lucknow", ["lucknow", "lko"]),
    (9, 164, "Kanpur Nagar", ["kanpur nagar", "kanpur", "cawnpore", "kanpur city"]),
    (9, 175, "Prayagraj", ["prayagraj", "allahabad", "prayag", "prayagraj (allahabad)"]),
    (9, 156, "Gorakhpur", ["gorakhpur", "gkp"]),
    (9, 128, "Agra", ["agra"]),
    (9, 181, "Meerut", ["meerut"]),
    (9, 139, "Bareilly", ["bareilly"]),
    (9, 129, "Aligarh", ["aligarh"]),
    (9, 153, "Ghaziabad", ["ghaziabad"]),
    # Maharashtra (27)
    (27, 479, "Mumbai", ["mumbai", "bombay", "mumbai city"]),
    (27, 480, "Mumbai Suburban", ["mumbai suburban", "bombay suburban"]),
    (27, 492, "Pune", ["pune", "poona"]),
    (27, 489, "Nagpur", ["nagpur"]),
    (27, 497, "Thane", ["thane"]),
    (27, 490, "Nashik", ["nashik", "nasik"]),
    (27, 466, "Aurangabad", ["aurangabad", "chhatrapati sambhajinagar", "sambhajinagar"]),
    # Rajasthan (8)
    (8, 104, "Jaipur", ["jaipur"]),
    (8, 106, "Jodhpur", ["jodhpur"]),
    (8, 108, "Kota", ["kota"]),
    (8, 118, "Udaipur", ["udaipur"]),
    (8, 97, "Ajmer", ["ajmer"]),
    (8, 100, "Bikaner", ["bikaner"]),
    (8, 98, "Alwar", ["alwar"]),
    # Bihar (10)
    (10, 216, "Patna", ["patna"]),
    (10, 211, "Gaya", ["gaya"]),
    (10, 215, "Muzaffarpur", ["muzaffarpur"]),
    (10, 207, "Bhagalpur", ["bhagalpur"]),
    (10, 209, "Darbhanga", ["darbhanga"]),
    (10, 217, "Purnia", ["purnia", "purnea"]),
    # Madhya Pradesh (23)
    (23, 418, "Bhopal", ["bhopal"]),
    (23, 426, "Indore", ["indore"]),
    (23, 427, "Jabalpur", ["jabalpur"]),
    (23, 423, "Gwalior", ["gwalior"]),
    (23, 435, "Ujjain", ["ujjain"]),
    # Delhi (7)
    (7, 90, "Central Delhi", ["central delhi", "central", "delhi", "new delhi"]),
    (7, 91, "North Delhi", ["north delhi", "north"]),
    (7, 95, "South Delhi", ["south delhi", "south"]),
    (7, 96, "West Delhi", ["west delhi", "west"]),
    (7, 92, "East Delhi", ["east delhi", "east"]),
    # Karnataka (29)
    (29, 529, "Bengaluru Urban", ["bengaluru urban", "bangalore", "bangalore urban", "bengaluru"]),
    (29, 545, "Mysuru", ["mysuru", "mysore"]),
    (29, 536, "Dharwad", ["dharwad", "hubli", "hubballi", "hubli-dharwad"]),
    (29, 528, "Belagavi", ["belagavi", "belgaum"]),
    (29, 535, "Dakshina Kannada", ["dakshina kannada", "mangalore", "mangaluru"]),
    # Tamil Nadu (33)
    (33, 565, "Chennai", ["chennai", "madras"]),
    (33, 566, "Coimbatore", ["coimbatore", "kovai"]),
    (33, 574, "Madurai", ["madurai"]),
    (33, 589, "Tiruchirappalli", ["tiruchirappalli", "trichy", "tiruchi"]),
    (33, 582, "Salem", ["salem"]),
    # Gujarat (24)
    (24, 438, "Ahmedabad", ["ahmedabad", "ahmadabad"]),
    (24, 452, "Surat", ["surat"]),
    (24, 455, "Vadodara", ["vadodara", "baroda"]),
    (24, 449, "Rajkot", ["rajkot"]),
    # West Bengal (19)
    (19, 314, "Kolkata", ["kolkata", "calcutta"]),
    (19, 312, "Howrah", ["howrah"]),
    (19, 318, "North 24 Parganas", ["north 24 parganas", "24 parganas north"]),
    (19, 320, "South 24 Parganas", ["south 24 parganas", "24 parganas south"]),
    # Odisha (21)
    (21, 367, "Khordha", ["khordha", "khurda", "bhubaneswar"]),
    (21, 357, "Cuttack", ["cuttack"]),
    (21, 374, "Sundargarh", ["sundargarh", "sundergarh", "rourkela"]),
    # Haryana (6)
    (6, 81, "Gurugram", ["gurugram", "gurgaon"]),
    (6, 79, "Faridabad", ["faridabad"]),
    (6, 86, "Panipat", ["panipat"]),
    (6, 74, "Ambala", ["ambala"]),
    # Punjab (3)
    (3, 42, "Ludhiana", ["ludhiana"]),
    (3, 27, "Amritsar", ["amritsar"]),
    (3, 38, "Jalandhar", ["jalandhar"]),
    # Telangana (36)
    (36, 643, "Hyderabad", ["hyderabad", "hyd"]),
    (36, 651, "Rangareddy", ["rangareddy", "ranga reddy"]),
    (36, 654, "Warangal Urban", ["warangal urban", "warangal", "hanumakonda"]),
    # Andhra Pradesh (28)
    (28, 510, "Visakhapatnam", ["visakhapatnam", "vizag"]),
    (28, 506, "Krishna", ["krishna", "vijayawada"]),
    (28, 504, "Guntur", ["guntur"]),
    # Kerala (32)
    (32, 562, "Thiruvananthapuram", ["thiruvananthapuram", "trivandrum"]),
    (32, 555, "Ernakulam", ["ernakulam", "kochi", "cochin"]),
    (32, 559, "Kozhikode", ["kozhikode", "calicut"]),
    # Assam (18)
    (18, 290, "Kamrup Metropolitan", ["kamrup metropolitan", "kamrup metro", "guwahati"]),
    # Jharkhand (20)
    (20, 345, "Ranchi", ["ranchi"]),
    (20, 339, "East Singhbhum", ["east singhbhum", "jamshedpur"]),
    (20, 338, "Dhanbad", ["dhanbad"]),
    # Chhattisgarh (22)
    (22, 395, "Raipur", ["raipur"]),
    (22, 391, "Durg", ["durg", "bhilai"]),
    (22, 386, "Bilaspur", ["bilaspur"]),
]


@dataclass(frozen=True)
class ResolvedGeo:
    state_code: int
    state_name: str
    district_code: int | None
    district_name: str | None


def _normalize(name: str) -> str:
    """Normalize text: lowercase, remove punctuation and extra spaces."""
    name = name.lower().strip()
    name = re.sub(r"[\(\)\[\],.\-_/]", " ", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def lookup_state(state_input: str) -> tuple[int, str] | None:
    """Resolve raw state string to (lgd_state_code, canonical_name) or None."""
    if not state_input or not state_input.strip():
        return None
    norm = _normalize(state_input)

    for code, canonical, aliases in CANONICAL_STATES:
        if norm == _normalize(canonical) or any(norm == _normalize(a) for a in aliases):
            return code, canonical
    return None


def lookup_district(state_code: int, district_input: str) -> tuple[int, str] | None:
    """Resolve raw district string within a state to (lgd_district_code, canonical_name) or None."""
    if not district_input or not district_input.strip():
        return None
    norm = _normalize(district_input)

    # Clean off common survey noise words: e.g. "district", "city"
    stripped = re.sub(r"\b(district|dist|city)\b", "", norm).strip()
    stripped = re.sub(r"\s+", " ", stripped)

    for s_code, d_code, canonical, aliases in CANONICAL_DISTRICTS:
        if s_code != state_code:
            continue
        canon_norm = _normalize(canonical)
        if norm == canon_norm or stripped == canon_norm:
            return d_code, canonical
        for a in aliases:
            a_norm = _normalize(a)
            if norm == a_norm or stripped == a_norm:
                return d_code, canonical

    return None


def record_geo_reject(state_raw: str, district_raw: str | None, reason: str) -> None:
    """Append unmatched geographical inputs to geo_rejects.csv (DATA ADDENDUM Rule 1)."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    write_header = not GEO_REJECTS_FILE.exists()
    with GEO_REJECTS_FILE.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if write_header:
            writer.writerow(["timestamp", "state_raw", "district_raw", "reason"])
        writer.writerow([
            datetime.now(UTC).isoformat(),
            state_raw,
            district_raw or "",
            reason,
        ])


def resolve_geo(state: str, district: str | None = None) -> ResolvedGeo | None:
    """Resolve state and district to canonical LGD entities.

    Never guesses. Unmatched inputs are logged to geo_rejects.csv and return None.
    """
    state_res = lookup_state(state)
    if not state_res:
        record_geo_reject(state, district, f"Unrecognized state: '{state}'")
        return None

    state_code, state_name = state_res

    if not district or not district.strip():
        return ResolvedGeo(
            state_code=state_code,
            state_name=state_name,
            district_code=None,
            district_name=None,
        )

    dist_res = lookup_district(state_code, district)
    if not dist_res:
        record_geo_reject(
            state,
            district,
            f"Unrecognized district: '{district}' in state '{state_name}'",
        )
        return None

    dist_code, dist_name = dist_res
    return ResolvedGeo(
        state_code=state_code,
        state_name=state_name,
        district_code=dist_code,
        district_name=dist_name,
    )


def seed_canonical_geo(session: Any) -> tuple[int, int]:
    """Seed the database geo and geo_aliases tables with canonical LGD data."""
    from app.models.geo import Geo, GeoAlias

    # Check existing count
    existing_geo = session.query(Geo).count()
    if existing_geo > 0:
        return existing_geo, session.query(GeoAlias).count()

    geo_count = 0
    alias_count = 0

    # 1. State aliases
    for s_code, s_name, s_aliases in CANONICAL_STATES:
        session.add(GeoAlias(alias=s_name, code=s_code, kind="state"))
        alias_count += 1
        for a in s_aliases:
            if _normalize(a) != _normalize(s_name):
                session.add(GeoAlias(alias=a, code=s_code, kind="state"))
                alias_count += 1

    # 2. Districts and aliases
    for s_code, d_code, d_name, d_aliases in CANONICAL_DISTRICTS:
        s_entry = next((s for s in CANONICAL_STATES if s[0] == s_code), None)
        state_name = s_entry[1] if s_entry else f"State_{s_code}"
        session.add(Geo(
            lgd_state_code=s_code,
            lgd_district_code=d_code,
            state=state_name,
            district=d_name,
        ))
        geo_count += 1

        session.add(GeoAlias(alias=d_name, code=d_code, kind="district"))
        alias_count += 1
        for a in d_aliases:
            if _normalize(a) != _normalize(d_name):
                session.add(GeoAlias(alias=a, code=d_code, kind="district"))
                alias_count += 1

    session.commit()
    return geo_count, alias_count
