# Procezo — tâches backend du pilote V1

## Execution Verdict

- **Livraison recommandée :** construire un monolithe Django/DRF par parcours métier vérifiables, puis préparer un pilote restreint.
- **Premier incrément exécutable :** un dossier fictif créé, affecté, consultable par les seules personnes autorisées, avec prochaine action et historique d'audit.
- **Chemin critique :** API et droits → audit → dossier → documents → demande et réponse → décision humaine → statistiques et recette du pilote.
- **Risque principal :** une liste, une pièce, un export ou un agrégat révèle un dossier ou une source protégée hors habilitation.
- **Décision nécessaire pour commencer :** aucune ; le prototype utilise des données fictives et refuse par défaut les actions dont la règle officielle manque.
- **Décisions avant données ou actes réels :** pouvoirs et habilitations, modèles et circuits d'actes, frontière GELEC/PV, conservation et exploitation (DEC-02 à DEC-05 du PRD).
- **Confiance :** élevée sur les capacités à réaliser ; moyenne sur l'ordre de finalisation des actes et des chiffres, qui dépend des validations DGDA.

## Contrat de planification

Ce document est un backlog **backend**, destiné au développement et à la recette du pilote V1. Il s'appuie sur [l'architecture backend](ARCHITECTURE_BACKEND_PROCEZO.md) et le [PRD V1](PRD_PROCEZO_V1.md). Les modules BE-01 à BE-18 et la préparation BE-22 sont désormais présents dans le dépôt ; les modules des étapes suivantes restent des responsabilités proposées tant qu'ils ne sont pas implémentés.

La V1 couvre les renseignements, dossiers, affectations, demandes, réponses, missions facultatives, feuilles, défenses, décisions humaines, relais GELEC manuel et cinq familles de statistiques. Le contentieux détaillé, le calcul et le recouvrement, le portail des tiers et les synchronisations GELEC/SYDONIA sont exclus. Une migration de l'ancien Procezo n'est pas présumée.

**Invariants communs :** API interne `/api/v1`, monolithe modulaire Django/DRF, SQLite sur disque local privé pour la petite V1, pièces hors racine web, compatibilité préparée avec PostgreSQL, contrôle des droits sur chaque accès, audit métier transactionnel, versions émises et reçues non écrasées. Les brouillons utilisent une version et signalent les conflits par `409`. Les dates de fait, de réception et d'enregistrement restent distinctes.

Les priorités `P0` et `P1` indiquent l'ordre de construction, sans retirer le caractère **Must** des exigences du pilote. Les dépendances indiquées sont **dures**, sauf lorsqu'elles sont signalées comme externes. Les validations DGDA ne bloquent pas le développement ni la recette sur données fictives ; elles bloquent les usages réels correspondants.

### Definition of Ready et Definition of Done communes

- **Ready :** le ticket a un comportement observable, une zone responsable, des données fictives de test et ses dépendances satisfaites. Si une règle officielle manque, la fonction reste en mode prototype ou désactivée pour usage réel.
- **Done :** les critères d'acceptation et les refus pertinents sont démontrés, les tests prévus passent, le contrat API est documenté, l'audit et les droits sont vérifiés, et les changements de données disposent d'une migration rejouable.

## Backlog priorisé

### Étape 1 — Socle sûr et premier dossier (BE-01 à BE-04)

**Statut : fait pour le prototype fictif (BE-01 à BE-04).** API, droits, audit, dossier et affectations livrés ; 14 tests passés, migrations appliquées et schéma OpenAPI validé. Voir le [guide d'exécution](../README.md).

**But :** obtenir un premier parcours de bout en bout, avec autorisation et audit dès le départ. **Sortie :** un agent autorisé ouvre un dossier fictif, voit son responsable et sa prochaine action ; un autre agent est refusé ; une réaffectation reste historisée.

### BE-01 — Exposer une API V1 cohérente

- **Type / priorité / responsable :** enabler · P0 · `platform`.
- **Source :** architecture, « API DRF interne », ADR-01.
- **Dépendances :** aucune.
- **Résultat :** projet Django/DRF, configuration séparée par environnement, `/api/v1`, identifiant de requête, pagination, filtres et tris autorisés, format stable des erreurs, OpenAPI versionnée. Aucun secret ni trace d'exception dans les réponses.
- **Critères d'acceptation :** une entrée invalide donne `400`, une ressource invisible `404`, une action interdite sur une ressource visible `403`, un conflit `409` et une dépendance indisponible `503`, avec `code`, `message` sûr et `request_id`.
- **Vérification :** tests de contrat API et contrôle de configuration de production.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### BE-02 — Décider et appliquer les droits d'accès

- **Type / priorité / responsable :** sécurité · P0 · `identity`.
- **Source :** FR-12/AC-12, NFR-03, ADR-03.
- **Dépendances :** BE-01.
- **Résultat :** utilisateurs, unités, appartenances et délégations datées ; sessions protégées, CSRF sur écritures et politique centrale `can(actor, action, resource, context)`. Identité et droits indéterminés sont refusés.
- **Critères d'acceptation :** rôle, unité, relation à l'objet et classification sont contrôlés ; la révocation retire l'accès à la requête suivante ; `is_staff` ou `is_superuser` ne donne aucun droit métier implicite.
- **Vérification :** matrice de tests par rôle/unité/objet, session, expiration et révocation.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### BE-03 — Rendre l'audit métier obligatoire

- **Type / priorité / responsable :** sécurité · P0 · `audit`.
- **Source :** FR-12/AC-12, architecture « Trois journaux », ADR-04.
- **Dépendances :** BE-01.
- **Résultat :** événements métier à ajout seul pour mutations, consultations sensibles, validations, téléchargements et exports ; journaux techniques structurés séparés, sans données de source, pièces, corps HTTP ni secrets.
- **Critères d'acceptation :** mutation et audit sont validés ou annulés ensemble ; une consultation sensible échoue si son audit obligatoire ne peut être persisté ; aucune API ordinaire ne modifie ou supprime un événement.
- **Vérification :** tests de transaction, panne d'audit et inspection des journaux.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### BE-04 — Créer et affecter un dossier traçable

- **Type / priorité / responsable :** fonctionnalité · P0 · `cases`.
- **Source :** FR-03/AC-03, NFR-06, JOURNEY-01.
- **Dépendances :** BE-02, BE-03.
- **Résultat :** dossier, affectations historisées, responsable, statut, prochaine action et chronologie ; mises à jour conditionnelles par version.
- **Critères d'acceptation :** une réaffectation conserve ancien responsable, auteur, date et motif ; l'ancien agent perd l'accès si ses autres droits ne le couvrent pas ; deux éditions concurrentes ne s'écrasent pas et la seconde reçoit `409`.
- **Vérification :** tests API, permissions et concurrence sur SQLite.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### Étape 2 — Renseignement, diffusion et fichiers privés (BE-05 à BE-07, BE-22)

**Statut : fait pour le prototype fictif sur SQLite (BE-05 à BE-07 et préparation BE-22).** Les modules `intelligence` et `documents`, la quarantaine, l'analyse ClamAV configurable, les migrations et la CI SQLite/PostgreSQL sont présents ; 26 tests SQLite passent. La validation PostgreSQL et la répétition du transfert seront faites plus tard. La configuration du scanner dans l'environnement pilote et l'usage réel attendent les décisions DGDA.

**But :** couvrir le renseignement autonome et poser la frontière des pièces avant les actes. **Sortie :** un renseignement sans cible peut être diffusé à deux unités sans dévoiler sa source ; un fichier n'est accessible qu'après contrôle.

### BE-05 — Enregistrer un renseignement, y compris sans cible

- **Type / priorité / responsable :** fonctionnalité · P0 · `intelligence`.
- **Source :** FR-01/AC-01, FR-18/AC-18, JOURNEY-03.
- **Dépendances :** BE-02, BE-03 ; BE-04 pour le lien au dossier.
- **Résultat :** objet, résumé, provenance, date de fait, confidentialité et responsable ; identité de source dans une table réservée ; lien renseignement–dossier plusieurs à plusieurs.
- **Critères d'acceptation :** aucun nom d'entreprise ni dossier n'est obligatoire ; une source protégée n'apparaît ni dans le résumé ordinaire ni dans une réponse API non habilitée ; un renseignement peut lier deux dossiers sans duplication.
- **Vérification :** tests de création sans cible, de liens multiples et d'accès à la source.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### BE-06 — Suivre chaque diffusion et retour séparément

- **Type / priorité / responsable :** fonctionnalité · P1 · `intelligence`.
- **Source :** FR-02/AC-02, FR-18/AC-18.
- **Dépendances :** BE-05.
- **Résultat :** destinataire, canal ou référence, date, action attendue, accusé et retours par diffusion ; idempotence des réessais.
- **Critères d'acceptation :** le retour d'une unité ne clôt pas celui d'une autre ; une interruption suivie d'un réessai ne crée pas deux diffusions confirmées ; le renseignement peut rester sans dossier.
- **Vérification :** scénario à deux unités, doublon et contrôle des droits.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### BE-07 — Stocker et servir les pièces sous contrôle

- **Type / priorité / responsable :** fonctionnalité et sécurité · P0 · `documents`.
- **Source :** FR-08/AC-08, NFR-02/03, architecture « Cohérence ».
- **Dépendances :** BE-02, BE-03.
- **Résultat :** quarantaine privée, bornes de taille/type/nombre, empreinte SHA-256, analyse antivirus, états d'opération et rattachement transactionnel. Les téléchargements repassent par la politique d'accès.
- **Critères d'acceptation :** une pièce non analysée ou rejetée est illisible ; scanner indisponible signifie quarantaine, pas acceptation ; un fichier manquant est signalé ; aucun lien public durable ni chemin fondé sur le nom fourni par le client.
- **Vérification :** fichiers invalides, panne scanner, coupure pendant dépôt, accès direct et fichier manquant.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### BE-22 — Garder une voie de migration vers PostgreSQL

- **Type / priorité / responsable :** enabler continu · P0 · `platform` et données.
- **Source :** ADR-02, architecture « Passage préparé de SQLite vers PostgreSQL ».
- **Dépendances :** BE-04 pour le premier schéma ; à réévaluer à chaque nouveau domaine.
- **Résultat :** migrations et requêtes ORM compatibles, CI testant les flux critiques sur SQLite et PostgreSQL, export applicatif versionné et procédure de répétition du transfert.
- **Critères d'acceptation :** migrations, droits, transitions, idempotence et comptages déjà disponibles passent sur les deux moteurs ; aucune bascule de production n'est déclenchée sans signal de charge ou d'exploitation.
- **Vérification :** CI sur deux bases et répétition documentée sur copie fictive ou protégée.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### Étape 3 — Demandes, actes et réponses (BE-08 à BE-12, BE-18)

**Statut : fait (prototype fictif).** Les demandes et leurs éléments versionnés, deux modes de préparation, versions de projet privées, transitions distinctes, réponses et rectifications historisées, appréciations par élément et vues de travail sont implémentés. Les constats de signature et d'émission restent des enregistrements fictifs ; DEC-02/03 bloquent toujours l'usage réel.

**But :** achever le parcours d'une demande depuis le brouillon jusqu'à l'analyse des réponses. **Sortie :** les deux modes de préparation rejoignent la même validation et conservent l'acte réellement envoyé ; deux réponses successives restent distinctes.

### BE-08 — Créer une demande et ses éléments attendus

- **Type / priorité / responsable :** fonctionnalité · P0 · `requests`.
- **Source :** FR-04/AC-04, FR-15/AC-15.
- **Dépendances :** BE-04, BE-07.
- **Résultat :** fiche de suivi avec auteur, cible, personne représentée distincte, objet et éléments demandés ; plusieurs demandes possibles par dossier ; brouillon versionné.
- **Critères d'acceptation :** un document importé n'impose pas de ressaisie de son texte intégral ; la personne représentée n'est pas confondue avec la cible ; parent non autorisé et version dépassée sont refusés.
- **Vérification :** tests de champs, de permissions parent et de conflit `409`.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### BE-09 — Préparer l'acte dans les deux modes

- **Type / priorité / responsable :** fonctionnalité · P1 · `requests` et `documents`.
- **Source :** FR-07/AC-07, FR-08/AC-08, NFR-02.
- **Dépendances :** BE-08.
- **Résultat :** aperçu et PDF imprimable du format Procezo, ou import contrôlé du document de l'agent ; génération bornée, reprenable et sans écrasement de version.
- **Critères d'acceptation :** les deux modes gardent le même dossier et le même circuit ; PDF, import et impression ne marquent jamais l'acte signé ou émis ; une génération interrompue laisse le brouillon reprenable.
- **Vérification :** deux parcours, coupure PDF, réessai idempotent et contrôle des versions.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### BE-10 — Valider, signer et tracer l'émission d'un acte

- **Type / priorité / responsable :** fonctionnalité · P1 · `requests`.
- **Source :** FR-07/08, AC-07/08, DEC-02/03.
- **Dépendances :** BE-09, BE-02, BE-03 ; **externe :** matrice et circuit DGDA avant émission réelle.
- **Résultat :** soumission, validation, constat de signature, émission et preuve d'envoi en états distincts ; version émise immuable et action d'émission idempotente.
- **Critères d'acceptation :** auteur non habilité, version invalide ou preuve obligatoire manquante bloquent l'étape ; un réessai renvoie le résultat initial sans seconde émission ; projet et version envoyée restent consultables séparément.
- **Vérification :** matrice de transitions, refus, double soumission et audit.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### BE-11 — Recevoir plusieurs réponses et annexes

- **Type / priorité / responsable :** fonctionnalité · P1 · `requests`.
- **Source :** FR-04/AC-04, FR-08/AC-08.
- **Dépendances :** BE-08, BE-07. BE-10 est un prérequis de recette du parcours complet, pas de la saisie d'une réponse fictive.
- **Résultat :** courriers et compléments successifs, pièces, date réelle de réception, date d'import et rattachement aux éléments demandés.
- **Critères d'acceptation :** une réponse couvrant un élément puis un complément couvrant un autre restent visibles ; une rectification de lien garde son historique ; un nouvel import n'écrase pas l'original.
- **Vérification :** scénario à trois éléments et deux courriers, avec rectification.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### BE-12 — Apprécier chaque élément sans suite automatique

- **Type / priorité / responsable :** fonctionnalité · P1 · `requests`.
- **Source :** FR-05/AC-05, FR-16/AC-16.
- **Dépendances :** BE-11.
- **Résultat :** réception, complétude et appréciation de fond par élément, avec motifs et historique des corrections.
- **Critères d'acceptation :** « reçu mais insuffisant » et « non reçu » sont distincts ; aucun de ces états ne devient une infraction ni une décision par automatisme.
- **Vérification :** tests par élément, correction et absence de transition automatique.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### BE-18 — Présenter le travail à traiter selon les droits

- **Type / priorité / responsable :** fonctionnalité · P1 · `cases`.
- **Source :** FR-14/AC-14.
- **Dépendances :** BE-04 ; intégrer les états de BE-10, BE-11 et BE-16 à leur livraison.
- **Résultat :** endpoints « Mon travail » et « À valider », avec affectations, actes soumis, retours, échéances et lien vers l'action autorisée.
- **Critères d'acceptation :** un agent ne voit que son périmètre ; un retard est calculé sans modifier le statut ; une alerte interne n'est pas une notification officielle au tiers.
- **Vérification :** scénarios d'affectation, de soumission, de retard et de refus.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### Étape 4 — Mission, feuille et défenses (BE-13 à BE-15)

**Statut : fait pour le prototype fictif sur SQLite (BE-13 à BE-15).** Missions, feuilles versionnées, PDF de projet privé, défenses et appréciations historisées sont présents. Les origines et le modèle officiels restent soumis à DEC-03 avant tout acte réel.

**But :** couvrir les constats avec ou sans mission lorsque la règle DGDA l'autorise. **Sortie :** une feuille à deux observations accepte une défense partielle et un complément, sans perte d'historique.

### BE-13 — Enregistrer une mission facultative

- **Type / priorité / responsable :** fonctionnalité · P1 · `inspections`.
- **Source :** FR-13/AC-13.
- **Dépendances :** BE-04, BE-07.
- **Résultat :** contexte, participants, constats, pièces et lien au dossier ; événement de chronologie.
- **Critères d'acceptation :** mission et pièces sont retrouvables ; sa création ne produit ni infraction, ni feuille, ni PV automatiquement.
- **Vérification :** cas à deux participants et trois pièces.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### BE-14 — Préparer une feuille à observations numérotées

- **Type / priorité / responsable :** fonctionnalité · P1 · `inspections`.
- **Source :** FR-06/07/17, AC-06/07/17, DEC-03.
- **Dépendances :** BE-04, BE-07. BE-13 est facultatif selon l'origine ; **externe :** origine et modèle DGDA avant acte réel.
- **Résultat :** auteur, adresse du destinataire, partie concernée, origine du constat, faits, observations numérotées, pièces et PDF de projet borné.
- **Critères d'acceptation :** une feuille peut citer une mission ; une feuille sans mission est possible uniquement pour une origine autorisée ; le PDF de projet ne vaut pas émission.
- **Vérification :** cas avec mission, sans mission autorisée et sans mission interdite.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### BE-15 — Conserver défenses, compléments et appréciations

- **Type / priorité / responsable :** fonctionnalité · P1 · `inspections`.
- **Source :** FR-06/AC-06, FR-16/AC-16.
- **Dépendances :** BE-14, BE-07.
- **Résultat :** défense liée à une ou plusieurs observations, compléments, documents et appréciations motivées historisées.
- **Critères d'acceptation :** une défense couvrant seulement la première de deux observations laisse la seconde sans défense ; un complément n'écrase ni défense ni appréciation antérieure.
- **Vérification :** scénario de défense partielle, complément et contrôle d'accès.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### Étape 5 — Décision humaine et relais GELEC (BE-16 à BE-17)

**Statut : fait pour le prototype fictif (BE-16 et BE-17).** Propositions motivées liées aux appréciations, retours et validations habilitées, rectifications historisées, transmission GELEC manuelle et réception confirmée séparément sont disponibles. Les actes réels attendent DEC-02 et DEC-04.

**But :** terminer les dossiers par une décision vérifiable. **Sortie :** classement ou relais uniquement après validation habilitée ; transmission GELEC et réception restent deux faits distincts.

### BE-16 — Valider une suite motivée

- **Type / priorité / responsable :** fonctionnalité · P1 · `decisions`.
- **Source :** FR-09/AC-09, FR-16/AC-16, DEC-02.
- **Dépendances :** BE-12 et BE-15 pour couvrir les deux origines du pilote, BE-02, BE-03 ; **externe :** pouvoirs DGDA avant décision réelle.
- **Résultat :** proposition motivée, retour avec commentaire, validation habilitée, classement ou orientation, historique de rectification.
- **Critères d'acceptation :** proposition sans motif refusée ; auteur seul ne peut valider par défaut ; une appréciation ne déclenche aucune suite ; une décision validée reste dans l'historique après correction.
- **Vérification :** tests de transitions, de droits, de motifs et d'audit.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### BE-17 — Tracer le transfert manuel vers GELEC

- **Type / priorité / responsable :** fonctionnalité · P1 · `decisions`.
- **Source :** FR-10/AC-10, ADR-06, DEC-04.
- **Dépendances :** BE-16 ; **externe :** frontière et preuve DGDA/GELEC avant relais réel.
- **Résultat :** préparation, transmission manuelle, référence si disponible, preuve et confirmation explicite de réception, avec clé d'idempotence.
- **Critères d'acceptation :** une référence absente n'est pas inventée ; une transmission incertaine reste transmise mais non confirmée ; une seconde confirmation ne crée pas un second transfert.
- **Vérification :** réessai, perte de réponse HTTP et confirmation tardive.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### Étape 6 — Statistiques vérifiables (BE-19)

**Statut : fait pour le prototype fictif (BE-19), avec indicateurs sans preuve masqués.** Les valeurs publiées utilisent les objets visibles et une liste de détail issue de la même règle de calcul ; la provenance et les suites documentées sont dédupliquées. Les définitions métier, les effets et la preuve de PV attendent la DGDA avant toute diffusion réelle.

**But :** obtenir les cinq familles de chiffres sans double compte ni fuite de données. **Sortie :** chaque valeur ouvre exactement les objets autorisés qui la composent.

### BE-19 — Produire les cinq familles de statistiques

- **Type / priorité / responsable :** fonctionnalité · P1 · `reporting`.
- **Source :** FR-11/AC-11, FR-19/AC-19, DEC-04, MET-04.
- **Dépendances :** BE-06, BE-10, BE-14, BE-16, BE-17 ; **externe :** définitions et visibilité DGDA avant diffusion des chiffres.
- **Résultat :** demandes et réponses ; feuilles et défenses ; classements sans suite ; dossiers avec PV prouvé ; renseignements, provenances, suites et effets. Chaque indicateur porte période, unité, définition versionnée et liste sous-jacente filtrée.
- **Critères d'acceptation :** chaque objet est compté une fois selon sa règle ; un dossier lié à deux renseignements n'est pas doublé ; « orienté vers PV » n'est pas « PV établi » ; l'indicateur PV reste masqué tant que sa preuve n'est pas définie.
- **Vérification :** jeu connu avec liens multiples, rapprochement papier et tests de droits sur valeur et détail.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### Étape 7 — Recette technique et ouverture du pilote (BE-20, BE-21, BE-23)

**Statut : préparation technique livrée sur données fictives ; ouverture du pilote réel en attente.** La matrice transversale, les trois parcours d'intégration, la sauvegarde/restauration SQLite et la sonde d'exploitation sont présents. La mesure sur réseau et volume pilotes, la copie chiffrée hors hôte, l'exercice d'incident sur l'infrastructure retenue et les validations DGDA restent nécessaires. Voir le [dossier de recette technique](RECETTE_TECHNIQUE_PILOTE.md).

**But :** consolider les preuves de sécurité, de performance et de reprise. Les tests de BE-20 se construisent au fil des étapes précédentes ; cette étape clôt leur couverture, elle ne reporte pas la sécurité à la fin.

### BE-20 — Vérifier tous les chemins d'accès et d'échec

- **Type / priorité / responsable :** test et sécurité · P1 · transversal.
- **Source :** FR-12/AC-12, NFR-02/03/06, architecture « Validation et portes de passage ».
- **Dépendances :** BE-02 et chaque domaine au fur et à mesure ; couverture complète après BE-19.
- **Résultat :** matrice de tests pour liste, détail, création, champs, fichiers, exports éventuels et agrégats ; entrées invalides, coupures, conflits, doublons et refus.
- **Critères d'acceptation :** aucun chemin testé ne révèle objet, existence protégée ou identité de source hors droit ; les erreurs restent stables et sans secret ; les réessais ne doublent pas les actes.
- **Vérification :** suite d'intégration et contrats API exécutés sur les deux bases lorsque pertinent.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### BE-21 — Restaurer et surveiller base, pièces et audit

- **Type / priorité / responsable :** exploitation · P1 · `platform`, `documents`, `audit`.
- **Source :** NFR-05, DEC-05, architecture « Déploiement et exploitation ».
- **Dépendances :** BE-03, BE-07 ; **externe :** objectifs de reprise et politique de conservation avant données réelles.
- **Résultat :** sauvegarde SQLite cohérente avec pièces et audit, copie protégée hors hôte, restauration documentée ; métriques et alertes sur verrous, disque, quarantaine, scan, PDF, audit et erreurs API ; procédure de déploiement et retour avant réouverture.
- **Critères d'acceptation :** restauration des actes, réponses, pièces et événements avec comparaison de références et empreintes ; panne de scanner maintient la quarantaine ; panne d'audit bloque l'action sensible et alerte.
- **Vérification :** exercice de restauration et incidents simulés. Les seuils RPO/RTO restent à approuver.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

### BE-23 — Démontrer les parcours et décider l'ouverture restreinte

- **Type / priorité / responsable :** validation et déploiement · P1 · backend avec métier et exploitation.
- **Source :** JOURNEY-01 à 03, NFR-01/05, PRD « Déploiement et critère de passage ».
- **Dépendances :** BE-01 à BE-22 pour le périmètre pilote ; décisions DGDA décrites dans les portes ci-dessous avant données réelles.
- **Résultat :** jeu fictif représentatif, mesure de recherche et d'ouverture de dossier sur le réseau pilote, revue des requêtes/index, rejeu des trois parcours et dossier de preuves pour l'ouverture.
- **Critères d'acceptation :** cibles provisoires de p95 recherche ≤ 3 s et ouverture ≤ 5 s mesurées ou écart explicitement décidé ; aucune consultation hors droit ; actes, décisions et chiffres rapprochables ; restauration démontrée. Une exposition sensible ou un acte irrégulier suspend le pilote.
- **Vérification :** compte rendu de recette, mesures, exercice de reprise et décision d'ouverture par les responsables désignés.
- **Prêt à démarrer :** dépendances satisfaites et données fictives du scénario disponibles.
- **Terminé lorsque :** critères démontrés, vérification passée et contrat API ou migration mis à jour si nécessaire.

## Graphe des dépendances

- **Chaîne critique provisoire :** BE-01 → BE-02/03 → BE-04 → BE-07 → BE-08 → BE-09 → BE-10 → BE-11/12 → BE-16 → BE-17 → BE-19 → BE-23. BE-11 peut commencer avant BE-10 sur données fictives ; le parcours complet requiert les deux.
- **En parallèle après BE-04 :** BE-05, BE-07, BE-13, BE-18 et le démarrage de BE-22.
- **En parallèle après BE-07 :** demande (BE-08 à BE-12) et mission/feuille (BE-13 à BE-15), avec intégration des contrats documentaires commune.
- **Contrôles continus :** BE-20 suit chaque nouvelle API ; BE-22 suit chaque migration ; BE-21 démarre dès que base, audit et pièces existent.
- **Dépendances externes :** DEC-02/03 pour les actes et décisions réels, DEC-04 pour relais/PV réels, DEC-05 pour données réelles. Elles ne bloquent pas la démonstration fictive.

## Matrice de traçabilité

| Résultat PRD | Tickets | Preuve principale |
| --- | --- | --- |
| Renseignement, diffusion, dossier et travail à traiter — FR-01/02/03/14/18 | BE-04/05/06/18 | JOURNEY-03 et affectation/révocation |
| Demande, document, réponses et appréciations — FR-04/05/07/08/15 | BE-07 à BE-12 | JOURNEY-01, réponse puis complément |
| Mission, feuille et défenses — FR-06/13/17 | BE-13/14/15 | JOURNEY-02, défense partielle |
| Suite humaine et GELEC — FR-09/10/16 | BE-16/17 | Retour, validation et confirmation séparés |
| Droits et traçabilité — FR-12, NFR-02/03/06 | BE-02/03/07/20 | Matrice de refus, coupures et conflits |
| Indicateurs — FR-11/19 | BE-19 | Comptage rapproché de la liste visible |
| Performance et reprise — NFR-01/05 | BE-21/23 | Mesures et restauration complète |

## Portes de décision

| Décision | Nécessaire avant | Repli du prototype | Autorité attendue |
| --- | --- | --- | --- |
| DEC-02 — pouvoirs, délégations et habilitations | Validation, émission et décision réelles | Refus par défaut, comptes et données fictifs | DGDA/DSI |
| DEC-03 — modèles, mentions, signature, notification et origines | Actes et feuilles réels | PDF marqués comme projets | DGDA métier |
| DEC-04 — PV, GELEC et preuve de réception | Relais réel et indicateur PV publié | Transfert simulé, indicateur masqué | DGDA et responsable GELEC |
| DEC-05 — conservation, hébergement, sauvegarde, RPO/RTO | Données réelles | Environnement fictif isolé | DGDA et exploitation |

## Handoff for Development

Commencer par **BE-01 à BE-04**. La première revue doit démontrer création, affectation, lecture autorisée, refus, révocation, audit et conflit de version sur un dossier fictif. Réaliser ensuite BE-05 et BE-07 pour éprouver tôt la confidentialité de source et les fichiers privés. Maintenir les contrats d'API, de droits, d'audit et de versions communs à tous les domaines. Ne pas figer un pouvoir, un délai ou une preuve GELEC encore non approuvé.

## Handoff for QA

Préparer des comptes de rôles et d'unités différents, une délégation révoquée, un renseignement sans cible, deux dossiers liés au même renseignement, une demande à trois éléments avec deux réponses, une feuille à deux observations avec défense partielle, et un transfert GELEC non confirmé. Rejouer JOURNEY-01 à 03 avec données fictives. Tester les refus par lien direct, liste, détail, pièce et statistique ; les coupures de scan/PDF/audit ; la concurrence ; les doubles soumissions ; puis la restauration complète. L'ouverture avec données réelles exige les décisions DEC-02 à DEC-05 et les preuves de BE-23.

