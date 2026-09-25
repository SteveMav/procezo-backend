# Procezo — exigences produit pour le pilote V1

Version de travail du 25 septembre 2026. Ce document spécifie un **pilote DGDA**, sous réserve des décisions métier indiquées ci-dessous. Les modèles, habilitations, délais et actes officiels n'y sont pas présumés approuvés.

<!-- prd-section: product-verdict -->
## Product Verdict

- **Décision produit :** centrer le pilote sur le dossier d'enquête, sa prochaine action et ses preuves ; couvrir les quatre besoins V1 et les fonctions de la note de cadrage nécessaires à leurs parcours, y compris mission de contrôle, documents, décisions et relais GELEC.
- **Acteur et résultat :** l'enquêteur et son responsable retrouvent le responsable, les actes, les réponses, les documents, les décisions et la prochaine action ; le responsable peut justifier les chiffres à partir des dossiers.
- **Frontière V1 :** de la réception d'un renseignement ou d'une instruction jusqu'au classement motivé ou au relais tracé vers GELEC ; demande préparée avec le format proposé par Procezo ou par import du document de l'agent, puis validation, signature, remise et réception documentées.
- **Ambiguïté principale :** les pouvoirs, modèles et circuits officiels de la DGDA restent à valider. La distinction P1/P2 de la note définit une séquence de réalisation, tandis que le pilote V1 couvre aussi les feuilles et statistiques, conformément à la décision du demandeur.
- **À décider maintenant :** unité pilote, pouvoirs et modèles applicables, règles d'accès aux sources, frontière des différents PV.
- **Peut attendre :** interface automatisée GELEC ou SYDONIA, portail externe, analyses avancées.
- **Préparation : `not ready` pour des données réelles ou l'émission d'actes.** Ce PRD sert au rejeu métier et à la conception conditionnelle ; les décisions DGDA bloquantes figurent plus bas.
- **Confiance : moyenne** sur les parcours proposés, faible sur les règles officielles et le gain réel, faute d'observation et de validation par l'autorité métier.

<!-- prd-section: product-contract -->
## Contrat produit

**Objectif.** Réduire les pertes de contexte entre renseignements, enquêtes, correspondances, observations et décisions, tout en conservant une traçabilité exploitable. La direction produit proposée est un dossier commun avec chronologie et prochaine action explicite. Un renseignement diffusé sans cible peut rester indépendant d'un dossier.

**Horizon.** Prototype avec données fictives, rejeu de trois cas anonymisés avec la DGDA, puis pilote limité dans une unité désignée. Aucune date ni budget de livraison n'est établi.

**Limites.** Procezo suit l'enquête avant le contentieux détaillé. Il ne calcule ni ne recouvre droits, taxes ou amendes. Il ne présume aucune API disponible avec GELEC ou SYDONIA. Il ne qualifie pas automatiquement une infraction.

**Invariants.** Une réponse absente ou partielle ne prouve pas une infraction. Une impression, une validation applicative, une signature et une notification sont des faits distincts. Les documents transmis et reçus ne sont pas écrasés par un nouveau brouillon. Les chiffres ne sont visibles qu'avec un périmètre et une définition explicites. Les données d'une source protégée ne figurent pas dans un export ordinaire.

**Autorité.** Le commanditaire et les représentants DGDA habilités décident des règles métier, des accès, des modèles, de l'unité pilote, de la conservation et de la frontière avec GELEC. L'équipe produit propose et vérifie les parcours.

<!-- prd-section: evidence-assumptions-decisions -->
## Éléments, hypothèses et décisions

| ID | Énoncé | Nature / confiance | Impact si faux | Source et validation |
|---|---|---|---|---|
| EVD-01 | Procezo vise les enquêtes avant PV et un relais vers GELEC. | Proposition documentaire / haute sur le texte | Fort | [Note de cadrage](Note_de_cadrage_Procezo_DGDA.pdf), p. 1–2, 6 ; confirmation DGDA. |
| EVD-02 | Les quatre besoins sont demandés en V1 dans la description récente. | Besoin rapporté / moyenne | Fort | [Description](description.md), §1 et §10 ; arbitrage commanditaire. |
| DEC-01 | La V1 couvre la note et les quatre besoins : les feuilles et statistiques P2 sont incluses dans le pilote, après les prérequis P1. | Décision utilisateur / haute | Fort | Réponse du demandeur du 25 septembre 2026 ; validation du périmètre par la DGDA pour engagement externe. |
| EVD-04 | La demande de communication n'a pas de format douanier formalisé actuellement ; Procezo peut proposer un format et l'agent doit aussi pouvoir importer son propre document. La comparaison avec la DGI n'établit aucune interdiction pour la DGDA. | Capture et clarification explicite du demandeur / haute sur l'intention produit | Fort | Capture et précision du demandeur ; faire valider par la DGDA les règles d'émission des deux types de document. |
| EVD-05 | Les captures décrivent les issues de la réponse, les données d'une feuille, les origines et suites du renseignement, l'alerte interservices et cinq familles de statistiques. | Besoins rapportés / moyenne | Fort | Cinq captures transmises par le demandeur ; rejouer ces cas avec la DGDA. |
| ASM-01 | Le dossier et la prochaine action réduiront les recherches et la double saisie. | Hypothèse / faible | Fort | Observation initiale, puis même tâche sur prototype et en pilote. |
| ASM-02 | Le transfert GELEC peut être confirmé manuellement durant le pilote. | Hypothèse / moyenne | Moyen | Accord DGDA et responsable GELEC ; test de transmission. |
| UNK-01 | Signataires, délais, notifications, confidentialité, conservation et place des différents PV. | Inconnu / faible | Très fort | Atelier DGDA, modèles et instructions applicables. |

<!-- prd-section: problem-and-outcomes -->
## Problème et résultats attendus

Les sources décrivent des traitements manuels et un risque de perte d'information, sans mesure du coût ou de la fréquence. L'état actuel des registres, courriers et outils doit être observé. L'hypothèse falsifiable est qu'un agent ne retrouve pas toujours rapidement la dernière pièce, la prochaine action, le responsable, la décision et la preuve d'envoi à partir d'un même dossier. Si le circuit actuel satisfait déjà ces besoins à faible coût, la valeur d'un nouveau produit doit être réévaluée.

| But | Résultat observable au pilote |
|---|---|
| GOAL-01 — continuité de l'enquête | Sur chacun des trois cas rejoués, l'agent retrouve responsable, prochaine action, actes et pièces sans registre parallèle complet. |
| GOAL-02 — actes et réponses traçables | Un acte émis, sa version signée si nécessaire, sa preuve d'envoi et ses réponses successives restent consultables par étape. |
| GOAL-03 — décisions humaines justifiables | Classement ou relais découle d'une décision motivée, validée par une autorité habilitée et liée aux faits et pièces. |
| GOAL-04 — pilotage vérifiable | Chaque valeur pilote ouvre les enregistrements qui la composent, selon les droits du lecteur. |

<!-- prd-section: actors-and-permissions -->
## Acteurs, propriété et droits

| Acteur | Ressources et actions proposées | Limite ou refus |
|---|---|---|
| Enquêteur affecté | Lit son dossier autorisé ; prépare renseignement, demande, feuille, analyse et proposition de suite ; ajoute pièces et réponses. | Aucune signature, émission ou décision finale par le seul fait d'être auteur. |
| Responsable métier habilité | Qualifie, affecte, contrôle, valide ou retourne selon sa délégation ; consulte les statistiques de son périmètre. | Une responsabilité hiérarchique ne donne pas automatiquement accès à l'identité d'une source protégée. |
| Gestionnaire documentaire ou courrier, si désigné | Enregistre signature, remise, réception et preuves selon mandat explicite. | Ne modifie pas l'appréciation métier. |
| Lecteur de pilotage, si désigné | Consulte agrégats et listes sous-jacentes autorisées. | Aucun accès implicite aux pièces ou identités protégées. |
| Administrateur technique | Gère les comptes et la disponibilité. | Aucun droit métier implicite de lecture, validation, clôture ou export. |
| Tiers et sources | Font l'objet des échanges ou fournissent des informations ; pas de compte V1. | Pas de portail externe V1. |

Une habilitation est conditionnée par le rôle **et** la relation au dossier, l'unité et la confidentialité. Lorsqu'elle est retirée, les listes, pièces, prévisualisations et exports ne doivent plus exposer le dossier. Les refus ne révèlent pas l'existence d'une source protégée. La matrice précise sera approuvée par la DGDA avant le pilote.

<!-- prd-section: goals-and-non-goals -->
## Objectifs et exclusions

Les quatre buts GOAL-01 à GOAL-04 constituent les objectifs du pilote. Sont exclus : le traitement détaillé du contentieux, le calcul et recouvrement, la rédaction d'un PV présenté comme officiel sans circuit validé, l'inférence automatique d'infraction, le portail des tiers, l'intégration automatisée GELEC/SYDONIA et l'analytique prédictive. La mission de contrôle figure dans la V1, mais elle n'est pas obligatoire pour tous les dossiers ou toutes les feuilles.

<!-- prd-section: scope-and-priorities -->
## Portée et priorités du pilote proposé

| Capacité | Priorité | Justification et condition |
|---|---|---|
| Comptes, habilitations, dossier, chronologie, affectation et prochaine action | Must | GOAL-01 et protection des données ; politique DGDA requise. |
| Renseignement indépendant, qualification, diffusion et retours par destinataire | Must | Cas d'alerte sans cible ; confidentialité. |
| Demande avec éléments distincts, réponses et compléments successifs | Must | GOAL-02 ; ne pas confondre complétude et suffisance. |
| Fiche de mission de contrôle avec responsable, participants, période, constats et pièces, quand une mission a lieu | Must | Fonction de la note ; permet de relier les constats au dossier sans rendre la mission universellement obligatoire. |
| Feuille avec observations distinctes, défenses et appréciations motivées | Must | Besoin V1 confirmé par le demandeur et fonction P2 de la note. |
| Deux modes de préparation de la demande : format proposé dans Procezo avec PDF, ou import du document de l'agent ; version émise, scan signé et preuve | Must | GOAL-02 ; aucun format douanier actuel n'est présumé. Les deux modes suivent le même circuit de suivi et de validation. |
| Décision motivée, classement ou transfert tracé avec confirmation de réception | Must | GOAL-03 et frontière GELEC. |
| Tableau de bord et statistiques simples, définition et accès aux éléments sous-jacents | Must | GOAL-04 ; besoin V1 confirmé par le demandeur et fonction P2 de la note. |
| Recherche transversale étendue et export du dossier entier | Should | Fallback : navigation et impression pièce par pièce. |
| Relances assistées | Could | Les échéances et règles officielles ne sont pas encore connues. |

Le pilote maintient manuellement signature, notification, numérisation et référence GELEC, avec trace de chaque opération. Les notifications internes affichent les éléments à traiter et les retours aux agents concernés ; aucun envoi automatique externe ou délai de relance n'est présumé. La séquence de réalisation respecte les dépendances P1 de la note avant les capacités P2, sans retirer ces dernières de la recette V1.

<!-- prd-section: critical-journeys-and-states -->
## Parcours, états et récupération

**JOURNEY-01 — réponse satisfaisante.** Un renseignement est saisi et qualifié ; un responsable ouvre et affecte un dossier ; l'enquêteur prépare une demande et ses éléments ; l'autorité habilitée valide le projet ; l'acte signé est envoyé avec preuve ; le courrier de réponse et ses annexes sont importés avec leur date réelle ; chaque élément est apprécié ; une proposition de classement motivée est validée ; le dossier entre dans les chiffres correspondants. Une correction après émission crée une nouvelle trace sans remplacer l'acte envoyé.

**JOURNEY-02 — réponse partielle et observations multiples.** Un dossier reçoit une demande puis plusieurs réponses ; les éléments restent individuellement « non reçu », « reçu » ou « à analyser », et l'appréciation de fond reste distincte. Si une mission est menée, ses participants, constats et pièces sont enregistrés. Une feuille peut provenir de cette mission ou d'une autre origine autorisée ; elle contient plusieurs observations étayées. Une défense peut couvrir certaines observations et recevoir des compléments. L'enquêteur motive l'appréciation de chacune. L'autorité compétente valide la suite ; un éventuel transfert est préparé, transmis puis confirmé reçu manuellement. Aucune absence de défense ne déclenche automatiquement une qualification d'infraction.

Après une réponse reçue par correspondance, l'enquêteur peut proposer un classement si elle est jugée satisfaisante, ou une mission de contrôle ou un relais vers la procédure de PV si elle ne l'est pas. Après des éléments de défense satisfaisants, une proposition de classement et une information de l'intéressé sont prévues ; dans l'autre cas, le relais vers GELEC peut être proposé. Ces suites sont des **options à motiver et à valider**, pas des transitions automatiques. Le lieu de rédaction du PV et le mode d'information du tiers restent ouverts.

**JOURNEY-03 — alerte interservices.** Un renseignement sans partie connue, provenant de la douane, d'un rapport de service ou d'informations de l'opinion, est enregistré et affecté à un agent ou une unité désignée. Il peut conduire à une mission, une demande, une feuille ou une alerte de type message phonique/note de service. Dans ce dernier cas, il est diffusé à plusieurs bureaux ; chaque envoi, accusé et retour est enregistré séparément. Un dossier n'est créé que si une investigation est justifiée. Aucun nom d'entreprise fictif ni infraction présumée ne sont nécessaires pour terminer le suivi et compter l'alerte.

| Objet | États de travail proposés | Règle et récupération |
|---|---|---|
| Renseignement | Brouillon → à qualifier → diffusé / lié à un dossier / archivé avec motif | Plusieurs diffusions et liens possibles ; échec d'envoi laisse la diffusion non confirmée. |
| Dossier | À affecter → en cours / en attente / à valider → clôturé | Issue séparée du statut ; réouverture motivée et historisée ; plusieurs actes parallèles possibles. |
| Demande ou feuille | Brouillon → à valider → validé → émis ou notifié → suivi des réponses → terminé | PDF brouillon distinct de l'acte émis ; échec de génération ou de dépôt conserve le brouillon et permet une reprise contrôlée. |
| Décision | Proposée → retournée / validée | Le retour conserve le motif ; une décision validée est corrigée par nouvel événement, sans effacement. |
| Transfert | Préparé → transmis → réception confirmée | Un transfert incertain reste « transmis » jusqu'à confirmation ; une tentative répétée ne crée pas deux réceptions. |

Les libellés et transitions officiels restent à valider. Une échéance dépassée est un indicateur calculé, pas un état qui masque le statut réel. Une page vide explique pourquoi aucun objet n'est visible ; une liste en chargement ou indisponible ne présente pas un total zéro comme résultat réel. Après interruption, l'agent vérifie l'état et reprend un brouillon ou une action non confirmée sans dupliquer un acte émis.

<!-- prd-section: functional-requirements -->
## Exigences fonctionnelles et critères de recette

Les exigences ci-dessous sont proposées pour le pilote. Leur émission opérationnelle dépend des validations DGDA. Un critère de refus s'applique également aux API, recherches, aperçus, téléchargements et exports.

| ID | Priorité | Obligation produit | Preuve de recette |
|---|---|---|---|
| FR-01 | Must | À la réception d'un renseignement, un agent autorisé peut enregistrer objet, résumé, provenance, date réelle et confidentialité sans cible identifiée. | AC-01 |
| FR-02 | Must | Un responsable autorisé peut diffuser un renseignement à plusieurs unités avec action attendue et suivi distinct de chaque retour. | AC-02 |
| FR-03 | Must | Un responsable autorisé peut ouvrir, affecter et réaffecter un dossier avec motif ; son statut, son responsable et sa prochaine action sont visibles aux personnes habilitées. | AC-03 |
| FR-04 | Must | Une demande contient une liste distincte d'éléments attendus et conserve chaque réponse, complément et pièce avec date de réception et lien à la demande. | AC-04 |
| FR-05 | Must | L'analyse de demande distingue pour chaque élément réception, complétude et appréciation de fond ; le système ne déduit pas une infraction de l'absence de réponse. | AC-05 |
| FR-06 | Must | Une feuille contient des observations numérotées liées à leurs faits et pièces ; chaque défense et complément peut viser une ou plusieurs observations, avec appréciation motivée. | AC-06 |
| FR-07 | Must | Pour une demande, l'agent choisit entre le format proposé par Procezo, avec aperçu et PDF imprimable, et l'import de son propre document ; les deux modes conservent le même dossier, les mêmes étapes de validation et la version réellement envoyée. Pour une feuille, la saisie et le PDF proposés restent soumis au modèle validé. | AC-07 |
| FR-08 | Must | Chaque acte et réponse conserve sa version transmise ou reçue, ses pièces, son origine, sa date réelle et sa preuve, et apparaît à la bonne étape du dossier. | AC-08 |
| FR-09 | Must | Une suite de dossier est proposée avec motif puis validée ou retournée par une personne habilitée ; le classement ou transfert ne se produit qu'après validation. | AC-09 |
| FR-10 | Must | Le relais GELEC conserve préparation, transmission, référence disponible et confirmation explicite de réception sans supposer d'intégration automatique. | AC-10 |
| FR-11 | Must | Chaque indicateur pilote affiche période, unité et définition ; sa valeur ouvre les éléments inclus que le lecteur a droit de voir, sans dévoiler les autres. | AC-11 |
| FR-12 | Must | Le produit refuse lecture, modification, validation et export hors habilitation et trace les accès sensibles et actions conséquentes. | AC-12 |
| FR-13 | Must | Quand une mission de contrôle est menée, l'agent autorisé enregistre son contexte, ses participants, ses constats et pièces, puis la rattache au dossier et, le cas échéant, à une feuille. | AC-13 |
| FR-14 | Must | Le responsable et l'enquêteur voient les affectations, actes à valider, retours, échéances et alertes de leur périmètre, avec lien vers l'action à traiter. | AC-14 |
| FR-15 | Must | Quel que soit le mode de préparation, la fiche de suivi de la demande identifie l'auteur, la cible (commissionnaire en douane ou entreprise commerciale/ONG), la personne représentée le cas échéant, l'objet et les éléments demandés nécessaires au suivi des réponses, sans obliger l'agent à recopier le texte intégral de son document importé. | AC-15 |
| FR-16 | Must | À la réception d'une réponse ou défense par correspondance, l'enquêteur enregistre son appréciation motivée et propose, selon le cas, classement, mission, complément ou relais PV/GELEC ; aucune suite n'est déclenchée automatiquement par la seule appréciation. | AC-16 |
| FR-17 | Must | Une feuille enregistre auteur, adresse du destinataire, origine du constat, partie concernée, faits et pièces ; la mission est facultative lorsque l'origine retenue par la DGDA le permet. | AC-17 |
| FR-18 | Must | Un renseignement conserve sa catégorie de provenance, son responsable et chaque suite distincte, y compris message phonique/note de service et retours des bureaux concernés. | AC-18 |
| FR-19 | Must | Les statistiques couvrent séparément demandes, feuilles, classements sans suite, dossiers ayant conduit à un PV et renseignements avec leurs effets, selon des définitions validées et des éléments vérifiables. | AC-19 |

**AC-01.** Un renseignement sans entreprise ni identifiant administratif peut être enregistré ; l'identité d'une source protégée, si collectée, reste séparée du résumé visible aux enquêteurs ordinaires.

**AC-02.** Deux diffusions du même renseignement produisent deux suivis ; un retour d'un bureau ne clôt pas celui de l'autre ; une répétition après interruption ne crée pas deux envois confirmés sans action distincte.

**AC-03.** Une réaffectation modifie le responsable affiché et conserve ancien responsable, auteur, date et motif. Un utilisateur dont l'affectation ou l'habilitation a pris fin perd l'accès au dossier.

**AC-04.** Une demande de trois éléments accepte une première réponse couvrant un élément, puis un complément couvrant un autre ; les deux courriers et leurs pièces restent visibles dans l'ordre des dates de réception. Une pièce mal rattachée peut être rectifiée sans effacer la trace.

**AC-05.** Un élément reçu peut être marqué insuffisant sur le fond avec motif ; un élément non reçu reste « non reçu ». Le rapport ne présente ni l'un ni l'autre comme infraction établie.

**AC-06.** Une feuille de deux observations accepte une défense couvrant seulement la première ; la seconde reste sans défense. Un complément ultérieur à la première ne remplace ni la défense initiale ni l'appréciation antérieure.

**AC-07.** En mode « format Procezo », l'agent saisit la demande, prévisualise le projet et génère un PDF imprimable. En mode « mon document », il importe son courrier, le prévisualise et le rattache à la même demande sans être forcé de générer le PDF Procezo. Dans les deux modes, le projet reste distinct de la version validée, signée et effectivement envoyée ; cette dernière est conservée avec la preuve d'envoi. Ni génération ni import ni impression ne renseignent automatiquement « signé » ou « notifié ». La présentation du format Procezo et le circuit d'émission des deux modes sont validés par la DGDA avant usage réel.

**AC-08.** Le scan d'un courrier papier et deux annexes, importés après réception, gardent la date de réception réelle distincte de la date d'import. Une nouvelle génération n'écrase pas le PDF émis ni le scan signé. Une génération échouée laisse le brouillon reprenable.

**AC-09.** Une proposition sans motif est refusée ; un validateur peut la retourner avec commentaire ; seul le validateur explicitement habilité confirme le classement ou la transmission. La décision validée demeure dans l'historique après rectification.

**AC-10.** Une référence GELEC absente n'est pas inventée. Une transmission non confirmée reste distincte d'une réception confirmée ; une seconde validation de la même réception ne crée pas un second transfert.

**AC-11.** Sur une période donnée, le nombre de renseignements reçus compte chaque renseignement une fois même s'il alimente deux dossiers ; un clic ouvre la liste correspondante, filtrée par les droits du lecteur. Un lecteur sans accès détaillé voit un agrégat autorisé seulement si la politique DGDA l'autorise.

**AC-12.** Un administrateur technique sans droit métier ne peut ouvrir un dossier ni exporter ses documents. La tentative refusée ne révèle pas l'identité d'une source protégée. Les consultations sensibles, validations et exports autorisés laissent une trace consultable par un contrôleur habilité.

**AC-13.** Une mission avec deux participants et trois pièces apparaît dans la chronologie du dossier ; une feuille peut citer son constat. Une autre feuille issue d'un constat autorisé peut être créée sans mission, si la règle DGDA l'admet. Une mission ne crée pas automatiquement une infraction ou un PV.

**AC-14.** Après affectation, l'enquêteur voit l'action dans « Mon travail » ; après soumission d'un acte, le validateur habilité voit l'élément dans « À valider ». Une échéance dépassée s'affiche comme retard sans changer le statut de l'acte. Une alerte interne n'est jamais considérée comme notification officielle au tiers.

**AC-15.** Dans les deux modes, l'agent peut choisir « commissionnaire en douane » ou « entreprise commerciale/ONG » pour la cible, renseigner l'auteur et l'objet, puis indexer les éléments recherchés afin de suivre les réponses. Si le commissionnaire ou déclarant agit pour autrui, la personne ou organisation représentée est enregistrée séparément de la cible. Le document importé reste la pièce de référence pour son texte intégral : les champs de suivi n'imposent pas une seconde rédaction du courrier. L'absence de relation « pour le compte de » ne crée pas une seconde société fictive. Les catégories et libellés finaux sont validés par la DGDA.

**AC-16.** Une réponse papier reçue par correspondance est liée à la demande avec date, courrier et annexes. Une appréciation satisfaisante permet de proposer un classement, soumis à validation. Une appréciation non satisfaisante permet de proposer une mission ou une suite vers le PV/GELEC, avec motif et décision humaine. Le changement d'appréciation conserve l'historique et ne déclenche pas rétroactivement une autre suite. Pour une défense satisfaisante, l'information à l'intéressé est tracée selon le circuit validé.

**AC-17.** Une feuille comporte auteur, adresse, partie concernée, faits et pièces par observation. Son origine distingue mission, renseignement, système tel que SYDONIA, ou constat sur terrain selon catégories approuvées. La source d'un renseignement, l'action menée et le support du constat ne sont pas confondus dans un seul champ. Une feuille sans mission peut être préparée lorsque la DGDA autorise cette origine.

**AC-18.** Un renseignement de provenance « douane », « rapport de service » ou « informations de l'opinion » peut être affecté et mener à plusieurs actions. Une note de service ou un message phonique d'alerte adressé à deux bureaux conserve destinataires, contenu ou référence, date, action attendue et retours distincts ; il peut exister sans entreprise ni dossier. Le canal exact et la preuve de diffusion restent à valider.

**AC-19.** Le tableau de bord permet de sélectionner période et périmètre autorisé puis d'obtenir séparément nombre de demandes, de feuilles, de classements sans suite, de dossiers ayant conduit à un PV et de renseignements par source et effet. Chaque valeur mène aux objets comptés ; un dossier lié à deux renseignements n'est pas compté deux fois dans les dossiers. Un dossier « orienté vers PV » n'est compté comme « ayant conduit à un PV » que si la preuve ou référence du PV, définie par la DGDA, existe.

<!-- prd-section: data-and-privacy -->
## Données, confidentialité et cycle de vie

| Catégorie | Utilité et sensibilité | Visibilité et correction | Conservation / limite |
|---|---|---|---|
| Renseignements et identité éventuelle de source | Informations opérationnelles ; identité potentiellement très sensible | Résumé selon dossier ; identité réservée à une habilitation spécifique | Durée et sort des archives à fixer par la DGDA ; identité exclue des exports ordinaires. |
| Parties, opérations et coordonnées | Identification et contexte ; données personnelles ou commerciales | Agents affectés et décideurs habilités ; rectification tracée | Minimiser aux données utiles ; éviter la copie complète de SYDONIA. |
| Actes, réponses et pièces | Preuve du parcours et des échanges | Lecture selon dossier, étape et classification ; correction par version ou rectification | Version effectivement transmise et original reçu conservés selon politique DGDA à définir. |
| Décisions, habilitations et audit | Responsabilité, contrôle et vérification | Accès de contrôle dédié ; aucune modification ordinaire de l'historique | Durée et règles d'accès à fixer avant données réelles. |

Les décisions relatives à la base juridique, la durée de conservation, l'effacement, l'export, l'hébergement et l'accès des personnes concernées relèvent de la DGDA et de ses spécialistes. En attente, le prototype emploie des données fictives. Une donnée contestée est marquée comme telle et corrigée avec provenance ; la pièce originale et le fait qu'elle a été reçue ne sont pas remplacés silencieusement. Désactiver un compte n'efface pas l'attribution historique de ses actes.

<!-- prd-section: non-functional-requirements -->
## Exigences de qualité mesurables

| ID | Scénario | Réponse observable | Seuil et validation |
|---|---|---|---|
| NFR-01 | Un agent cherche un dossier autorisé par référence sur le réseau du site pilote. | Liste et ouverture utilisables, avec état de chargement explicite. | Cible provisoire : 95 % des recherches en 3 s et ouvertures en 5 s ; mesure sur réseau et volume pilotes, puis validation DGDA. |
| NFR-02 | Une génération PDF ou un import est interrompu. | Résultat indiqué comme réussi, échoué ou à confirmer ; le brouillon et les fichiers déjà acceptés restent retrouvables. | Aucun acte émis ni fichier reçu ne disparaît dans les scénarios de reprise du pilote. |
| NFR-03 | Un lecteur non habilité suit un lien direct, recherche ou exporte. | Aucun contenu du dossier ou de source protégée n'est exposé. | Tous les cas de refus de la matrice DGDA réussissent en recette. |
| NFR-04 | Un agent utilise clavier et lecteur d'écran sur les parcours critiques. | Formulaires, erreurs, validation, pièces et états sont nommés et navigables. | Recette clavier et technologie d'assistance sur JOURNEY-01 à 03 ; référentiel d'accessibilité applicable à confirmer. |
| NFR-05 | Le site pilote subit une panne et les données sont restaurées. | Les actes émis, réponses, preuves et historiques redeviennent consultables ; toute perte est explicitée. | Objectifs de reprise et perte maximale à fixer avec la DGDA avant données réelles ; exercice de restauration obligatoire. |
| NFR-06 | Plusieurs agents modifient le même brouillon. | Chacun voit qu'une version plus récente existe avant d'écraser le travail de l'autre. | Rejeu de modification concurrente en recette. |

L'interface pilote est en français. Date de fait, date d'enregistrement et horodatage des actions restent distingués ; le fuseau utilisé pour l'affichage et les rapports doit être convenu avec la DGDA.

<!-- prd-section: metrics-and-analytics -->
## Mesure du pilote et statistiques

| ID | Question et définition | Périmètre et fenêtre | Statut, garde-fou et décision |
|---|---|---|---|
| MET-01 | Part des dossiers pilotes dont responsable et prochaine action sont identifiables : dossiers éligibles avec ces deux informations / dossiers pilotes éligibles. | Unité pilote ; revue hebdomadaire ; dossier compté une fois. | Référence inconnue ; mesurer avant/après. Garde-fou : temps de saisie et registres parallèles. |
| MET-02 | Part des actes émis avec version transmise et preuve d'envoi reliées : actes satisfaisant les deux / actes émis éligibles. | Demandes et feuilles du pilote, par mois. | Cible à fixer après observation ; auditer un échantillon papier. |
| MET-03 | Part des dossiers clôturés ou transférés avec décision motivée validée : dossiers conformes / dossiers clos ou transférés. | Unité pilote, par mois. | Objectif de complétude à approuver ; garde-fou : décisions contestées ou prématurées. |
| MET-04 | Vérifiabilité d'un indicateur : valeurs pilotes dont les éléments et règles de calcul sont retrouvables / valeurs examinées. | Chaque revue mensuelle ; échantillon convenu. | Pas de cible observée ; toute divergence est examinée avant diffusion. |
| MET-05 | Temps médian pour retrouver la prochaine action et la dernière pièce sur les mêmes cas. | Agents pilotes, tâche avant/après, cas équivalents. | Hypothèse de gain à tester ; garde-fou : erreurs de choix et consultation indue. |

Les événements minimaux sont réception de renseignement, affectation, émission d'acte, réception de réponse, validation de décision, transmission et confirmation de réception. Chaque événement porte référence de l'objet, auteur ou unité autorisée, date de fait et date d'enregistrement ; les journaux analytiques n'incluent pas l'identité d'une source protégée. Les comptes sont dédupliqués par identifiant d'objet et type d'événement. La DGDA valide les définitions, la visibilité et la période de reporting avant diffusion des tableaux de bord.

**Catalogue de statistiques V1 issu des captures.** Pour chaque période et périmètre habilité : demandes de communication émises et leurs réponses ; feuilles créées, émises/notifiées et défenses ; dossiers classés sans suite par date de décision validée ; dossiers ayant conduit à un PV, distincts des simples orientations vers PV ; renseignements reçus par provenance, suites produites et effets obtenus. Les « effets » possibles (mission, demande, feuille, alerte diffusée, dossier ouvert, puis issue) restent des catégories à définir avec la DGDA ; une action ne prouve pas à elle seule un résultat. Le nombre de dossiers liés et l'évolution de leur issue peuvent être consultés depuis le renseignement, avec contrôle des droits et sans double compte.

<!-- prd-section: dependencies-and-integrations -->
## Dépendances et frontières externes

| Dépendance | Contrat attendu et repli | Responsable / statut |
|---|---|---|
| Modèles et circuit des actes | Modèle, mentions, signataire, validation, signature et notification approuvés avant usage réel ; prototype fictif en attendant. | DGDA / ouvert, bloquant. |
| Politique d'habilitation et sources | Matrice par unité, dossier et confidentialité ; données fictives en attendant. | DGDA / ouvert, bloquant. |
| GELEC | Référence, bordereau et confirmation manuelle au pilote ; aucun échange automatique présumé. | DGDA + responsable GELEC / ouvert. |
| SYDONIA | Références d'opérations saisies si connues ; aucune synchronisation présumée. | DGDA / non requis au pilote. |
| Courrier et archivage papier | Responsabilité d'envoi, numérisation, preuve et contrôle du dossier physique. | Unité pilote / à désigner. |
| Réseau, hébergement et sauvegarde | Capacité mesurée et restauration testée avant données réelles. | DGDA + exploitation / ouvert, bloquant. |

<!-- prd-section: risks-and-open-decisions -->
## Risques et décisions ouvertes

| ID | Risque ou décision | Impact et défaut provisoire | Détection / propriétaire | Blocage |
|---|---|---|---|---|
| DEC-01 | Note et quatre besoins en V1, P1 puis P2 comme séquence. | Décidé par le demandeur ; portée documentée ci-dessus. | Validation de l'engagement externe par la DGDA. | Ne bloque plus la rédaction ; validation DGDA requise avant engagement. |
| DEC-02 | Qui rédige, valide, signe, notifie, classe et transfère ? | Acte irrégulier ; aucune émission réelle avant matrice approuvée. | Rejeu des cas et délégations DGDA. | Bloque le pilote réel. |
| DEC-03 | Quelle présentation et quelles mentions pour le format de demande proposé par Procezo, quels contrôles pour un document importé, et quels modèles, délais et origines de feuille sont officiels ? | Acte ou échéance invalide ; les deux modes restent des projets tant que la DGDA n'a pas validé leurs conditions d'émission. | Exemples de courriers, modèles et instructions DGDA. | Bloque l'émission réelle, pas la conception des deux modes. |
| DEC-04 | Où sont produits les différents PV, quand commence GELEC et quelle preuve établit qu'un dossier « a conduit à un PV » ? | Duplication ou trou de responsabilité et chiffre trompeur ; repli : transfert tracé sans rédaction de PV officiel, indicateur PV non publié tant que sa preuve n'est pas définie. | Atelier conjoint DGDA/GELEC. | Bloque relais réel et indicateur PV si non clarifié. |
| RISK-01 | Source ou secret commercial exposé. | Préjudice élevé ; séparation et accès minimal. | Recette de refus, revue des exports ; DGDA. | Arrêt du pilote si exposition. |
| RISK-02 | Double saisie papier et numérique persistante. | Adoption faible ; mesurer le temps, observer les contournements. | Observation hebdomadaire ; équipe produit et unité pilote. | Réévaluer l'expansion. |
| RISK-03 | Statistique juste en calcul mais fausse en saisie. | Pilotage erroné ; rapprochement avec pièces et dossiers. | Audit d'échantillon ; responsable métier. | Pas de diffusion sans correction. |
| DEC-05 | Conservation, hébergement, migration et objectifs de reprise. | Données ou exploitation non maîtrisées ; données fictives en attendant. | Autorité DGDA et exploitation. | Bloque les données réelles. |

<!-- prd-section: rollout-and-release -->
## Déploiement et critère de passage

1. **Prototype fictif :** démontrer JOURNEY-01 à 03, puis relever toute étape, pouvoir ou document manquant. Aucune sortie n'est présentée comme un acte officiel.
2. **Préparation pilote :** DGDA valide unité, modèles, habilitations, politique de données, circuits papier, frontière GELEC et objectifs d'exploitation ; mesurer la pratique initiale sur les mêmes tâches.
3. **Pilote restreint :** agents désignés, formation et support nommés ; rapprochement régulier avec le papier, les décisions et les statistiques. La coexistence avec les registres actuels est documentée et son coût mesuré.
4. **Décision d'expansion :** trois parcours réalisés sans contournement critique, aucune consultation hors droit, actes et chiffres vérifiables, restauration démontrée et retour métier favorable. Une exposition sensible ou un acte non conforme suspend le pilote.

Si le pilote est suspendu, les dossiers déjà traités restent consultables/exportables par les personnes habilitées selon la politique DGDA ; le circuit papier continue sous responsabilité de l'unité. La migration de l'ancien Procezo n'est pas présumée : la DGDA choisit quelles données reprendre et comment les signaler comme historiques.

<!-- prd-section: traceability-and-readiness -->
## Traçabilité et Definition of Ready

| But et parcours | Exigences | Preuve | Mesures et risques |
|---|---|---|---|
| GOAL-01, JOURNEY-01/03 | FR-01 à FR-03, FR-12, FR-14, FR-18 | AC-01 à AC-03, AC-12, AC-14, AC-18 | MET-01/05, RISK-01/02 |
| GOAL-02, JOURNEY-01/02 | FR-04 à FR-08, FR-13, FR-15, FR-17 | AC-04 à AC-08, AC-13, AC-15, AC-17 | MET-02, DEC-02/03 |
| GOAL-03, JOURNEY-01/02 | FR-09/10, FR-16 | AC-09/10, AC-16 | MET-03, DEC-04 |
| GOAL-04, trois parcours | FR-11, FR-19 | AC-11, AC-19 | MET-04, RISK-03 |

**Prêt pour maquettes et revue métier conditionnelle. Non prêt pour émission d'actes officiels ou données réelles sans DEC-02 à 05.** La portée DEC-01 est arrêtée par le demandeur, sous réserve d'engagement formel DGDA. Les critères de recette seront rejoués sur dossiers anonymisés et modèles validés ; les seuils non observés restent provisoires.

<!-- prd-section: handoff-for-architecture -->
## Handoff for Architecture

Objectif : dossier d'enquête et prochaine action traçables, actes et pièces reliés, décision humaine et chiffres vérifiables. Acteurs : enquêteur, responsable habilité, gestionnaire du courrier éventuel, lecteur autorisé, administrateur technique sans droit métier implicite. Horizon : prototype fictif puis pilote dans une unité. La V1 couvre la note et les quatre besoins, avec construction des prérequis P1 avant la recette des fonctions P2 ; contentieux détaillé, calculs et intégrations automatisées sont exclus.

Préserver les relations plusieurs-à-plusieurs entre renseignements et dossiers, les réponses multiples, les observations et défenses multiples, les actes parallèles, les versions émises, la date réelle de réception et les preuves. Séparer brouillon, validation, signature, notification et réception confirmée. Toute consultation et tout export doivent respecter rôle, unité, relation au dossier et classification, y compris les listes et statistiques. L'identité d'une source protégée requiert une politique dédiée. L'administration technique n'accorde aucun pouvoir métier. Les transferts GELEC sont manuels et explicitement confirmés au pilote.

Les données concernent personnes et organisations, sources sensibles, correspondances, pièces, décisions et audit ; durées, hébergement, migration, accès des personnes et objectifs de reprise relèvent de DEC-05. Les qualités à satisfaire sont NFR-01 à 06, avec seuils provisoires à confirmer sur le site pilote. Pour la demande de communication, prévoir le format proposé par Procezo **et** l'import du document de l'agent ; les deux modes partagent fiche de suivi, validation, historique, réponses et preuve d'envoi. La présentation du PDF proposé et les contrôles d'un document importé relèvent de DEC-03. Aucune architecture ne doit figer un délai, un pouvoir de signature ou une interface externe avant décision DGDA. La portée DEC-01 est arrêtée pour ce PRD ; DEC-02 à 05 et RISK-01 à 03 conditionnent la suite.

## Sources

- [Note de cadrage Procezo / DGDA, 18 septembre 2026](Note_de_cadrage_Procezo_DGDA.pdf), six pages.
- [Description de travail Procezo, 24 septembre 2026](description.md), notamment §§1, 5, 6, 8, 10–11.
- [Brief de découverte Procezo](BRIEF_BRAINSTORMING_PROCEZO.md), direction et hypothèses de pilote.
