# Marsad Al-Idara — مرصد الإدارة
### Système d'Aide à la Décision pour la Transparence Administrative Tunisienne

> **Digitalisation des données publiques non structurées au service du pilotage de l'administration.**
> Une plateforme de traitement automatique des textes juridiques du Journal Officiel de la République Tunisienne (JORT) transformant des décrets en données exploitables pour les décideurs publics, les chercheurs, et les citoyens.

---

## Table des matières

1. [Présentation du projet](#1-présentation-du-projet)
2. [Pipeline ETL & Intelligence Artificielle](#2-pipeline-etl--intelligence-artificielle)
3. [Architecture des données](#3-architecture-des-données)
4. [Business Intelligence & Tableaux de bord](#4-business-intelligence--tableaux-de-bord)
5. [Interface & Visualisation](#5-interface--visualisation)
6. [Installation & Déploiement](#6-installation--déploiement)
7. [Valeur publique & Gouvernance](#7-valeur-publique--gouvernance)
8. [Lexique](#lexique)

---

## 1. Présentation du projet

L'administration publique tunisienne publie quotidiennement des décrets de nomination, révocation, et restructuration institutionnelle dans le JORT. Ces données — sources primaires de la gouvernance — restent **enfouies dans des documents PDF non structurés**, inaccessibles à toute analyse automatisée.

**Marsad Al-Idara** résout ce problème fondamental en construisant un pipeline d'intelligence artificielle qui :

- **Extrait** automatiquement le texte brut des éditions du JORT (PDF numérisés ou scannés)
- **Reconnaît** les entités nommées (personnes, rôles, institutions, dates) par traitement du langage naturel
- **Structure** et **historise** ces nominations dans une base de données relationnelle temporelle
- **Visualise** les parcours de carrière des fonctionnaires sur une frise chronologique interactive

L'outil constitue un instrument de **données ouvertes (Open Data)** et de **pilotage de l'administration**, permettant aux décideurs publics, aux journalistes d'investigation, et aux chercheurs académiques de cartographier la structure de l'État tunisien à travers le temps.

---

## 2. Pipeline ETL & Intelligence Artificielle

Le cœur du système repose sur un pipeline **ETL (Extract, Transform, Load)** formalisé en trois phases distinctes et observables.

```
╔══════════════════════════════════════════════════════════════════════╗
║                   PIPELINE ETL — MARSAD AL-IDARA                    ║
╠══════════════╦══════════════════════════╦═════════════════════════════╣
║   EXTRACT    ║       TRANSFORM          ║           LOAD              ║
║──────────────║──────────────────────────║─────────────────────────────║
║ JORT PDF     ║ 1. OpenDataLoader PDF    ║ PostgreSQL                  ║
║ (numérique)  ║    → Markdown structuré  ║  · persons                  ║
║      +       ║    (layout multi-colonne ║  · institutions             ║
║ Tesseract    ║    JORT respecté)        ║  · person_roles             ║
║ OCR (fallback║                          ║    (valid_from / valid_to)  ║
║ pour scans   ║ 2. Ollama LLM (NER)      ║  · decrees (source JORT)    ║
║ anciens)     ║    → Entités extraites : ║  · institution_hierarchy    ║
║              ║    · Personne            ║                             ║
║              ║    · Rôle / Titre        ║ Vectorisation               ║
║              ║    · Institution         ║  · pgvector (embeddings)    ║
║              ║    · Date d'effet        ║  · Recherche sémantique     ║
╚══════════════╩══════════════════════════╩═════════════════════════════╝
```

### 2.1 Phase Extract — Acquisition des données brutes

Deux stratégies d'extraction sont orchestrées par `pipeline/extractor.py` selon la nature du document :

| Type de source | Outil | Cas d'usage |
|---|---|---|
| PDF numérique (post-2000) | **OpenDataLoader PDF** | Respecte les layouts multi-colonnes du JORT |
| PDF scanné (archives historiques) | **Tesseract OCR** (`ara+fra`) | Fallback automatique si < 100 caractères extraits |
| HTML (portail JORT en ligne) | **BeautifulSoup** | Éditions récentes au format web |

Le texte arabe extrait est systématiquement normalisé via `arabic_reshaper` et l'algorithme `python-bidi` pour corriger la directionnalité RTL (Right-To-Left) avant traitement.

### 2.2 Phase Transform — NER par LLM local (Ollama)

La transformation applique un modèle de langue local (**Ollama**) sur le texte extrait pour réaliser une **Reconnaissance d'Entités Nommées (REN / NER)** spécialisée dans le domaine juridico-administratif tunisien :

```python
# Prompt NER structuré envoyé à Ollama
{
  "task": "Extraire les nominations du décret suivant",
  "entities": ["personne", "rôle", "institution", "date_effet", "action"],
  "output_format": "JSON"
}
```

Cette approche traite des formulations juridiques complexes du type :
> *"Il est mis fin aux fonctions de M. X en sa qualité de Directeur Général de Y, à compter du..."*

Le modèle identifie la **personne**, le **rôle**, l'**institution**, l'**action** (nomination/révocation), et la **date d'entrée en vigueur**.

### 2.3 Phase Load — Persistance temporelle

Les entités structurées sont chargées dans PostgreSQL en respectant le modèle relationnel temporel, avec un lien de traçabilité systématique vers le décret source (numéro JORT, date de publication, texte brut).

---

## 3. Architecture des données

### 3.1 Diagramme de flux de données (DFD)

```
Niveau 0 — Diagramme de contexte

    ┌──────────┐      Fichiers PDF/HTML       ┌──────────────────┐
    │  Source  │ ───────────────────────────▶ │                  │
    │  JORT    │                              │  MARSAD ETL      │
    │ (externe)│ ◀─────────────────────────── │  (Système)       │
    └──────────┘    Statut de traitement      └────────┬─────────┘
                                                       │ Données structurées
                                                       ▼
    ┌──────────┐                             ┌──────────────────────┐
    │Décideurs │ ◀─── Tableaux de bord ───── │   PostgreSQL         │
    │ publics  │                             │   (ODS + pgvector)   │
    └──────────┘                             └──────────────────────┘

Niveau 1 — Décomposition du pipeline

 [1.0 Détection] → [2.0 Extraction] → [3.0 NER LLM] → [4.0 Chargement] → [5.0 Indexation]
  (PDF/HTML/Scan)  (Markdown/Texte)   (JSON entités)    (PostgreSQL)       (pgvector FTS)
```

### 3.2 Modèle Entité-Association (MER) — Suivi historique temporel

Le modèle relationnel implémente le pattern académique **SCD-2 (Slowly Changing Dimension Type 2)**, standard de l'entreposage de données pour le suivi historique des changements :

```
┌─────────────┐         ┌──────────────────────────────┐         ┌──────────────────┐
│   PERSONNES │         │         NOMINATIONS           │         │  INSTITUTIONS    │
│─────────────│         │──────────────────────────────│         │──────────────────│
│ id (PK)     │ 1 ── N  │ person_id      (FK)           │ N ── 1  │ id (PK)          │
│ name_fr     │         │ institution_id (FK)           │         │ name_fr          │
│ name_ar     │         │ role_fr                       │         │ name_ar          │
│ name_variants│        │ valid_from  ◄── DATE DÉBUT    │         │ type             │
│ birth_year  │         │ valid_to    ◄── NULL = actif  │         │ name_variants[]  │
└─────────────┘         │ decree_id (FK) ◄── traçabilité│         └──────────────────┘
                        │ action  (nommé|révoqué|...)   │
                        └──────────────────────────────┘
                                       │ N
                                       ▼ 1
                               ┌───────────────────┐
                               │      DECRETS      │
                               │───────────────────│
                               │ decree_number     │
                               │ jort_issue        │
                               │ date_published    │
                               │ date_effective    │
                               │ raw_text          │
                               │ embedding ◄── pgvector (1536d)
                               │ confidence        │
                               │ needs_review      │
                               └───────────────────┘
```

**Principe clé — Traçabilité totale :** chaque nomination est liée au décret JORT qui la fonde. Il est possible de remonter de n'importe quelle situation actuelle jusqu'au texte juridique officiel source.

**Requête analytique — Parcours de carrière complet :**
```sql
SELECT
    p.name_fr,
    pr.role_fr,
    i.name_fr                                        AS institution,
    pr.valid_from                                    AS debut,
    COALESCE(pr.valid_to, CURRENT_DATE)              AS fin,
    COALESCE(pr.valid_to, CURRENT_DATE) - pr.valid_from AS duree_jours,
    d.jort_issue                                     AS source_decret
FROM person_roles pr
JOIN persons      p ON p.id = pr.person_id
JOIN institutions i ON i.id = pr.institution_id
JOIN decrees      d ON d.id = pr.decree_id
ORDER BY pr.valid_from ASC;
```

### 3.3 Hiérarchie institutionnelle temporelle

La table `institution_hierarchy` capture les réorganisations ministérielles avec leurs dates de validité, permettant de reconstruire l'organigramme de l'État à **n'importe quelle date historique** — fonctionnalité impossible avec un modèle statique classique.

---

## 4. Business Intelligence & Tableaux de bord

### 4.1 PostgreSQL comme entrepôt de données opérationnel (ODS)

La base de données PostgreSQL joue le rôle d'un **entrepôt de données opérationnel**, connecté à **Power BI Desktop** via le connecteur natif PostgreSQL (mode DirectQuery ou Import).

```
PostgreSQL / marsad
        │
        │  Vues analytiques (CREATE VIEW)
        ▼
┌───────────────────────────────────────────────────┐
│               VUES BI DISPONIBLES                  │
│                                                   │
│  v_duree_moyenne_par_ministere                     │
│  → Durée moyenne de détention d'un poste          │
│    par portefeuille ministériel                   │
│                                                   │
│  v_taux_rotation_institutionnel                    │
│  → Nombre de titulaires successifs                │
│    par poste sur une période donnée               │
│                                                   │
│  v_mobilite_fonctionnaires                         │
│  → Nombre de postes occupés par agent             │
│    (indice de mobilité interne)                   │
│                                                   │
│  v_activite_reglementaire                          │
│  → Volume de décrets de nomination                │
│    par mois / année / ministère                   │
└───────────────────────────────────────────────────┘
        │
        │  Power BI : Get Data → PostgreSQL → localhost:5432/marsad
        ▼
   Dashboards interactifs pour décideurs publics
```

### 4.2 Indicateurs clés de performance (KPIs)

| Indicateur | Description | Usage |
|---|---|---|
| **Durée moyenne de mandat** | Par poste ou ministère | Évaluation de la stabilité institutionnelle |
| **Taux de rotation** | Nombre de titulaires / période | Mesure de la continuité administrative |
| **Indice de mobilité** | Postes occupés par fonctionnaire | Analyse des trajectoires de carrière |
| **Densité réglementaire** | Décrets/mois par institution | Activité législative et réorganisations |
| **Délai de publication** | Date décision → Date JORT | Efficacité du processus d'officialisation |

---

## 5. Interface & Visualisation

### 5.1 API REST — FastAPI

L'interface de programmation expose les données structurées via une **API REST** documentée automatiquement (Swagger UI sur `/docs`) :

| Endpoint | Description |
|---|---|
| `GET /api/snapshot?date=YYYY-MM-DD` | Organigramme complet de l'État à une date donnée |
| `GET /api/persons/{id}` | Profil complet et historique de carrière d'un fonctionnaire |
| `GET /api/institutions/{id}` | Fiche d'une institution avec sa hiérarchie |
| `GET /api/search?q=<terme>` | Recherche unifiée sur les personnes et institutions |

### 5.2 Frontend interactif — React & D3.js

L'interface utilisateur offre trois modes de visualisation complémentaires :

**Frise chronologique interactive (D3.js)**
- Axe temporel couvrant l'histoire administrative tunisienne (1956 → présent)
- Segmentation par ères politiques (Bourguiba, Ben Ali, Transition, Saied...)
- Curseur temporel *scrubable* : déplacer le curseur reconstruit l'organigramme en temps réel

**Carte organisationnelle hiérarchique**
- Visualisation de la chaîne de commandement de l'État
- Nœuds cliquables révélant le titulaire actuel et son parcours
- Mise à jour dynamique à chaque changement de date

**Tiroir de profil fonctionnaire**
- Fiche détaillée : nom, rôle actuel, institution
- Timeline personnelle des postes occupés (via `person_roles`)
- Lien direct vers le décret JORT source de chaque nomination

---

## 6. Installation & Déploiement

### Prérequis

- Docker & Docker Compose
- Python 3.11+
- Node.js 20+
- Tesseract OCR (`tesseract-ocr-ara` + `tesseract-ocr-fra`)
- Ollama (modèle recommandé : `mistral` ou `llama3`)

### Lancement rapide

```bash
# 1. Cloner le dépôt
git clone https://github.com/<utilisateur>/tunisian-admin-map
cd tunisian-admin-map

# 2. Démarrer PostgreSQL et Ollama
docker compose up -d

# 3. Le schéma est appliqué automatiquement via docker-entrypoint-initdb.d

# 4. Lancer le pipeline ETL
cd pipeline
pip install -r requirements.txt
python extractor.py          # Phase Extract (OCR + OpenDataLoader)
# python transformer.py      # Phase Transform (NER via Ollama)
# python loader.py           # Phase Load → PostgreSQL

# 5. Lancer l'API backend
cd backend/api
pip install fastapi uvicorn
uvicorn main:app --reload --port 8000

# 6. Lancer le frontend
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### Services Docker

| Service | Port | Description |
|---|---|---|
| PostgreSQL | 5432 | Base de données principale (schéma temporel + pgvector) |
| Ollama | 11434 | Inférence LLM locale (NER, embeddings) |

---

## 7. Valeur publique & Gouvernance

### Digitalisation des textes juridiques

La Tunisie publie chaque année plusieurs centaines de décrets de nomination dans le JORT. Marsad Al-Idara transforme ce **patrimoine informationnel non structuré** en **données ouvertes (Open Data)** exploitables — une contribution directe à la mission de transparence de l'État.

### Pilotage de l'administration

En quantifiant la durée des mandats, les taux de rotation et les trajectoires de carrière, le système fournit aux **décideurs publics** des indicateurs objectifs pour :
- Évaluer la stabilité des équipes de direction
- Identifier les institutions à fort turnover
- Analyser les patterns de mobilité inter-ministérielle

### Gouvernance et contrôle

Chaque donnée du système est ancrée dans un texte juridique officiel. Cette **traçabilité de source** répond aux exigences fondamentales de la gouvernance publique :

> *"Toute nomination dans le système Marsad est vérifiable jusqu'à son décret d'origine dans le JORT."*

### Ouverture et réplicabilité

L'architecture open source et la dépendance exclusive à des **outils libres** (PostgreSQL, Python, Ollama, React) garantissent que l'approche est réplicable pour d'autres administrations publiques de la région MENA souhaitant digitaliser leurs données de gouvernance.

---

## Lexique

| Terme | Définition |
|---|---|
| **JORT** | Journal Officiel de la République Tunisienne — source primaire des textes juridiques officiels |
| **ETL** | Extract, Transform, Load — processus standardisé d'alimentation d'un entrepôt de données |
| **NER** | Named Entity Recognition — identification automatique d'entités nommées dans un texte |
| **SCD-2** | Slowly Changing Dimension Type 2 — modèle de suivi historique en entrepôt de données |
| **Open Data / Données ouvertes** | Données publiques accessibles librement, réutilisables et redistribuables |
| **Pilotage de l'administration** | Usage de KPIs et tableaux de bord pour orienter la gestion publique par les faits |
| **Décideurs publics** | Ministres, directeurs généraux, et responsables institutionnels habilités à agir |
| **ODS** | Operational Data Store — entrepôt de données opérationnel, couche intermédiaire avant BI |
| **pgvector** | Extension PostgreSQL pour le stockage et la recherche vectorielle sémantique |
| **DFD** | Diagramme de Flux de Données — outil de modélisation des systèmes d'information |

---

<div align="center">

**Marsad Al-Idara** — Pour une administration publique transparente, mesurable, et pilotée par les données.

*Projet académique — Informatique de Gestion*

</div>
