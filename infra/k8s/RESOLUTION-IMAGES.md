# Résolution du problème d'images Docker

Si vous voyez des erreurs `ErrImageNeverPull` ou `ImagePullBackOff`, c'est que Kubernetes ne trouve pas les images Docker localement.

## Solution pour Docker Desktop

Avec Docker Desktop, les images construites localement devraient être accessibles à Kubernetes. Si ce n'est pas le cas :

### Option 1 : Vérifier que les images existent

```powershell
docker images | Select-String "docker-"
```

Vous devriez voir :
- docker-generator:latest
- docker-keyword-filter:latest
- docker-url-inspector:latest
- docker-format-checker:latest
- docker-aggregator:latest
- docker-final-router:latest
- docker-ui-dashboard:latest

### Option 2 : Reconstruire les images

Si les images n'existent pas, reconstruisez-les :

```powershell
cd services
docker build -t docker-generator:latest generator/
docker build -t docker-keyword-filter:latest keyword-filter/
docker build -t docker-url-inspector:latest url-inspector/
docker build -t docker-format-checker:latest format-checker/
docker build -t docker-aggregator:latest aggregator/
docker build -t docker-final-router:latest final-router/
docker build -t docker-ui-dashboard:latest ui-dashboard/
```

### Option 3 : Redémarrer Docker Desktop

Parfois, un redémarrage de Docker Desktop résout le problème :

1. Fermer Docker Desktop complètement
2. Redémarrer Docker Desktop
3. Attendre que Kubernetes redémarre
4. Réappliquer les deployments :

```powershell
cd infra/k8s
kubectl apply -f .
```

### Option 4 : Utiliser un registry local (Alternative)

Si les images locales ne fonctionnent toujours pas, vous pouvez utiliser un registry local ou changer la stratégie de pull.

Modifier les deployments pour utiliser `imagePullPolicy: IfNotPresent` et tagger les images avec un préfixe localhost :

```powershell
docker tag docker-generator:latest localhost:5000/docker-generator:latest
# Répéter pour toutes les images
```

Puis mettre à jour les deployments pour utiliser `localhost:5000/docker-generator:latest`.

## Vérification

Après avoir résolu le problème, vérifiez :

```powershell
kubectl get pods -n mqtt-filtering
```

Tous les pods devraient être en statut `Running` et `Ready 1/1`.

## Alternative : Utiliser Minikube

Si Docker Desktop continue à poser problème, Minikube est une alternative fiable :

```powershell
# Installer Minikube
choco install minikube

# Démarrer Minikube
minikube start

# Configurer l'environnement Docker de Minikube
minikube docker-env | Invoke-Expression

# Construire les images dans l'environnement Minikube
cd services
docker build -t docker-generator:latest generator/
# ... (construire toutes les autres)

# Déployer
cd ../infra/k8s
kubectl apply -f .
```


