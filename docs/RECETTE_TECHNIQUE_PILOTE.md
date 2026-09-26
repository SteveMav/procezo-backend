# Étape 7 — recette technique et préparation du pilote fictif

Ce dossier couvre BE-20, BE-21 et la préparation backend de BE-23. Les tests automatiques utilisent des données fictives. L'ouverture sur données réelles exige encore les décisions DGDA DEC-02 à DEC-05, la mesure sur le réseau et le volume pilotes, une copie chiffrée hors hôte, une restauration sur l'infrastructure retenue et la décision formelle des responsables.

## BE-20 — matrice d'accès et d'échec

| Surface | Autorisé / refusé / panne vérifiés par |
| --- | --- |
| Dossiers, affectations, chronologie, concurrence | `cases.tests`, `platform_api.test_access_matrix` |
| Renseignements, identité de source, diffusion et retours | `intelligence.tests`, `documents.tests`, `platform_api.test_access_matrix`, `platform_api.test_journeys` |
| Pièces, quarantaine, téléchargement, empreinte, audit | `documents.tests`, `platform_api.test_access_matrix`, `platform_api.test_snapshot` |
| Demandes, actes, réponses, liens et appréciations | `requests_app.tests`, `platform_api.test_access_matrix`, `platform_api.test_journeys` |
| Missions, feuilles, projets PDF, défenses | `inspections.tests`, `platform_api.test_access_matrix`, `platform_api.test_journeys` |
| Décisions et GELEC, transitions et réessais | `decisions.tests`, `platform_api.test_access_matrix`, `platform_api.test_journeys` |
| Travail et statistiques, valeur et détail | `cases.tests`, `reporting.tests`, `platform_api.test_access_matrix`, `platform_api.test_journeys` |
| Erreurs `400/403/404/409/503`, champs et absence de source | Tests des domaines et `platform_api.test_access_matrix` |

La matrice transversale utilise un compte d'une autre unité, même avec `is_superuser=True`, et vérifie les listes, liens directs, fichiers, agrégats, créations et modification. Les tests métier vérifient la révocation, le scanner indisponible, la panne d'audit, les PDF interrompus, les versions concurrentes et les clés d'idempotence. Rejouer la suite sur SQLite et PostgreSQL via la CI ; en cas d'échec PostgreSQL, ne pas déclarer la double base validée.

```powershell
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py spectacular --file openapi/v1.yaml --validate
```

## BE-21 — sauvegarde et reprise SQLite

La sauvegarde embarque la base via l'API SQLite de sauvegarde en ligne, toutes les pièces privées, les PDF de demandes et de feuilles, puis un manifeste d'empreintes SHA-256 et de nombres d'objets. Elle refuse une pièce référencée absente ou altérée. Elle couvre également les événements d'audit, réponses, décisions et transferts présents dans la base. **Suspendre d'abord toutes les écritures HTTP et tout travail sur les fichiers** : le drapeau de commande atteste cette suspension, mais ne peut pas la faire respecter au niveau du proxy ou des processus. Un instantané base et fichiers pris pendant des écritures n'a pas de garantie de cohérence commune.

1. L'exploitation annonce la fenêtre, ferme les écritures au proxy, attend la fin des requêtes et du scan/PDF en cours, puis relève l'heure du dernier événement d'audit. Le circuit papier reste disponible.
2. Créer une destination neuve sur volume privé : `python manage.py snapshot_sqlite D:\snapshots\procezo-AAAA-MM-JJ --writes-suspended`. La commande vérifie la base, les références et les empreintes avant succès.
3. Exécuter `python manage.py verify_snapshot D:\snapshots\procezo-AAAA-MM-JJ`. Copier ensuite le répertoire entier vers un support **chiffré et protégé hors hôte** avec l'outil approuvé par l'exploitation ; vérifier la copie à destination avec `verify_snapshot`. Ne placer ni la copie ni son manifeste sous la racine web ou dans Git.
4. Sur une machine de reprise isolée, exécuter `python manage.py restore_snapshot D:\snapshots\procezo-AAAA-MM-JJ --database D:\reprise\db.sqlite3 --private-root D:\reprise\private`. Les deux destinations doivent être neuves. Configurer cette instance sur ces chemins, lancer `python manage.py check`, puis relire avec un compte habilité un acte, une réponse, une pièce et leur chronologie d'audit. Rapprocher les nombres et SHA-256 du manifeste ; consigner toute perte depuis la dernière sauvegarde.
5. Garder l'instance restaurée fermée aux écritures jusqu'à validation. Pour déployer une migration : sauvegarde vérifiée, migration sur copie, contrôle des trois parcours, puis ouverture. En échec **avant réouverture**, restaurer ensemble le binaire compatible, la base et les pièces de l'instantané ; **après nouvelles écritures**, établir une réconciliation explicite avant tout retour.

L'exercice automatisé `platform_api.test_snapshot.SQLiteRestorationExercise` utilise le vrai schéma Django et compare acte, réponse, pièce, feuille et audit après restauration. Il ne prouve ni la copie hors hôte, ni le chiffrement, ni les délais RPO/RTO. Fréquence, rétention, objectifs de perte et de reprise attendent DEC-05.

### Surveillance et incidents

`python manage.py ops_health --request-log CHEMIN_JOURNAL_JSON --require-log` émet des compteurs sans donnée métier et échoue si un seuil est franchi. L'exploitation doit fournir un journal JSON protégé et tournant, issu des lignes `procezo.requests`, puis exécuter cette commande régulièrement par son ordonnanceur avec collecte du code de sortie et alerte au responsable désigné. Le journal doit rester assez court pour que la fenêtre récente tienne dans les 10 derniers Mio ; sinon `request_log_truncated` bloque le contrôle. Paramètres : `--window-minutes`, `--min-free-bytes`, `--max-quarantine`, `--max-scan-failures`, `--max-api-5xx`, `--max-database-locks`. Les seuils par défaut sont conservateurs et **provisoires** : 15 minutes, 1 Gio libre, zéro quarantaine, scan raté, 5xx ou verrou.

| Signal | Action d'exploitation |
| --- | --- |
| `scanner_unconfigured`, `scanner_unavailable`, `quarantine_backlog` | Vérifier ClamAV, laisser les pièces en quarantaine, relancer l'analyse autorisée après remise en état. |
| `audit_failure` | Fermer les écritures sensibles, vérifier la base et l'audit avant réouverture ; une consultation sensible doit aussi échouer. |
| `database_locks`, `disk_low` | Vérifier disque local/WAL, transactions longues et capacité ; ne pas forcer des réessais d'actes. |
| `api_errors`, `pdf_failure` | Rapprocher `request_id`, route et horodatage dans les journaux techniques, puis contrôler l'état du brouillon et ses versions. |
| `request_log_missing`, `request_log_truncated` | Réparer la collecte avant de conclure à une absence d'incident. |

Le dernier événement d'audit, les volumes de quarantaine et les échecs de scan sont exposés par la commande. Les latences HTTP figurent dans les journaux JSON (`duration_ms`) ; leur collecte, p95/p99, routage d'alerte, disponibilité externe et contrôle de la copie hors hôte relèvent de l'infrastructure du pilote. Simuler une panne de scanner, d'audit et de disque sur une **copie fictive isolée**, puis joindre les codes de sortie et les preuves de non-ouverture au compte rendu.

## BE-23 — mesures et décision d'ouverture

Les tests `platform_api.test_journeys` rejouent JOURNEY-01 à 03 sur données fictives, avec refus d'un autre bureau, classements et chiffres rapprochés, défense partielle, GELEC transmis puis reçu, et alerte sans dossier. Ils ne remplacent pas la recette métier sur le réseau DGDA.

Depuis un poste du **réseau pilote**, avec un compte fictif habilité et un dossier connu du jeu représentatif :

```powershell
$env:PROCEZO_PILOT_USERNAME = "compte-de-recette"
$env:PROCEZO_PILOT_PASSWORD = "<secret fourni hors dépôt>"
python scripts/measure_pilot.py https://site-pilote-interne DOS-REFERENCE UUID-DU-DOSSIER --samples 50 --output D:\preuves\mesure.json
```

Le script ouvre une session protégée par CSRF, vérifie que la recherche retourne le dossier autorisé, mesure recherche et fiche séparément après trois passages de chauffe, puis calcule les p95. Cibles **provisoires** : recherche ≤ 3 s et ouverture ≤ 5 s. Conserver dans le procès-verbal la date, le poste/réseau, la révision Git, le nombre de dossiers/pièces, la concurrence, le résultat JSON et les écarts. Examiner les requêtes SQL/plans sur le même jeu : `reference` possède un index unique et le détail utilise la clé primaire ; le filtre de recherche `icontains` peut nécessiter une optimisation si la mesure échoue.

| Porte | État à documenter avant ouverture restreinte |
| --- | --- |
| Trois parcours fictifs, refus croisés et suite API sur les deux moteurs | Tests automatiques, puis procès-verbal métier signé |
| Recherche p95 ≤ 3 s et ouverture p95 ≤ 5 s | Mesure réseau sur volume pilote, ou écart accepté explicitement |
| Statistiques et actes rapprochables | Détail des indicateurs, preuves documentaires et audit vérifiés par le métier |
| Sauvegarde hors hôte et restauration complète | Exercice infrastructure, empreintes et temps mesurés |
| Scanner, audit, stockage, collecte de logs et alertes | Incidents simulés, responsables et seuils validés |
| DEC-02 à DEC-05, identité/MFA, hébergement et RPO/RTO | Décisions DGDA/DSI/exploitation explicites avant données réelles |

**Décision actuelle : ouverture réelle non autorisée.** L'exposition d'une source, d'un dossier ou d'une pièce hors droit, ou un acte irrégulier, suspend immédiatement le pilote. La décision d'ouverture doit être consignée par les responsables désignés après revue des preuves ci-dessus.
