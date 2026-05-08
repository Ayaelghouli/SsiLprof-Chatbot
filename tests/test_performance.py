"""
test_performance.py
====================
Script d'évaluation automatique de Ssi Lprof
Usage: python test_performance.py
"""

import sys
import os
import time
import json
from datetime import datetime

# ── path setup ──
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from src.inference.bot_engine import bot_engine
from src.profiling.profile_engine import StudentProfile

# =========================
# COULEURS TERMINAL
# =========================
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# =========================
# SCÉNARIOS DE TEST
# =========================
SCENARIOS = [

    # ─────────────────────────────────────────
    # SCÉNARIO 1 — Médecine (Bac PC, 15.0)
    # ─────────────────────────────────────────
    {
        "name": "Médecine — Bac PC 15.0",
        "description": "Élève en PC avec 15, veut faire médecine puis change vers ingénierie",
        "steps": [
            {
                "input": "__start__",
                "check": lambda r: "Ssi Lprof" in r or "orientation" in r.lower(),
                "label": "Message d'accueil"
            },
            {
                "input": "1",
                "check": lambda r: "bac" in r.lower() or "type" in r.lower(),
                "label": "Intent orientation → demande bac"
            },
            {
                "input": "PC",
                "check": lambda r: "moyenne" in r.lower(),
                "label": "Bac PC → demande moyenne"
            },
            {
                "input": "15",
                "check": lambda r: "domaine" in r.lower() or "intéresse" in r.lower(),
                "label": "Moyenne 15 → demande objectif"
            },
            {
                "input": "médecine",
                "check": lambda r: "FMP" in r or "fmp" in r.lower(),
                "label": "Objectif médecine → FMP dans réponse"
            },
            {
                "input": "parle-moi de FMP",
                "check": lambda r: "12" in r and ("médecine" in r.lower() or "pharmacie" in r.lower()),
                "label": "Fiche FMP — seuil 12.00"
            },
            {
                "input": "15 c'est suffisant pour FMP ?",
                "check": lambda r: ("accessible" in r.lower() or "✅" in r or "oui" in r.lower()) and len(r) < 600,
                "label": "Question courte → réponse courte + accessible"
            },
            {
                "input": "et ISPITS c'est quoi ?",
                "check": lambda r: "ispits" in r.lower() or "infirmier" in r.lower(),
                "label": "ISPITS détectée"
            },
            {
                "input": "j'ai une mention très bien, est-ce que je peux avoir une bourse ?",
                "check": lambda r: "jidara" in r.lower() or "Jidara" in r,
                "label": "Mention très bien → Jidara"
            },
            {
                "input": "c'est quoi Jidara exactement ?",
                "check": lambda r: "jidara" in r.lower() and ("fondation" in r.lower() or "excellence" in r.lower()),
                "label": "Détails Jidara"
            },
            {
                "input": "logement à Rabat si j'intègre FMP ?",
                "check": lambda r: "onousc" in r.lower() or "cité" in r.lower() or "logement" in r.lower(),
                "label": "Logement → ONOUSC"
            },
            {
                "input": "non en fait je veux faire ingénierie pas médecine",
                "check": lambda r: ("ensa" in r.lower() or "ingénierie" in r.lower() or "ingenierie" in r.lower()),
                "label": "Reset objectif → ingénierie"
            },
            {
                "input": "ENSA ou ENSAM laquelle choisir ?",
                "check": lambda r: "ensa" in r.lower() and "ensam" in r.lower(),
                "label": "Comparaison ENSA vs ENSAM"
            },
            {
                "input": "parle-moi de l'ENSAM",
                "check": lambda r: "ensam" in r.lower() and "mécanique" in r.lower(),
                "label": "Fiche ENSAM (pas ENSA!)"
            },
            {
                "input": "merci beaucoup",
                "check": lambda r: "plaisir" in r.lower() or "courage" in r.lower(),
                "label": "Remerciement"
            },
            {
                "input": "au revoir",
                "check": lambda r: "revoir" in r.lower() or "bonne chance" in r.lower(),
                "label": "Fin conversation"
            },
        ]
    },

    # ─────────────────────────────────────────
    # SCÉNARIO 2 — Bourses (Bac SM, 13.0)
    # ─────────────────────────────────────────
    {
        "name": "Bourses & Logement — Bac SM 13.0",
        "description": "Élève intéressé par les aides financières",
        "steps": [
            {
                "input": "__start__",
                "check": lambda r: "Ssi Lprof" in r,
                "label": "Accueil"
            },
            {
                "input": "2",
                "check": lambda r: any(kw in r.lower() for kw in ["bourse", "aide", "minhaty", "logement", "intéresse"]),
                "label": "Intent bourse"
            },
            {
                "input": "des infos sur les bourses au Maroc",
                "check": lambda r: any(kw in r.lower() for kw in ["minhaty", "jidara", "onousc"]),
                "label": "Liste des bourses"
            },
            {
                "input": "comment s'inscrire à Minhaty ?",
                "check": lambda r: "minhaty" in r.lower() and ("rsu" in r.lower() or "inscription" in r.lower()),
                "label": "Minhaty — étapes inscription"
            },
            {
                "input": "quel est le montant de la bourse ?",
                "check": lambda r: any(kw in r for kw in ["6334", "3167", "DH", "dh"]),
                "label": "Montant bourse Minhaty"
            },
            {
                "input": "j'ai besoin d'un logement étudiant",
                "check": lambda r: "onousc" in r.lower() or "cité" in r.lower(),
                "label": "Logement → ONOUSC"
            },
            {
                "input": "en fait je veux faire orientation aussi",
                "check": lambda r: any(kw in r.lower() for kw in ["bac", "type", "orientation", "école"]),
                "label": "Switch bourse → orientation"
            },
            {
                "input": "SM",
                "check": lambda r: "moyenne" in r.lower(),
                "label": "Bac SM → demande moyenne"
            },
            {
                "input": "13",
                "check": lambda r: "domaine" in r.lower() or "intéresse" in r.lower(),
                "label": "Moyenne 13 → demande objectif"
            },
            {
                "input": "informatique",
                "check": lambda r: any(kw in r.lower() for kw in ["ensa", "est", "fst", "ofppt"]),
                "label": "Objectif informatique → écoles"
            },
            {
                "input": "avec 13 en SM j'ai une chance à l'ENSA ?",
                "check": lambda r: "12" in r and ("accessible" in r.lower() or "✅" in r),
                "label": "ENSA seuil SM 12.00 → accessible"
            },
        ]
    },

    # ─────────────────────────────────────────
    # SCÉNARIO 3 — Edge Cases
    # ─────────────────────────────────────────
    {
        "name": "Edge Cases — Robustesse",
        "description": "Cas limites et questions difficiles",
        "steps": [
            {
                "input": "__start__",
                "check": lambda r: len(r) > 10,
                "label": "Start normal"
            },
            {
                "input": "blablabla xyz 123",
                "check": lambda r: len(r) > 5,  # juste pas de crash
                "label": "Texte incompréhensible — pas de crash"
            },
            {
                "input": "bac SVT",
                "check": lambda r: "moyenne" in r.lower(),
                "label": "Bac SVT reconnu"
            },
            {
                "input": "9.5",
                "check": lambda r: len(r) > 5,
                "label": "Moyenne faible — pas de crash"
            },
            {
                "input": "médecine",
                "check": lambda r: any(kw in r.lower() for kw in ["fmp", "ispits", "médecine", "seuil"]),
                "label": "Objectif médecine avec moyenne faible"
            },
            {
                "input": "site web de ENSA",
                "check": lambda r: "ensa-maroc" in r.lower() or "cursussup" in r.lower() or "http" in r.lower(),
                "label": "Site web ENSA"
            },
            {
                "input": "c'est quoi OFPPT ?",
                "check": lambda r: "ofppt" in r.lower() or "formation professionnelle" in r.lower(),
                "label": "OFPPT détecté"
            },
            {
                "input": "je veux devenir pilote",
                "check": lambda r: any(kw in r.lower() for kw in ["era", "aiac", "aviation", "pilote"]),
                "label": "Pilote → ERA ou AIAC"
            },
        ]
    },
]

# =========================
# RUNNER
# =========================
def run_scenario(scenario):
    session = StudentProfile()
    results = []
    total = len(scenario["steps"])
    passed = 0

    print(f"\n{'='*60}")
    print(f"{BOLD}{BLUE}📋 {scenario['name']}{RESET}")
    print(f"   {scenario['description']}")
    print(f"{'='*60}")

    for i, step in enumerate(scenario["steps"], 1):
        start = time.time()
        try:
            res = bot_engine(step["input"], session)
            reply = res.get("reply", "")
            duration = round(time.time() - start, 2)

            ok = step["check"](reply)
            passed += ok

            status = f"{GREEN}✅ PASS{RESET}" if ok else f"{RED}❌ FAIL{RESET}"
            print(f"\n  {status} [{i}/{total}] {step['label']} ({duration}s)")

            if not ok:
                # affiche la réponse tronquée pour debug
                preview = reply[:200].replace('\n', ' ')
                print(f"  {YELLOW}↳ Reply: {preview}...{RESET}")

            results.append({
                "step": step["label"],
                "passed": ok,
                "duration": duration,
                "reply_preview": reply[:300]
            })

        except Exception as e:
            duration = round(time.time() - start, 2)
            print(f"\n  {RED}💥 ERROR{RESET} [{i}/{total}] {step['label']} ({duration}s)")
            print(f"  {RED}↳ {str(e)}{RESET}")
            results.append({
                "step": step["label"],
                "passed": False,
                "duration": duration,
                "error": str(e)
            })

    score = round(passed / total * 10, 1)
    color = GREEN if score >= 8 else YELLOW if score >= 6 else RED

    print(f"\n  {color}{BOLD}Score: {passed}/{total} ({score}/10){RESET}")
    return {"scenario": scenario["name"], "passed": passed, "total": total, "score": score, "details": results}


# =========================
# MAIN
# =========================
def main():
    print(f"\n{BOLD}{'='*60}")
    print(f"  🎓 SSI LPROF — TEST DE PERFORMANCE")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}{RESET}")

    all_results = []
    total_passed = 0
    total_steps = 0

    for scenario in SCENARIOS:
        result = run_scenario(scenario)
        all_results.append(result)
        total_passed += result["passed"]
        total_steps += result["total"]

    # ── RAPPORT FINAL ──
    global_score = round(total_passed / total_steps * 10, 1)
    color = GREEN if global_score >= 8 else YELLOW if global_score >= 6 else RED

    print(f"\n{'='*60}")
    print(f"{BOLD}📊 RAPPORT FINAL{RESET}")
    print(f"{'='*60}")

    for r in all_results:
        c = GREEN if r["score"] >= 8 else YELLOW if r["score"] >= 6 else RED
        bar = "█" * int(r["score"]) + "░" * (10 - int(r["score"]))
        print(f"  {c}{bar}{RESET}  {r['score']}/10  {r['scenario']}")

    print(f"\n  {color}{BOLD}Score Global: {total_passed}/{total_steps} = {global_score}/10{RESET}")

    if global_score >= 9:
        print(f"\n  {GREEN}{BOLD}🏆 EXCELLENT — Prêt pour la démo jury !{RESET}")
    elif global_score >= 7:
        print(f"\n  {YELLOW}{BOLD}✅ BON — Quelques ajustements mineurs{RESET}")
    else:
        print(f"\n  {RED}{BOLD}⚠️  À AMÉLIORER avant la démo{RESET}")

    # ── SAVE REPORT ──
    report = {
        "date": datetime.now().isoformat(),
        "global_score": global_score,
        "total_passed": total_passed,
        "total_steps": total_steps,
        "scenarios": all_results
    }

    report_path = os.path.join(os.path.dirname(__file__), "test_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n  📄 Rapport sauvegardé: {report_path}\n")
    return global_score


if __name__ == "__main__":
    score = main()
    sys.exit(0 if score >= 7 else 1)