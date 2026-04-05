"""
=============================================================================
  simulation.py  -  Moteur probabiliste
=============================================================================

  Ce module contient toute la logique mathematique du modele :

    - Variable discrete   : N ~ Poisson(lambda)
      Nombre de coupures electriques par jour.

    - Variable continue   : D_i ~ Exp(mu)
      Duree de chaque coupure individuelle.

    - Somme aleatoire     : T = sum_{i=1}^{N} D_i
      Duree totale d'interruption journaliere.

  Formules analytiques :
    E[T]   = lambda / mu
    Var[T] = 2 * lambda / mu^2
    sigma  = sqrt(Var[T])

  La simulation Monte-Carlo genere N_SIM journees independantes
  et produit les distributions empiriques, quantiles et probabilites
  de depassement de seuils.

  References :
    - Ross, S.M. (2019). Introduction to Probability Models, chap. 5
    - Cours de Probabilites et Statistiques, chap. 5 (Monte-Carlo)
=============================================================================
"""

import numpy as np
from scipy import stats
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Structure de donnees : parametres d'entree
# ---------------------------------------------------------------------------

@dataclass
class ParametresSimulation:
    """
    Conteneur des parametres d'entree de la simulation.

    Attributs :
        lam     (float) : Taux moyen de coupures par jour (lambda, loi de Poisson).
                          Doit etre > 0.
        duree_moy (float): Duree moyenne d'une coupure en heures (= 1/mu).
                          Doit etre > 0.
        n_sim   (int)   : Nombre de journees simulees (recommande : >= 1000).
        seuils  (list)  : Liste de seuils t* en heures pour P(T > t*).
        seed    (Optional[int]) : Graine aleatoire pour la reproductibilite.
    """
    lam      : float
    duree_moy: float
    n_sim    : int
    seuils   : list = field(default_factory=lambda: [1.0, 2.0, 3.0, 4.0, 5.0])
    seed     : Optional[int] = 42

    def __post_init__(self):
        """Validation des parametres a la creation."""
        if self.lam <= 0:
            raise ValueError(f"lambda doit etre > 0, recu : {self.lam}")
        if self.duree_moy <= 0:
            raise ValueError(f"duree_moy doit etre > 0, recue : {self.duree_moy}")
        if self.n_sim < 100:
            raise ValueError(f"n_sim doit etre >= 100, recu : {self.n_sim}")

    @property
    def mu(self) -> float:
        """Taux de retablissement mu = 1 / duree_moy."""
        return 1.0 / self.duree_moy


# ---------------------------------------------------------------------------
# Structure de donnees : resultats de sortie
# ---------------------------------------------------------------------------

@dataclass
class ResultatsSimulation:
    """
    Conteneur de tous les resultats produits par la simulation.

    Attributs :
        params          : Parametres utilises pour cette simulation.
        N_data          : Tableau (n_sim,) des nombres de coupures par jour.
        T_data          : Tableau (n_sim,) des durees totales journalieres (h).

        E_T_theorique   : Esperance theorique de T = lambda / mu.
        V_T_theorique   : Variance theorique de T = 2*lambda / mu^2.
        E_T_empirique   : Moyenne empirique de T sur les simulations.
        V_T_empirique   : Variance empirique (non biaisee) de T.
        sigma_empirique : Ecart-type empirique de T.

        quantiles       : Dict {p -> valeur} pour p in [25,50,75,90,95,99].
        proba_depas     : Dict {seuil -> P(T > seuil)} pour chaque seuil demande.

        pmf_poisson     : Tableau des probabilites P(N=k) pour k=0..k_max.
        convergence_n   : Tableau des tailles d'echantillon pour la courbe de convergence.
        convergence_moy : Tableau des moyennes empiriques correspondantes.
        convergence_ic  : Tableau des demi-intervalles de confiance a 95%.
    """
    params          : ParametresSimulation
    N_data          : np.ndarray
    T_data          : np.ndarray

    E_T_theorique   : float = 0.0
    V_T_theorique   : float = 0.0
    E_T_empirique   : float = 0.0
    V_T_empirique   : float = 0.0
    sigma_empirique : float = 0.0

    quantiles       : dict = field(default_factory=dict)
    proba_depas     : dict = field(default_factory=dict)

    pmf_poisson     : np.ndarray = field(default_factory=lambda: np.array([]))
    convergence_n   : np.ndarray = field(default_factory=lambda: np.array([]))
    convergence_moy : np.ndarray = field(default_factory=lambda: np.array([]))
    convergence_ic  : np.ndarray = field(default_factory=lambda: np.array([]))


# ---------------------------------------------------------------------------
# Moteur de simulation
# ---------------------------------------------------------------------------

class MoteurSimulation:
    """
    Classe principale du moteur probabiliste.

    Methodes publiques :
        executer(params) -> ResultatsSimulation
            Lance la simulation complete et retourne les resultats.

    Exemple d'utilisation :
        moteur = MoteurSimulation()
        params = ParametresSimulation(lam=2.5, duree_moy=0.75, n_sim=10000)
        resultats = moteur.executer(params)
        print(resultats.E_T_empirique)
    """

    def executer(self, params: ParametresSimulation) -> ResultatsSimulation:
        """
        Execute la simulation Monte-Carlo complete.

        Etapes :
          1. Initialisation de la graine aleatoire.
          2. Tirage de N ~ Poisson(lambda) pour chaque journee.
          3. Pour chaque journee, tirage de n_i durees D_ij ~ Exp(mu).
          4. Calcul de T_i = sum(D_ij).
          5. Calcul de tous les indicateurs statistiques.
          6. Construction des donnees pour les graphiques.

        Args :
            params (ParametresSimulation) : Parametres valides.

        Returns :
            ResultatsSimulation : Tous les resultats calcules.
        """
        # -- 1. Graine aleatoire --
        if params.seed is not None:
            np.random.seed(params.seed)

        # -- 2. Tirage du nombre de coupures par jour --
        # N_i ~ Poisson(lambda) pour i = 1..n_sim
        N_data = np.random.poisson(lam=params.lam, size=params.n_sim)

        # -- 3 & 4. Tirage des durees et calcul de la somme --
        # T_i = sum_{j=1}^{N_i} D_{ij}   avec D_{ij} ~ Exp(mu)
        # Si N_i = 0, la journee est sans coupure : T_i = 0
        T_data = self._simuler_durees_totales(N_data, params.mu)

        # -- 5. Indicateurs analytiques (valeurs theoriques) --
        E_T_th = params.lam / params.mu                  # E[T] = lambda * E[D]
        V_T_th = 2.0 * params.lam / (params.mu ** 2)    # Var[T] = 2*lambda/mu^2

        # -- 5b. Indicateurs empiriques --
        E_T_em  = float(np.mean(T_data))
        V_T_em  = float(np.var(T_data, ddof=1))          # ddof=1 : estimateur non biaise
        sigma   = float(np.std(T_data,  ddof=1))

        # -- 5c. Quantiles --
        niveaux = [25, 50, 75, 90, 95, 99]
        valeurs = np.percentile(T_data, niveaux)
        quantiles = {p: float(v) for p, v in zip(niveaux, valeurs)}

        # -- 5d. Probabilites de depassement P(T > t*) --
        proba_depas = {}
        for t_star in params.seuils:
            proba_depas[float(t_star)] = float(np.mean(T_data > t_star))

        # -- 6. PMF de la loi de Poisson theorique --
        k_max = max(15, int(params.lam * 3))
        k_vals = np.arange(0, k_max + 1)
        pmf_poisson = stats.poisson.pmf(k_vals, params.lam)

        # -- 6b. Donnees de convergence (pour le graphique LGN) --
        # On calcule la moyenne empirique pour des sous-echantillons croissants
        n_points = min(150, params.n_sim)
        sizes = np.unique(
            np.logspace(1, np.log10(params.n_sim), n_points).astype(int)
        )
        sizes = sizes[sizes <= params.n_sim]
        conv_moy = np.array([float(np.mean(T_data[:n])) for n in sizes])
        # Intervalle de confiance a 95% : +/- 1.96 * sigma / sqrt(n)
        conv_ic  = 1.96 * sigma / np.sqrt(sizes.astype(float))

        # -- Assemblage du resultat --
        return ResultatsSimulation(
            params          = params,
            N_data          = N_data,
            T_data          = T_data,
            E_T_theorique   = E_T_th,
            V_T_theorique   = V_T_th,
            E_T_empirique   = E_T_em,
            V_T_empirique   = V_T_em,
            sigma_empirique = sigma,
            quantiles       = quantiles,
            proba_depas     = proba_depas,
            pmf_poisson     = pmf_poisson,
            convergence_n   = sizes,
            convergence_moy = conv_moy,
            convergence_ic  = conv_ic,
        )

    def _simuler_durees_totales(self, N_data: np.ndarray, mu: float) -> np.ndarray:
        """
        Calcule la duree totale T_i = sum_{j=1}^{N_i} D_{ij} pour chaque journee.

        Optimisation : les journees avec N_i = 0 sont traitees en masse
        (T_i = 0 directement) ; les autres utilisent une generation vectorisee
        par groupe de meme N_i pour eviter une boucle Python pure.

        Args :
            N_data (np.ndarray) : Nombre de coupures pour chaque journee.
            mu     (float)      : Taux de retablissement (1/duree_moy).

        Returns :
            np.ndarray : Tableau des durees totales (meme longueur que N_data).
        """
        T = np.zeros(len(N_data), dtype=float)

        # Indices des journees avec au moins une coupure
        idx_nonzero = np.where(N_data > 0)[0]

        if len(idx_nonzero) == 0:
            return T  # Tous a zero

        # Methode vectorisee : on tire toutes les durees en un seul appel
        # puis on les accumule par journee avec numpy.add.reduceat
        n_vals = N_data[idx_nonzero]          # Nombre de coupures par journee non nulle
        total_draws = int(n_vals.sum())        # Nombre total de tirages a effectuer

        # Tirage groupé de toutes les durées
        all_durees = np.random.exponential(scale=1.0 / mu, size=total_draws)

        # Indices de debut de chaque groupe dans all_durees
        offsets = np.concatenate([[0], np.cumsum(n_vals[:-1])])

        # Somme par groupe : T_i = sum des n_vals[i] durees a partir de offsets[i]
        T[idx_nonzero] = np.add.reduceat(all_durees, offsets)

        return T
