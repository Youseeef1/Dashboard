# 📊 Dashboard Funnel — Campagne d'appels IA

## Objectif
Ce dashboard Streamlit permet d’analyser la performance d’une campagne d’appels automatisés (IA) à partir de données stockées sur Google Sheets.

##  Choix techniques
- **Streamlit** : création rapide d’un dashboard interactif et lisible pour un client non technique  
- **Plotly** : visualisations dynamiques (funnel, bar charts)  
- **Google Sheets API (gspread + credentials)** : récupération automatique des donnée par API de google (je vous laisse le fichier .json à récupérer et pensez à modifier le path au début du fichier Dashboard.py )  
- **Pandas** : nettoyage, transformation et calcul des indicateurs  

Un travail important de **nettoyage des données** a été réalisé (formats, valeurs manquantes, normalisation texte) afin de garantir des analyses fiables.

## 📊 À regarder en priorité
1. **KPIs globaux**  
   - Total appels  
   - Taux de passage filtre  --> premier filtre automatique
   - Taux de conversion (confirmateur)  --> appels aboutissants à un résultat positif 
   - L'effet du filtrage et les différentes classes de résultats (histogramme des résultats)

3. **Analyse par liste**  
   → Identifier les sources de leads les plus performantes avec leurs nombres d'appels et aussi le résultat de ces appels en comparant le code postale avant et après l'appel , cela nous montre les listes les plus efficaces.  

## 🔍 Analyses complémentaires
- Profil des bons prospects (type de logement ,type de sol, type de chauffage)  
- Durée des appels (corrélation avec qualité des leads)  
- Meilleures plages horaires pour appeler (très important)  
- Analyse géographique (volume d'appel par ville, code postale, le taux du filtre par ville)  

##  Finalité
Ce dashboard a pour objectif d’apporter une aide à la décision en mettant en évidence les leviers d’optimisation de la campagne.

Il permet notamment de :
- comprendre où se situent les pertes dans le funnel de conversion  
- identifier les listes de prospects les plus rentables  
- analyser les caractéristiques des leads à fort potentiel  
- déterminer les créneaux horaires les plus efficaces pour maximiser les résultats  

##  Compilation du code 
Utiliser la commande  streamlit run Dashboard.py

