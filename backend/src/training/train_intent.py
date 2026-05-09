import json
import joblib
from pathlib import Path
from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.metrics import classification_report

from src.utils.text_cleaner import clean_text


root = Path(__file__).resolve().parents[2]
data_intent = root / "data"
models_dir = root / "models"
models_dir.mkdir(exist_ok=True)


with open(data_intent / "intents.json", encoding="utf-8") as f:
    data = json.load(f)

texts = []
labels = []
for intent in data["intents"]:
    for p in intent["patterns"]:
        texts.append(clean_text(p))
        labels.append(intent["tag"])

print("samples:", len(texts), "classes:", len(set(labels)))


# split before augmentation — test data stays clean

X_train, X_test, y_train, y_test = train_test_split(
    texts, labels,
    test_size=0.2,
    stratify=labels,
    random_state=42
)


# augmentation on train only
synonyms = {
    "ecole":       ["institut", "etablissement", "centre de formation"],
    "bourse":      ["aide financiere", "financement", "subvention"],
    "bonjour":     ["salut", "hello", "bonsoir"],
    "je veux":     ["j'aimerais", "je souhaite", "je cherche"],
    "comment":     ["de quelle facon", "comment est-ce que"],
    "maroc":       ["marocain", "au maroc"],
    "conditions":  ["criteres", "exigences"],
    "filiere":     ["specialite", "domaine"],
    "moyenne":     ["note", "resultat", "score"],
    "details":     ["informations"],
    "obtenir":     ["avoir", "recevoir"],
    "inscription": ["candidature", "dossier"],
}

X_train_aug = list(X_train)
y_train_aug = list(y_train)

for text, label in zip(X_train, y_train):
    for word, variants in synonyms.items():
        if word in text:
            for v in variants:
                X_train_aug.append(text.replace(word, v))
                y_train_aug.append(label)

print("after augmentation:", len(X_train_aug))
print(dict(Counter(y_train_aug)))


model = Pipeline([
    ("features", FeatureUnion([
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5))),
        ("word", TfidfVectorizer(analyzer="word",    ngram_range=(1, 3))),
    ])),
    ("clf", LinearSVC(class_weight="balanced"))
])


cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(model, X_train_aug, y_train_aug, cv=cv, scoring="accuracy")
print("CV accuracy:", scores.mean(), "+/-", scores.std())


model.fit(X_train_aug, y_train_aug)

pred = model.predict(X_test)
print("\nclassification report:")
print(classification_report(y_test, pred))


def predict_intent(text):
    return model.predict([clean_text(text)])[0]


print("\n--- tests ---")
tests = [
    "Peux-tu me donner plus de détails sur l'ENSA ?",
    "au revoir merci",
    "je veux une bourse",
    "bonjour",
    "je suis en bac PC avec 15 de moyenne",
]
for t in tests:
    print(f"  {t!r} => {predict_intent(t)}")


joblib.dump(model, models_dir / "intent_pipeline.pkl")
print("\nmodel saved in:", models_dir)