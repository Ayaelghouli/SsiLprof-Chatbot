import json
import os
import joblib
from groq import Groq
from dotenv import load_dotenv
import re 

from src.inference.semantic_rag import semantic_search, build_index, metadata
import src.inference.semantic_rag as rag_module
from src.profiling.profile_engine import StudentProfile, extract_info_from_text
from src.utils.text_cleaner import clean_text
from src.scoring.scoring_engine import recommend_schools


# config
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
data_path = os.path.join(base_dir, "data", "data_complet.json")
pipeline_path = os.path.join(base_dir, "models", "intent_pipeline.pkl")


# load model
try:
    model_pipeline = joblib.load(pipeline_path)
except Exception as e:
    model_pipeline = None
    print(f"warning: ML model not loaded — {e}")


# load knowledge base
with open(data_path, "r", encoding="utf-8") as f:
    knowledge_base = json.load(f)

build_index(knowledge_base)


# objectif keywords
OBJECTIFS = {
    "medecine":     ["medecine", "médecine", "docteur", "pharmacie", "dentaire", "infirmier", "paramedical", "kinesitherapie", "sage femme"],
    "ingenierie":   ["ingenierie", "ingénierie", "ingenieur", "ingénieur", "genie civil", "génie civil", "genie electrique", "genie mecanique", "genie industriel", "electronique", "telecommunications"],
    "informatique": ["informatique", "ia", "intelligence artificielle", "data science", "machine learning", "cybersecurite", "reseaux", "programmation", "developpement", "mobile", "cloud"],
    "commerce":     ["commerce", "management", "marketing", "gestion", "vente", "entrepreneuriat", "business"],
    "finance":      ["finance", "banque", "comptabilite", "audit", "assurance"],
    "droit":        ["droit", "juridique", "avocat", "sciences politiques"],
    "architecture": ["architecture", "urbanisme"],
    "design":       ["design", "art", "graphisme", "cinema", "photographie", "animation"],
    "agriculture":  ["agriculture", "agronomie", "veterinaire", "agro"],
    "tourisme":     ["tourisme", "hotellerie"],
    "sport":        ["sport", "entraîneur", "coach"],
    "militaire":    ["militaire", "armee", "armée", "defense", "police"],
    "bourse":       ["bourse", "bourses", "minhaty", "jidara", "onousc", "logement", "aide financiere", "aides financieres", "minah"],
}


def get_intent(text):
    if not model_pipeline:
        return None
    try:
        cleaned = clean_text(text)
        dec = model_pipeline.decision_function([cleaned])[0]
        s = dec - dec.min()
        if s.max() > 0:
            s /= s.max()
        idx = s.argmax()
        return model_pipeline.classes_[idx] if s[idx] > 0.75 else None
    except:
        return None


def detect_objectif(lower_text):
    for obj, keywords in OBJECTIFS.items():
        if any(kw in lower_text for kw in keywords):
            return obj
    return None


def get_context(query, profile_data=None, top_k=5):
    results = semantic_search(query, top_k=top_k * 2)
    if not results:
        return []
    COMMON_WORDS = {"EST", "ENA", "IMA"}
    query_upper = re.sub(r"['\u2019\u2018\-]", " ", query.upper())
    pinned = []
    for school in rag_module.metadata:
        name = school.get("School_Name", "").upper().strip()
        if not name:
            continue
        if name in COMMON_WORDS:
            if not re.search(r'(?:SUR|À|A|L |DE L |ENTRE)\s+' + re.escape(name) + r'\b', query_upper):
                continue
        if re.search(r'\b' + re.escape(name) + r'\b', query_upper):
            if school not in pinned:
                pinned.append(school)
            if school in results:
                results.remove(school)
    def mention_pos(school):
        name = school.get("School_Name", "").upper().strip()
        m = re.search(r'\b' + re.escape(name) + r'\b', query_upper)
        return m.start() if m else 999
    pinned.sort(key=mention_pos)
    results = pinned + [r for r in results if r not in pinned]
    if profile_data and profile_data.get("bac"):
        scored = recommend_schools(profile_data, results, top_k=top_k)
        for r in scored:
            r["school"]["compatibilite"] = min(100, max(0, r["score"]))
        final = [r["school"] for r in scored]
        for p in reversed(pinned):
            if p in final:
                final.remove(p)
            final.insert(0, p)
        return final[:top_k]

    return results[:top_k]

def ask_groq(messages, model="llama-3.3-70b-versatile", max_tokens=500):
    res = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.1,
        max_tokens=max_tokens
    )
    return res.choices[0].message.content


def bot_engine(user_text: str, profile: StudentProfile):
    text = user_text.strip()
    lower = text.lower()

    # welcome message
    if text == "__start__":
        return {
            "reply": (
                "Bonjour 👋 Je suis **Ssi Lprof**, ton conseiller d'orientation.\n\n"
                "1️⃣ **Orientation Scolaire** — Trouver l'école selon ton profil\n"
                "2️⃣ **Bourses & Logement** — Aides financières et cité universitaire\n\n"
                "Tape **1** ou **2**, ou dis-moi directement 😊"
            ),
            "profile": profile.data
        }
    # FIX 1: "2" → menu bourses مباشرة بدون ما يسول bac
    if text.strip() == "2":
        return {
            "reply": (
                "Tu cherches des infos sur les aides étudiantes 😊\n\n"
                "Voici ce qui est disponible au Maroc :\n\n"
                "1️⃣ **Minhaty** — Bourse sociale nationale (via RSU)\n"
                "2️⃣ **Jidara** — Bourse excellence + ordinateur + mentor\n"
                "3️⃣ **ONOUSC** — Logement en cité universitaire\n"
                "4️⃣ **Entraide Nationale** — Aide pour situations précaires\n"
                "5️⃣ **Bourse FM6** — Pour enfants du personnel enseignant\n\n"
                "Sur laquelle tu veux plus de détails ? 💬"
            ),
            "profile": profile.data
        }

    # intent detection
    tag = get_intent(text)
    print(f"intent: {tag}")

    if tag == "remerciement":
        return {"reply": "Avec plaisir 😊 Bon courage pour tes études !", "profile": profile.data}

    if tag == "fin_conversation":
        return {"reply": "Au revoir 👋 Bonne chance pour ton parcours !", "profile": profile.data}

    # update profile from message
    new_data = extract_info_from_text(lower)

    objectif = detect_objectif(lower)
    if objectif:
        new_data["objectif"] = objectif

    if new_data and any(new_data.values()):
        profile.update_profile(new_data)

    # ask for missing info before going to RAG
    missing = profile.get_missing_question()
    if missing:
        return {"reply": missing, "profile": profile.data}

    # build query and retrieve context
    if tag in ["question_details", "orientation_ecoles"]:
        query = text
    else:
        query = f"{text} {profile.data.get('objectif') or ''}".strip()
    context = get_context(query, profile.data)

    print(f"rag: '{query}' → {[r.get('School_Name') for r in context[:3]]}")

    # build system prompt
    system = f"""
Tu es **Ssi Lprof**, conseiller d'orientation marocain — expert, bienveillant, honnête.
Tu parles comme un grand frère marocain : chaleureux, direct, jamais condescendant.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 PROFIL DE L'ÉLÈVE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Bac     : {profile.data.get('bac') or 'Non précisé'}
- Moyenne : {profile.data.get('moyenne') or 'Non précisée'}
- Objectif: {profile.data.get('objectif') or 'Non précisé'}

⚠️ Bac scientifique = SM, PC ou SVT (traite-les comme équivalents sauf si seuil spécifique).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 DONNÉES RAG (source unique autorisée)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{json.dumps(context, ensure_ascii=False, indent=2)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📐 FORMAT DE RÉPONSE SELON LE TYPE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[TYPE A] RECOMMANDATION D'ÉCOLES
→ Pour CHAQUE école dans le RAG, affiche EXACTEMENT ce bloc :

🎓 **NomÉcole** (Ville)
   ├─ Seuil requis : X.X | Ta moyenne : {profile.data.get('moyenne') or '?'} → ✅ ACCESSIBLE / ⚠️ LIMITE / ❌ DIFFICILE / 🚫 INCOMPATIBLE
   ├─ Compatibilité : XX%
   ├─ Filières : [liste courte]
   └─ Pourquoi : [1 phrase max, en lien avec l'objectif de l'élève]

Règle accessibilité :
  ✅ ACCESSIBLE   → moyenne ≥ seuil + 0.5
  ⚠️ LIMITE       → seuil - 0.5 ≤ moyenne < seuil + 0.5
  ❌ DIFFICILE    → moyenne < seuil - 0.5
  🚫 INCOMPATIBLE → bac non accepté par l'école

[TYPE B] INFORMATION SUR UNE ÉCOLE SPÉCIFIQUE
→ Présente les infos clés : seuil, filières, ville, site.
→ Compare moyenne vs seuil avec le label accessibilité ci-dessus.
→ 4-6 lignes max. Pas de liste à puces inutiles.

[TYPE C] BOURSE / AIDE FINANCIÈRE
→ NE JAMAIS afficher seuil, compatibilité ou classement d'écoles.
→ Structure obligatoire :
   💰 **Nom de la bourse**
   - Qui peut en bénéficier : ...
   - Conditions : ...
   - Comment postuler : ...
   - Site officiel : ...

[TYPE D] QUESTION SIMPLE (suffisant ? chance ? délai ?)
→ 2-3 lignes directes. Pas de structure, pas de liste.
→ Exemple : "Avec 14.2 en SM, ENSA est limite — tente ta chance, les dossiers comptent aussi 💪"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ RÈGLES ABSOLUES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. SOURCE   → Utilise UNIQUEMENT les données RAG. Zéro invention.
2. MÉLANGE  → Ne jamais mélanger écoles et bourses dans un même classement.
3. CHAMPS   → Ne jamais afficher : interests, Descreptions, _id, score brut, embeddings.
4. ABSENCE  → Info absente du RAG → "Je n'ai pas cette info, consulte le site officiel."
5. LANGUE   → Français uniquement. Quelques mots darija sont OK si naturels.
6. LONGUEUR → Réponse courte si question simple. Complète si recommandation.
7. CONCLUSION → Termine toujours par : "Tawakel 3la Allah 💪"
"""

    reply = ask_groq([
        {"role": "system", "content": system},
        {"role": "user",   "content": text}
    ])

    return {"reply": reply, "profile": profile.data, "debug_scores": context}