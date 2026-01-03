# 📊 RAPPORT COMPLET DU PROJET - Système de Filtrage de Messages MQTT

**Date du rapport :** 29 Décembre 2025  
**Version :** 1.0  
**État :** ✅ Opérationnel (Docker) | ✅ Opérationnel (Kubernetes)

---

## 📋 TABLE DES MATIÈRES

1. [Vue d'ensemble du projet](#1-vue-densemble-du-projet)
2. [Architecture complète](#2-architecture-complète)
3. [Services détaillés](#3-services-détaillés)
4. [Technologies utilisées](#4-technologies-utilisées)
5. [Déploiement Docker](#5-déploiement-docker)
6. [Déploiement Kubernetes](#6-déploiement-kubernetes)
7. [Dashboard UI](#7-dashboard-ui)
8. [Problèmes rencontrés et résolus](#8-problèmes-rencontrés-et-résolus)
9. [État actuel](#9-état-actuel)
10. [Structure du projet](#10-structure-du-projet)
11. [Flux de données complet](#11-flux-de-données-complet)
12. [Configuration et personnalisation](#12-configuration-et-personnalisation)

---

## 1. VUE D'ENSEMBLE DU PROJET

### 1.1 Objectif

Ce projet implémente un **système de filtrage de messages en temps réel** utilisant une architecture de **microservices** communiquant via le protocole **MQTT**. Le système analyse chaque message à travers plusieurs inspections (mots-clés suspects, URLs malveillantes, règles de format) avant de prendre une décision finale : **ALLOW**, **QUARANTINE**, ou **BLOCK**.

### 1.2 Cas d'usage

- **Filtrage de spam** : Détecter et bloquer les messages suspects
- **Sécurité** : Identifier les URLs malveillantes et les mots-clés suspects
- **Validation de format** : Vérifier que les messages respectent les règles de format
- **Décision automatisée** : Prendre des décisions basées sur des scores agrégés

### 1.3 Caractéristiques principales

✅ **Architecture microservices** - Services indépendants et découplés  
✅ **Communication asynchrone** - Via MQTT (Message Queue Telemetry Transport)  
✅ **Tracing distribué** - Suivi complet des messages avec traceId/spanId  
✅ **Résilience** - Gestion des timeouts et modes dégradés  
✅ **Observabilité** - Logs structurés et métriques  
✅ **Visualisation temps réel** - Dashboard web interactif  
✅ **Dockerisé** - Déploiement facile avec Docker Compose  
✅ **Kubernetes-ready** - Manifests K8s complets  

---

## 2. ARCHITECTURE COMPLÈTE

### 2.1 Schéma d'architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MQTT BROKER (Mosquitto)                   │
│                    Topics: msg.raw, msg.*.result,                │
│                    msg.score, msg.decision                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                       │
        ▼                     ▼                       ▼
┌──────────────┐    ┌──────────────┐        ┌──────────────┐
│   GENERATOR  │    │ KEYWORD      │        │    URL      │
│              │    │   FILTER     │        │ INSPECTOR   │
│ Génère msg   │───▶│              │        │             │
│ toutes les   │    │ Détecte      │        │ Détecte     │
│ 5 secondes   │    │ mots-clés    │        │ URLs        │
└──────────────┘    └──────────────┘        └──────────────┘
        │                     │                       │
        │                     │                       │
        │         ┌─────────────┴─────────────┐        │
        │         │                           │        │
        │         ▼                           ▼        │
        │  ┌──────────────┐          ┌──────────────┐ │
        │  │   FORMAT     │          │  AGGREGATOR  │ │
        │  │   CHECKER    │          │              │ │
        │  │              │          │ Joint les 3  │ │
        │  │ Vérifie      │          │ résultats    │ │
        │  │ format       │          │ + timeout    │ │
        │  └──────────────┘          └──────────────┘ │
        │                                    │         │
        │                                    ▼         │
        │                            ┌──────────────┐ │
        │                            │ FINAL ROUTER │ │
        │                            │              │ │
        │                            │ Décision     │ │
        │                            │ ALLOW/       │ │
        │                            │ QUARANTINE/  │ │
        │                            │ BLOCK        │ │
        │                            └──────────────┘ │
        │                                    │         │
        └────────────────────────────────────┼─────────┘
                                             │
                                             ▼
                                    ┌──────────────┐
                                    │ UI DASHBOARD │
                                    │              │
                                    │ Visualisation│
                                    │ temps réel   │
                                    └──────────────┘
```

### 2.2 Flux de messages

1. **Generator** → Publie sur `msg.raw` toutes les 5 secondes
2. **3 Inspecteurs parallèles** (Keyword, URL, Format) → S'abonnent à `msg.raw`, publient leurs résultats
3. **Aggregator** → Attend les 3 résultats, joint par `messageId`, calcule un score
4. **Final Router** → Applique des seuils, prend une décision
5. **UI Dashboard** → Visualise tout en temps réel

### 2.3 Topics MQTT

| Topic | Description | Publisher | Subscribers |
|-------|-------------|-----------|-------------|
| `msg.raw` | Messages bruts générés | Generator | Keyword Filter, URL Inspector, Format Checker, UI Dashboard |
| `msg.keyword.result` | Résultats du filtre de mots-clés | Keyword Filter | Aggregator, UI Dashboard |
| `msg.url.result` | Résultats de l'inspecteur d'URLs | URL Inspector | Aggregator, UI Dashboard |
| `msg.format.result` | Résultats du vérificateur de format | Format Checker | Aggregator, UI Dashboard |
| `msg.score` | Score agrégé final | Aggregator | Final Router, UI Dashboard |
| `msg.decision` | Décision finale | Final Router | UI Dashboard |

---

## 3. SERVICES DÉTAILLÉS

### 3.1 Generator Service

**Fichier :** `services/generator/main.py`  
**Image Docker :** `docker-generator:latest`  
**Port :** N/A (client MQTT uniquement)

#### Fonctionnalités

- Génère des messages bruts toutes les 5 secondes (configurable)
- Crée des traces distribuées (traceId, spanId, parentSpanId)
- Génère des UUIDs uniques pour chaque message
- Contenu varié pour tester différents scénarios

#### Configuration

```yaml
BROKER_HOST: mosquitto
BROKER_PORT: 1883
RAW_TOPIC: msg.raw
INTERVAL_SECONDS: 5
```

#### Format de message publié

```json
{
  "messageId": "uuid-v4",
  "timestamp": "2025-12-29T23:00:00.000Z",
  "content": "Check out this amazing offer! Click here: http://suspicious-site.com",
  "trace": {
    "traceId": "uuid-v4",
    "spanId": "uuid-v4",
    "parentSpanId": null
  }
}
```

#### Logs

```
messageId=<uuid> traceId=<uuid> serviceName=generator latencyMs=<ms> eventType=message_published status=success
```

---

### 3.2 Keyword Filter Service

**Fichier :** `services/keyword-filter/main.py`  
**Image Docker :** `docker-keyword-filter:latest`

#### Fonctionnalités

- S'abonne à `msg.raw`
- Détecte les mots-clés suspects dans une blacklist
- Calcule un score basé sur le nombre de mots-clés trouvés
- Publie sur `msg.keyword.result`

#### Configuration

```yaml
BROKER_HOST: mosquitto
BROKER_PORT: 1883
INPUT_TOPIC: msg.raw
OUTPUT_TOPIC: msg.keyword.result
KEYWORD_BLACKLIST: URGENT,WIN,CLICK,OFFER
```

#### Algorithme

- Convertit le contenu en majuscules
- Recherche chaque mot-clé de la blacklist
- Score = `min(1.0, nombre_mots_clés_trouvés * 0.3)`
- `passed = true` si aucun mot-clé trouvé

#### Format de résultat

```json
{
  "messageId": "uuid",
  "timestamp": "ISO8601",
  "trace": {
    "traceId": "uuid",
    "spanId": "uuid",
    "parentSpanId": "uuid"
  },
  "result": {
    "passed": false,
    "foundKeywords": ["URGENT", "CLICK"],
    "score": 0.6
  },
  "serviceName": "keyword-filter"
}
```

---

### 3.3 URL Inspector Service

**Fichier :** `services/url-inspector/main.py`  
**Image Docker :** `docker-url-inspector:latest`

#### Fonctionnalités

- S'abonne à `msg.raw`
- Extrait toutes les URLs du contenu (regex)
- Vérifie si les domaines sont dans une liste de domaines suspects
- Calcule un score basé sur les URLs trouvées

#### Configuration

```yaml
BROKER_HOST: mosquitto
BROKER_PORT: 1883
INPUT_TOPIC: msg.raw
OUTPUT_TOPIC: msg.url.result
SUSPICIOUS_DOMAINS: suspicious-site.com,spam-domain.net
```

#### Algorithme

- Extrait les URLs avec regex : `http(s)?://[^\s]+`
- Parse les domaines
- Vérifie contre la liste de domaines suspects
- Score = `min(1.0, nombre_urls_suspectes * 0.5)`

---

### 3.4 Format Checker Service

**Fichier :** `services/format-checker/main.py`  
**Image Docker :** `docker-format-checker:latest`

#### Fonctionnalités

- S'abonne à `msg.raw`
- Vérifie la longueur du message
- Détecte les caractères interdits
- Calcule le ratio de symboles

#### Configuration

```yaml
BROKER_HOST: mosquitto
BROKER_PORT: 1883
INPUT_TOPIC: msg.raw
OUTPUT_TOPIC: msg.format.result
MAX_LENGTH: 200
FORBIDDEN_CHARS: |,<,>
MAX_SYMBOL_RATIO: 0.3
```

#### Règles de validation

1. **Longueur** : Message ne doit pas dépasser `MAX_LENGTH` caractères
2. **Caractères interdits** : Ne doit pas contenir `FORBIDDEN_CHARS`
3. **Ratio symboles** : Ratio symboles/lettres ne doit pas dépasser `MAX_SYMBOL_RATIO`

#### Score

- Chaque violation ajoute 0.33 au score
- Score final = `min(1.0, violations * 0.33)`

---

### 3.5 Aggregator Service

**Fichier :** `services/aggregator/main.py`  
**Image Docker :** `docker-aggregator:latest`

#### Fonctionnalités

- S'abonne aux 3 topics de résultats (`msg.keyword.result`, `msg.url.result`, `msg.format.result`)
- Joint les résultats par `messageId`
- Gère les timeouts (3 secondes par défaut)
- Calcule un score global (moyenne des 3 scores)
- Publie sur `msg.score`

#### Configuration

```yaml
BROKER_HOST: mosquitto
BROKER_PORT: 1883
TOPIC_KEYWORD: msg.keyword.result
TOPIC_URL: msg.url.result
TOPIC_FORMAT: msg.format.result
OUTPUT_TOPIC: msg.score
JOIN_TIMEOUT_SECONDS: 3
```

#### Algorithme de jointure

1. Reçoit un résultat → Stocke dans `pending_results[messageId]`
2. Vérifie si les 3 résultats sont présents
3. Si oui → Calcule le score (moyenne) et publie
4. Si non → Attend jusqu'au timeout

#### Gestion des timeouts

- Thread séparé vérifie toutes les secondes les messages en attente
- Si un message dépasse `JOIN_TIMEOUT_SECONDS` :
  - Calcule le score avec les résultats disponibles
  - Ajoute une pénalité : `score += (nombre_résultats_manquants * 0.2)`
  - Marque comme `degraded: true`
  - Publie le score dégradé

#### Format de score

```json
{
  "messageId": "uuid",
  "timestamp": "ISO8601",
  "trace": {
    "traceId": "uuid",
    "spanId": "uuid",
    "parentSpanId": "uuid"
  },
  "score": 0.65,
  "degraded": false,
  "serviceName": "aggregator"
}
```

#### Bug corrigé

- **Problème initial** : Import `threading` redondant causant `UnboundLocalError`
- **Solution** : Suppression de l'import redondant dans la fonction `main()`

---

### 3.6 Final Router Service

**Fichier :** `services/final-router/main.py`  
**Image Docker :** `docker-final-router:latest`

#### Fonctionnalités

- S'abonne à `msg.score`
- Applique des seuils pour prendre une décision
- Publie sur `msg.decision`
- Compte les métriques (ALLOW/QUARANTINE/BLOCK)

#### Configuration

```yaml
BROKER_HOST: mosquitto
BROKER_PORT: 1883
INPUT_TOPIC: msg.score
OUTPUT_TOPIC: msg.decision
THRESHOLD_A: 0.3
THRESHOLD_B: 0.7
```

#### Algorithme de décision

```
Si score < THRESHOLD_A (0.3)  → ALLOW
Si THRESHOLD_A ≤ score < THRESHOLD_B (0.7) → QUARANTINE
Si score ≥ THRESHOLD_B (0.7) → BLOCK
```

#### Format de décision

```json
{
  "messageId": "uuid",
  "timestamp": "ISO8601",
  "trace": {
    "traceId": "uuid",
    "spanId": "uuid",
    "parentSpanId": "uuid"
  },
  "score": 0.65,
  "decision": "QUARANTINE",
  "serviceName": "final-router"
}
```

---

### 3.7 UI Dashboard Service

**Fichier :** `services/ui-dashboard/main.py`  
**Image Docker :** `docker-ui-dashboard:latest`  
**Port :** 5000

#### Fonctionnalités

- S'abonne à **tous** les topics MQTT
- Backend Flask avec WebSocket (Flask-SocketIO)
- Frontend HTML/JavaScript avec Socket.IO client
- Affichage en temps réel des données

#### Topics souscrits

- `msg.raw` - Messages bruts
- `msg.keyword.result` - Résultats keyword
- `msg.url.result` - Résultats URL
- `msg.format.result` - Résultats format
- `msg.score` - Scores finaux
- `msg.decision` - Décisions finales

#### Interface web

**Sections affichées :**

1. **Messages Bruts** - Contenu des messages générés
2. **Scores Partiels** - Résultats des 3 inspecteurs
3. **Score Final** - Score agrégé avec indicateur dégradé
4. **Décisions Finales** - ALLOW/QUARANTINE/BLOCK avec badges colorés
5. **Latence** - Temps entre message brut et décision
6. **Statistiques** - Nombre total de messages et décisions

#### Technologies frontend

- HTML5 / CSS3 (design moderne avec gradients)
- JavaScript (Socket.IO client)
- WebSocket pour communication temps réel
- Animations CSS pour les nouveaux messages

#### Technologies backend

- Flask 3.0.0
- Flask-SocketIO 5.3.5
- Paho MQTT 1.6.1
- Python 3.11

#### Calcul de latence

- Stocke le timestamp du message brut
- Lors de la réception de la décision, calcule la différence
- Affiche en millisecondes

---

## 4. TECHNOLOGIES UTILISÉES

### 4.1 Backend

| Technologie | Version | Usage |
|------------|---------|-------|
| Python | 3.11 | Langage principal |
| Paho MQTT | 1.6.1 | Client MQTT |
| Flask | 3.0.0 | Framework web (Dashboard) |
| Flask-SocketIO | 5.3.5 | WebSocket pour temps réel |

### 4.2 Infrastructure

| Technologie | Version | Usage |
|------------|---------|-------|
| Docker | Latest | Conteneurisation |
| Docker Compose | Latest | Orchestration locale |
| Kubernetes | 1.34.0 | Orchestration cloud |
| Mosquitto | 2.0 | Broker MQTT |

### 4.3 Frontend

| Technologie | Version | Usage |
|------------|---------|-------|
| HTML5 | - | Structure |
| CSS3 | - | Styling |
| JavaScript | ES6+ | Logique client |
| Socket.IO | 4.5.4 | WebSocket client |

---

## 5. DÉPLOIEMENT DOCKER

### 5.1 Structure Docker

**Fichier principal :** `infra/docker/docker-compose.yml`

#### Services Docker

1. **mosquitto** - Broker MQTT (image: `eclipse-mosquitto:2.0`)
2. **generator** - Service de génération (build local)
3. **keyword-filter** - Filtre de mots-clés (build local)
4. **url-inspector** - Inspecteur d'URLs (build local)
5. **format-checker** - Vérificateur de format (build local)
6. **aggregator** - Agrégateur (build local)
7. **final-router** - Routeur final (build local)
8. **ui-dashboard** - Dashboard web (build local)

#### Réseau Docker

- **Nom :** `mqtt-network`
- **Type :** Bridge
- **Tous les services** sont sur le même réseau

#### Volumes Docker

- `mosquitto_data` - Persistence des données MQTT
- `mosquitto_log` - Logs Mosquitto

### 5.2 Configuration Mosquitto

**Fichier :** `infra/docker/mosquitto.conf`

```conf
listener 1883
allow_anonymous true

persistence true
persistence_location /mosquitto/data/

log_dest file /mosquitto/log/mosquitto.log
log_type all
```

### 5.3 Dockerfiles

Chaque service a son propre Dockerfile :

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
CMD ["python", "main.py"]
```

**Exception :** UI Dashboard copie aussi le dossier `templates/`

### 5.4 Commandes Docker

#### Démarrer le système

```bash
cd infra/docker
docker-compose up --build
```

#### Démarrer en arrière-plan

```bash
docker-compose up -d --build
```

#### Voir les logs

```bash
docker logs -f generator
docker logs -f aggregator
docker logs -f final-router
```

#### Arrêter le système

```bash
docker-compose down
```

### 5.5 Problèmes résolus (Docker)

1. **Version obsolète dans docker-compose.yml**
   - **Problème :** `version: '3.8'` est obsolète
   - **Solution :** Supprimé la ligne `version`

2. **Cache Docker corrompu**
   - **Problème :** `unexpected end of JSON input`
   - **Solution :** Build avec `--no-cache`

---

## 6. DÉPLOIEMENT KUBERNETES

### 6.1 Structure Kubernetes

**Répertoire :** `infra/k8s/`

#### Manifests créés

1. **namespace.yaml** - Namespace `mqtt-filtering`
2. **configmaps.yaml** - 8 ConfigMaps de configuration
3. **mosquitto-deployment.yaml** - Deployment + Service pour Mosquitto
4. **generator-deployment.yaml** - Deployment Generator
5. **keyword-filter-deployment.yaml** - Deployment Keyword Filter
6. **url-inspector-deployment.yaml** - Deployment URL Inspector
7. **format-checker-deployment.yaml** - Deployment Format Checker
8. **aggregator-deployment.yaml** - Deployment Aggregator
9. **final-router-deployment.yaml** - Deployment Final Router
10. **ui-dashboard-deployment.yaml** - Deployment + Service NodePort pour Dashboard

### 6.2 ConfigMaps

#### topics-config
- `RAW_TOPIC`: "msg.raw"
- `KEYWORD_RESULT_TOPIC`: "msg.keyword.result"
- `URL_RESULT_TOPIC`: "msg.url.result"
- `FORMAT_RESULT_TOPIC`: "msg.format.result"
- `SCORE_TOPIC`: "msg.score"
- `DECISION_TOPIC`: "msg.decision"

#### keyword-blacklist
- `KEYWORD_BLACKLIST`: "URGENT,WIN,CLICK,OFFER"

#### suspicious-domains
- `SUSPICIOUS_DOMAINS`: "suspicious-site.com,spam-domain.net"

#### router-thresholds
- `THRESHOLD_A`: "0.3"
- `THRESHOLD_B`: "0.7"

#### format-rules
- `MAX_LENGTH`: "200"
- `FORBIDDEN_CHARS`: "|,<,>"
- `MAX_SYMBOL_RATIO`: "0.3"

#### aggregator-config
- `JOIN_TIMEOUT_SECONDS`: "3"

#### generator-config
- `INTERVAL_SECONDS`: "5"

#### broker-config
- `BROKER_PORT`: "1883"
- `mosquitto.conf`: Configuration complète

### 6.3 Health Checks

#### Readiness Probes

**Services Python :**
```yaml
readinessProbe:
  exec:
    command:
    - /bin/sh
    - -c
    - "python -c 'import paho.mqtt.client as mqtt; c = mqtt.Client(); c.connect(\"mosquitto\", 1883, 1); c.disconnect()'"
  initialDelaySeconds: 10
  periodSeconds: 10
```

**Mosquitto :**
```yaml
readinessProbe:
  tcpSocket:
    port: 1883
  initialDelaySeconds: 5
  periodSeconds: 10
```

**UI Dashboard :**
```yaml
readinessProbe:
  httpGet:
    path: /
    port: 5000
  initialDelaySeconds: 15
  periodSeconds: 10
```

#### Liveness Probes

Tous les services ont des liveness probes pour détecter les crashes.

### 6.4 Services Kubernetes

#### mosquitto (ClusterIP)
- Port 1883 (MQTT)
- Port 9001 (WebSocket)
- Accessible uniquement dans le cluster

#### ui-dashboard (NodePort)
- Port 5000 (HTTP)
- NodePort 30080
- Accessible depuis l'extérieur

### 6.5 Déploiement

#### Ordre recommandé

1. Namespace
2. ConfigMaps
3. Mosquitto (doit être prêt avant les autres)
4. Inspecteurs (keyword, url, format)
5. Generator
6. Aggregator
7. Final Router
8. UI Dashboard

#### Commandes

```bash
# Déploiement complet
cd infra/k8s
kubectl apply -f namespace.yaml
kubectl apply -f configmaps.yaml
kubectl apply -f mosquitto-deployment.yaml
kubectl wait --for=condition=ready pod -l app=mosquitto -n mqtt-filtering
kubectl apply -f generator-deployment.yaml
kubectl apply -f keyword-filter-deployment.yaml
kubectl apply -f url-inspector-deployment.yaml
kubectl apply -f format-checker-deployment.yaml
kubectl apply -f aggregator-deployment.yaml
kubectl apply -f final-router-deployment.yaml
kubectl apply -f ui-dashboard-deployment.yaml
```

### 6.6 Problèmes résolus (Kubernetes)

1. **Namespace non trouvé**
   - **Problème :** Erreurs "namespace not found" lors du déploiement
   - **Solution :** Appliquer les fichiers dans le bon ordre avec délai

2. **Kustomization.yaml**
   - **Problème :** Erreur si Kustomize n'est pas installé
   - **Solution :** Ignorer ce fichier ou installer Kustomize

3. **Images non trouvées (Minikube)**
   - **Problème :** `ErrImageNeverPull` - Minikube ne trouve pas les images locales
   - **Solution :** Utiliser `imagePullPolicy: IfNotPresent` et charger les images avec `minikube image load` ou construire dans l'environnement Minikube

4. **Service UI Dashboard non trouvé**
   - **Problème :** Le service n'existe pas dans le namespace
   - **Solution :** Vérifier que le déploiement est complet avec `kubectl get svc -n mqtt-filtering`

---

## 7. DASHBOARD UI

### 7.1 Architecture

**Backend :**
- Flask serveur web
- Flask-SocketIO pour WebSocket
- 6 clients MQTT (un par topic)
- Threads séparés pour chaque client MQTT

**Frontend :**
- Page HTML unique (`templates/index.html`)
- Socket.IO client pour WebSocket
- JavaScript pour mise à jour DOM
- CSS moderne avec animations

### 7.2 Fonctionnalités

#### Affichage en temps réel

1. **Messages Bruts**
   - Contenu du message
   - MessageId
   - Timestamp

2. **Scores Partiels**
   - Keyword : Pass/Fail, Score, Mots-clés trouvés
   - URL : Pass/Fail, Score, URLs trouvées
   - Format : Pass/Fail, Score, Violations

3. **Score Final**
   - Score agrégé (0.0 - 1.0)
   - Badge coloré (vert/orange/rouge)
   - Indicateur "DÉGRADÉ" si timeout

4. **Décisions Finales**
   - Décision : ALLOW (vert) / QUARANTINE (orange) / BLOCK (rouge)
   - Score final
   - Latence en millisecondes
   - Scores partiels détaillés
   - Contenu du message original

5. **Statistiques**
   - Nombre total de messages
   - Nombre total de décisions

### 7.3 Design

- **Couleurs :** Gradient violet/bleu
- **Cards :** Cartes blanches avec ombres
- **Animations :** Slide-in pour nouveaux messages
- **Badges :** Colorés selon le score/décision
- **Responsive :** S'adapte à différentes tailles d'écran

### 7.4 Accès

**Docker :**
```
http://localhost:5000
```

**Kubernetes :**
```bash
# Port-forward
kubectl port-forward svc/ui-dashboard 5000:5000 -n mqtt-filtering

# Ou NodePort
minikube service ui-dashboard -n mqtt-filtering
```

---

## 8. PROBLÈMES RENCONTRÉS ET RÉSOLUS

### 8.1 Docker Compose

#### Problème 1 : Version obsolète
- **Erreur :** `the attribute 'version' is obsolete`
- **Cause :** Docker Compose v2 ne nécessite plus la version
- **Solution :** Supprimé `version: '3.8'` du docker-compose.yml

#### Problème 2 : Cache Docker corrompu
- **Erreur :** `unexpected end of JSON input` pour `docker-generator`
- **Cause :** Cache Docker corrompu
- **Solution :** Build avec `--no-cache` pour forcer une reconstruction complète

### 8.2 Service Aggregator

#### Problème : UnboundLocalError
- **Erreur :** `UnboundLocalError: cannot access local variable 'threading'`
- **Cause :** Import `threading` redondant dans la fonction `main()` masquant l'import global
- **Solution :** Supprimé l'import redondant ligne 232
- **Fichier modifié :** `services/aggregator/main.py`

### 8.3 Kubernetes

#### Problème 1 : Namespace non trouvé
- **Erreur :** `namespaces "mqtt-filtering" not found`
- **Cause :** Timing - les ressources sont créées avant que le namespace soit prêt
- **Solution :** Appliquer dans l'ordre avec délais ou utiliser `kubectl wait`

#### Problème 2 : Images non trouvées (Minikube)
- **Erreur :** `ErrImageNeverPull` / `ImagePullBackOff`
- **Cause :** Minikube utilise un environnement Docker isolé
- **Solution :** 
  - Utiliser `imagePullPolicy: IfNotPresent`
  - Charger les images avec `minikube image load`
  - Ou construire dans l'environnement Minikube avec `minikube docker-env`

#### Problème 3 : Service UI Dashboard non trouvé
- **Erreur :** `services "ui-dashboard" not found`
- **Cause :** Le service n'a pas été créé ou est dans un autre namespace
- **Solution :** Vérifier avec `kubectl get svc -n mqtt-filtering`

### 8.4 UI Dashboard

#### Problème : RuntimeError Werkzeug
- **Erreur :** `RuntimeError: The Werkzeug web server is not designed to run in production`
- **Cause :** Flask-SocketIO nécessite `allow_unsafe_werkzeug=True` en production
- **Solution :** Ajouté le paramètre dans `socketio.run()`

---

## 9. ÉTAT ACTUEL

### 9.1 Déploiement Docker

**Statut :** ✅ **OPÉRATIONNEL**

- Tous les services sont fonctionnels
- Dashboard accessible sur http://localhost:5000
- Messages générés toutes les 5 secondes
- Décisions prises correctement

**Commandes de vérification :**
```bash
docker ps  # Voir tous les conteneurs
docker logs -f generator  # Voir les logs
```

### 9.2 Déploiement Kubernetes

**Statut :** ✅ **OPÉRATIONNEL**

- Cluster : Minikube
- Namespace : `mqtt-filtering`
- Tous les pods : `Running` et `Ready 1/1`
- Services : Mosquitto (ClusterIP), UI Dashboard (NodePort)

**Commandes de vérification :**
```bash
kubectl get pods -n mqtt-filtering
kubectl get svc -n mqtt-filtering
kubectl logs -f deployment/generator -n mqtt-filtering
```

**Accès au Dashboard :**
```bash
kubectl port-forward svc/ui-dashboard 5000:5000 -n mqtt-filtering
# Puis ouvrir http://localhost:5000
```

### 9.3 Métriques actuelles

- **Services déployés :** 8 (7 microservices + 1 broker)
- **Topics MQTT :** 6
- **ConfigMaps Kubernetes :** 8
- **Deployments Kubernetes :** 8
- **Services Kubernetes :** 2
- **Lignes de code Python :** ~1500
- **Fichiers de configuration :** 20+

---

## 10. STRUCTURE DU PROJET

```
adminstration de reseau/
│
├── services/                          # Microservices
│   ├── generator/
│   │   ├── Dockerfile
│   │   ├── main.py                    # Génère messages bruts
│   │   └── requirements.txt
│   │
│   ├── keyword-filter/
│   │   ├── Dockerfile
│   │   ├── main.py                    # Filtre mots-clés
│   │   └── requirements.txt
│   │
│   ├── url-inspector/
│   │   ├── Dockerfile
│   │   ├── main.py                    # Inspecte URLs
│   │   └── requirements.txt
│   │
│   ├── format-checker/
│   │   ├── Dockerfile
│   │   ├── main.py                    # Vérifie format
│   │   └── requirements.txt
│   │
│   ├── aggregator/
│   │   ├── Dockerfile
│   │   ├── main.py                    # Agrège résultats
│   │   └── requirements.txt
│   │
│   ├── final-router/
│   │   ├── Dockerfile
│   │   ├── main.py                    # Prend décisions
│   │   └── requirements.txt
│   │
│   └── ui-dashboard/
│       ├── Dockerfile
│       ├── main.py                    # Backend Flask
│       ├── requirements.txt
│       └── templates/
│           └── index.html             # Frontend
│
├── infra/
│   ├── docker/
│   │   ├── docker-compose.yml        # Orchestration Docker
│   │   └── mosquitto.conf            # Config MQTT broker
│   │
│   └── k8s/                          # Manifests Kubernetes
│       ├── namespace.yaml
│       ├── configmaps.yaml
│       ├── mosquitto-deployment.yaml
│       ├── generator-deployment.yaml
│       ├── keyword-filter-deployment.yaml
│       ├── url-inspector-deployment.yaml
│       ├── format-checker-deployment.yaml
│       ├── aggregator-deployment.yaml
│       ├── final-router-deployment.yaml
│       ├── ui-dashboard-deployment.yaml
│       ├── kustomization.yaml
│       ├── deploy.sh                 # Script déploiement bash
│       ├── deploy.ps1                # Script déploiement PowerShell
│       ├── README.md
│       ├── SETUP-K8S.md
│       ├── DEMARRAGE-RAPIDE.md
│       └── RESOLUTION-IMAGES.md
│
├── docs/
│   └── README.md                     # Documentation technique
│
├── scripts/
│   ├── check-docker.ps1              # Vérification Docker
│   ├── test-mqtt.sh                  # Tests MQTT
│   └── test-pub.sh                   # Publication test
│
├── README.md                         # Documentation principale
├── QUICKSTART.md                     # Guide démarrage rapide
├── INSTALL-DOCKER.md                 # Installation Docker
└── RAPPORT-COMPLET-PROJET.md         # Ce document
```

---

## 11. FLUX DE DONNÉES COMPLET

### 11.1 Exemple de flux complet

**T0 : Generator publie**
```json
{
  "messageId": "abc-123",
  "timestamp": "2025-12-29T23:00:00.000Z",
  "content": "URGENT!!! WIN $1000000 NOW!!! Click: http://suspicious-site.com",
  "trace": {
    "traceId": "trace-456",
    "spanId": "span-789",
    "parentSpanId": null
  }
}
```
→ Publié sur `msg.raw`

**T0+10ms : Keyword Filter traite**
- Trouve : "URGENT", "WIN", "CLICK"
- Score : 0.9 (3 mots-clés × 0.3)
- Publie sur `msg.keyword.result`

**T0+15ms : URL Inspector traite**
- Trouve : "http://suspicious-site.com"
- Domaine suspect détecté
- Score : 0.5
- Publie sur `msg.url.result`

**T0+20ms : Format Checker traite**
- Longueur OK
- Pas de caractères interdits
- Ratio symboles OK
- Score : 0.0
- Publie sur `msg.format.result`

**T0+25ms : Aggregator reçoit les 3 résultats**
- Calcule : (0.9 + 0.5 + 0.0) / 3 = 0.47
- Publie sur `msg.score` avec `degraded: false`

**T0+30ms : Final Router prend décision**
- Score : 0.47
- 0.3 ≤ 0.47 < 0.7 → **QUARANTINE**
- Publie sur `msg.decision`

**T0+35ms : UI Dashboard affiche**
- Affiche le message brut
- Affiche les 3 scores partiels
- Affiche le score final (0.47)
- Affiche la décision (QUARANTINE en orange)
- Affiche la latence (~35ms)

### 11.2 Cas de timeout

Si un inspecteur ne répond pas dans les 3 secondes :

1. Aggregator attend 3 secondes
2. Reçoit seulement 2 résultats sur 3
3. Calcule le score avec les 2 résultats disponibles
4. Ajoute une pénalité : `score += (1 * 0.2) = +0.2`
5. Publie avec `degraded: true`
6. Router prend quand même une décision
7. Dashboard affiche "DÉGRADÉ" en jaune

---

## 12. CONFIGURATION ET PERSONNALISATION

### 12.1 Variables d'environnement

Toutes les configurations peuvent être modifiées via variables d'environnement :

#### Generator
- `INTERVAL_SECONDS` - Intervalle de génération (défaut: 5)

#### Keyword Filter
- `KEYWORD_BLACKLIST` - Liste de mots-clés séparés par virgules

#### URL Inspector
- `SUSPICIOUS_DOMAINS` - Liste de domaines suspects

#### Format Checker
- `MAX_LENGTH` - Longueur maximale
- `FORBIDDEN_CHARS` - Caractères interdits
- `MAX_SYMBOL_RATIO` - Ratio symboles max

#### Aggregator
- `JOIN_TIMEOUT_SECONDS` - Timeout pour jointure

#### Final Router
- `THRESHOLD_A` - Seuil bas (défaut: 0.3)
- `THRESHOLD_B` - Seuil haut (défaut: 0.7)

### 12.2 Modification des ConfigMaps (Kubernetes)

```bash
# Modifier un ConfigMap
kubectl edit configmap keyword-blacklist -n mqtt-filtering

# Redémarrer les pods pour appliquer
kubectl rollout restart deployment/keyword-filter -n mqtt-filtering
```

### 12.3 Scaling

**Kubernetes :**
```bash
# Scaler un service
kubectl scale deployment/keyword-filter --replicas=3 -n mqtt-filtering
```

**Note :** Seuls les inspecteurs peuvent être scalés. Generator, Aggregator et Router doivent rester à 1 replica.

---

## 📊 RÉSUMÉ EXÉCUTIF

### Ce qui a été réalisé

✅ **7 microservices** Python fonctionnels  
✅ **1 broker MQTT** (Mosquitto) configuré  
✅ **1 dashboard web** temps réel  
✅ **Déploiement Docker** complet et opérationnel  
✅ **Déploiement Kubernetes** complet et opérationnel  
✅ **Tracing distribué** implémenté  
✅ **Gestion des timeouts** et modes dégradés  
✅ **Health checks** (readiness/liveness probes)  
✅ **Configuration externalisée** (ConfigMaps)  
✅ **Documentation complète**  

### Technologies maîtrisées

- Python 3.11
- MQTT (Paho MQTT)
- Docker & Docker Compose
- Kubernetes (Deployments, Services, ConfigMaps)
- Flask & WebSocket
- Architecture microservices
- Tracing distribué

### État final

**Docker :** ✅ 100% opérationnel  
**Kubernetes :** ✅ 100% opérationnel  
**Dashboard :** ✅ Accessible et fonctionnel  
**Documentation :** ✅ Complète  

---

**Fin du rapport**

*Rapport généré le 29 Décembre 2025*

