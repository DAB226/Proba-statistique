"""
=============================================================================
  utils.py  -  Fonctions utilitaires
=============================================================================

  Ce module fournit des fonctions independantes de l'interface graphique :

    - export_csv(resultats, chemin)
        Exporte les resultats numeriques dans un fichier CSV.

    - export_rapport_txt(resultats, chemin)
        Genere un rapport texte synthetique.

    - formater_duree(heures)
        Convertit une duree en heures vers une chaine "Xh Ymin".

    - erreur_relative(theorique, empirique)
        Calcule l'erreur relative en pourcentage.

  Auteur  : [Votre nom]
  Version : 1.0.0
=============================================================================
"""

import csv
import os
from datetime import datetime
from simulation import ResultatsSimulation


# ---------------------------------------------------------------------------
# Formatage
# ---------------------------------------------------------------------------

def formater_duree(heures: float) -> str:
    """
    Convertit une duree en heures vers une chaine lisible.

    Exemples :
        formater_duree(1.875) -> "1h 52min"
        formater_duree(0.5)   -> "0h 30min"
        formater_duree(0.0)   -> "0h 00min"

    Args :
        heures (float) : Duree en heures (>= 0).

    Returns :
        str : Chaine au format "Xh Ymin".
    """
    heures = max(0.0, heures)
    h = int(heures)
    m = int(round((heures - h) * 60))
    return f"{h}h {m:02d}min"


def erreur_relative(theorique: float, empirique: float) -> float:
    """
    Calcule l'erreur relative entre valeur theorique et empirique.

    err = |empirique - theorique| / theorique * 100  (en %)

    Args :
        theorique (float) : Valeur de reference (>0).
        empirique (float) : Valeur estimee.

    Returns :
        float : Erreur relative en pourcentage, ou 0.0 si theorique == 0.
    """
    if abs(theorique) < 1e-12:
        return 0.0
    return abs(empirique - theorique) / abs(theorique) * 100.0


# ---------------------------------------------------------------------------
# Export CSV
# ---------------------------------------------------------------------------

def export_csv(res: ResultatsSimulation, chemin: str) -> None:
    """
    Exporte les resultats de simulation dans un fichier CSV.

    Structure du fichier :
      Section 1 : Parametres utilises
      Section 2 : Indicateurs statistiques (theorique vs empirique)
      Section 3 : Quantiles
      Section 4 : Probabilites de depassement
      Section 5 : Donnees brutes (N_i, T_i) -- 2 colonnes, n_sim lignes

    Args :
        res    (ResultatsSimulation) : Resultats a exporter.
        chemin (str)                 : Chemin du fichier .csv de destination.

    Raises :
        OSError : Si le fichier ne peut pas etre cree (permissions, chemin invalide).
    """
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")

        # En-tete du fichier
        writer.writerow(["Simulateur de Coupures Electriques - Ouagadougou"])
        writer.writerow([f"Export genere le : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"])
        writer.writerow([])

        # -- Section 1 : Parametres --
        writer.writerow(["=== PARAMETRES ==="])
        writer.writerow(["Lambda (coupures/jour)", res.params.lam])
        writer.writerow(["Duree moyenne (h)",      res.params.duree_moy])
        writer.writerow(["mu (h^-1)",              round(res.params.mu, 4)])
        writer.writerow(["Nb simulations",         res.params.n_sim])
        writer.writerow(["Graine aleatoire",       res.params.seed])
        writer.writerow([])

        # -- Section 2 : Indicateurs --
        writer.writerow(["=== INDICATEURS STATISTIQUES ==="])
        writer.writerow(["Indicateur", "Theorique", "Empirique", "Erreur relative (%)"])
        writer.writerow([
            "E[T] (h)",
            round(res.E_T_theorique, 4),
            round(res.E_T_empirique, 4),
            round(erreur_relative(res.E_T_theorique, res.E_T_empirique), 3)
        ])
        writer.writerow([
            "Var[T] (h^2)",
            round(res.V_T_theorique, 4),
            round(res.V_T_empirique, 4),
            round(erreur_relative(res.V_T_theorique, res.V_T_empirique), 3)
        ])
        writer.writerow([
            "Sigma[T] (h)",
            round(res.V_T_theorique ** 0.5, 4),
            round(res.sigma_empirique, 4),
            round(erreur_relative(res.V_T_theorique ** 0.5, res.sigma_empirique), 3)
        ])
        writer.writerow([])

        # -- Section 3 : Quantiles --
        writer.writerow(["=== QUANTILES ==="])
        writer.writerow(["Percentile (%)", "Valeur (h)", "Valeur (hh:mm)"])
        for p, v in res.quantiles.items():
            writer.writerow([p, round(v, 4), formater_duree(v)])
        writer.writerow([])

        # -- Section 4 : Probabilites --
        writer.writerow(["=== PROBABILITES DE DEPASSEMENT ==="])
        writer.writerow(["Seuil t* (h)", "P(T > t*)"])
        for seuil, prob in res.proba_depas.items():
            writer.writerow([seuil, round(prob, 4)])
        writer.writerow([])

        # -- Section 5 : Donnees brutes (premieres 500 lignes max) --
        writer.writerow(["=== DONNEES BRUTES (500 premieres journees) ==="])
        writer.writerow(["Jour", "N (nb coupures)", "T (duree totale h)"])
        limit = min(500, res.params.n_sim)
        for i in range(limit):
            writer.writerow([i + 1, int(res.N_data[i]), round(float(res.T_data[i]), 4)])


# ---------------------------------------------------------------------------
# Export rapport texte
# ---------------------------------------------------------------------------

def export_rapport_txt(res: ResultatsSimulation, chemin: str) -> None:
    """
    Genere un rapport de synthese en texte brut (.txt).

    Le rapport reprend les parametres, indicateurs, quantiles et
    probabilites de depassement sous forme tabulaire lisible.

    Args :
        res    (ResultatsSimulation) : Resultats a resumer.
        chemin (str)                 : Chemin du fichier .txt de destination.
    """
    sep = "=" * 60
    lignes = [
        sep,
        "  RAPPORT DE SIMULATION - COUPURES ELECTRIQUES OUAGADOUGOU",
        sep,
        f"  Date : {datetime.now().strftime('%d/%m/%Y a %H:%M:%S')}",
        "",
        "  PARAMETRES",
        "  " + "-" * 40,
        f"  Lambda (coupures/jour)  : {res.params.lam}",
        f"  Duree moy. coupure      : {formater_duree(res.params.duree_moy)} "
        f"({res.params.duree_moy} h)",
        f"  mu (taux retablissement): {res.params.mu:.4f} h^-1",
        f"  Nombre de simulations   : {res.params.n_sim:,}",
        "",
        "  INDICATEURS STATISTIQUES",
        "  " + "-" * 40,
        f"  {'Indicateur':<20} {'Theorique':>12} {'Empirique':>12} {'Erreur':>10}",
        f"  {'E[T] (h)':<20} {res.E_T_theorique:>12.4f} {res.E_T_empirique:>12.4f} "
        f"{erreur_relative(res.E_T_theorique, res.E_T_empirique):>9.2f}%",
        f"  {'Var[T] (h^2)':<20} {res.V_T_theorique:>12.4f} {res.V_T_empirique:>12.4f} "
        f"{erreur_relative(res.V_T_theorique, res.V_T_empirique):>9.2f}%",
        f"  {'Sigma[T] (h)':<20} {res.V_T_theorique**0.5:>12.4f} {res.sigma_empirique:>12.4f} "
        f"{erreur_relative(res.V_T_theorique**0.5, res.sigma_empirique):>9.2f}%",
        f"  {'E[T] (hh:mm)':<20} {formater_duree(res.E_T_theorique):>12}",
        "",
        "  QUANTILES",
        "  " + "-" * 40,
    ]
    for p, v in res.quantiles.items():
        lignes.append(f"  Q{p:<4}  {v:.4f} h  = {formater_duree(v)}")

    lignes += [
        "",
        "  PROBABILITES DE DEPASSEMENT",
        "  " + "-" * 40,
    ]
    for seuil, prob in res.proba_depas.items():
        barre = "#" * int(prob * 30)
        lignes.append(f"  P(T > {seuil:.1f}h) = {prob:.4f}  |{barre:<30}|")

    lignes += ["", sep]

    with open(chemin, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes))
