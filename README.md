# Système de Filtrage de Messages - Architecture Microservices MQTT

## Vue d'ensemble

Ce projet implémente un système de filtrage de messages en temps réel utilisant une architecture de microservices communiquant via MQTT. Chaque message passe par plusieurs inspections (mots-clés, URLs, format) avant qu'une décision finale ne soit prise (ALLOW/QUARANTINE/BLOCK).

## Architecture

```
Generator → msg.raw
    ↓
    ├─→ Keyword Filter → msg.keyword.result
    ├─→ URL Inspector → msg.url.result
    └─→ Format Checker → msg.format.result
            ↓
        Aggregator → msg.score
            ↓
        Final Router → msg.decision
            ↓
        UI Dashboard (visualisation temps réel)
```

## Démarrage Rapide

### Prérequis
- Docker et Docker Compose installés

**⚠️ Docker n'est pas installé ?** Consultez [INSTALL-DOCKER.md](INSTALL-DOCKER.md) pour les instructions complètes d'installation.

### Lancer le système complet

```bash
cd infra/docker
docker-compose up --build
```

### Tester le système

#### Option 1 : Dashboard Web (Recommandé)
Ouvrez votre navigateur et allez sur :
```
http://localhost:5000
```

Le dashboard affiche en temps réel :
- Messages bruts
- Scores partiels (keyword, URL, format)
- Score final + statut dégradé
- Décisions (ALLOW/QUARANTINE/BLOCK)
- Latence approximative

#### Option 2 : Terminal MQTT
Dans un nouveau terminal, s'abonner aux décisions :
```bash
docker exec -it mqtt-broker mosquitto_sub -t msg.decision -v
```

Vous devriez voir des décisions toutes les 5 secondes.

### Vérifier les logs

```bash
# Logs du generator
docker logs -f generator

# Logs de l'aggregator
docker logs -f aggregator

# Logs du router
docker logs -f final-router
```

## Services

### 1. Generator
- Génère des messages bruts toutes les 5 secondes
- Publie sur `msg.raw`
- Crée des traces distribuées (traceId, spanId)

### 2. Keyword Filter
- S'abonne à `msg.raw`
- Détecte les mots-clés suspects (blacklist)
- Publie sur `msg.keyword.result`

### 3. URL Inspector
- S'abonne à `msg.raw`
- Détecte les URLs et domaines suspects
- Publie sur `msg.url.result`

### 4. Format Checker
- S'abonne à `msg.raw`
- Vérifie les règles de format (longueur, caractères interdits, ratio symboles)
- Publie sur `msg.format.result`

### 5. Aggregator
- S'abonne aux 3 topics de résultats
- Joint les résultats par `messageId`
- Gère les timeouts (3 secondes par défaut)
- Calcule un score global
- Publie sur `msg.score`

### 6. Final Router
- S'abonne à `msg.score`
- Applique des seuils pour prendre une décision
- Publie sur `msg.decision`

### 7. UI Dashboard
- S'abonne à tous les topics MQTT (msg.raw, résultats, score, decision)
- Affiche en temps réel via WebSocket :
  - Messages bruts
  - Scores partiels des 3 inspecteurs
  - Score final + statut dégradé
  - Décisions finales (ALLOW/QUARANTINE/BLOCK)
  - Latence (timestamp début → fin)
- Interface web accessible sur http://localhost:5000

## Configuration

Tous les services sont configurables via variables d'environnement. Voir `infra/docker/docker-compose.yml` pour les valeurs par défaut.

### Variables importantes

- `BROKER_HOST` - Adresse du broker MQTT
- `INTERVAL_SECONDS` - Intervalle de génération (Generator)
- `JOIN_TIMEOUT_SECONDS` - Timeout pour l'aggregation (Aggregator)
- `THRESHOLD_A`, `THRESHOLD_B` - Seuils de décision (Router)

## Observabilité

### Logs Structurés
Chaque service produit des logs structurés avec :
- `messageId` - ID du message
- `traceId` - ID de la trace distribuée
- `serviceName` - Nom du service
- `latencyMs` - Latence de traitement
- `eventType` - Type d'événement
- `status` - Statut (success/error)

### Métriques
Chaque service expose des métriques dans les logs :
- Messages traités
- Erreurs
- Latences
- (Aggregator) Timeouts et résultats manquants
- (Router) Compteurs ALLOW/QUARANTINE/BLOCK

### Tracing Distribué
Propagation automatique de `traceId`, `spanId`, `parentSpanId` dans tous les messages pour reconstruire les traces complètes.

## Tests de Résilience

### Test 1 : Arrêter un inspecteur
```bash
docker stop keyword-filter
```
L'aggregator devrait détecter le timeout et publier un score dégradé, menant à une décision QUARANTINE.

### Test 2 : Vérifier les traces
Filtrer les logs par `traceId` pour suivre un message complet :
```bash
docker logs generator | grep "traceId=abc123"
docker logs keyword-filter | grep "traceId=abc123"
docker logs aggregator | grep "traceId=abc123"
docker logs final-router | grep "traceId=abc123"
```

## Structure du Projet

```
.
├── services/
│   ├── generator/          # Service de génération
│   ├── keyword-filter/     # Filtre de mots-clés
│   ├── url-inspector/      # Inspecteur d'URLs
│   ├── format-checker/     # Vérificateur de format
│   ├── aggregator/         # Agrégateur de résultats
│   ├── final-router/       # Routeur final
│   └── ui-dashboard/       # Dashboard de visualisation
├── infra/
│   ├── docker/             # Configuration Docker
│   │   ├── docker-compose.yml
│   │   └── mosquitto.conf
│   └── k8s/                # Manifests Kubernetes (à venir)
└── docs/                   # Documentation
    └── README.md           # Documentation détaillée
```

## Documentation

Voir `docs/README.md` pour :
- Contrats MQTT détaillés
- Schémas JSON complets
- Spécifications des champs obligatoires

## Développement

### Lancer un service individuellement

```bash
cd services/generator
docker build -t generator .
docker run -e BROKER_HOST=localhost -e BROKER_PORT=1883 generator
```

### Tests locaux (sans Docker)

1. Lancer Mosquitto localement
2. Installer les dépendances : `pip install -r requirements.txt`
3. Lancer chaque service dans un terminal séparé

## Prochaines Étapes

- [ ] Manifests Kubernetes
- [ ] Dashboard de monitoring (Prometheus/Grafana)
- [ ] Intégration Jaeger pour le tracing
- [ ] Tests unitaires et d'intégration
- [ ] CI/CD pipeline

