import re


class StudentProfile:
    def __init__(self):
        self.data = {
            "moyenne":  None,
            "bac":      None,
            "interets": [],
            "objectif": None,
            "intent":   None  # 'orientation' or 'bourse'
        }

    def update_profile(self, new_data: dict):
        for key in self.data:
            if key in new_data and new_data[key]:
                if isinstance(self.data[key], list):
                    existing = set(self.data[key])
                    new_items = new_data[key] if isinstance(new_data[key], list) else [new_data[key]]
                    self.data[key] = list(existing | set(new_items))
                else:
                    self.data[key] = new_data[key]

    def get_missing_question(self):
        # bourse intent — no need to ask for moyenne or objectif
        if self.data["intent"] == "bourse":
            return None
        if self.data["objectif"]:
            if not self.data["bac"]:
                return "Pour personnaliser ma recommandation, quel est ton type de bac ? (SM, PC, SVT, technique...)"
            if not self.data["moyenne"]:
                return "Et quelle est ta moyenne générale ?"
            return None
        # orientation intent — need all three
        if not self.data["bac"]:
            return "Pour t'orienter, j'ai besoin de savoir : quel est ton type de bac ? (SM, PC, SVT, économie, lettres ou technique...)"
        if self.data["bac"] == "SCIENTIFIQUE":
            self.data["bac"] = None  # reset pour forcer la question
            return "Tu as un bac scientifique, mais lequel exactement ? \n\n• **SM** (Sciences Maths) \n• **PC** (Physique-Chimie) \n• **SVT** (Sciences de la Vie) \n• **STE/STM** (Technique)"

        if not self.data["moyenne"]:
            return "Quelle est ta moyenne générale ?"

        if not self.data["objectif"]:
            return "Quel domaine t'intéresse le plus ? (Médecine, Ingénierie, Commerce...)"

        return None


BAC_MAP = [
    (r"sciences?\s*maths?|s\.?\s*maths?|\bsm\b|math[eé]matiques?",                                          "SM"),
    (r"sciences?\s*physiques?|physique[\s\-]*chimie|\bpc\b|\bsp\b|chimie[\s\-]*physique",                    "PC"),
    (r"sciences?\s*(?:de\s*la\s*)?(?:vie|vivant|terre)|svt\b|bio(?:logie)?|sciences?\s*nat",                 "SVT"),
    (r"\bste\b|\bstm\b|sciences?\s*(?:et\s*)?tech(?:nologies?|nique)?|[eé]lec|m[eé]ca|g[eé]nie|industriel", "STE"),
    (r"[eé]conomie|[eé]co(?:nomiques?)?|\bsgc\b|gestion|comptab|sciences?\s*[eé]co|commerce|management",    "ECO"),
    (r"lettres?|humanit[eé]s?|philosophie|sciences?\s*humaines?|histoire|litt[eé]rature?",                   "LETTRES"),
    (r"bac\s*sci(?:entifique)?|scientifique",                                                                 "SCIENTIFIQUE"),
]

OBJECTIF_MAP = [
    (r"info(?:rmatique)?|cod(?:e|ing)|d[eé]v(?:elop)?|programmation|logiciel|cyber|r[eé]seau", "informatique"),
    (r"\bia\b|intelligence\s*artificielle|machine\s*learning|data",                              "ia"),
    (r"m[eé]decine|docteur|m[eé]dical|chirurgi",                                                "medecine"),
    (r"pharmacie",                                                                               "pharmacie"),
    (r"infirmi[eè]r|soin|param[eé]dical|sage.?femme",                                          "paramedical"),
    (r"ing[eé]ni(?:eur|erie)|\binge\b",                                                         "ingenierie"),
    (r"commerce|marketing|vente|business|management",                                            "commerce"),
    (r"finance|banque|comptabilit[eé]|audit",                                                   "finance"),
    (r"architecture|archi",                                                                      "architecture"),
    (r"agriculture|agronomie|v[eé]t[eé]rinaire",                                               "agriculture"),
    (r"droit|juriste|avocat",                                                                   "droit"),
    (r"militaire|arm[eé]e|gendarm|police",                                                      "militaire"),
    (r"journalisme|m[eé]dia|presse|communication",                                              "communication"),
    (r"sport|coach|kinesith",                                                                   "sport"),
    (r"art\b|design|cin[eé]ma|th[eé][aâ]tre",                                                 "arts"),
    (r"bourse|minhaty|jidara|logement|cit[eé]\s*uni",                                          "social"),
]

GRADE_PATTERNS = [
    r'\b(1[0-9]|[89])[.,](\d{1,2})\b',
    r'\b(1[0-9]|[89])\s*/\s*20\b',
    r'(?:moyenne|note|avec|j.?ai)\s+(1[0-9]|[89])\b',
    r'\b(1[0-9])\s+(?:de\s+)?moyenne\b',
    r'bac\s+\w+\s+(1[0-9]|[89])\b',
    r'(?:^|\s)(1[0-9])\b',
]
SCHOOL_NAMES = {
    "ensa", "encg", "ensam", "inpt", "enim", "insea", "iscae",
    "fmp", "cpge", "bts", "est", "ofppt", "iav", "aiac", "cmc",
    "fst", "fsjes", "flsh", "hem", "ima", "isic", "ifmia", "irfc",
    "isadac", "inas", "isitt", "apesa", "erssm", "epc", "imm",
    "ismac", "ispits", "ena", "ista", "ista", "onousc"
}


def extract_info_from_text(user_input: str, client=None) -> dict:
    # client param kept for compatibility with bot_engine.py but not used
    text = user_input.lower().strip()
    result = {"moyenne": None, "bac": None, "objectif": None, "interets": [], "intent": None}


    # detect bac type
    for pattern, bac_type in BAC_MAP:
        if re.search(pattern, text, re.IGNORECASE):
            result["bac"] = bac_type
            break

    # detect moyenne
    for pattern in GRADE_PATTERNS:
        m = re.search(pattern, text)
        if m:
            try:
                g = m.groups()
                val = float(f"{g[0]}.{g[1]}") if len(g) == 2 and g[1] and g[1].isdigit() else float(g[0])
                if 8 <= val <= 20:
                    result["moyenne"] = val
                    break
            except (ValueError, IndexError):
                pass

    # detect objectif and interests
    for pattern, objectif in OBJECTIF_MAP:
        if re.search(pattern, text, re.IGNORECASE):
            if result["objectif"] is None:
                result["objectif"] = objectif
            if objectif not in result["interets"]:
                result["interets"].append(objectif)

    result["interets"] = result["interets"][:5]
    if re.search(r"bourse|minhaty|jidara|logement|aide|social", text):
        result["intent"] = "bourse"
    elif result.get("objectif") or result.get("bac") or result.get("moyenne"):
        result["intent"] = "orientation"
    elif any(f" {s} " in f" {text} " for s in SCHOOL_NAMES):
        result["intent"] = "orientation"
    return result


def build_profile(user_input: str = "") -> dict:
    student = StudentProfile()
    student.update_profile(extract_info_from_text(user_input))
    return student.data

if __name__ == "__main__":
    tests = [
        ("je veux une bourse", "bourse"),
        ("minhaty comment s'inscrire", "bourse"),
        ("je veux faire médecine", "orientation"),
        ("différence entre ENSA et ENCG", "orientation"),
        ("bac PC 15 de moyenne", "orientation"),
        ("je suis perdu", None),
    ]
    for text, expected in tests:
        result = extract_info_from_text(text.lower())
        intent = result.get("intent")
        status = "✅" if intent == expected else "❌"
        print(f"{status} '{text}' → {intent} (expected: {expected})")