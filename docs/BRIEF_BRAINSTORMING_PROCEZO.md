# Procezo — brief de découverte produit

Sources : [note de cadrage du 18 septembre 2026](Note_de_cadrage_Procezo_DGDA.pdf) et [description de travail du 24 septembre 2026](description.md). Ce document propose une direction de conception ; il ne valide aucune règle métier ou juridique à la place de la DGDA.

<!-- brainstorm-section: discovery-verdict -->
## Discovery Verdict

- **Direction recommandée :** organiser Procezo autour du **dossier d'enquête et de sa prochaine action**, avec quatre parcours courts mais complets en V1 : renseignement, demande de communication, feuille d'observation et statistiques vérifiables. La gestion documentaire du dossier et la production rapide de PDF imprimables sont une capacité transversale obligatoire de ces parcours. Préparer d'abord trois démonstrations sur données fictives, puis un pilote limité avec la DGDA.
- **Utilisateur et résultat :** l'enquêteur sait ce qui a été reçu, ce qui manque, qui doit agir et quelle suite a été validée ; il retrouve tous les documents du dossier par étape, prépare les actes papier depuis une saisie courte avec PDF à imprimer, puis numérise ou importe les réponses papier et leurs pièces dans le suivi. Le responsable peut retrouver les actes, leurs versions transmises, les réponses reçues et justifier ses chiffres.
- **Pourquoi :** les quatre besoins sont explicitement prioritaires dans `description.md` ; la note de cadrage prévoit déjà dossiers, historique, décisions et relais vers GELEC. Le dossier relie ces activités sans imposer un ordre unique à tous les cas.
- **Hypothèse la plus risquée :** les pratiques réelles des unités peuvent être représentées par ces parcours sans obliger les agents à tenir simultanément un dossier papier ou un autre registre complet.
- **Validation suivante :** rejouer trois dossiers anonymisés avec enquêteurs, responsable métier et gestionnaire des documents ; relever chaque étape manquante, double saisie et règle contestée.
- **À décider maintenant :** faire valider par le commanditaire la couverture des quatre besoins en V1 et choisir l'unité pilote.
- **Peut attendre :** intégration automatisée à GELEC/SYDONIA, analytics avancés et portail externe.
- **Confiance : moyenne** sur le cadrage fonctionnel, faible sur l'adoption et les règles opérationnelles, faute d'observation métier directe.

<!-- brainstorm-section: mandate-and-horizon -->
## Mandat et horizon

Transformer deux documents de cadrage en choix de produit et en programme de validation pour l'atelier DGDA, les maquettes et un pilote. Le périmètre concerne l'enquête **avant le contentieux détaillé**. Le calcul et le recouvrement des droits, taxes et amendes restent hors Procezo. La note envisage une progression cadrage → conception → réalisation → pilote → déploiement ; aucune date ni budget de livraison n'est établi dans les sources.

<!-- brainstorm-section: evidence-and-assumptions -->
## Éléments établis, rapportés et incertains

| Élément | Statut | Confiance | Impact si faux | Source ou vérification |
|---|---|---|---|---|
| La note propose un outil centré sur les enquêtes et un relais vers GELEC. | Fait documentaire, proposition soumise à validation DGDA | Haute sur le texte, moyenne sur son adoption | Fort | Note, p. 1–2 et 6 ; validation du périmètre en atelier |
| Les quatre besoins doivent figurer en V1. | Besoin rapporté par l'équipe dans le document récent | Moyenne | Fort | `description.md`, §1 ; confirmation du commanditaire |
| La note classe feuilles et tableaux de bord en P2. | Fait documentaire contradictoire avec la V1 récente | Haute | Fort | Note, p. 5 ; arbitrage explicite |
| Le dossier est un bon pivot de navigation et de coordination. | Hypothèse de conception | Moyenne | Fort | Rejeu de dossiers réels anonymisés et test de maquettes |
| Les droits, modèles, délais, signataires, notification et place des PV sont connus. | Inconnu | Faible | Très fort | Autorités DGDA, modèles officiels, cas réels |
| L'intégration GELEC/SYDONIA est disponible. | Inconnu ; aucune intégration présumée | Faible | Moyen pour le pilote, fort pour l'automatisation | Inventaire des accès et décision DGDA |
| Les agents pourront cesser une partie de la double saisie. | Hypothèse de valeur | Faible | Fort | Observation du travail actuel et pilote comparatif |

<!-- brainstorm-section: problem-and-opportunity -->
## Problème et opportunité

Quand une information arrive ou qu'une enquête est ouverte, plusieurs personnes doivent conserver les faits, demander des pièces, analyser les réponses, motiver une suite et rendre compte. Les sources décrivent un risque de traitements manuels et de perte d'information, mais ne mesurent ni fréquence ni coût actuel. L'alternative vraisemblable est un assemblage de courriers, fichiers et registres ; elle doit être observée plutôt que supposée suffisante ou insuffisante.

**Énoncé falsifiable :** dans les unités pilotes, le suivi actuel ne permet pas toujours de retrouver rapidement, pour un dossier donné, la dernière pièce, la prochaine action, le responsable, la décision validée et la preuve d'envoi ; un parcours commun devrait améliorer cette traçabilité sans allonger significativement le travail. Si l'observation montre déjà une traçabilité fiable et un coût faible, le besoin d'un nouveau produit doit être réévalué.

<!-- brainstorm-section: actors-and-stakeholders -->
## Acteurs

| Acteur | Rôle dans le pilote | Résultat attendu | Point de blocage à vérifier |
|---|---|---|---|
| Enquêteur | Utilisateur principal | Saisir une fois, suivre les pièces et préparer la suite | Double saisie, règles de validation, temps de travail |
| Responsable d'unité | Approbateur et opérateur | Affecter, contrôler, décider et justifier l'activité | Habilitations et délégations effectives |
| Gestionnaire de documents / courrier | Opérateur à confirmer | Préserver versions, signatures et preuves d'envoi | Circuit papier et archivage officiels |
| Direction DGDA | Commanditaire et autorité métier | Pilotage fiable et frontière claire avec GELEC | Validation des règles, budget et conduite du changement |
| Tiers concernés et sources | Personnes affectées, non utilisateurs V1 | Traitement correct des informations et réponses | Confidentialité, exactitude et accès aux données |
| Administrateur technique | Exploitant | Service disponible et restaurable | Ne doit pas obtenir de droits métier par défaut |

<!-- brainstorm-section: goals-and-non-goals -->
## Objectifs et exclusions

Objectifs : rendre visibles les prochaines actions ; conserver le lien entre source, demande, réponse, observation, défense et décision ; permettre de vérifier chaque chiffre depuis les dossiers qui le composent ; tracer le relais vers GELEC quand il existe.

Exclusions de la première portée : calcul du contentieux, automatisation GELEC/SYDONIA, portail de réponse externe, inférence automatique d'infraction, modèle de document présenté comme officiel sans validation.

<!-- brainstorm-section: insights-and-contradictions -->
## Enseignements et tensions

- La note décrit une séquence en six étapes, mais `description.md` précise qu'une alerte peut être diffusée sans dossier ni entreprise identifiée et que plusieurs actes peuvent avancer en parallèle. Le parcours doit donc guider sans imposer une chaîne obligatoire.
- Une réponse peut être complète en pièces et rester insuffisante sur le fond ; le simple statut « satisfaisant / non satisfaisant » de la note ne suffit pas pour suivre les éléments demandés.
- La note P1/P2 et la priorité V1 récente divergent. Une V1 qui couvre quatre besoins **à profondeur limitée** répond au cadrage récent, sous réserve d'arbitrage DGDA.
- Le passage vers GELEC est une frontière de responsabilité, pas une preuve qu'une API existe. Une référence et une réception confirmée manuellement peuvent suffire au pilote.

## Trois parcours à rejouer en atelier

1. **Réponse satisfaisante :** recevoir un renseignement → vérifier sa confidentialité et le qualifier → ouvrir/affecter un dossier → préparer une demande avec éléments attendus → faire valider, émettre et conserver la preuve → rattacher réponse et justificatifs à chaque élément → motiver le classement → retrouver le dossier dans la statistique correspondante. Vérifier qui signe, qui classe et quels documents font foi.
2. **Réponses partielles et observations multiples :** ouvrir un dossier → émettre une demande → enregistrer réponse partielle et complément sans écraser la première → formaliser plusieurs observations étayées → notifier la feuille → rattacher une ou plusieurs défenses aux observations concernées → apprécier chacune avec motif → faire valider la suite → tracer un éventuel transfert et sa réception par GELEC. Vérifier si une mission est requise et où chaque type de PV est produit.
3. **Alerte interservices :** recevoir une information sans cible identifiée → la qualifier et protéger la source → diffuser à plusieurs bureaux avec action attendue → enregistrer séparément leurs accusés et retours → ouvrir un dossier seulement si une investigation le justifie → conserver le résultat dans les statistiques sans créer de fausse entreprise ou infraction.

<!-- brainstorm-section: option-portfolio -->
## Directions envisageables

### A — Modules complets par fonction

Chaque équipe retrouve un module spécialisé renseignement, demandes, feuilles ou rapports. Le parcours suit les menus et consolide ensuite les actes dans le dossier. L'adoption paraît familière, mais les interfaces et validations risquent d'être construites avant que leur articulation réelle soit vérifiée. À choisir si les unités opèrent déjà par fonctions stables ; à écarter si les dossiers traversent souvent plusieurs services. Test le moins coûteux : cartographier quelques cas réels entre unités.

### B — Dossier et prochaine action, avec quatre parcours fins

À chaque réception ou événement, l'agent retrouve le dossier ou la diffusion concernée, voit le responsable et la prochaine action, puis produit l'acte nécessaire. Les quatre besoins figurent en V1, avec le niveau de détail indispensable au parcours et à sa traçabilité. Le changement demandé est de travailler à partir d'une chronologie commune. Risque principal : processus officiels et circuits papier incompatibles avec un suivi unique. À choisir si le rejeu de dossiers montre une perte de contexte entre actes ; à écarter si le dossier commun n'apporte aucune valeur observée. Test : maquette cliquable et simulation de trois dossiers.

### C — Registre et modèles standardisés, sans nouveau logiciel métier complet

Un registre contrôlé, des modèles approuvés et une revue hebdomadaire peuvent réduire les oublis à coût initial faible. Les agents continuent les courriers et classements actuels, puis un responsable consolide les chiffres. Risques : travail manuel, versionnement fragile et difficulté à protéger les sources sensibles. À choisir si les volumes sont faibles et le processus déjà fiable ; à écarter si plusieurs acteurs doivent retrouver l'historique fin ou si les erreurs de consolidation sont récurrentes. Test : essai manuel sur des cas anonymisés et mesure du temps/erreurs.

<!-- brainstorm-section: comparison-and-recommendation -->
## Comparaison et recommandation

| Critère pour le pilote | A — Modules | B — Dossier | C — Registre |
|---|---|---|---|
| Couverture des quatre besoins | Forte, développement large | Forte, portée étroite | Possible, effort humain fort |
| Vérification de la prochaine action et des chiffres | Nécessite une consolidation | Native au parcours proposé | Dépend de la discipline manuelle |
| Temps pour apprendre les règles réelles | Plus long | Court via trois scénarios | Court |
| Confidentialité et traçabilité | À concevoir | À concevoir dès le parcours | Difficiles à assurer à grande échelle |
| Coût d'une hypothèse métier erronée | Élevé | Modéré si le pilote reste étroit | Faible au départ |

**Recommandation : B pour la conception et le pilote**, sous réserve du rejeu métier. Le prix accepté est une couverture fonctionnelle initiale peu profonde : les cas rares resteront traités par procédure encadrée. C est le meilleur comparateur de coût ; si un registre et des modèles suffisent à satisfaire les mêmes exigences sur le terrain, il doit gagner. Un échec répété à représenter les dossiers réels ferait revenir vers A ou vers une intervention de processus.

<!-- brainstorm-section: first-learning-scope -->
## Première portée d'apprentissage

**Véhicule :** prototype testé avec données fictives, puis pilote dans une unité choisie par la DGDA. Le prototype répond aux questions de parcours ; seul le pilote peut montrer adoption et valeur opérationnelle.

**Parcours minimal :** réception/qualification → diffusion ou dossier → action attribuée → demande et réponse ou feuille et défense → décision motivée → clôture ou relais → chiffre traçable. Les trois variantes ci-dessus doivent pouvoir être rejouées sans inventer de cible, de mission ou de réponse.

**Capacités minimales du pilote :** comptes et accès par habilitation validée ; dossiers/alertes et chronologie ; affectation et prochaine action ; demandes avec éléments distincts et réponses successives ; feuilles avec observations et défenses distinctes ; numérisation ou import de chaque courrier de réponse, défense et pièce papier, rattachés à l'acte correspondant avec date réelle de réception ; décisions ; tous les documents reçus et produits consultables par étape du dossier ; saisie courte préremplie, aperçu, PDF téléchargeable et imprimable pour les demandes et feuilles ; impression d'un document ou d'un dossier PDF de consultation selon les droits ; conservation de la version émise, de l'original signé numérisé et de la preuve de remise ou d'envoi ; quelques indicateurs dont chaque valeur mène à ses dossiers. Les modèles et règles utilisés doivent être approuvés pour le pilote.

**Opérations manuelles visibles :** signature et notification selon le circuit DGDA après impression, numérisation éventuelle du document signé, saisie de la preuve de remise ou d'envoi, référence GELEC et confirmation de réception. Imprimer un PDF ne vaut pas validation, signature ou notification. Les intégrations ne sont pas prérequises.

**Signaux de décision :** les trois scénarios sont exécutables de bout en bout par les agents désignés ; chaque document du dossier est retrouvable à l'étape correspondante ; une demande et une feuille sont saisies une seule fois puis générées en PDF imprimable ; un courrier reçu sur papier et ses annexes sont numérisés ou importés, liés au bon acte et visibles dans la chronologie ; un complément ne remplace pas la première réponse ; la version réellement transmise et sa preuve restent disponibles après modification d'un brouillon ; chaque acte émis et chaque valeur statistique a une pièce ou un enregistrement retraçable ; aucune consultation non autorisée n'est constatée ; les agents identifient plus vite la prochaine action qu'avec leur pratique initiale, mesurée sur les mêmes cas. Les seuils temporels précis et le nombre de dossiers du pilote seront arrêtés après mesure de référence et choix de l'unité. Une faille d'accès ou une impossibilité de respecter le circuit officiel suspend le pilote.

<!-- brainstorm-section: validation-backlog -->
## Validation ordonnée

| Priorité | Hypothèse | Preuve actuelle | Test proposé | Règle de décision | Horizon / responsable | Limite |
|---:|---|---|---|---|---|---|
| 1 | Les quatre besoins sont bien obligatoires en V1 et la frontière GELEC est acceptée. | Documents divergents sur les priorités | Arbitrage avec commanditaire DGDA et responsable GELEC | Périmètre et types de PV consignés par écrit avant spécification | Atelier initial / DGDA | Une validation de principe ne fixe pas tous les cas |
| 2 | Les trois parcours représentent les pratiques légitimes. | Parcours proposés, non observés | Rejeu de dossiers anonymisés avec enquêteurs et valideurs | Chaque écart critique reçoit une décision de règle, de variante ou de hors portée | Atelier initial / métier | Échantillon de cas potentiellement incomplet |
| 3 | Le dossier commun réduit pertes de contexte et double saisie. | Aucune mesure | Observation du travail actuel, puis tâches sur prototype | Les agents retrouvent pièces, responsable et prochaine action sans contournement ; comparer temps et erreurs à la référence | Conception / équipe produit | Prototype ≠ usage quotidien |
| 4 | Les documents, habilitations et délais peuvent être appliqués sans risque. | À confirmer dans les deux sources | Collecte de modèles officiels et revue des règles par personnes habilitées | Aucun acte pilote émis avant validation de son modèle et de son circuit | Avant pilote / DGDA | Les règles peuvent varier selon unité |
| 5 | Les statistiques reflètent l'activité sans ressaisie. | Indicateurs proposés | Recalcul contradictoire d'un échantillon de chiffres du pilote | Chaque chiffre est explicable par une liste de dossiers/actes et une définition validée | Pilote / responsable métier | La qualité dépend de la saisie initiale |

<!-- brainstorm-section: risks-and-safeguards -->
## Risques et garde-fous

| Risque | Effet possible | Garde-fou proposé | Validation nécessaire |
|---|---|---|---|
| Source protégée ou données commerciales exposées | Préjudice aux personnes et à l'enquête | Séparer identité de source et résumé exploitable ; accès par besoin ; journaliser consultations et exports | Politique DGDA avant données réelles |
| Projet d'acte confondu avec acte officiel | Notification ou décision irrégulière | Distinguer brouillon, validation, signature et émission ; conserver la version envoyée | Signataires et modèles DGDA |
| Absence de réponse assimilée à une infraction | Conclusion erronée | Séparer absence, réponse partielle et appréciation motivée ; validation humaine des suites | Règles métier DGDA |
| Statistiques trompeuses | Pilotage erroné | Définition d'indicateurs, déduplication, accès aux dossiers sous-jacents selon droits | Responsable métier |
| Réseau ou hébergement inadapté | Service inutilisable ou données non maîtrisées | Essai sur les sites pilotes, décision d'hébergement et restauration testée avant généralisation | DGDA et exploitation |

<!-- brainstorm-section: discovery-stress-test -->
## Test de résistance

- **Pourquoi le problème pourrait être moins grave :** les équipes ont peut-être déjà un registre et un circuit documentaire suffisamment fiables ; aucune fréquence de perte ni coût de double saisie n'est mesuré.
- **Hypothèse qui invaliderait la direction :** les unités ne peuvent pas partager un dossier et une chronologie utilisables sans violer leurs règles de confidentialité ou de compétence.
- **Alternative crédible la moins coûteuse :** modèles approuvés, registre contrôlé et revue des actions en retard.
- **Échec principal :** le logiciel ajoute une saisie après les courriers papier sans devenir la source de suivi opérationnel.
- **Signal d'arrêt ou de pivot :** les mêmes informations sont ressaisies systématiquement, un acte officiel ne peut être correctement représenté, ou une donnée sensible devient visible hors habilitation. Expansion uniquement après parcours répétés, chiffres vérifiés et restauration démontrée.

<!-- brainstorm-section: decisions-and-unknowns -->
## Décisions et inconnues

**Proposition à arbitrer :** quatre besoins présents en V1 à profondeur limitée ; dossier comme pivot ; relais GELEC d'abord tracé manuellement. **Décisions DGDA nécessaires :** unité pilote, rôles et signataires, modèles et mentions obligatoires, délais, types de PV et lieu de leur production, confidentialité des sources, définitions des indicateurs. **Décisions différables :** API, automatisations, analyses avancées, portail externe. Aucun pouvoir de signature, délai légal ou échange technique n'est déduit des documents.

<!-- brainstorm-section: handoff-for-prd -->
## Handoff for PRD

- **Objectif produit :** rendre l'enquête précontentieuse traçable et pilotable, de la réception du renseignement jusqu'à une clôture motivée ou un relais confirmé.
- **Acteurs :** enquêteurs, responsables d'unité, opérateurs documentaires et administrateurs ; direction comme commanditaire ; sources et parties comme personnes affectées.
- **Situation et résultat :** suivre pièces, actes, réponses, responsables et prochaine action, puis produire des statistiques explicables.
- **Valeur proposée :** dossier/chronologie communs avec quatre parcours fins plutôt que quatre silos complets.
- **Frontière MVP :** trois scénarios de référence, droits approuvés, dossier documentaire complet par étape, PDF imprimables créés depuis les formulaires de demande et de feuille, impression du dossier selon les droits, versions émises et preuves papier conservées, réponses et défenses papier numérisées ou importées sans écrasement puis traitées par élément, décision motivée, relais manuel, indicateurs traçables. Les automatisations externes sont exclues.
- **Contraintes :** GELEC garde le contentieux détaillé ; les règles, modèles et habilitations requièrent validation DGDA ; aucune donnée sensible réelle dans le prototype non autorisé.
- **Évidence :** note de cadrage p. 1–6 et `description.md` §1–2, §5–6 et §10 ; pas encore d'observation de terrain.
- **Hypothèses critiques :** utilité du dossier commun, adéquation des trois parcours, baisse effective de la double saisie, faisabilité du circuit documentaire et des droits.
- **Signaux :** exécution de bout en bout, prochaine action retrouvée, chiffres recalculables, absence d'accès indu ; arrêter sur défaut de confidentialité ou impossibilité de respecter un acte officiel.
- **Questions ouvertes :** priorités officiellement arbitrées, règles de signature/notification, délais, origine admise d'une feuille, types de PV, périmètre de visibilité interservices et conditions d'hébergement.
