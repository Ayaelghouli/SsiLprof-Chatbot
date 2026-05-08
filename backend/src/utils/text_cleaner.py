import re

def clean_text(t):
    t = t.lower().strip()
    t = re.sub(r"[^\w\s\-àáâãäåèéêëìíîïòóôõöùúûüýçñ]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t