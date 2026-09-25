# Procezo — backend, étape 1

Cette livraison couvre **BE-01 à BE-04** du [backlog](BACKLOG_BACKEND_PROCEZO.md) : API V1, droits, audit et premier dossier fictif. Elle utilise Django 5.2, DRF, SQLite et des sessions Django. Les rôles, unités et classifications sont une politique de **prototype** ; la matrice DGDA et l'identité/MFA restent à approuver avant toute donnée réelle.

## Démarrage local

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
$env:PROCEZO_DEMO_PASSWORD = "une-phrase-secrete-de-demo"
python manage.py seed_demo
python manage.py runserver
```

`seed_demo` est limité à `DEBUG=True`. Il crée une unité `DEMO`, quatre comptes fictifs et un dossier affecté. Il ne change pas le mot de passe d'un compte déjà présent. La base locale `db.sqlite3` et les secrets sont ignorés par Git.

## API

Base : `/api/v1/`. Le schéma versionné est dans [openapi/v1.yaml](openapi/v1.yaml) et disponible à `/api/v1/schema/`.

| Méthode | Route | Usage |
| --- | --- | --- |
| GET, POST, DELETE | `/session/` | Cookie CSRF, connexion, déconnexion |
| GET, POST | `/dossiers/` | Liste filtrée/paginée, création |
| GET, PATCH | `/dossiers/{uuid}/` | Fiche et modification conditionnelle |
| GET, POST | `/dossiers/{uuid}/affectations/` | Historique et réaffectation motivée |
| GET | `/dossiers/{uuid}/chronologie/` | Historique des actions |
| GET | `/audit/?unit={uuid}` | Audit de l'unité, contrôleur délégué uniquement |

Le navigateur commence par `GET /session/`, puis envoie le cookie de session et l'en-tête `X-CSRFToken` issu du cookie `csrftoken` pour les écritures, y compris la connexion et la déconnexion. Aucun jeton permanent d'agent n'est utilisé. Les comptes locaux sont uniquement prévus pour la démonstration fictive.

Créer un dossier (compte `demo_manager`) :

```json
{
  "unit": "UUID_DE_L_UNITE_DEMO",
  "classification": 0,
  "assignee": 2,
  "next_action": "Contrôler la pièce fictive",
  "assignment_reason": "Affectation initiale fictive"
}
```

`assignee` est l'identifiant numérique du compte Django affiché par `seed_demo` ; l'exemple `2` peut différer sur une base existante. `classification` vaut `0` (ordinaire) ou `1` (restreint) dans cette politique de prototype. Une modification ou réaffectation fournit `version` reçue dans la fiche ; une version périmée renvoie `409` et ne modifie rien.

Exemple de réaffectation :

```json
{"version": 1, "assignee": 3, "reason": "Rééquilibrage fictif"}
```

Les erreurs API portent `code`, `message` et `request_id` ; les erreurs de validation ajoutent `fields`. Les listes sont filtrées avant sérialisation, avec `page` et `page_size` (maximum 100). Filtres de dossiers : `unit`, `status`, `reference` ; tris : `created_at`, `-created_at`, `reference`, `-reference`. Une ressource invisible donne `404`, une action interdite sur un dossier visible `403`.

## Contrôles

```powershell
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py spectacular --file openapi/v1.yaml --validate
```

Pour le contrôle de déploiement, utiliser `DJANGO_SETTINGS_MODULE=procezo.settings.prod`, `PROCEZO_SECRET_KEY`, `PROCEZO_ALLOWED_HOSTS` et un chemin absolu `PROCEZO_DB_PATH`, puis `python manage.py check --deploy`. La terminaison TLS et la confiance accordée à `X-Forwarded-Proto` doivent être configurées au niveau du proxy interne. La base et ses sauvegardes doivent être sur disque privé local. L'exploitation réelle attend les décisions DGDA du backlog.

Le contrôle de déploiement signale volontairement `security.W021` : le préchargement HSTS exige une décision sur le domaine final et n'est pas activé pour ce prototype interne.
