"""
=============================================================================
  Simulateur de Coupures d'Electricite - Ouagadougou
  Projet - Probabilites et Statistiques
=============================================================================

  Point d'entree principal de l'application.

  Usage :
      python main.py

  Dependances :
      pip install numpy scipy matplotlib

  Architecture :
      main.py          -> Lance l'application
      simulation.py    -> Moteur probabiliste (Poisson + Exponentielle)
      app.py           -> Interface graphique Tkinter principale
      utils.py         -> Fonctions utilitaires (export CSV, PDF)

  Auteurs  : DABIRE Malong Evrard, KINDA Irénée, TRAORE Inoussa
  Version : 1.0.0
  Date    : 2026
=============================================================================
"""

from app import SimulateurApp


def main():
    """
    Fonction principale : initialise et lance la fenetre Tkinter.
    """
    app = SimulateurApp()
    app.mainloop()


if __name__ == "__main__":
    main()
