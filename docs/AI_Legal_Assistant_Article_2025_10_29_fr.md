![AI Legal Assistant](./ai_legal_article_10c.png)

# Concevoir la transparence dans des flux de travail juridiques natifs à l’IA

## Introduction : aperçu du projet

⚖️ **AI Legal Assistant** est un système modulaire et explicable qui explore comment les grands modèles de langage peuvent *augmenter* le raisonnement juridique plutôt que le remplacer. Il est conçu pour analyser des documents juridiques, identifier les clauses clés, évaluer les risques et générer des résumés en langage clair — tout en exposant le raisonnement derrière chaque résultat. Le système vise à apporter **clarté, traçabilité et confiance** au travail juridique assisté par l’IA. Né du besoin d’une **IA fiable et auditable dans les flux de travail juridiques**, ce projet montre comment l’explicabilité peut être intégrée directement au cœur de la conception du système — et non ajoutée plus tard comme rustine ou simple couche de conformité.

[Voir le projet sur GitHub **AI Legal Assistant** →](https://github.com/markiskorova/ai-legal-assistant)

Voici ce que nous construisons, comment le système est structuré et vers quoi il évolue.

## Vue d’ensemble du système

![Workflow Diagram](./ai_legal_article_workflow_d.png)

Au cœur d’**AI Legal Assistant**, on retrouve la même logique que celle utilisée par les avocats lorsqu’ils examinent des documents et construisent des dossiers :

**Document → Constatations → Dossier → Problématiques → Stratégie → Explicabilité**

Chaque étape transforme le texte brut en raisonnement structuré :  
- **Document :** Ingérer et analyser le texte juridique (contrats, NDA, politiques, etc.).  
- **Constatations :** Extraire les clauses, évaluer les risques et résumer les résultats.  
- **Dossier :** Regrouper les documents liés au sein d’un espace de travail de dossier unifié.  
- **Problématiques :** Détecter les arguments récurrents ou les motifs qui traversent les constatations.  
- **Stratégie :** Suggérer les prochaines étapes ou les priorités de négociation.  
- **Explicabilité :** Révéler les preuves, la logique et la provenance du modèle.

Cette approche en couches reflète la manière dont le raisonnement juridique fonctionne en pratique — contextualisé, itératif et fondé sur les preuves — tout en rendant chaque sortie de modèle **traçable, inspectable et vérifiable**.

## Fonctionnalités clés

### Analyse des clauses et évaluation des risques

Des contrôles déterministes basés sur des règles fonctionnent de concert avec le raisonnement du LLM pour identifier les types de clauses, les risques potentiels et les révisions recommandées. Chaque constat inclut des références aux preuves, des niveaux de confiance et une justification résumée.

### Agrégation des dossiers et raisonnement

Les documents peuvent être regroupés en dossiers, ce qui permet au système d’agréger les constatations au niveau des clauses en problématiques ou motifs juridiques plus larges.

### Couche d’explicabilité

Chaque sortie du modèle inclut sa **justification, un extrait de preuve et un score de confiance**, ce qui rend possible l’audit ou la reconstitution de chaque conclusion.

### Provenance et observabilité (prévu)

Un tableau de bord à venir suivra l’usage des tokens, les versions de modèles, les coûts et les révisions de prompts — afin de soutenir la conformité, la gouvernance et l’optimisation des performances.

## Pile technique et architecture

La pile est volontairement simple et modulaire — conçue pour la clarté, la portabilité et la reproductibilité.

- **Backend :** Django + Django REST Framework  
- **Base de données :** PostgreSQL (avec pgvector en option pour les requêtes sémantiques)  
- **Traitement asynchrone :** Celery + Redis  
- **Frontend :** Tableau de bord React léger pour la visualisation des dossiers  
- **Interface LLM :** OpenAI GPT-4o avec validation via schémas JSON et vérification des preuves  
- **Infrastructure :** Docker + Terraform (AWS ECS, RDS, S3) + GitHub Actions CI/CD  

Chaque composant est construit comme une application autonome au sein du projet Django, ce qui garantit une évolutivité future et une intégration aisée avec d’autres domaines comme la conformité ou la découverte (e-discovery).

## Pourquoi c’est important

L’IA transforme déjà le secteur juridique, mais de nombreux outils restent des **boîtes noires** — ils produisent des résultats sans exposer leur raisonnement. Pour une profession fondée sur les preuves et l’argumentation, ce manque de visibilité est un problème structurel. **AI Legal Assistant** vise à changer cela en montrant comment **l’explicabilité et la provenance peuvent être tissées directement dans l’architecture elle-même**. Plutôt que de traiter la transparence comme une réflexion tardive, ce projet en fait le fondement d’une collaboration fiable entre l’IA et les juristes.

L’objectif n’est pas de remplacer le raisonnement juridique — mais de rendre le raisonnement de l’IA **visible, vérifiable et exploitable** par les avocats.

## Prochaines étapes

Le projet en est encore à un stade précoce de développement, avec le backend et les modèles de données en cours de finalisation. Les prochains jalons incluent :

1. Implémenter l’extraction des clauses et la validation basée sur des règles  
2. Ajouter l’agrégation au niveau du dossier et la détection des problématiques  
3. Construire l’API d’explicabilité pour exposer les preuves et les scores de confiance  
4. Développer un tableau de bord d’observabilité pour le suivi des coûts et de la provenance  

Vous pouvez suivre l’avancement ou explorer le code ici :  
[GitHub Repository – AI Legal Assistant](https://github.com/markiskorova/ai-legal-assistant)  

## Questions ouvertes de conception

Au fur et à mesure que le système évolue, plusieurs questions restent au cœur de l’exploration :  
- Comment le raisonnement juridique piloté par l’IA doit-il être présenté aux avocats — sous la forme d’un récit ou de vues orientées données ?  
- Où se situe la limite entre une synthèse utile et un excès dans la simplification des contenus juridiques ?  
- Quelles formes de visualisation des preuves créent le plus de confiance ?

Si vous travaillez dans la legal tech, la conformité ou l’IA explicable, vos retours m’intéressent.

#LegalTech #ExplainableAI #AINative #Transparency #Django #OpenAI #SoftwareArchitecture #EthicalAI
