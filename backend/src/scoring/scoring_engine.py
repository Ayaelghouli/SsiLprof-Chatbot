import re


# seuil patterns per bac type
BAC_SEUIL_PATTERNS = {
    "SM":      [r"sciences?\s*maths?\s*[AB]?\s*:\s*([\d.]+)",
                r"\bsm\s*:\s*([\d.]+)",
                r"s\.maths?\s*[AB]?\s*:\s*([\d.]+)"],

    "PC":      [r"\bpc\s*(?:/\s*svt)?\s*:\s*([\d.]+)",
                r"physique[\s\-]*chimie\s*:\s*([\d.]+)"],

    "SVT":     [r"\bsvt\s*(?:/\s*pro)?\s*:\s*([\d.]+)",
                r"sciences?\s*vie\s*:\s*([\d.]+)",
                r"pc\s*/\s*svt\s*:\s*([\d.]+)"],

    "STE":     [r"\bste\s*(?:/\s*stm)?\s*:\s*([\d.]+)",
                r"technique\s*:\s*([\d.]+)",
                r"bac\.?\s*pro\s*:\s*([\d.]+)"],

    "STM":     [r"\bstm\s*(?:/\s*ste)?\s*:\s*([\d.]+)",
                r"technique\s*:\s*([\d.]+)"],

    "ECO":     [r"[eé]conomie\s*:\s*([\d.]+)",
                r"\beco\s*(?:\s*et\s*sgc)?\s*:\s*([\d.]+)",
                r"\bsgc\s*:\s*([\d.]+)"],

    "LETTRES": [r"lettres?\s*:\s*([\d.]+)",
                r"litt[eé]raire\s*:\s*([\d.]+)"],
}

# objectif to school keywords mapping
OBJECTIF_KEYWORDS = {
    "informatique":  ["informatique", "info", "numerique", "digital", "systemes", "reseaux", "logiciel", "cyber"],
    "ia":            ["intelligence artificielle", "ia", "machine learning", "data", "big data", "apprentissage"],
    "medecine":      ["medecine", "sante", "medical", "chirurgie", "docteur"],
    "pharmacie":     ["pharmacie", "medicament"],
    "paramedical":   ["infirmier", "soin", "paramedical", "kinesitherapie", "sage-femme"],
    "ingenierie":    ["ingenierie", "genie", "mecanique", "electrique", "civil", "industriel", "electronique"],
    "commerce":      ["commerce", "business", "marketing", "vente", "management", "entrepreneuriat"],
    "finance":       ["finance", "banque", "comptabilite", "audit", "bourse"],
    "architecture":  ["architecture", "urbanisme", "design espace"],
    "agriculture":   ["agriculture", "agronomie", "veterinaire", "agro"],
    "droit":         ["droit", "juridique", "loi", "justice"],
    "militaire":     ["militaire", "armee", "defense", "securite", "gendarmerie"],
    "communication": ["communication", "journalisme", "medias", "presse"],
    "sport":         ["sport", "activite physique", "coach"],
    "arts":          ["art", "design", "cinema", "theatre", "creation"],
}

# schools that require CPGE — not accessible directly after bac
CNC_KEYWORDS = ["Accès impossible directement", "Bac+2 minimum", "CPGE"]


def extract_seuil(seuil_text: str, bac: str) -> float:
    # try bac-specific patterns first
    patterns = BAC_SEUIL_PATTERNS.get(bac.upper(), [rf"\b{bac}\s*:\s*([\d.]+)"])
    for pattern in patterns:
        m = re.search(pattern, seuil_text, re.IGNORECASE)
        if m:
            return float(m.group(1).replace(",", "."))

    # fallback: first xx.xx number in text
    nums = re.findall(r'\b(\d{2}\.\d{2})\b', seuil_text)
    if nums:
        return float(nums[0])

    # fallback: "très sélectif" or "> 16"
    if re.search(r"tr[eè]s\s+s[eé]lectif|>\s*1[678]", seuil_text, re.IGNORECASE):
        return 16.5

    return 12.0  # universal default


def match_objectif(objectif: str, school: dict) -> int:
    # returns 0-3 based on how well the school matches the objectif
    if not objectif:
        return 0

    keywords = OBJECTIF_KEYWORDS.get(objectif.lower(), [objectif.lower()])

    school_text = " ".join([
        school.get("Filieres", ""),
        school.get("Filiéres", ""),
        school.get("Careers", ""),
        school.get("interests", ""),
        school.get("category", ""),
    ]).lower()

    matches = sum(1 for kw in keywords if kw in school_text)
    return min(matches, 3)


def score_ecole(profile: dict, school: dict) -> int:
    moyenne    = float(profile.get("moyenne") or 0)
    bac        = str(profile.get("bac") or "").upper()
    objectif   = str(profile.get("objectif") or "")
    seuil_text = str(school.get("Seuils", ""))
    score      = 0

    # eligibility
    if any(kw in seuil_text for kw in CNC_KEYWORDS):
        score -= 50
    else:
        seuil = extract_seuil(seuil_text, bac)
        marge = moyenne - seuil
        if marge >= 0:
            score += 50
            score += min(int(marge * 3), 10)
        elif marge >= -1:
            score += 20

    # objectif match — plus de poids
    obj_score = match_objectif(objectif, school) * 20  # 20 au lieu de 10
    score += obj_score

    # NOUVEAU : pénalité si 0 match objectif
    if objectif and match_objectif(objectif, school) == 0:
        score -= 40  # pénalise fortement les écoles hors domaine

    return max(score, 0)

def recommend_schools(profile: dict, schools: list, top_k: int = 3) -> list:
    results = []

    for school in schools:
        obj_match = match_objectif(profile.get("objectif", ""), school)
        if profile.get("objectif") and obj_match == 0:
            continue
        bac     = str(profile.get("bac") or "").upper()
        moyenne = float(profile.get("moyenne") or 0)
        seuil   = extract_seuil(str(school.get("Seuils", "")), bac)

        results.append({
            "school":   school,
            "score":    score_ecole(profile, school),
            "eligible": moyenne >= seuil,
            "seuil":    seuil,
            "marge":    round(moyenne - seuil, 2),
        })

    # eligible first, then by score, then by margin
    results.sort(
        key=lambda x: (
            not x["eligible"],
            -x["score"],
            -x["marge"]
        )
    )
    for r in results:
        print(r["school"].get("Nom"), r["score"])
    return results[:top_k]