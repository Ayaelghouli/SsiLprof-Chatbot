# Ssi Lprof — Assistant d'Orientation Scolaire
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![MongoDB](https://img.shields.io/badge/MongoDB-Local-brightgreen)
![Groq](https://img.shields.io/badge/LLM-Groq-orange)

Chatbot intelligent d'orientation pour les lycéens marocains. Il analyse le profil de l'élève (bac, moyenne, objectif) et recommande des établissements adaptés ou informe sur les bourses et aides sociales.

---

## Architecture

```
SsilProf_Chatbot/
├── backend/
│   ├── data/
│   │   ├── intents.json
│   │   └── data_complet.json
│   ├── models/
│   │   └── intent_pipeline.pkl
│   ├── src/
│   │   ├── inference/
│   │   │   ├── bot_engine.py
│   │   │   └── semantic_rag.py
│   │   ├── profiling/
│   │   │   └── profile_engine.py
│   │   ├── scoring/
│   │   │   └── scoring_engine.py
│   │   ├── training/
│   │   │   └── train_intent.py
│   │   └── utils/
│   │       └── text_cleaner.py
│   ├── server.py
│   ├── database.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── tests/
├── README.md
└── .gitignore
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
git clone https://github.com/Ayaelghouli/SsiLprof-Chatbot.git
cd ssilprof-chatbot/backend

python -m venv env
env\Scripts\activate        # Windows


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



------------------------------------------------------------------------------ liste des commandes niveau deploiement -----------------------------------------------------------

================================================================
   SSILPROF CHATBOT — RÉSUMÉ DU DÉPLOIEMENT SUR VM
================================================================

1. INSTALLER LES DÉPENDANCES PYTHON
--------------------------------------
sudo apt install -y python3.10 python3.10-venv python3-pip


2. CLONER LE PROJET
---------------------
cd /opt
git clone https://github.com/Ayaelghouli/SsiLprof-Chatbot.git
cd SsiLprof-Chatbot/backend


3. CRÉER L'ENVIRONNEMENT VIRTUEL ET INSTALLER LES PACKAGES
------------------------------------------------------------
python3.10 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install motor "pydantic[email]"


4. TRANSFÉRER LES FICHIERS DE DONNÉES (depuis la machine locale)
-----------------------------------------------------------------
scp backend/data/intents.json administrateur@<ip-vm>:/home/administrateur/SsiLprof-Chatbot/backend/data/
scp backend/data/data_complet.json administrateur@<ip-vm>:/home/administrateur/SsiLprof-Chatbot/backend/data/


5. ENTRAÎNER LE MODÈLE ML
---------------------------
python -m src.training.train_intent


6. INSTALLER ET DÉMARRER MONGODB
----------------------------------
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg --dearmor -o /usr/share/keyrings/mongodb.gpg
echo "deb [signed-by=/usr/share/keyrings/mongodb.gpg] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update && sudo apt install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod


7. LANCER LE SERVEUR EN ARRIÈRE-PLAN AVEC TMUX
------------------------------------------------
sudo apt install -y tmux
tmux new -s ssilprof
source env/bin/activate
python server.py
# Appuyer sur Ctrl+B puis D pour détacher


8. CONFIGURER NGINX
---------------------
sudo nano /etc/nginx/sites-available/ssilprof

--- coller cette configuration ---
server {
    listen 80;
    server_name _;

    location /static/ {
        alias /home/administrateur/SsiLprof-Chatbot/frontend/;
    }

    location / {
        root /home/administrateur/SsiLprof-Chatbot/frontend;
        index index.html;
        try_files $uri $uri/ =404;
    }

    location /chat {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /login {
        proxy_pass http://127.0.0.1:8000;
    }

    location /signup {
        proxy_pass http://127.0.0.1:8000;
    }

    location /recommendations {
        proxy_pass http://127.0.0.1:8000;
    }
}
--- fin de la configuration ---

sudo ln -s /etc/nginx/sites-available/ssilprof /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/172.16.20.58
sudo nginx -t
sudo systemctl restart nginx
sudo chmod -R 755 /home/administrateur/SsiLprof-Chatbot/


9. ACCÉDER À L'APPLICATION
----------------------------
http://172.16.20.74


================================================================
   REDÉMARRER APRÈS UN REBOOT
================================================================
sudo systemctl start mongod
tmux new -s ssilprof
cd /home/administrateur/SsiLprof-Chatbot/backend
source env/bin/activate
python server.py

================================================================
   COMMANDES UTILES
================================================================
tmux attach -t ssilprof                       # rattacher la session serveur
sudo systemctl status mongod                  # vérifier l'état de MongoDB
sudo tail -f /var/log/nginx/error.log         # consulter les erreurs Nginx
sudo systemctl restart nginx                  # redémarrer Nginx
================================================================
