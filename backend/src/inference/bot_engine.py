import json
import os
import joblib
from groq import Groq
from dotenv import load_dotenv

from src.inference.semantic_rag import semantic_search, build_index
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
    "informatique": ["informatique", "ia", "intelligence artificielle", "data science", "machine learning", "cybersecurite", "reseaux", "programmation", "developpement", "web", "mobile", "cloud"],
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


def get_intent(text, threshold=0.75):
    if not model_pipeline:
        return None
    cleaned = clean_text(text)
    scores = model_pipeline.decision_function([cleaned])[0]
    s = scores - scores.min()
    if s.max() > 0:
        s /= s.max()
    idx = s.argmax()
    return model_pipeline.classes_[idx] if s[idx] >= threshold else None


def detect_objectif(text):
    for objectif, keywords in OBJECTIFS.items():
        if any(kw in text for kw in keywords):
            return objectif
    return None


def get_context(query, profile_data=None, top_k=5):
    results = semantic_search(query, top_k=top_k * 2)
    if not results:
        return []
    if profile_data and profile_data.get("bac"):
        scored = recommend_schools(profile_data, results, top_k=top_k)
        return [r["school"] for r in scored]
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
    query = f"{text} {profile.data.get('objectif') or ''}".strip()
    context = get_context(query, profile.data)

    print(f"rag: '{query}' → {[r.get('School_Name') for r in context[:3]]}")

    # build system prompt
    system = f"""
Tu es "Ssi Lprof", conseiller d'orientation marocain expert, bienveillant et honnête.

━━━━━━━━━━━━━━━━━━━━━━━━
PROFIL DE L'ÉLÈVE:
- Bac     : {profile.data.get('bac') or 'Non précisé'}
- Moyenne : {profile.data.get('moyenne') or 'Non précisée'}
- Objectif: {profile.data.get('objectif') or 'Non précisé'}

━━━━━━━━━━━━━━━━━━━━━━━━
DONNÉES RAG:
{json.dumps(context, ensure_ascii=False, indent=2)}

━━━━━━━━━━━━━━━━━━━━━━━━
RÈGLES:
1. Utilise UNIQUEMENT les données RAG ci-dessus — jamais d'invention.
2. École demandée → compare moyenne vs seuil → ACCESSIBLE / LIMITE / DIFFICILE / INCOMPATIBLE (si CPGE requis).
3. Bourse demandée → conditions + étapes + site officiel.
4. Question simple (suffisant? chance? site?) → 2-3 lignes directes, pas de structure.
5. Recommandation générale → liste avec // et explication courte.
6. Si info absente du RAG → "Je n'ai pas cette info, consulte le site officiel."
7. Ne jamais mélanger bourses et écoles dans le même classement.
8. Langue: Français. Ton: grand frère marocain chaleureux.
9. Ne JAMAIS afficher les champs techniques bruts (interests, Descreptions).
10. Le bac scientifique regroupe les filières SM, PC et SVT.
11. Conclusion courte: "Tawakel 3la Allah 💪"
"""

    reply = ask_groq([
        {"role": "system", "content": system},
        {"role": "user",   "content": text}
    ])

    return {"reply": reply, "profile": profile.data, "debug_scores": context}


# local test
if __name__ == "__main__":
    session = StudentProfile()
    print("ssi lprof ready")
    while True:
        msg = input("you: ")
        if msg in ["exit", "quit"]:
            break
        res = bot_engine(msg, session)
        print(f"\nbot: {res['reply']}")
        print(f"profile: {res['profile']}")
        print("-" * 40)