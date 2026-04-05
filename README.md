# Simulateur de Coupures Électriques — Ouagadougou
## Projet — Probabilités et Statistiques

---

## Description

Application de simulation probabiliste modélisant les coupures d'électricité
à Ouagadougou (Burkina Faso) à partir d'un modèle combinant :

- **Variable discrète** : N ~ Poisson(λ) — nombre de coupures par jour
- **Variable continue** : D_i ~ Exp(μ) — durée de chaque coupure
- **Somme aléatoire** : T = Σ D_i — durée totale journalière

---

## Architecture des fichiers

```
sim_coupures/
│
├── main.py          # Point d'entrée — lance l'application
├── app.py           # Interface graphique Tkinter (fenêtre principale)
├── simulation.py    # Moteur probabiliste (Monte-Carlo)
├── utils.py         # Fonctions utilitaires (export CSV, TXT)
├── requirements.txt # Dépendances Python
└── README.md        # Ce fichier
```

---

## Installation

### 1. Prérequis
- Python 3.10 ou supérieur
- Tkinter (inclus dans la plupart des distributions Python)

  Sur Ubuntu/Debian si Tkinter manque :
  ```bash
  sudo apt-get install python3-tk
  ```

  Sur macOS avec Homebrew :
  ```bash
  brew install python-tk
  ```

### 2. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 3. Lancer l'application
```bash
python main.py
```

---

## Utilisation

### Panneau des paramètres (gauche)

| Paramètre | Description | Valeur défaut |
|-----------|-------------|---------------|
| λ | Nombre moyen de coupures/jour | 2.5 |
| 1/μ | Durée moyenne d'une coupure (h) | 0.75 h (45 min) |
| N_sim | Nombre de journées simulées | 5 000 |
| Graine | Graine aléatoire (vide = aléatoire) | 42 |
| Seuils t* | 5 seuils pour P(T > t*) | 1,2,3,4,5 h |

### Onglets de résultats (droite)

1. **📊 Graphiques** — 4 graphiques interactifs :
   - PMF de Poisson (théorique vs empirique)
   - Distribution de T (histogramme)
   - Fonction de survie P(T > t*)
   - Convergence Monte-Carlo (LGN)

2. **📋 Indicateurs** — Tableau comparatif théorique/empirique :
   - Espérance, variance, écart-type
   - Quantiles Q25, Q50, Q75, Q90, Q95, Q99
   - Probabilités de dépassement avec interprétation

3. **📁 Données brutes** — 200 premières journées simulées avec
   catégorisation (aucune / légère / modérée / sévère)

### Boutons d'export

- **📥 Exporter CSV** — Indicateurs + données brutes (500 lignes)
- **📄 Rapport texte** — Synthèse tabulaire en .txt
- **🖼 Sauvegarder graphiques** — Figure en .png ou .pdf

---

## Formules mathématiques

```
N ~ Poisson(λ)        E[N] = λ        Var[N] = λ
D_i ~ Exp(μ)          E[D] = 1/μ      Var[D] = 1/μ²

T = Σ(i=1..N) D_i

E[T]   = λ / μ
Var[T] = 2λ / μ²
σ[T]   = √(2λ/μ²)
```

---

## Dépendances

| Bibliothèque | Version min | Usage |
|---|---|---|
| numpy | 1.24 | Génération aléatoire vectorisée |
| scipy | 1.10 | Loi de Poisson (PMF, stats) |
| matplotlib | 3.7 | Graphiques intégrés dans Tkinter |
| tkinter | stdlib | Interface graphique |

---

## Auteur
DABIRE Malyong Evrard
KINDA Irénée
TRAORE Inoussa
