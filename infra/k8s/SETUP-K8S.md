# Configuration d'un Cluster Kubernetes Local

Vous devez avoir un cluster Kubernetes en cours d'exécution pour déployer l'application. Voici plusieurs options pour Windows.

## Option 1 : Docker Desktop avec Kubernetes (Recommandé - Le plus simple)

Si vous avez Docker Desktop installé :

1. **Ouvrir Docker Desktop**
2. **Aller dans Settings → Kubernetes**
3. **Cocher "Enable Kubernetes"**
4. **Cliquer sur "Apply & Restart"**
5. **Attendre que Kubernetes démarre** (icône Kubernetes en bas à droite doit être vert)

Vérifier :
```powershell
kubectl cluster-info
kubectl get nodes
```

## Option 2 : Minikube

### Installation

1. **Télécharger Minikube** :
   - Télécharger depuis : https://minikube.sigs.k8s.io/docs/start/
   - Ou avec Chocolatey : `choco install minikube`

2. **Démarrer Minikube** :
```powershell
minikube start
```

3. **Vérifier** :
```powershell
kubectl cluster-info
kubectl get nodes
```

### Important pour Minikube

Les images Docker doivent être disponibles dans l'environnement Docker de Minikube :

```powershell
# Configurer l'environnement Docker de Minikube
minikube docker-env | Invoke-Expression

# Construire les images
cd ../../services
docker build -t docker-generator:latest generator/
docker build -t docker-keyword-filter:latest keyword-filter/
docker build -t docker-url-inspector:latest url-inspector/
docker build -t docker-format-checker:latest format-checker/
docker build -t docker-aggregator:latest aggregator/
docker build -t docker-final-router:latest final-router/
docker build -t docker-ui-dashboard:latest ui-dashboard/
```

## Option 3 : Kind (Kubernetes in Docker)

### Installation

```powershell
# Avec Chocolatey
choco install kind

# Ou télécharger depuis : https://kind.sigs.k8s.io/docs/user/quick-start/
```

### Créer un cluster

```powershell
kind create cluster --name mqtt-filtering
```

### Charger les images

```powershell
# Construire les images localement
cd ../../services
docker build -t docker-generator:latest generator/
docker build -t docker-keyword-filter:latest keyword-filter/
docker build -t docker-url-inspector:latest url-inspector/
docker build -t docker-format-checker:latest format-checker/
docker build -t docker-aggregator:latest aggregator/
docker build -t docker-final-router:latest final-router/
docker build -t docker-ui-dashboard:latest ui-dashboard/

# Charger les images dans Kind
kind load docker-image docker-generator:latest --name mqtt-filtering
kind load docker-image docker-keyword-filter:latest --name mqtt-filtering
kind load docker-image docker-url-inspector:latest --name mqtt-filtering
kind load docker-image docker-format-checker:latest --name mqtt-filtering
kind load docker-image docker-aggregator:latest --name mqtt-filtering
kind load docker-image docker-final-router:latest --name mqtt-filtering
kind load docker-image docker-ui-dashboard:latest --name mqtt-filtering
```

## Vérification

Après avoir démarré un cluster, vérifiez :

```powershell
# Vérifier la connexion
kubectl cluster-info

# Vérifier les nodes
kubectl get nodes

# Vérifier le contexte actuel
kubectl config current-context
```

## Déploiement

Une fois le cluster prêt, vous pouvez déployer :

```powershell
cd infra/k8s
kubectl apply -f .
```

## Dépannage

### kubectl ne trouve pas le cluster

Vérifier la configuration :
```powershell
kubectl config view
```

### Erreur "connection refused"

- Vérifier que le cluster est démarré
- Pour Docker Desktop : vérifier que Kubernetes est activé dans Settings
- Pour Minikube : `minikube status`
- Pour Kind : `kind get clusters`

### Images non trouvées

- Pour Minikube : utiliser `minikube docker-env` puis reconstruire
- Pour Kind : utiliser `kind load docker-image`
- Pour Docker Desktop : les images locales devraient fonctionner

## Recommandation

**Pour Windows, Docker Desktop avec Kubernetes activé est la solution la plus simple** car :
- ✅ Déjà installé si vous utilisez Docker
- ✅ Pas besoin d'outils supplémentaires
- ✅ Les images Docker locales fonctionnent directement
- ✅ Interface graphique pour gérer le cluster


