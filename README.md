# Ssi Lprof — Assistant d'Orientation Scolaire

Chatbot intelligent d'orientation pour les lycéens marocains. Il analyse le profil de l'élève (bac, moyenne, objectif) et recommande des établissements adaptés ou informe sur les bourses et aides sociales.

---

## Architecture

```
SsilProf_Chatbot/
├── backend/
│   ├── data/
│   │   ├── intents.json          # patterns d'entraînement
│   │   └── data_complet.json     # base de connaissance (écoles + bourses)
│   ├── models/
│   │   └── intent_pipeline.pkl   # modèle ML entraîné
│   ├── src/
│   │   ├── inference/
│   │   │   ├── bot_engine.py     # logique principale du chatbot
│   │   │   └── semantic_rag.py   # recherche hybride FAISS + BM25
│   │   ├── profiling/
│   │   │   └── profile_engine.py # extraction et gestion du profil élève
│   │   ├── scoring/
│   │   │   └── scoring_engine.py # scoring et recommandation d'écoles
│   │   └── utils/
│   │       └── text_cleaner.py   # nettoyage du texte
│   ├── server.py                 # API FastAPI
│   └── database.py               # connexion MongoDB
├── frontend/
│   ├── css/style.css
│   ├── js/script.js
│   └── index.html
├── tests/
├── requirements.txt
└── .env
```

---

## Stack technique

| Composant | Technologie |
|---|---|
| API backend | FastAPI + Uvicorn |
| Classification d'intentions | LinearSVC + TF-IDF (scikit-learn) |
| Recherche sémantique | FAISS + sentence-transformers |
| Recherche par mots-clés | BM25 (rank-bm25) |
| Génération de réponses | Groq API (LLaMA 3.3 70B) |
| Base de données | MongoDB |
| Authentification | bcrypt + sessions token |
| Frontend | HTML / CSS / JavaScript |

---

## Pipeline ML

Le module de classification d'intentions utilise un pipeline scikit-learn combinant deux représentations TF-IDF :

- **char_wb** (n-grammes de caractères, 2–5) : robuste aux fautes d'orthographe
- **word** (n-grammes de mots, 1–3) : capture le sens général

Le classifieur **LinearSVC** avec `class_weight="balanced"` gère les classes déséquilibrées.

L'augmentation de données par synonymes est appliquée **uniquement sur le train set** pour éviter le data leakage.

---

## Recherche hybride (RAG)

La recherche dans la base de connaissance combine deux approches :

```
score_final = 0.65 × score_sémantique (FAISS) + 0.35 × score_lexical (BM25)
```

- **FAISS** : similarité cosinus sur embeddings multilingues (`paraphrase-multilingual-MiniLM-L12-v2`)
- **BM25** : correspondance exacte de mots-clés

---

## Installation

```bash
git clone https://github.com/votre-repo/ssilprof-chatbot.git
cd ssilprof-chatbot/backend

python -m venv env
env\Scripts\activate        # Windows
# source env/bin/activate   # Linux/Mac

pip install -r requirements.txt
```

Créer le fichier `.env` :

```
GROQ_API_KEY=votre_cle_groq
MONGODB_URI=votre_uri_mongodb
```

---

## Entraînement du modèle

```bash
python -m src.training.train_intent
```

---

## Lancement

```bash
python server.py
```

L'application sera disponible sur `http://127.0.0.1:8000`

---

## Fonctionnalités

- Détection d'intention par ML (10 classes, 92% accuracy)
- Extraction automatique du profil élève (bac, moyenne, objectif)
- Recommandation d'écoles avec scoring selon l'éligibilité et l'adéquation
- Recherche hybride dans la base de connaissance
- Informations sur les bourses et aides sociales (Minhaty, Jidara, ONOUSC)
- Authentification sécurisée avec sessions
- Historique des conversations en base de données

---

## Projet de Fin d'Études — 2025/2026