# Déploiement Kubernetes

Ce répertoire contient tous les manifests Kubernetes pour déployer le système de filtrage de messages MQTT.

## Structure

```
infra/k8s/
├── namespace.yaml              # Namespace mqtt-filtering
├── configmaps.yaml             # Toutes les ConfigMaps (topics, blacklist, seuils, etc.)
├── mosquitto-deployment.yaml   # Deployment + Service pour le broker MQTT
├── generator-deployment.yaml  # Service de génération
├── keyword-filter-deployment.yaml
├── url-inspector-deployment.yaml
├── format-checker-deployment.yaml
├── aggregator-deployment.yaml
├── final-router-deployment.yaml
└── ui-dashboard-deployment.yaml # Deployment + Service NodePort pour le dashboard
```

## Prérequis

1. Un cluster Kubernetes fonctionnel
2. `kubectl` configuré pour accéder au cluster
3. Les images Docker doivent être disponibles :
   - `docker-generator:latest`
   - `docker-keyword-filter:latest`
   - `docker-url-inspector:latest`
   - `docker-format-checker:latest`
   - `docker-aggregator:latest`
   - `docker-final-router:latest`
   - `docker-ui-dashboard:latest`

### Construire et pousser les images

Si vous utilisez un registry local (ex: minikube):

```bash
# Pour minikube
eval $(minikube docker-env)

# Construire les images
cd ../../services
for service in generator keyword-filter url-inspector format-checker aggregator final-router ui-dashboard; do
  docker build -t docker-$service:latest $service/
done
```

Ou pousser vers un registry Docker:

```bash
REGISTRY=your-registry.com
for service in generator keyword-filter url-inspector format-checker aggregator final-router ui-dashboard; do
  docker tag docker-$service:latest $REGISTRY/docker-$service:latest
  docker push $REGISTRY/docker-$service:latest
done
```

Puis mettre à jour les images dans les Deployments.

## Déploiement

### Option 1 : Déploiement manuel (ordre recommandé)

```bash
# 1. Créer le namespace
kubectl apply -f namespace.yaml

# 2. Créer les ConfigMaps
kubectl apply -f configmaps.yaml

# 3. Déployer Mosquitto (doit être prêt avant les autres)
kubectl apply -f mosquitto-deployment.yaml

# 4. Attendre que Mosquitto soit prêt
kubectl wait --for=condition=ready pod -l app=mosquitto -n mqtt-filtering --timeout=60s

# 5. Déployer les inspecteurs
kubectl apply -f keyword-filter-deployment.yaml
kubectl apply -f url-inspector-deployment.yaml
kubectl apply -f format-checker-deployment.yaml

# 6. Déployer le generator
kubectl apply -f generator-deployment.yaml

# 7. Déployer l'aggregator
kubectl apply -f aggregator-deployment.yaml

# 8. Déployer le router
kubectl apply -f final-router-deployment.yaml

# 9. Déployer le dashboard
kubectl apply -f ui-dashboard-deployment.yaml
```

### Option 2 : Déploiement en une commande

```bash
kubectl apply -f .
```

Puis attendre que tous les pods soient prêts:

```bash
kubectl wait --for=condition=ready pod --all -n mqtt-filtering --timeout=120s
```

## Vérification

### Vérifier les pods

```bash
kubectl get pods -n mqtt-filtering
```

Tous les pods doivent être en statut `Running` et `Ready`.

### Vérifier les services

```bash
kubectl get svc -n mqtt-filtering
```

### Vérifier les logs

```bash
# Logs d'un service spécifique
kubectl logs -f deployment/generator -n mqtt-filtering
kubectl logs -f deployment/aggregator -n mqtt-filtering
kubectl logs -f deployment/final-router -n mqtt-filtering
```

### Accéder au Dashboard

Le dashboard est exposé via un Service NodePort sur le port 30080.

**Pour minikube:**
```bash
minikube service ui-dashboard -n mqtt-filtering
```

**Pour un cluster standard:**
```bash
# Récupérer l'IP du node
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
echo "Dashboard disponible sur: http://$NODE_IP:30080"
```

**Ou avec port-forward:**
```bash
kubectl port-forward svc/ui-dashboard 5000:5000 -n mqtt-filtering
# Puis ouvrir http://localhost:5000
```

## Configuration

Toutes les configurations sont dans les ConfigMaps et peuvent être modifiées sans reconstruire les images:

- **Topics**: `configmaps.yaml` → `topics-config`
- **Blacklist keywords**: `configmaps.yaml` → `keyword-blacklist`
- **Domaines suspects**: `configmaps.yaml` → `suspicious-domains`
- **Seuils router**: `configmaps.yaml` → `router-thresholds`
- **Règles format**: `configmaps.yaml` → `format-rules`
- **Timeout aggregator**: `configmaps.yaml` → `aggregator-config`
- **Interval generator**: `configmaps.yaml` → `generator-config`

Après modification d'une ConfigMap, redémarrer les pods concernés:

```bash
kubectl rollout restart deployment/<service-name> -n mqtt-filtering
```

## Health Checks

Tous les Deployments incluent des probes:

- **Readiness Probe**: Vérifie que le service est prêt à recevoir du trafic
- **Liveness Probe**: Vérifie que le service est toujours en vie

Les probes pour les services Python utilisent une connexion MQTT de test.
Le dashboard utilise une probe HTTP sur le port 5000.

## Scaling

Pour scaler un service:

```bash
kubectl scale deployment/<service-name> --replicas=3 -n mqtt-filtering
```

**Note**: Seuls les inspecteurs peuvent être scalés horizontalement. Le generator, aggregator et router doivent rester à 1 replica pour maintenir la cohérence.

## Dépannage

### Pods en CrashLoopBackOff

```bash
# Vérifier les logs
kubectl logs <pod-name> -n mqtt-filtering

# Vérifier les événements
kubectl describe pod <pod-name> -n mqtt-filtering
```

### Problèmes de connexion MQTT

Vérifier que Mosquitto est accessible:

```bash
kubectl exec -it deployment/mosquitto -n mqtt-filtering -- mosquitto_sub -h localhost -t '$SYS/#' -C 1
```

### Problèmes de configuration

Vérifier les ConfigMaps:

```bash
kubectl get configmap -n mqtt-filtering
kubectl describe configmap <configmap-name> -n mqtt-filtering
```

## Nettoyage

Pour supprimer tous les déploiements:

```bash
kubectl delete namespace mqtt-filtering
```

Ou supprimer individuellement:

```bash
kubectl delete -f .
```
