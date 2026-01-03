# Système de Filtrage de Messages avec Microservices MQTT

## Architecture

Ce projet implémente un système de filtrage de messages basé sur une architecture de microservices communiquant via MQTT.

### Services

1. **Generator** - Génère des messages bruts toutes les 5 secondes
2. **Keyword Filter** - Filtre les mots-clés suspects
3. **URL Inspector** - Inspecte les URLs et domaines
4. **Format Checker** - Vérifie les règles de format
5. **Aggregator** - Agrège les résultats des 3 inspecteurs
6. **Final Router** - Prend la décision finale (ALLOW/QUARANTINE/BLOCK)

## Contrats MQTT

### Topics

- `msg.raw` - Messages bruts générés
- `msg.keyword.result` - Résultats du filtre de mots-clés
- `msg.url.result` - Résultats de l'inspecteur d'URLs
- `msg.format.result` - Résultats du vérificateur de format
- `msg.score` - Score agrégé
- `msg.decision` - Décision finale

## Schéma d'Événement JSON

### Message Raw (msg.raw)

```json
{
  "messageId": "uuid",
  "timestamp": "ISO8601",
  "content": "string",
  "trace": {
    "traceId": "uuid",
    "spanId": "uuid",
    "parentSpanId": null
  }
}
```

### Message Result (msg.keyword.result, msg.url.result, msg.format.result)

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
    "passed": boolean,
    "score": float,
    ...
  },
  "serviceName": "string"
}
```

### Message Score (msg.score)

```json
{
  "messageId": "uuid",
  "timestamp": "ISO8601",
  "trace": {
    "traceId": "uuid",
    "spanId": "uuid",
    "parentSpanId": "uuid"
  },
  "score": float,
  "degraded": boolean,
  "serviceName": "aggregator"
}
```

### Message Decision (msg.decision)

```json
{
  "messageId": "uuid",
  "timestamp": "ISO8601",
  "trace": {
    "traceId": "uuid",
    "spanId": "uuid",
    "parentSpanId": "uuid"
  },
  "score": float,
  "decision": "ALLOW|QUARANTINE|BLOCK",
  "serviceName": "final-router"
}
```

## Champs Obligatoires

### Tous les messages
- `messageId` (string, UUID) - Clé de corrélation
- `timestamp` (string, ISO8601)
- `trace.traceId` (string, UUID)
- `trace.spanId` (string, UUID)
- `trace.parentSpanId` (string, UUID ou null)

### Message Raw uniquement
- `content` (string) - Contenu du message

### Messages Result
- `result` (object) - Résultat de l'inspection
- `result.passed` (boolean)
- `result.score` (float, 0.0-1.0)

### Message Score
- `score` (float, 0.0-1.0)
- `degraded` (boolean) - Indique si le résultat est dégradé (timeout)

### Message Decision
- `score` (float)
- `decision` (string) - "ALLOW", "QUARANTINE", ou "BLOCK"

## Décisions

Le router applique les seuils suivants :
- `score < THRESHOLD_A` → **ALLOW**
- `THRESHOLD_A ≤ score < THRESHOLD_B` → **QUARANTINE**
- `score ≥ THRESHOLD_B` → **BLOCK**

Par défaut : `THRESHOLD_A = 0.3`, `THRESHOLD_B = 0.7`

## Observabilité

### Logs Structurés

Chaque service loggue avec le format :
```
messageId=<uuid> traceId=<uuid> serviceName=<name> latencyMs=<ms> eventType=<type> status=<status>
```

### Métriques

Chaque service expose des métriques :
- Messages traités
- Latence
- Erreurs
- Aggregator : timeouts, résultats manquants
- Router : compteurs ALLOW/QUARANTINE/BLOCK

### Tracing Distribué

Propagation de `traceId`, `spanId`, `parentSpanId` dans tous les messages pour reconstruire les traces.

## Démarrage Local

### Prérequis
- Docker et Docker Compose

### Lancer le système

```bash
cd infra/docker
docker-compose up --build
```

### Tester

S'abonner aux décisions :
```bash
docker exec -it mqtt-broker mosquitto_sub -t msg.decision
```

Publier un message de test :
```bash
docker exec -it mqtt-broker mosquitto_pub -t msg.raw -m '{"messageId":"test","content":"test"}'
```

### Vérifications

1. ✅ S'abonner à `msg.decision` → voir ALLOW/QUARANTINE/BLOCK
2. ✅ Comparer timestamps → voir les latences
3. ✅ Éteindre un inspecteur → aggregator timeout → QUARANTINE
4. ✅ Logs structurés avec traceId pour suivre une trace complète

## Structure du Projet

```
.
├── services/
│   ├── generator/
│   ├── keyword-filter/
│   ├── url-inspector/
│   ├── format-checker/
│   ├── aggregator/
│   └── final-router/
├── infra/
│   ├── docker/
│   │   ├── docker-compose.yml
│   │   └── mosquitto.conf
│   └── k8s/
└── docs/
    └── README.md
```

