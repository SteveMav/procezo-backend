# Procezo — backend, étapes 1 à 7

Cette livraison couvre **BE-01 à BE-19 et BE-22** du [backlog](docs/BACKLOG_BACKEND_PROCEZO.md) : API V1, droits, audit, dossiers, renseignements, diffusions, pièces privées, demandes, réponses, missions, feuilles, défenses, appréciations, décisions humaines, relais GELEC manuel, statistiques de prototype et préparation PostgreSQL. Elle utilise Django 5.2, DRF, SQLite et des sessions Django. Les rôles, unités et classifications sont une politique de **prototype** ; la matrice DGDA, la frontière GELEC et l'identité/MFA restent à approuver avant toute donnée réelle.

L'étape 7 ajoute les tests transversaux de droits et de parcours, une sauvegarde/restauration SQLite vérifiable et un contrôle d'exploitation. Le [dossier de recette et d'exploitation du pilote](docs/RECETTE_TECHNIQUE_PILOTE.md) donne les commandes et les portes d'ouverture. Les mesures sur le réseau pilote, l'exercice hors hôte et les décisions DGDA sont encore à réaliser avant toute donnée réelle.

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
| GET, POST | `/renseignements/` | Liste et création sans cible obligatoire |
| GET, PATCH | `/renseignements/{uuid}/` | Fiche et modification avec `version` |
| GET | `/renseignements/{uuid}/source/` | Identité réservée, délégation dédiée |
| GET, POST | `/renseignements/{uuid}/dossiers/` | Liens plusieurs à plusieurs, écriture avec `version` |
| GET, POST | `/renseignements/{uuid}/diffusions/` | Diffusions avec `idempotency_key` |
| GET | `/diffusions/{uuid}/` | Diffusion visible au bureau destinataire |
| POST | `/diffusions/{uuid}/confirmer/` | Confirmer l'envoi enregistré d'une diffusion en attente |
| GET, POST | `/diffusions/{uuid}/retours/` | Accusés et retours indépendants avec `idempotency_key` |
| GET, POST | `/documents/` | Liste par parent et dépôt multipart |
| GET | `/documents/{uuid}/`, `/documents/{uuid}/telecharger/` | Métadonnées et téléchargement contrôlé |
| POST | `/documents/{uuid}/reanalyser/` | Relancer l'analyse d'une pièce en quarantaine |
| GET, POST | `/demandes/?case={uuid}` | Liste d'un dossier et création d'une demande |
| GET, PATCH | `/demandes/{uuid}/` | Fiche, éléments, versions d'acte et édition conditionnelle du brouillon |
| GET | `/demandes/{uuid}/apercu/` | Aperçu structuré marqué comme projet fictif |
| POST | `/demandes/{uuid}/preparer/` | Créer ou retrouver la version PDF du projet ou associer un PDF importé |
| POST | `/demandes/{uuid}/soumettre/`, `/valider/`, `/retourner/` | Circuit de validation avec versions et historique |
| POST | `/demandes/{uuid}/constater-signature/`, `/constater-emission/` | Constats distincts avec pièces de preuve et clé d'idempotence |
| GET | `/demandes/{uuid}/historique/`, `/actes/{uuid}/telecharger/` | Historique et accès contrôlé à chaque version |
| GET, POST | `/demandes/{uuid}/reponses/` | Courriers reçus et compléments successifs |
| GET, POST | `/demandes/{uuid}/elements/{uuid}/appreciations/` | Historique des appréciations par élément |
| GET | `/reponses/{uuid}/` | Lecture d'une réponse |
| POST | `/reponses/{uuid}/rectifier-liens/` | Rectification historisée des liens |
| GET, POST | `/missions/?case={uuid}` | Missions et pièces du dossier |
| GET, POST | `/feuilles/?case={uuid}` | Feuilles et observations numérotées |
| GET, PATCH | `/feuilles/{uuid}/` | Lecture et édition conditionnelle de la feuille |
| GET | `/feuilles/{uuid}/apercu/` | Aperçu du projet fictif |
| POST | `/feuilles/{uuid}/preparer/` | Préparer le PDF du projet fictif |
| GET | `/projets-feuille/{uuid}/telecharger/` | Télécharger une version PDF privée |
| GET, POST | `/feuilles/{uuid}/defenses/` | Défenses et compléments successifs |
| GET, POST | `/feuilles/{uuid}/observations/{uuid}/appreciations/` | Appréciations motivées historisées |
| GET | `/defenses/{uuid}/` | Lire une défense |
| GET, POST | `/decisions/?case={uuid}` | Historique du dossier et proposition motivée depuis une appréciation |
| GET | `/decisions/{uuid}/`, `/decisions/{uuid}/historique/` | Décision et événements de validation ou de retour |
| POST | `/decisions/{uuid}/valider/`, `/decisions/{uuid}/retourner/` | Validation habilitée ou retour commenté |
| GET, POST | `/transferts-gelec/?case={uuid}` | Préparation du relais après validation |
| GET | `/transferts-gelec/{uuid}/` | État et preuves du transfert |
| POST | `/transferts-gelec/{uuid}/transmettre/`, `/confirmer-reception/` | Constats manuels distincts avec clés d'idempotence |
| GET | `/mon-travail/?kind=cases|requests|decisions`, `/a-valider/?kind=requests|decisions` | Travail et validations filtrés par les droits |
| GET | `/statistiques/?unit={uuid}&start=AAAA-MM-JJ&end=AAAA-MM-JJ` | Cinq familles de statistiques du périmètre visible |
| GET | `/statistiques/{key}/?unit={uuid}&start=AAAA-MM-JJ&end=AAAA-MM-JJ` | Objets comptés, paginés et filtrés par les droits |

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

## Renseignements et fichiers

La création d'un renseignement demande `unit`, `classification`, `subject`, `summary`, `provenance`, `occurred_on` et un `assignee` habilité ; aucune entreprise ni dossier n'est requis. `source_identity` est facultatif et réservé à un responsable disposant de `source.write`. La lecture de `/source/` exige séparément `source.read`. Les diffusions exigent `intelligence.distribute`. Ces délégations datées sont à créer pour les comptes fictifs concernés ; `is_staff` et `is_superuser` ne les remplacent pas. `sent_at` en création ou `/confirmer/` constate un envoi effectué hors de l'application ; aucun message externe n'est envoyé par cette API. Un responsable d'un bureau destinataire peut ensuite lire le renseignement diffusé et enregistrer ses propres retours, jamais sa source protégée.

Le dépôt multipart utilise `file` et exactement un parent `case` ou `intelligence`. Les pièces liées directement à un renseignement restent réservées aux délégations `source.write` et `source.read`, car elles peuvent contenir une identité de source. PDF, PNG et JPEG sont acceptés, jusqu'à 10 Mio et 20 pièces par parent. Les octets sont placés dans `PROCEZO_PRIVATE_FILES_ROOT` (par défaut `private/`, ignoré par Git) sous un nom UUID, sans route publique. `PROCEZO_CLAMSCAN_PATH` doit indiquer l'exécutable ClamAV `clamscan` pour analyser les pièces. Sans scanner ou en cas de délai/erreur, elles restent en `quarantine` et ne se téléchargent pas. Une analyse positive les met en `rejected`. L'application compare également l'empreinte SHA-256 avant téléchargement. Prévoir un volume privé durable et une procédure de sauvegarde des fichiers avec la base avant le pilote.

## Répétition SQLite vers PostgreSQL (BE-22)

La CI exécute `check`, les migrations, les tests et la génération du schéma sur SQLite et PostgreSQL. Pour une répétition sur une **copie fictive ou protégée**, figer les écritures, sauvegarder SQLite et les pièces, puis :

1. Configurer `PROCEZO_DB_PATH` sur la copie SQLite et `PROCEZO_PRIVATE_FILES_ROOT` sur la copie des pièces ; exécuter `python manage.py export_transfer CHEMIN_NOUVEAU`. Le répertoire contient `data.json` et un manifeste versionné avec empreinte et nombres d'objets. Il contient aussi les identités de source et mots de passe hachés : le protéger comme la base.
2. Créer une base PostgreSQL vide ; définir `PROCEZO_DB_ENGINE=postgresql`, `PROCEZO_PG_NAME`, `PROCEZO_PG_USER`, `PROCEZO_PG_PASSWORD`, `PROCEZO_PG_HOST`, `PROCEZO_PG_PORT`, puis `python manage.py migrate` et `python manage.py loaddata CHEMIN_NOUVEAU/data.json`.
3. Copier le répertoire privé vers l'hôte cible sans changer les noms UUID, puis exécuter `python manage.py verify_transfer CHEMIN_NOUVEAU`. Rejouer les parcours autorisés et refusés. Conserver SQLite intact jusqu'à la décision de bascule.

Le transfert ne déclenche aucune bascule de production. Après de nouvelles écritures sur PostgreSQL, un retour à SQLite nécessite une réconciliation des données créées.

## Demandes, réponses et travail à traiter

Une demande appartient à un dossier visible et modifiable. Elle enregistre le type et le nom de la cible, la personne représentée distincte si elle existe, l'objet, jusqu'à 20 éléments attendus et une échéance facultative. Plusieurs demandes peuvent appartenir au même dossier. Les modifications du brouillon exigent `version`; une version dépassée renvoie `409`. Un document importé ne demande pas la recopie du texte du courrier.

En mode `generated`, `POST /preparer/` avec `{"version": 1}` produit un PDF privé marqué **PROJET FICTIF - NON ÉMIS**. En mode `imported`, utiliser `{"version": 1, "document": "UUID"}` avec un PDF déjà accepté par `/documents/` et rattaché au même dossier. Chaque préparation est liée à une version de brouillon ; un réessai de la même version retrouve la même préparation. Les anciennes versions restent téléchargeables par les lecteurs autorisés du dossier. Une panne de génération ne modifie pas le brouillon.

La suite est `soumettre` → `valider` ou `retourner` → `constater-signature` → `constater-emission`. Chaque action exige la version courante. Le validateur doit être un responsable avec délégation `request.validate` et différent de l'auteur. Les constats suivants exigent `request.sign` et `request.issue`. La signature demande l'UUID d'un PDF accepté (`proof`) et la date réelle `signed_at` ; l'émission demande un PDF de preuve d'envoi (`dispatch_proof`), la date réelle `sent_at` et une `idempotency_key` UUID. Ces dates sont distinctes de l'horodatage serveur. Un réessai identique retourne l'émission initiale ; une clé différente renvoie `409`. Aucun courrier n'est envoyé par l'API. La réponse contient `issuance.prototype_only: true` : ces constats sont réservés aux données fictives jusqu'à validation de DEC-02/03.

Les réponses papier sont enregistrées avec un courrier importé et accepté (`letter`), leurs annexes, `received_on`, les UUID `item_ids` couverts et, pour un complément, `complement_of`. L'heure `recorded_at` est celle du serveur. La rectification des liens exige `version`, `reason`, `add_item_ids` et/ou `remove_link_ids` ; les liens retirés restent dans l'historique. Chaque appréciation exige sa propre version, un motif et trois axes distincts : `receipt` (`received`/`not_received`), `completeness` (`unknown`/`complete`/`insufficient`) et `substance` (`pending`/`satisfactory`/`unsatisfactory`). Aucune appréciation ne déclenche de suite automatique.

`/mon-travail/` pagine séparément les dossiers affectés (`kind=cases`) et les demandes de l'agent (`kind=requests`) ; `overdue` et `internal_alert` sont calculés à la lecture. `/a-valider/` ne retourne que les demandes soumises accessibles au responsable délégué, hors ses propres demandes. Ces alertes internes ne constituent pas une notification au tiers. La validation des habilitations, modèles, signature, émission et délais réels reste une décision DGDA.

## Missions, feuilles et défenses (BE-13 à BE-15)

Une mission se crée sur un dossier modifiable avec `case`, `context`, `findings`, `occurred_on`, `participants` (identifiants de comptes actifs habilités dans l'unité) et jusqu'à 20 UUID de `documents` acceptés du même dossier. Son événement apparaît dans `/dossiers/{uuid}/chronologie/`. Une mission ne crée ni feuille, ni infraction, ni PV.

Une feuille contient `case`, `origin`, `recipient_address`, `concerned_party`, `facts` et une liste de 1 à 20 `observations` avec `facts` et `documents`. Avec `mission`, l'origine doit être `mission` et la mission doit appartenir au dossier. Sans mission, seule l'origine `field` est ouverte pour le prototype fictif ; les autres origines attendent la règle DGDA DEC-03. La feuille reste un brouillon `prototype_only`. `PATCH` demande `version` et renvoie `409` sur conflit. Les observations ne peuvent plus être remplacées après une défense.

`POST /feuilles/{uuid}/preparer/` avec `{"version": 1}` crée ou retrouve un PDF privé marqué **PROJET FICTIF - NON ÉMIS**. Une génération interrompue laisse la feuille intacte. Chaque version préparée conserve son PDF et son empreinte ; le téléchargement vérifie l'empreinte et les droits du dossier. Ce PDF ne constate aucune validation, signature, émission ou notification officielle.

Une défense utilise un courrier `letter` accepté du dossier, `received_on`, les `observation_ids` couverts et éventuellement `annexes` et `complement_of`. Les courriers successifs restent distincts. Une appréciation utilise `version`, `defense`, `conclusion` (`pending`, `satisfactory`, `unsatisfactory`) et `reason`. Elle exige que la défense soit liée à l'observation ; les corrections ajoutent une nouvelle version. Aucune appréciation ne déclenche automatiquement une décision. Les pièces sont déposées par `/documents/` sur le dossier et doivent être acceptées après scan avant tout rattachement.

## Décisions et relais GELEC (BE-16 et BE-17)

Une proposition de décision exige `case`, `case_version`, `kind` (`classification`, `mission`, `complement`, `gelec`), `reason` et exactement une appréciation actuelle du dossier : `request_assessment` ou `observation_assessment`. Un motif vide, une appréciation encore en attente ou une version périmée sont refusés. Une seule proposition peut attendre validation par dossier. Après un retour ou une validation, une nouvelle proposition utilise `replaces` avec l'UUID de la décision précédente ; celle-ci reste consultable dans l'historique. Le validateur doit être un autre agent, responsable de l'unité et titulaire de la délégation datée `decision.validate`. `version` est obligatoire pour `valider` et `retourner` ; le retour exige `comment`. `/a-valider/?kind=decisions` et `/mon-travail/?kind=decisions` affichent les actions autorisées.

Seule une décision `gelec` validée et encore courante peut préparer un transfert. `gelec.transfer` est requis pour préparer et constater la transmission ; `gelec.confirm` est requis pour constater la réception. `transmettre` demande `version`, `idempotency_key`, `proof` (PDF accepté du dossier) et `transmitted_at`; `reference` est facultative. L'état devient `transmitted` même si la réception est incertaine. `confirmer-reception` demande une autre clé, un PDF de preuve et `received_at`; une référence peut alors être ajoutée. Les dates saisies restent distinctes des horodatages serveur. Un réessai identique retourne le même transfert ; une clé ou des faits différents donnent `409`. Aucun appel réseau à GELEC ni PV officiel n'est créé. Les décisions et transferts portent `prototype_only: true` en attendant DEC-02 et DEC-04.

## Statistiques vérifiables (BE-19)

`GET /api/v1/statistiques/?unit=UUID&start=2026-09-01&end=2026-09-30` renvoie les cinq familles, la version de définition `prototype-1`, la période inclusive en dates UTC, l'unité, les valeurs et leurs `detail_url`. Chaque détail retourne `count`, `next`, `previous` et les UUID/liens des objets comptés. `page` et `page_size` (maximum 100) paginent le détail. Les chiffres sont recalculés depuis les objets accessibles au lecteur, jamais saisis manuellement. Une unité sans appartenance active donne `404`; un enquêteur ne compte que ses dossiers et renseignements visibles, un responsable ceux de son unité selon sa classification. Les consultations sont auditées ; une panne d'audit bloque la réponse.

Les demandes émises suivent `issued_at`; les réponses et défenses suivent leur date réelle `received_on`; les feuilles, dossiers liés à un renseignement et renseignements suivent leur date d'enregistrement ; les classements suivent `validated_at` de la décision courante. Un classement remplacé par une décision validée ne reste pas dans le total. Les groupes de provenance et les suites « lié à un dossier », « diffusé » et « avec retour » comptent chaque renseignement une fois ; un dossier lié à deux renseignements reste un seul dossier. Les deux dernières suites exigent la délégation `intelligence.distribute` et leurs détails aussi. Le lien à un dossier ne prouve pas un effet métier.

Les feuilles émises/notifiées, les effets métier et les dossiers avec PV établi ont `status: masked`, `value: null` et aucun détail : les événements ou preuves nécessaires ne sont pas encore définis. Une transmission GELEC ne devient jamais un PV par calcul. La DGDA doit valider définitions, périodes, visibilité et preuve de PV avant une diffusion réelle des tableaux.

## Contrôles

```powershell
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py spectacular --file openapi/v1.yaml --validate
```

Pour le contrôle de déploiement, utiliser `DJANGO_SETTINGS_MODULE=procezo.settings.prod`, `PROCEZO_SECRET_KEY`, `PROCEZO_ALLOWED_HOSTS` et un chemin absolu `PROCEZO_DB_PATH`, puis `python manage.py check --deploy`. La terminaison TLS et la confiance accordée à `X-Forwarded-Proto` doivent être configurées au niveau du proxy interne. La base et ses sauvegardes doivent être sur disque privé local. L'exploitation réelle attend les décisions DGDA du backlog.

Le contrôle de déploiement signale volontairement `security.W021` : le préchargement HSTS exige une décision sur le domaine final et n'est pas activé pour ce prototype interne.
