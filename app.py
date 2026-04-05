"""
=============================================================================
  app.py  -  Interface graphique Tkinter principale
=============================================================================

  Ce module definit la classe SimulateurApp, fenetre principale de
  l'application. Elle orchestre :

    - Le panneau gauche  : formulaire de saisie des parametres
    - Le panneau droit   : notebook a onglets avec graphiques et tableaux
    - La barre de statut : progression, messages, duree d'execution

  Palette de couleurs inspiree du drapeau burkinabe :
    Rouge    : #EF3340   (couleur principale, accents)
    Vert     : #009639   (succes, confirmations)
    Jaune    : #FFD700   (avertissements, highlights)
    Bleu     : #003366   (titres, texte)
    Blanc    : #FFFFFF   (fonds de panneaux)
    Gris     : #F5F5F5   (arriere-plan general)

  Dependances :
    tkinter (stdlib), matplotlib, numpy

  Auteurs  : DABIRE Malong Evrard, KINDA Irénée, TRAORE Inoussa
  Version : 1.0.0
=============================================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import os

import numpy as np
import matplotlib
matplotlib.use("TkAgg")                          # Backend Tkinter obligatoire
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from simulation import MoteurSimulation, ParametresSimulation, ResultatsSimulation
from utils import export_csv, export_rapport_txt, formater_duree, erreur_relative


# ---------------------------------------------------------------------------
# Constantes de style
# ---------------------------------------------------------------------------

# Palette couleurs
C_ROUGE   = "#EF3340"
C_VERT    = "#009639"
C_JAUNE   = "#FFD700"
C_BLEU    = "#003366"
C_BLEU_CL = "#1A5276"
C_GRIS    = "#F5F5F5"
C_GRIS_FK = "#E8E8E8"
C_BLANC   = "#FFFFFF"
C_TEXTE   = "#1A1A2E"
C_BORDURE = "#CCCCCC"

# Polices
FONT_TITRE   = ("Georgia", 16, "bold")
FONT_SOUSTI  = ("Georgia", 11, "italic")
FONT_LABEL   = ("Helvetica", 10)
FONT_BOLD    = ("Helvetica", 10, "bold")
FONT_MONO    = ("Courier New", 10)
FONT_SMALL   = ("Helvetica", 8)

# Dimensions
LARGEUR_PANNEAU_G = 300     # Largeur du panneau parametres (pixels)
HAUTEUR_MIN       = 750     # Hauteur minimale de la fenetre
LARGEUR_MIN       = 1200    # Largeur minimale


# ---------------------------------------------------------------------------
# Classe principale : fenetre Tkinter
# ---------------------------------------------------------------------------

class SimulateurApp(tk.Tk):
    """
    Fenetre principale de l'application de simulation.

    Herite de tk.Tk (fenetre racine Tkinter).

    Structure de l'interface :
      +-------------------+----------------------------------------+
      |   PANNEAU GAUCHE  |        PANNEAU DROIT (notebook)        |
      |   (parametres)    |  [Graphiques] [Indicateurs] [Données]  |
      +-------------------+----------------------------------------+
      |              BARRE DE STATUT                               |
      +------------------------------------------------------------+

    Attributs principaux :
        moteur       (MoteurSimulation)  : Moteur de calcul.
        resultats    (ResultatsSimulation) : Derniers resultats calcules.
        _vars        (dict)              : Variables Tkinter des champs de saisie.
        canvas_fig   (FigureCanvasTkAgg) : Canvas Matplotlib principal.
    """

    def __init__(self):
        """Initialise la fenetre et tous ses composants."""
        super().__init__()

        # --- Configuration de la fenetre ---
        self.title("Simulateur de Coupures Electriques — Ouagadougou")
        self.minsize(LARGEUR_MIN, HAUTEUR_MIN)
        self.configure(bg=C_GRIS)

        # Taille initiale centree (les decorations systeme restent visibles :
        # barre de titre, boutons reduire / agrandir / FERMER).
        self._centrer_fenetre(LARGEUR_MIN + 100, HAUTEUR_MIN + 50)

        # Maximiser sans passer en plein ecran (full-screen masquerait
        # les boutons systeme et le bouton fermer du gestionnaire de fenetres).
        import platform
        systeme = platform.system()
        if systeme == "Windows":
            self.state("zoomed")          # maximise avec barre de titre
        elif systeme == "Linux":
            try:
                self.attributes("-zoomed", True)   # idem sous la plupart des WM
            except tk.TclError:
                pass                      # ignoré si le WM ne supporte pas

        # Protocole de fermeture propre : demander confirmation avant de quitter
        # (evite la perte de resultats en cours de simulation).
        self.protocol("WM_DELETE_WINDOW", self._confirmer_fermeture)

        # --- Moteur et resultats ---
        self.moteur    = MoteurSimulation()
        self.resultats : ResultatsSimulation | None = None

        # --- Variables Tkinter pour les champs de saisie ---
        self._vars = self._creer_variables()

        # --- Styles ttk ---
        self._configurer_styles()

        # --- Construction de l'interface ---
        self._construire_interface()

        # --- Lancer une simulation par defaut au demarrage ---
        self.after(200, self._simulation_initiale)

    # -----------------------------------------------------------------------
    # Initialisation
    # -----------------------------------------------------------------------

    def _creer_variables(self) -> dict:
        """
        Cree et retourne les variables Tkinter utilisees dans le formulaire.

        Returns :
            dict : {nom_variable: StringVar/IntVar/DoubleVar}
        """
        return {
            "lam"      : tk.DoubleVar(value=2.5),
            "duree_moy": tk.DoubleVar(value=0.75),
            "n_sim"    : tk.IntVar(value=5000),
            "seed"     : tk.StringVar(value="42"),
            "seuil_1"  : tk.DoubleVar(value=1.0),
            "seuil_2"  : tk.DoubleVar(value=2.0),
            "seuil_3"  : tk.DoubleVar(value=3.0),
            "seuil_4"  : tk.DoubleVar(value=4.0),
            "seuil_5"  : tk.DoubleVar(value=5.0),
            "theme"    : tk.StringVar(value="Burkina"),
        }

    def _configurer_styles(self):
        """Configure les styles ttk pour l'application."""
        style = ttk.Style(self)
        style.theme_use("clam")

        # Notebook (onglets)
        style.configure("TNotebook",
                         background=C_GRIS, borderwidth=0)
        style.configure("TNotebook.Tab",
                         background=C_GRIS_FK, foreground=C_BLEU,
                         padding=[12, 6], font=FONT_BOLD)
        style.map("TNotebook.Tab",
                  background=[("selected", C_BLEU)],
                  foreground=[("selected", C_BLANC)])

        # Bouton principal
        style.configure("Principal.TButton",
                         background=C_ROUGE, foreground=C_BLANC,
                         font=("Helvetica", 11, "bold"),
                         padding=[10, 8], borderwidth=0, relief="flat")
        style.map("Principal.TButton",
                  background=[("active", "#C0392B"), ("pressed", "#A93226")])

        # Bouton secondaire
        style.configure("Secondaire.TButton",
                         background=C_BLEU, foreground=C_BLANC,
                         font=FONT_BOLD, padding=[8, 5], borderwidth=0)
        style.map("Secondaire.TButton",
                  background=[("active", C_BLEU_CL)])

        # Progressbar
        style.configure("Vert.Horizontal.TProgressbar",
                         troughcolor=C_GRIS_FK, background=C_VERT,
                         thickness=8)

        # Labels
        style.configure("Titre.TLabel",
                         background=C_GRIS, foreground=C_BLEU,
                         font=FONT_TITRE)
        style.configure("Soustitre.TLabel",
                         background=C_GRIS, foreground=C_BLEU_CL,
                         font=FONT_SOUSTI)
        style.configure("Normal.TLabel",
                         background=C_BLANC, foreground=C_TEXTE,
                         font=FONT_LABEL)

        # Separateur
        style.configure("TSeparator", background=C_BORDURE)

    def _centrer_fenetre(self, largeur: int, hauteur: int):
        """
        Centre la fenetre sur l'ecran.

        Args :
            largeur (int) : Largeur souhaitee de la fenetre.
            hauteur (int) : Hauteur souhaitee de la fenetre.
        """
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - largeur) // 2
        y  = (sh - hauteur) // 2
        self.geometry(f"{largeur}x{hauteur}+{x}+{y}")

    # -----------------------------------------------------------------------
    # Construction de l'interface
    # -----------------------------------------------------------------------

    def _construire_interface(self):
        """
        Construit la structure principale de la fenetre :
          - En-tete colore
          - Conteneur central (panneau gauche + panneau droit)
          - Barre de statut inferieure
        """
        # En-tete
        self._construire_entete()

        # Conteneur principal (horizontal)
        conteneur = tk.Frame(self, bg=C_GRIS)
        conteneur.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # Panneau gauche : parametres
        self._construire_panneau_gauche(conteneur)

        # Separateur vertical
        sep = tk.Frame(conteneur, bg=C_BORDURE, width=1)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=4)

        # Panneau droit : resultats
        self._construire_panneau_droit(conteneur)

        # Barre de statut
        self._construire_barre_statut()

    def _construire_entete(self):
        """
        Construit l'en-tete de la fenetre avec les couleurs du drapeau.
        Trois bandes : rouge (haut), vert (milieu), titre blanc (droite).
        """
        entete = tk.Frame(self, bg=C_ROUGE, height=72)
        entete.pack(fill=tk.X, side=tk.TOP)
        entete.pack_propagate(False)

        # Bande verte a gauche (clin d'oeil au drapeau)
        bande_v = tk.Frame(entete, bg=C_VERT, width=14)
        bande_v.pack(side=tk.LEFT, fill=tk.Y)

        # Etoile jaune (decorative)
        etoile = tk.Label(entete, text="★", font=("Arial", 28),
                          bg=C_VERT, fg=C_JAUNE, width=2)
        etoile.pack(side=tk.LEFT, padx=0)

        # Zone titre
        zone_titre = tk.Frame(entete, bg=C_ROUGE)
        zone_titre.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=16)

        tk.Label(zone_titre,
                 text="Simulateur de Coupures Électriques",
                 font=("Georgia", 15, "bold"),
                 bg=C_ROUGE, fg=C_BLANC).pack(anchor="w", pady=(10, 0))
        tk.Label(zone_titre,
                 text="Modèle probabiliste  •  Poisson + Exponentielle  •  Monte-Carlo",
                 font=("Georgia", 9, "italic"),
                 bg=C_ROUGE, fg="#FFCCCB").pack(anchor="w")

        # Badge version
        tk.Label(entete, text=" v1.0 ",
                 font=("Courier New", 8), bg="#C0392B",
                 fg=C_BLANC, relief="flat", padx=4).pack(side=tk.RIGHT, padx=12, pady=22)

        # Bouton fermer dans l'en-tete (secours si la barre systeme est masquee)
        btn_fermer = tk.Button(
            entete,
            text    = "  ✕  Fermer  ",
            font    = ("Helvetica", 9, "bold"),
            bg      = "#A93226",
            fg      = C_BLANC,
            activebackground = "#7B241C",
            activeforeground = C_BLANC,
            relief  = "flat",
            bd      = 0,
            cursor  = "hand2",
            command = self._confirmer_fermeture,
            padx    = 6,
            pady    = 4,
        )
        btn_fermer.pack(side=tk.RIGHT, padx=(0, 6), pady=18)

    def _construire_panneau_gauche(self, parent: tk.Frame):
        """
        Construit le panneau gauche contenant le formulaire de parametres,
        les boutons d'action et les options d'export.

        Args :
            parent (tk.Frame) : Conteneur parent.
        """
        # Cadre avec scrollbar pour la lisibilite
        cadre = tk.Frame(parent, bg=C_BLANC, width=LARGEUR_PANNEAU_G,
                         relief="flat", bd=0)
        cadre.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 0))
        cadre.pack_propagate(False)

        # ---- Titre du panneau ----
        tk.Label(cadre, text="⚙  Paramètres",
                 font=("Helvetica", 12, "bold"),
                 bg=C_BLEU, fg=C_BLANC,
                 pady=8).pack(fill=tk.X)

        # ---- Zone de formulaire avec scrollbar ----
        canvas_scroll = tk.Canvas(cadre, bg=C_BLANC, highlightthickness=0)
        scrollbar     = ttk.Scrollbar(cadre, orient="vertical",
                                       command=canvas_scroll.yview)
        frame_form    = tk.Frame(canvas_scroll, bg=C_BLANC)

        frame_form.bind("<Configure>",
            lambda e: canvas_scroll.configure(
                scrollregion=canvas_scroll.bbox("all")))

        canvas_scroll.create_window((0, 0), window=frame_form, anchor="nw")
        canvas_scroll.configure(yscrollcommand=scrollbar.set)

        canvas_scroll.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Remplir le formulaire
        self._remplir_formulaire(frame_form)

    def _remplir_formulaire(self, parent: tk.Frame):
        """
        Ajoute tous les champs de saisie dans le formulaire.

        Sections :
          1. Parametres du modele (lambda, duree_moy, n_sim, seed)
          2. Seuils de depassement (t*1 ... t*5)
          3. Boutons d'action (Simuler, Reinitialiser)
          4. Boutons d'export (CSV, TXT)

        Args :
            parent (tk.Frame) : Cadre conteneur du formulaire.
        """
        pad = {"padx": 14, "pady": 4}

        # ----------------------------------------------------------------
        # Section 1 : Parametres du modele
        # ----------------------------------------------------------------
        self._section(parent, "1. Modèle probabiliste")

        # Lambda
        self._champ(parent,
            label    = "λ — Coupures / jour",
            variable = self._vars["lam"],
            tooltip  = "Taux moyen de coupures (loi de Poisson). Valeur estimee "
                       "a Ouagadougou en saison chaude : 2.5",
            vmin=0.01, vmax=50.0, pas=0.1)

        # Duree moyenne
        self._champ(parent,
            label    = "1/μ — Durée moy. coupure (h)",
            variable = self._vars["duree_moy"],
            tooltip  = "Duree moyenne d'une coupure en heures (loi exponentielle). "
                       "45 min = 0.75 h",
            vmin=0.01, vmax=24.0, pas=0.05)

        # Info : mu calcule
        self._label_info(parent, "μ calculé automatiquement = 1 / (1/μ)")

        # Nb simulations
        self._champ(parent,
            label    = "N_sim — Nb de journées simulées",
            variable = self._vars["n_sim"],
            tooltip  = "Nombre de journees a simuler (Monte-Carlo). "
                       "Recommande : 5000 a 50000 pour une bonne convergence.",
            vmin=100, vmax=500000, pas=1000, entier=True)

        # Graine
        tk.Label(parent, text="Graine aleatoire (seed)",
                 font=FONT_LABEL, bg=C_BLANC, fg=C_TEXTE,
                 anchor="w").pack(fill=tk.X, **pad)
        cadre_seed = tk.Frame(parent, bg=C_BLANC)
        cadre_seed.pack(fill=tk.X, padx=14, pady=(0, 4))
        self._entry_seed = tk.Entry(cadre_seed, textvariable=self._vars["seed"],
                                    font=FONT_MONO, width=10,
                                    bg=C_GRIS_FK, relief="solid", bd=1)
        self._entry_seed.pack(side=tk.LEFT)
        tk.Label(cadre_seed, text=" (vide = aleatoire)",
                 font=FONT_SMALL, bg=C_BLANC, fg="gray").pack(side=tk.LEFT)

        # ----------------------------------------------------------------
        # Section 2 : Seuils
        # ----------------------------------------------------------------
        ttk.Separator(parent, orient="horizontal").pack(fill=tk.X, padx=10, pady=8)
        self._section(parent, "2. Seuils t* de dépassement (h)")

        for i in range(1, 6):
            self._champ(parent,
                label    = f"Seuil t*{i} (h)",
                variable = self._vars[f"seuil_{i}"],
                tooltip  = f"Seuil numero {i} pour le calcul de P(T > t*).",
                vmin=0.1, vmax=24.0, pas=0.5)

        # ----------------------------------------------------------------
        # Section 3 : Boutons d'action
        # ----------------------------------------------------------------
        ttk.Separator(parent, orient="horizontal").pack(fill=tk.X, padx=10, pady=8)

        btn_simuler = ttk.Button(
            parent,
            text    = "▶  Lancer la simulation",
            style   = "Principal.TButton",
            command = self._lancer_simulation_thread
        )
        btn_simuler.pack(fill=tk.X, padx=14, pady=(2, 4))

        btn_reset = ttk.Button(
            parent,
            text    = "↺  Réinitialiser",
            style   = "Secondaire.TButton",
            command = self._reinitialiser
        )
        btn_reset.pack(fill=tk.X, padx=14, pady=(0, 4))

        # ----------------------------------------------------------------
        # Section 4 : Export
        # ----------------------------------------------------------------
        ttk.Separator(parent, orient="horizontal").pack(fill=tk.X, padx=10, pady=8)
        self._section(parent, "3. Exporter les résultats")

        btn_csv = ttk.Button(
            parent,
            text    = "📥  Exporter CSV",
            style   = "Secondaire.TButton",
            command = self._exporter_csv
        )
        btn_csv.pack(fill=tk.X, padx=14, pady=(2, 4))

        btn_txt = ttk.Button(
            parent,
            text    = "📄  Rapport texte (.txt)",
            style   = "Secondaire.TButton",
            command = self._exporter_rapport
        )
        btn_txt.pack(fill=tk.X, padx=14, pady=(0, 4))

        btn_png = ttk.Button(
            parent,
            text    = "🖼  Sauvegarder graphiques (.png)",
            style   = "Secondaire.TButton",
            command = self._exporter_graphiques
        )
        btn_png.pack(fill=tk.X, padx=14, pady=(0, 12))

    def _section(self, parent: tk.Frame, titre: str):
        """
        Ajoute un titre de section dans le formulaire.

        Args :
            parent (tk.Frame) : Conteneur.
            titre  (str)      : Texte du titre de section.
        """
        tk.Label(parent, text=titre,
                 font=("Helvetica", 9, "bold"),
                 bg=C_GRIS_FK, fg=C_BLEU,
                 anchor="w", padx=8, pady=4
                 ).pack(fill=tk.X, padx=0, pady=(4, 2))

    def _label_info(self, parent: tk.Frame, texte: str):
        """
        Ajoute un label informatif (gris, petit) dans le formulaire.

        Args :
            parent (tk.Frame) : Conteneur.
            texte  (str)      : Texte d'information.
        """
        tk.Label(parent, text=f"  ℹ  {texte}",
                 font=FONT_SMALL, bg=C_BLANC, fg="gray",
                 anchor="w", wraplength=260, justify="left"
                 ).pack(fill=tk.X, padx=14, pady=(0, 4))

    def _champ(self, parent: tk.Frame, label: str, variable,
               tooltip: str = "", vmin=0.0, vmax=1000.0,
               pas=0.1, entier=False):
        """
        Cree un champ de saisie avec label, zone d'entree et curseur (Scale).

        Args :
            parent   (tk.Frame)            : Conteneur.
            label    (str)                 : Etiquette du champ.
            variable (tk.DoubleVar/IntVar) : Variable liee.
            tooltip  (str)                 : Texte d'aide affiche au survol.
            vmin     (float)               : Valeur minimale du curseur.
            vmax     (float)               : Valeur maximale du curseur.
            pas      (float)               : Pas du curseur.
            entier   (bool)                : True si valeur entiere.
        """
        # Label
        lbl = tk.Label(parent, text=label,
                        font=FONT_LABEL, bg=C_BLANC, fg=C_TEXTE, anchor="w")
        lbl.pack(fill=tk.X, padx=14, pady=(6, 0))

        # Zone entree + valeur
        cadre = tk.Frame(parent, bg=C_BLANC)
        cadre.pack(fill=tk.X, padx=14, pady=(2, 0))

        entry = tk.Entry(cadre, textvariable=variable,
                         font=FONT_MONO, width=9,
                         bg=C_GRIS_FK, relief="solid", bd=1, fg=C_BLEU)
        entry.pack(side=tk.LEFT, padx=(0, 8))

        # Curseur (Scale)
        resolution = 1 if entier else pas
        scale = tk.Scale(cadre,
                         variable   = variable,
                         from_      = vmin,
                         to         = vmax,
                         resolution = resolution,
                         orient     = tk.HORIZONTAL,
                         length     = 160,
                         bg         = C_BLANC,
                         fg         = C_BLEU,
                         troughcolor= C_ROUGE,
                         highlightthickness=0,
                         showvalue  = 0,
                         sliderlength=14)
        scale.pack(side=tk.LEFT)

        # Tooltip simple (label qui apparait au survol)
        if tooltip:
            self._ajouter_tooltip(lbl, tooltip)
            self._ajouter_tooltip(entry, tooltip)

    def _ajouter_tooltip(self, widget, texte: str):
        """
        Attache une infobulle simple a un widget.

        La bulle s'affiche apres 500 ms de survol et disparait
        quand le curseur quitte le widget.

        Args :
            widget : Widget Tkinter cible.
            texte  (str) : Texte de l'infobulle.
        """
        tip_window = []  # liste muable pour la fermeture

        def entrer(event):
            # Creer la fenetre de tooltip
            w = tk.Toplevel(widget)
            w.wm_overrideredirect(True)      # Pas de decoration de fenetre
            w.configure(bg="#FFFFCC")
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + widget.winfo_height() + 4
            w.geometry(f"+{x}+{y}")
            tk.Label(w, text=texte, font=FONT_SMALL,
                     bg="#FFFFCC", fg=C_TEXTE,
                     wraplength=260, justify="left",
                     padx=6, pady=4).pack()
            tip_window.append(w)

        def sortir(event):
            for w in tip_window:
                try:
                    w.destroy()
                except Exception:
                    pass
            tip_window.clear()

        widget.bind("<Enter>", entrer)
        widget.bind("<Leave>", sortir)

    def _construire_panneau_droit(self, parent: tk.Frame):
        """
        Construit le panneau droit avec un notebook a 3 onglets :
          - Onglet 1 : Graphiques Matplotlib (4 graphes)
          - Onglet 2 : Tableau des indicateurs statistiques
          - Onglet 3 : Données brutes (N et T des 200 premieres journees)

        Args :
            parent (tk.Frame) : Conteneur parent.
        """
        cadre_droite = tk.Frame(parent, bg=C_GRIS)
        cadre_droite.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Notebook
        self.notebook = ttk.Notebook(cadre_droite, style="TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # --- Onglet 1 : Graphiques ---
        self.onglet_graphiques = tk.Frame(self.notebook, bg=C_GRIS)
        self.notebook.add(self.onglet_graphiques, text="  📊  Graphiques  ")
        self._construire_onglet_graphiques(self.onglet_graphiques)

        # --- Onglet 2 : Indicateurs ---
        self.onglet_indicateurs = tk.Frame(self.notebook, bg=C_BLANC)
        self.notebook.add(self.onglet_indicateurs, text="  📋  Indicateurs  ")
        self._construire_onglet_indicateurs(self.onglet_indicateurs)

        # --- Onglet 3 : Données brutes ---
        self.onglet_donnees = tk.Frame(self.notebook, bg=C_BLANC)
        self.notebook.add(self.onglet_donnees, text="  📁  Données brutes  ")
        self._construire_onglet_donnees(self.onglet_donnees)

    def _construire_onglet_graphiques(self, parent: tk.Frame):
        """
        Cree la figure Matplotlib integree dans Tkinter.

        La figure est composee de 4 sous-graphiques disposes en 2x2 :
          [0,0] PMF de Poisson (distribution de N)
          [0,1] Histogramme de T (distribution de la duree totale)
          [1,0] Fonction de survie P(T > t*)
          [1,1] Convergence de la moyenne (LGN)

        Args :
            parent (tk.Frame) : Onglet conteneur.
        """
        # Figure Matplotlib
        self.fig = Figure(figsize=(10, 7), dpi=96,
                          facecolor=C_GRIS, tight_layout=True)
        self._init_sous_graphiques()

        # Canvas Tkinter
        self.canvas_fig = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas_fig.draw()
        self.canvas_fig.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Barre d'outils Matplotlib (zoom, sauvegarde, etc.)
        toolbar_frame = tk.Frame(parent, bg=C_GRIS)
        toolbar_frame.pack(fill=tk.X)
        toolbar = NavigationToolbar2Tk(self.canvas_fig, toolbar_frame)
        toolbar.configure(background=C_GRIS)
        toolbar.update()

    def _init_sous_graphiques(self):
        """
        Initialise (ou reinitialise) les 4 sous-graphiques de la figure.
        Appele a la creation et apres chaque simulation.
        """
        self.fig.clear()
        gs = gridspec.GridSpec(2, 2, figure=self.fig,
                               hspace=0.42, wspace=0.35,
                               left=0.08, right=0.97,
                               top=0.95, bottom=0.08)
        # Stocker les axes pour les mettre a jour
        self.ax_pmf   = self.fig.add_subplot(gs[0, 0])  # PMF Poisson
        self.ax_hist  = self.fig.add_subplot(gs[0, 1])  # Histogramme T
        self.ax_surv  = self.fig.add_subplot(gs[1, 0])  # Survie
        self.ax_conv  = self.fig.add_subplot(gs[1, 1])  # Convergence

        # Message d'attente dans chaque axe
        for ax in [self.ax_pmf, self.ax_hist, self.ax_surv, self.ax_conv]:
            ax.set_facecolor(C_GRIS)
            ax.text(0.5, 0.5, "En attente de simulation...",
                    transform=ax.transAxes,
                    ha="center", va="center",
                    color="gray", fontsize=10, style="italic")
            ax.set_xticks([])
            ax.set_yticks([])

    def _construire_onglet_indicateurs(self, parent: tk.Frame):
        """
        Cree un tableau Treeview affichant les indicateurs statistiques.

        Colonnes :
          Indicateur | Valeur theorique | Valeur empirique | Erreur relative

        Args :
            parent (tk.Frame) : Onglet conteneur.
        """
        # Titre
        tk.Label(parent,
                 text="Tableau de bord des indicateurs statistiques",
                 font=("Georgia", 12, "bold"),
                 bg=C_BLANC, fg=C_BLEU, pady=10
                 ).pack(fill=tk.X, padx=16)

        # Sous-titre dynamique
        self._lbl_sous_titre = tk.Label(parent,
                 text="Lancez une simulation pour afficher les résultats.",
                 font=FONT_SOUSTI, bg=C_BLANC, fg="gray")
        self._lbl_sous_titre.pack(fill=tk.X, padx=16, pady=(0, 8))

        ttk.Separator(parent, orient="horizontal").pack(fill=tk.X, padx=16, pady=4)

        # --- Treeview : indicateurs principaux ---
        self._construire_treeview_indicateurs(parent)

        ttk.Separator(parent, orient="horizontal").pack(fill=tk.X, padx=16, pady=10)

        # --- Treeview : probabilites de depassement ---
        tk.Label(parent, text="Probabilités de dépassement P(T > t*)",
                 font=FONT_BOLD, bg=C_BLANC, fg=C_BLEU
                 ).pack(anchor="w", padx=16, pady=(0, 4))
        self._construire_treeview_probas(parent)

    def _construire_treeview_indicateurs(self, parent: tk.Frame):
        """
        Construit le Treeview des indicateurs statistiques.

        Args :
            parent (tk.Frame) : Conteneur parent.
        """
        colonnes = ("indicateur", "theorique", "empirique", "erreur")
        self.tree_indic = ttk.Treeview(
            parent, columns=colonnes, show="headings",
            height=10, selectmode="none"
        )

        # En-tetes
        entetes = {
            "indicateur" : ("Indicateur",      200),
            "theorique"  : ("Valeur théorique", 150),
            "empirique"  : ("Valeur empirique", 150),
            "erreur"     : ("Erreur relative",  120),
        }
        for col, (texte, larg) in entetes.items():
            self.tree_indic.heading(col, text=texte, anchor="center")
            self.tree_indic.column(col, width=larg, anchor="center", minwidth=80)

        # Couleurs alternees
        self.tree_indic.tag_configure("pair",   background="#F0F4F8")
        self.tree_indic.tag_configure("impair", background=C_BLANC)
        self.tree_indic.tag_configure("bonne",  foreground=C_VERT)
        self.tree_indic.tag_configure("alerte", foreground=C_ROUGE)

        # Scrollbar
        scrollbar = ttk.Scrollbar(parent, orient="vertical",
                                   command=self.tree_indic.yview)
        self.tree_indic.configure(yscrollcommand=scrollbar.set)

        self.tree_indic.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                              padx=(16, 0), pady=4)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y, pady=4)

    def _construire_treeview_probas(self, parent: tk.Frame):
        """
        Construit le Treeview des probabilites de depassement.

        Args :
            parent (tk.Frame) : Conteneur parent.
        """
        colonnes = ("seuil", "proba", "barre", "interpretation")
        self.tree_probas = ttk.Treeview(
            parent, columns=colonnes, show="headings",
            height=6, selectmode="none"
        )
        entetes = {
            "seuil"          : ("Seuil t* (h)",  100),
            "proba"          : ("P(T > t*)",     100),
            "barre"          : ("Visualisation", 200),
            "interpretation" : ("Interpretation",280),
        }
        for col, (texte, larg) in entetes.items():
            self.tree_probas.heading(col, text=texte, anchor="center")
            self.tree_probas.column(col, width=larg, anchor="center", minwidth=60)

        self.tree_probas.tag_configure("faible",  foreground=C_VERT)
        self.tree_probas.tag_configure("moyen",   foreground="#E67E22")
        self.tree_probas.tag_configure("eleve",   foreground=C_ROUGE)

        sb2 = ttk.Scrollbar(parent, orient="vertical",
                             command=self.tree_probas.yview)
        self.tree_probas.configure(yscrollcommand=sb2.set)

        self.tree_probas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                               padx=(16, 0), pady=4)
        sb2.pack(side=tk.LEFT, fill=tk.Y, pady=4)

    def _construire_onglet_donnees(self, parent: tk.Frame):
        """
        Construit l'onglet affichant les donnees brutes (N_i, T_i)
        pour les 200 premieres journees simulees.

        Args :
            parent (tk.Frame) : Onglet conteneur.
        """
        tk.Label(parent,
                 text="Données brutes (200 premières journées)",
                 font=("Georgia", 12, "bold"),
                 bg=C_BLANC, fg=C_BLEU, pady=10
                 ).pack(fill=tk.X, padx=16)

        tk.Label(parent,
                 text="N = nombre de coupures  |  T = durée totale d'interruption (h)",
                 font=FONT_SMALL, bg=C_BLANC, fg="gray"
                 ).pack(anchor="w", padx=16, pady=(0, 6))

        colonnes = ("jour", "N", "T", "T_fmt", "cat")
        self.tree_data = ttk.Treeview(
            parent, columns=colonnes, show="headings",
            height=25, selectmode="none"
        )
        entetes = {
            "jour"  : ("Jour",          60),
            "N"     : ("N (coupures)",  110),
            "T"     : ("T (h)",         100),
            "T_fmt" : ("T (hh:mm)",     100),
            "cat"   : ("Catégorie",     160),
        }
        for col, (texte, larg) in entetes.items():
            self.tree_data.heading(col, text=texte, anchor="center")
            self.tree_data.column(col, width=larg, anchor="center", minwidth=50)

        self.tree_data.tag_configure("aucune",  background="#E8F8E8", foreground=C_VERT)
        self.tree_data.tag_configure("legere",  background=C_BLANC)
        self.tree_data.tag_configure("moderee", background="#FFF3E0", foreground="#E67E22")
        self.tree_data.tag_configure("severe",  background="#FDEDEC", foreground=C_ROUGE)

        # Scrollbars
        sb_v = ttk.Scrollbar(parent, orient="vertical", command=self.tree_data.yview)
        sb_h = ttk.Scrollbar(parent, orient="horizontal", command=self.tree_data.xview)
        self.tree_data.configure(yscrollcommand=sb_v.set, xscrollcommand=sb_h.set)

        sb_v.pack(side=tk.RIGHT, fill=tk.Y)
        sb_h.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree_data.pack(fill=tk.BOTH, expand=True, padx=(16, 0))

    def _construire_barre_statut(self):
        """
        Construit la barre de statut en bas de la fenetre.

        Contient :
          - Label de statut (messages, duree de calcul)
          - Barre de progression
          - Label d'information sur la version
        """
        barre = tk.Frame(self, bg=C_BLEU, height=32)
        barre.pack(fill=tk.X, side=tk.BOTTOM)
        barre.pack_propagate(False)

        # Progressbar
        self._progressbar = ttk.Progressbar(
            barre, style="Vert.Horizontal.TProgressbar",
            length=180, mode="determinate"
        )
        self._progressbar.pack(side=tk.RIGHT, padx=12, pady=6)

        # Label de version (droite)
        tk.Label(barre, text="© PFA Probabilité & Statistiques 2025",
                 font=FONT_SMALL, bg=C_BLEU, fg="#AAAACC"
                 ).pack(side=tk.RIGHT, padx=8)

        # Label de statut (gauche)
        self._lbl_statut = tk.Label(
            barre, text="  ⬤  Prêt",
            font=("Helvetica", 9),
            bg=C_BLEU, fg=C_VERT, anchor="w"
        )
        self._lbl_statut.pack(side=tk.LEFT, padx=12)

    # -----------------------------------------------------------------------
    # Actions utilisateur
    # -----------------------------------------------------------------------

    def _lire_parametres(self) -> ParametresSimulation | None:
        """
        Lit et valide les parametres saisis dans le formulaire.

        Returns :
            ParametresSimulation si les valeurs sont valides, None sinon.
            En cas d'erreur, affiche une boite de dialogue.
        """
        try:
            lam       = float(self._vars["lam"].get())
            duree_moy = float(self._vars["duree_moy"].get())
            n_sim     = int(self._vars["n_sim"].get())

            # Lecture de la graine (peut etre vide)
            seed_str = self._vars["seed"].get().strip()
            seed     = int(seed_str) if seed_str else None

            # Seuils
            seuils = []
            for i in range(1, 6):
                s = float(self._vars[f"seuil_{i}"].get())
                if s > 0:
                    seuils.append(s)
            seuils = sorted(set(seuils)) if seuils else [1, 2, 3, 4, 5]

            return ParametresSimulation(
                lam       = lam,
                duree_moy = duree_moy,
                n_sim     = n_sim,
                seuils    = seuils,
                seed      = seed
            )

        except ValueError as e:
            messagebox.showerror(
                "Erreur de parametre",
                f"Valeur invalide dans le formulaire :\n{e}\n\n"
                "Verifiez que tous les champs contiennent des nombres valides."
            )
            return None

    def _lancer_simulation_thread(self):
        """
        Lance la simulation dans un thread secondaire pour ne pas bloquer
        l'interface graphique pendant le calcul.

        Etapes :
          1. Lecture et validation des parametres.
          2. Mise a jour de l'interface (statut, progressbar).
          3. Lancement du thread de calcul.
        """
        params = self._lire_parametres()
        if params is None:
            return

        # Mettre a jour l'interface
        self._set_statut("⏳  Simulation en cours...", C_JAUNE)
        self._progressbar["value"] = 0
        self._progressbar.start(10)      # Animation indeterminate

        # Lancer dans un thread daemon (se ferme quand l'app se ferme)
        thread = threading.Thread(
            target = self._executer_simulation,
            args   = (params,),
            daemon = True
        )
        thread.start()

    def _executer_simulation(self, params: ParametresSimulation):
        """
        Fonction executee dans le thread secondaire.
        Lance le calcul puis planifie la mise a jour de l'interface
        via after() (thread-safe).

        Args :
            params (ParametresSimulation) : Parametres valides.
        """
        debut = time.time()
        try:
            resultats = self.moteur.executer(params)
            duree = time.time() - debut
            # Retour sur le thread principal via after()
            self.after(0, lambda: self._afficher_resultats(resultats, duree))
        except Exception as e:
            self.after(0, lambda: self._afficher_erreur(str(e)))

    def _afficher_resultats(self, resultats: ResultatsSimulation, duree: float):
        """
        Met a jour tous les composants de l'interface avec les resultats.
        Appelee depuis le thread principal via after().

        Args :
            resultats (ResultatsSimulation) : Resultats calcules.
            duree     (float)               : Duree de calcul en secondes.
        """
        self.resultats = resultats

        # Arreter la progressbar
        self._progressbar.stop()
        self._progressbar["value"] = 100

        # Mettre a jour chaque composant
        self._mettre_a_jour_graphiques(resultats)
        self._mettre_a_jour_indicateurs(resultats)
        self._mettre_a_jour_donnees(resultats)

        # Statut final
        msg = (f"  ✓  Simulation terminée  —  "
               f"{resultats.params.n_sim:,} journées  —  "
               f"Durée : {duree:.2f}s  —  "
               f"E[T] = {formater_duree(resultats.E_T_empirique)}")
        self._set_statut(msg, C_VERT)

    def _afficher_erreur(self, message: str):
        """
        Affiche une erreur apres un echec de simulation.

        Args :
            message (str) : Message d'erreur.
        """
        self._progressbar.stop()
        self._progressbar["value"] = 0
        self._set_statut(f"  ✗  Erreur : {message}", C_ROUGE)
        messagebox.showerror("Erreur de simulation", message)

    def _set_statut(self, texte: str, couleur: str = C_BLANC):
        """
        Met a jour le texte et la couleur du label de statut.

        Args :
            texte   (str) : Nouveau texte.
            couleur (str) : Couleur du texte (hex).
        """
        self._lbl_statut.configure(text=texte, fg=couleur)
        self.update_idletasks()    # Force le rafraichissement immediat

    def _confirmer_fermeture(self):
        """
        Demande confirmation avant de fermer l'application.

        Si une simulation est en cours (resultats presents), propose une boite
        de dialogue Oui/Non pour eviter une fermeture accidentelle.
        Sinon ferme directement.
        """
        reponse = messagebox.askyesno(
            title   = "Fermer l'application",
            message = "Voulez-vous vraiment quitter le simulateur ?",
            icon    = messagebox.QUESTION,
            default = messagebox.NO,
        )
        if reponse:
            # Fermeture propre : detruire la figure Matplotlib avant de quitter
            # pour eviter les avertissements de garbage collector.
            try:
                plt.close(self.fig)
            except Exception:
                pass
            self.destroy()

    def _reinitialiser(self):
        """Remet les parametres a leurs valeurs par defaut."""
        self._vars["lam"].set(2.5)
        self._vars["duree_moy"].set(0.75)
        self._vars["n_sim"].set(5000)
        self._vars["seed"].set("42")
        for i, v in enumerate([1.0, 2.0, 3.0, 4.0, 5.0], start=1):
            self._vars[f"seuil_{i}"].set(v)
        self._set_statut("  ↺  Paramètres réinitialisés", C_JAUNE)

    def _simulation_initiale(self):
        """
        Lance automatiquement une premiere simulation avec les valeurs par defaut
        pour que l'interface ne soit pas vide au demarrage.
        """
        self._lancer_simulation_thread()

    # -----------------------------------------------------------------------
    # Mise a jour des graphiques
    # -----------------------------------------------------------------------

    def _mettre_a_jour_graphiques(self, res: ResultatsSimulation):
        """
        Redessine les 4 graphiques Matplotlib avec les nouveaux resultats.

        Args :
            res (ResultatsSimulation) : Resultats de la simulation.
        """
        self._init_sous_graphiques()   # Efface les axes precedents

        self._graphique_pmf_poisson(res)
        self._graphique_histogramme_T(res)
        self._graphique_survie(res)
        self._graphique_convergence(res)

        # Rafraichir le canvas Tkinter
        self.fig.tight_layout(pad=1.5)
        self.canvas_fig.draw()

    def _graphique_pmf_poisson(self, res: ResultatsSimulation):
        """
        Trace la fonction de masse de probabilite (PMF) de N ~ Poisson(lambda).

        Affiche :
          - Barres bleues : P(N = k) theorique
          - Histogramme orange translucide : frequences observees
          - Annotation : P(N >= 1)

        Args :
            res (ResultatsSimulation) : Resultats contenant pmf_poisson et N_data.
        """
        ax = self.ax_pmf
        ax.set_facecolor(C_GRIS)

        k_max  = len(res.pmf_poisson) - 1
        k_vals = np.arange(0, k_max + 1)

        # Frequences empiriques observees
        n_obs = res.params.n_sim
        freq_obs = np.bincount(res.N_data, minlength=k_max + 1)[:k_max + 1] / n_obs

        # Barres theoriques
        ax.bar(k_vals - 0.2, res.pmf_poisson, width=0.35,
               color=C_BLEU, alpha=0.85, label="P(N=k) théorique", zorder=3)

        # Barres empiriques
        ax.bar(k_vals + 0.2, freq_obs, width=0.35,
               color=C_ROUGE, alpha=0.65, label="Fréq. observée", zorder=3)

        # Annotation P(N >= 1)
        p_au_moins_1 = 1 - np.exp(-res.params.lam)
        ax.text(0.98, 0.97,
                f"P(N≥1) = {p_au_moins_1:.3f}",
                transform=ax.transAxes,
                ha="right", va="top", fontsize=8,
                color=C_BLEU, style="italic",
                bbox=dict(boxstyle="round,pad=0.3", fc=C_GRIS_FK, alpha=0.8))

        ax.set_title(f"Distribution N ~ Poisson(λ={res.params.lam})",
                     color=C_BLEU, fontsize=9, fontweight="bold")
        ax.set_xlabel("k (nombre de coupures)", fontsize=8, color=C_TEXTE)
        ax.set_ylabel("Probabilité", fontsize=8, color=C_TEXTE)
        ax.legend(fontsize=7)
        ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=7)

    def _graphique_histogramme_T(self, res: ResultatsSimulation):
        """
        Trace l'histogramme de la duree totale T.

        Affiche :
          - Histogramme de densite de T
          - Ligne rouge : E[T] empirique
          - Ligne verte : Q90
          - Ligne orange : Q50 (mediane)
          - Legende avec les valeurs numeriques

        Args :
            res (ResultatsSimulation) : Resultats contenant T_data et indicateurs.
        """
        ax = self.ax_hist
        ax.set_facecolor(C_GRIS)

        # Histogramme
        n_bins = min(60, res.params.n_sim // 50)
        ax.hist(res.T_data, bins=n_bins, density=True,
                color=C_BLEU, alpha=0.72, edgecolor="white",
                linewidth=0.3, label="Distribution de T", zorder=3)

        # Lignes verticales des indicateurs
        ax.axvline(res.E_T_empirique, color=C_ROUGE, lw=1.8, ls="--",
                   label=f"E[T] = {res.E_T_empirique:.3f} h", zorder=4)
        ax.axvline(res.quantiles[50], color=C_VERT, lw=1.5, ls="-.",
                   label=f"Q50 = {res.quantiles[50]:.3f} h", zorder=4)
        ax.axvline(res.quantiles[90], color=C_ROUGE, lw=1.5, ls=":",
                   label=f"Q90 = {res.quantiles[90]:.3f} h", zorder=4, alpha=0.8)

        ax.set_title("Distribution de T (durée totale/jour)",
                     color=C_BLEU, fontsize=9, fontweight="bold")
        ax.set_xlabel("Durée totale (heures)", fontsize=8, color=C_TEXTE)
        ax.set_ylabel("Densité", fontsize=8, color=C_TEXTE)
        ax.legend(fontsize=7)
        ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=7)

    def _graphique_survie(self, res: ResultatsSimulation):
        """
        Trace la fonction de survie empirique P(T > t).

        Affiche :
          - Courbe rouge : P(T > t) en fonction de t
          - Points marques aux seuils demandes
          - Lignes pointillees pour la lisibilite
          - Annotation du seuil principal (seuil_3)

        Args :
            res (ResultatsSimulation) : Resultats contenant T_data et seuils.
        """
        ax = self.ax_surv
        ax.set_facecolor(C_GRIS)

        # Courbe de survie sur une grille fine
        t_max  = min(np.percentile(res.T_data, 99.5), 15.0)
        t_grid = np.linspace(0, t_max, 300)
        survie = np.array([float(np.mean(res.T_data > t)) for t in t_grid])

        ax.plot(t_grid, survie, color=C_ROUGE, lw=2.0,
                label="P(T > t) empirique", zorder=3)

        # Marquer les seuils demandes
        couleurs_seuils = [C_VERT, "#E67E22", C_ROUGE, C_BLEU, "#8E44AD"]
        for idx, (seuil, prob) in enumerate(res.proba_depas.items()):
            c = couleurs_seuils[idx % len(couleurs_seuils)]
            ax.plot(seuil, prob, "o", color=c, ms=7, zorder=5)
            ax.plot([0, seuil], [prob, prob], ls=":", lw=0.8, color=c, alpha=0.7)
            ax.plot([seuil, seuil], [0, prob], ls=":", lw=0.8, color=c, alpha=0.7)
            ax.annotate(f"{prob:.2f}",
                        xy=(seuil, prob),
                        xytext=(seuil + 0.2, prob + 0.03),
                        fontsize=7, color=c)

        ax.set_title("Fonction de survie  P(T > t*)",
                     color=C_BLEU, fontsize=9, fontweight="bold")
        ax.set_xlabel("Seuil t* (heures)", fontsize=8, color=C_TEXTE)
        ax.set_ylabel("P(T > t*)", fontsize=8, color=C_TEXTE)
        ax.set_ylim(0, 1.05)
        ax.set_xlim(0)
        ax.grid(linestyle="--", alpha=0.35, zorder=0)
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=7)

    def _graphique_convergence(self, res: ResultatsSimulation):
        """
        Trace la convergence de la moyenne empirique vers E[T] (Loi des Grands Nombres).

        Affiche :
          - Courbe bleue : moyenne empirique sur sous-echantillons croissants
          - Ligne rouge pointillee : E[T] theorique
          - Zone coloree : intervalle de confiance a 95%

        Args :
            res (ResultatsSimulation) : Resultats contenant convergence_*.
        """
        ax = self.ax_conv
        ax.set_facecolor(C_GRIS)

        sizes = res.convergence_n
        moy   = res.convergence_moy
        ic    = res.convergence_ic
        th    = res.E_T_theorique

        # Courbe de convergence
        ax.semilogx(sizes, moy, color=C_BLEU, lw=1.8,
                    label=r"$\hat{\mu}_n$ empirique", zorder=3)

        # Valeur theorique
        ax.axhline(th, color=C_ROUGE, ls="--", lw=1.8,
                   label=f"E[T] = {th:.3f} h", zorder=4)

        # Intervalle de confiance 95%
        ax.fill_between(sizes, th - ic, th + ic,
                        alpha=0.2, color=C_ROUGE, label="IC 95%", zorder=2)

        # Annotation de la convergence
        if len(moy) > 0:
            ecart_final = abs(moy[-1] - th)
            ax.text(0.98, 0.05,
                    f"Écart final : {ecart_final:.4f} h",
                    transform=ax.transAxes,
                    ha="right", va="bottom", fontsize=7,
                    color=C_BLEU, style="italic",
                    bbox=dict(boxstyle="round,pad=0.3", fc=C_GRIS_FK, alpha=0.8))

        ax.set_title("Convergence Monte-Carlo (LGN)",
                     color=C_BLEU, fontsize=9, fontweight="bold")
        ax.set_xlabel("Nombre de simulations n (log)", fontsize=8, color=C_TEXTE)
        ax.set_ylabel("Moyenne empirique (h)", fontsize=8, color=C_TEXTE)
        ax.legend(fontsize=7)
        ax.grid(linestyle="--", alpha=0.35, zorder=0)
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=7)

    # -----------------------------------------------------------------------
    # Mise a jour des tableaux
    # -----------------------------------------------------------------------

    def _mettre_a_jour_indicateurs(self, res: ResultatsSimulation):
        """
        Rafraichit le tableau des indicateurs statistiques.

        Args :
            res (ResultatsSimulation) : Resultats.
        """
        # Vider l'ancien contenu
        for item in self.tree_indic.get_children():
            self.tree_indic.delete(item)

        # Sous-titre
        self._lbl_sous_titre.configure(
            text=(f"λ = {res.params.lam}  |  1/μ = {res.params.duree_moy} h  |  "
                  f"N_sim = {res.params.n_sim:,}  |  "
                  f"E[T] = {formater_duree(res.E_T_empirique)}"),
            fg=C_BLEU
        )

        # Construire les lignes
        lignes = [
            ("E[T]  (h)",
             f"{res.E_T_theorique:.5f}",
             f"{res.E_T_empirique:.5f}",
             erreur_relative(res.E_T_theorique, res.E_T_empirique)),

            ("E[T]  (hh:mm)",
             formater_duree(res.E_T_theorique),
             formater_duree(res.E_T_empirique), None),

            ("Var[T]  (h²)",
             f"{res.V_T_theorique:.5f}",
             f"{res.V_T_empirique:.5f}",
             erreur_relative(res.V_T_theorique, res.V_T_empirique)),

            ("σ[T]  (h)",
             f"{res.V_T_theorique**0.5:.5f}",
             f"{res.sigma_empirique:.5f}",
             erreur_relative(res.V_T_theorique**0.5, res.sigma_empirique)),

            ("P(N = 0) — jour sans coupure",
             f"{np.exp(-res.params.lam):.5f}",
             f"{np.mean(res.N_data == 0):.5f}",
             erreur_relative(np.exp(-res.params.lam),
                             float(np.mean(res.N_data == 0)))),
        ]

        # Ajouter les quantiles
        for p, v in res.quantiles.items():
            lignes.append((
                f"Q{p:02d} — percentile {p}%",
                "—",
                f"{v:.5f}",
                None
            ))

        # Inserer dans le Treeview
        for i, (nom, th, em, err) in enumerate(lignes):
            tag = "pair" if i % 2 == 0 else "impair"
            err_str = f"{err:.2f} %" if err is not None else "—"
            self.tree_indic.insert("", "end",
                values=(nom, th, em, err_str),
                tags=(tag,))

        # Tableau des probabilites de depassement
        for item in self.tree_probas.get_children():
            self.tree_probas.delete(item)

        for seuil, prob in res.proba_depas.items():
            barre = "█" * int(prob * 20) + "░" * (20 - int(prob * 20))

            # Interpretation contextuelle
            if prob > 0.5:
                interp = "⚠ Très fréquent (>1 jour/2)"
                tag    = "eleve"
            elif prob > 0.2:
                interp = "⚡ Fréquent (~1 jour/4 ou plus)"
                tag    = "moyen"
            elif prob > 0.05:
                interp = "ℹ Occasionnel"
                tag    = "moyen"
            else:
                interp = "✓ Rare (<5% des jours)"
                tag    = "faible"

            self.tree_probas.insert("", "end",
                values=(f"{seuil:.1f} h", f"{prob:.4f}", barre, interp),
                tags=(tag,))

    def _mettre_a_jour_donnees(self, res: ResultatsSimulation):
        """
        Rafraichit le tableau des donnees brutes (200 premieres journees).

        Args :
            res (ResultatsSimulation) : Resultats.
        """
        for item in self.tree_data.get_children():
            self.tree_data.delete(item)

        limite = min(200, res.params.n_sim)
        for i in range(limite):
            n = int(res.N_data[i])
            t = float(res.T_data[i])

            # Categoriser la journee
            if n == 0:
                cat = "✓ Aucune coupure"
                tag = "aucune"
            elif t < 1.0:
                cat = "Légère (< 1h)"
                tag = "legere"
            elif t < 3.0:
                cat = "⚡ Modérée (1h-3h)"
                tag = "moderee"
            else:
                cat = "⚠ Sévère (> 3h)"
                tag = "severe"

            self.tree_data.insert("", "end",
                values=(i + 1, n, f"{t:.4f}", formater_duree(t), cat),
                tags=(tag,))

    # -----------------------------------------------------------------------
    # Export
    # -----------------------------------------------------------------------

    def _verifier_resultats(self) -> bool:
        """
        Verifie qu'une simulation a ete lancee avant d'exporter.

        Returns :
            bool : True si des resultats sont disponibles.
        """
        if self.resultats is None:
            messagebox.showwarning(
                "Aucun résultat",
                "Veuillez d'abord lancer une simulation."
            )
            return False
        return True

    def _exporter_csv(self):
        """Exporte les resultats dans un fichier CSV choisi par l'utilisateur."""
        if not self._verifier_resultats():
            return

        chemin = filedialog.asksaveasfilename(
            title            = "Exporter en CSV",
            defaultextension = ".csv",
            filetypes        = [("Fichiers CSV", "*.csv"), ("Tous", "*.*")],
            initialfile      = "resultats_simulation.csv"
        )
        if not chemin:
            return  # Annulation

        try:
            export_csv(self.resultats, chemin)
            self._set_statut(f"  ✓  CSV exporté : {os.path.basename(chemin)}", C_VERT)
            messagebox.showinfo("Export réussi",
                                f"Fichier CSV sauvegardé :\n{chemin}")
        except OSError as e:
            messagebox.showerror("Erreur d'export", str(e))

    def _exporter_rapport(self):
        """Exporte un rapport texte synthetique."""
        if not self._verifier_resultats():
            return

        chemin = filedialog.asksaveasfilename(
            title            = "Exporter le rapport",
            defaultextension = ".txt",
            filetypes        = [("Fichiers texte", "*.txt"), ("Tous", "*.*")],
            initialfile      = "rapport_simulation.txt"
        )
        if not chemin:
            return

        try:
            export_rapport_txt(self.resultats, chemin)
            self._set_statut(f"  ✓  Rapport exporté : {os.path.basename(chemin)}", C_VERT)
            messagebox.showinfo("Export réussi",
                                f"Rapport sauvegardé :\n{chemin}")
        except OSError as e:
            messagebox.showerror("Erreur d'export", str(e))

    def _exporter_graphiques(self):
        """
        Sauvegarde la figure des graphiques en PNG.

        Ouvre un dialogue pour choisir le chemin de destination,
        puis sauvegarde la figure Matplotlib a 150 DPI.
        """
        if not self._verifier_resultats():
            return

        chemin = filedialog.asksaveasfilename(
            title            = "Sauvegarder les graphiques",
            defaultextension = ".png",
            filetypes        = [("Images PNG", "*.png"),
                                 ("Images PDF", "*.pdf"),
                                 ("Tous", "*.*")],
            initialfile      = "graphiques_simulation.png"
        )
        if not chemin:
            return

        try:
            self.fig.savefig(chemin, dpi=150, bbox_inches="tight",
                             facecolor=C_GRIS)
            self._set_statut(f"  ✓  Graphiques exportés : {os.path.basename(chemin)}", C_VERT)
            messagebox.showinfo("Export réussi",
                                f"Graphiques sauvegardés :\n{chemin}")
        except OSError as e:
            messagebox.showerror("Erreur d'export", str(e))
