# RPA — Optimisation par Programmation Linéaire en Nombres Entiers

> Implémentation du modèle bi-phasé proposé par **Seguin & Routhier (CODIT 2019)**  
> pour l'automatisation des processus robotiques (RPA) appliquée aux services financiers.

---

## Description

Dans le cadre d'un projet scolaire en première année de maîtrise, l'objectif est de se renseigner sur le principe des RPA et les différentes méthodes de résolution de ce problème, afin de créer un outil de visualisation capable de comparer ces méthodes entre elles et de visualiser les résultats d'une résolution en elle-même.

La méthode appliquée dans ce dépôt est celle décrite dans l'article de Mme Seguin : *Robotic process automation (RPA) using an integer linear programming formulation*. Dans ce dernier, la résolution du problème de RPA est découpée en deux phases.

1. **Phase 1** — Le nombre minimal de robots nécessaires pour traiter l'ensemble des transactions, en pénalisant les démarrages et reconfigurations.
2. **Phase 2** — L'assignation exacte de chaque transaction à chaque robot sur chaque période.

Les résultats sont ensuite visualisés via un dashboard interactif Streamlit.

---

## Structure du projet

```
rpa-optimisation/
│
├── Phase1.mod          # Modèle AMPL – Phase 1 : minimisation du nombre de robots
├── Phase1.dat          # Données d'entrée – 12 types de transactions, 36 périodes
│
├── Phase2.mod          # Modèle AMPL – Phase 2 : assignation des transactions
├── Phase2.dat          # Données d'entrée – issues de la résolution de Phase 1
│
├── main.py             # Script principal : résolution Phase 1 → Phase 2 → export JSON
├── dashboard.py        # Interface de visualisation Streamlit
│
├── resultats.json      # Résultats de l'optimisation (généré par main.py)
├── requirements.txt    # Dépendances Python
└── README.md
```

---

## Prérequis

| Outil | Version minimale | Rôle |
|---|---|---|
| Python | 3.10+ | Langage principal |
| AMPL Community Edition | — | Environnement de modélisation |
| HiGHS | inclus avec amplpy | Solveur MIP (gratuit) |

---

## Installation

```bash
# Cloner le dépôt
git clone https://github.com/<utilisateur>/rpa-optimisation.git
cd rpa-optimisation

# Installer les dépendances Python
pip install amplpy streamlit plotly pandas
```

Pour activer HiGHS dans amplpy (première utilisation) :
```bash
python -m amplpy setup --quiet
python -m amplpy install highs
```

---

## Utilisation

### Étape 1 — Résolution de l'optimisation

```bash
python main.py
```

Ce script enchaîne automatiquement les deux phases :

```
Phase 1  →  Calcule le nombre minimal de robots par période
    ↓
Phase 2  →  Assigne chaque transaction à un robot
    ↓
resultats.json  →  Export des résultats pour le dashboard
```

### Étape 2 — Visualisation

Depuis le répertoire rpa-optimisation:
```bash
streamlit run dashboard.py
```

Ouvre automatiquement le dashboard dans le navigateur (`http://localhost:8501`).

---

## Format du fichier `resultats.json`

```json
{
  "transactions": [
    {
      "periode":     1, // à qu'elle période
      "transaction": 3, // qu'elle transaction
      "robot":       1, // quel robot
      "qte_volume":  59 // quelle quantité traité
    },
    {
        ...
    },
    ...
  ],
  "duree_periode": {
    "1": 4500,
    ...
    "9": 23400
  },
  "nb_robot_periode": {
    "1": 3,
    ...
    "9": 1
  },
  "duree_transaction": {
    "1": 120,
    ...
    "9": 1320
  }
}
```

| Champ | Description |
|---|---|
| `transactions` | Liste de toutes les assignations `(robot, période, type, volume)` |
| `duree_periode` | Durée en secondes de chaque période active |
| `nb_robot_periode` | Nombre de robots par période active |
| `duree_transaction` | Durée en secondes pour traiter un exemplaire de chaque type |

---

## Dashboard interactif

Le dashboard propose 4 onglets et un panneau de filtres latéral.

### Filtres (barre latérale)
- Sélection des périodes, types de transactions et robots à afficher.
- Tous les graphiques se mettent à jour en temps réel.

### Onglet 1 — Vue Générale
Graphique de type Gantt matriciel :
- **Axe X** : périodes
- **Axe Y** : types de transactions
- Rectangles : un rectangle coloré par robot, empilés dans chaque cellule


### Onglet 2 — Par Robot
- Sélection d'un robot individuel
- Gantt filtré sur ce robot 
- Graphique en secteurs de la répartition sur ce robot
- Tableau détaillé avec le temps utilisé vs durée disponible

### Onglet 3 — Résumé Charge
- **Heatmap** : total des transactions par `(période × type)`
- **Barres empilées** : volume total par période, décomposé par type
- **Tableau croisé** : robots × `(période, type)`

### Onglet 4 — Export LaTeX
- Génère un tableau des résultat pour un format LaTex
- Option de découpage automatique si le tableau est trop large
- Bouton de téléchargement du fichier `.tex`

---

## Référence

> Seguin, S., & Routhier, G. (2019).  
> **Robotic process automation (RPA) using an integer linear programming formulation.**