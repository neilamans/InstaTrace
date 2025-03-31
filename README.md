# InstaTrace : Protéger vos habitudes numériques, anticiper les cybermenaces.
## Notice d’installation et d’exécution
### Prérequis

Avant de commencer, assurez-vous d'avoir installé les bibliothèques Python nécessaires :

```bash
pip install pandas numpy scikit-learn matplotlib seaborn plotly streamlit
```

### Structure du projet

Le projet se compose de trois fichiers Python principaux :
- dataTrain.py : fichier de génération des données simulées
- InstaTrace.py : fichier principal d'analyse et de détection d'anomalies
- interface.py : Interface web de visualisation des résultats

### Étapes d'exécution

#### 1. Génération des données
Commencez par générer les données simulées en exécutant le fichier dataTrain.py :

```bash
python dataTrain.py
```
Ce script va créer un dossier TrainData contenant un fichier simulated_activities.json. 
Ce fichier contient des activités utilisateur simulées, incluant à la fois des comportements normaux et des comportements anormaux (connexions à des heures inhabituelles, depuis des pays inhabituels, actions sensibles ...)

#### 2. Analyse et détection d'anomalies
Exécutez ensuite le fichier principal d'analyse :

```bash
python InstaTrace.py
```
Ce script va :
- Charger les données générées
- Normaliser les logs provenant de différentes sources
- Extraire des caractéristiques pertinentes (heure de connexion, jour de la semaine, etc.)
- Appliquer l'algorithme IsolationForest pour détecter les anomalies
- Générer des visualisations et des rapports des résultats
  
L'exécution de ce script créera un dossier output contenant :
- anomaly_by_hour.png : Graphique montrant la répartition des activités normales et anormales par heure
- anomaly_distribution.png : Distribution des scores d'anomalie
- anomaly_report.txt : Rapport détaillé des anomalies détectées
- results.csv : Ensemble des données avec les scores d'anomalie associés
- suspicious_cases.csv : Liste des cas suspects identifiés
- top_suspicious.png : Visualisation des cas les plus suspects
  
#### 3. Visualisation via l'interface web
Pour explorer les résultats de manière interactive, lancez l'interface web :

```bash
streamlit run interface.py
```
Cette commande ouvrira automatiquement une page web dans votre navigateur par défaut 
L'interface Streamlit offre une visualisation interactive des résultats, comprenant :
- Un tableau de bord avec des métriques clés (nombre total d'événements, anomalies détectées, alertes prioritaires)
- Des graphiques de distribution des anomalies
- Des visualisations d'activités par heure et par jour
- Une liste détaillée des alertes de haute priorité
- Des statistiques par utilisateur
  
Streamlit a été choisi pour sa simplicité d'implémentation et sa capacité à créer rapidement des applications web interactives 

#### Remarques importantes
- Assurez-vous d'exécuter les scripts dans l'ordre indiqué
- Tous les fichiers doivent être placés dans le même dossier
- L'interface web restera active jusqu'à ce que vous fermiez le terminal ou appuyiez sur Ctrl+C
