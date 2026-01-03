# 🚀 Démarrage Rapide Kubernetes

## Solution la plus simple : Docker Desktop

Vous avez Docker Desktop installé. Voici comment activer Kubernetes :

### Étapes

1. **Ouvrir Docker Desktop**
2. **Cliquer sur l'icône ⚙️ (Settings)** en haut à droite
3. **Aller dans la section "Kubernetes"** dans le menu de gauche
4. **Cocher "Enable Kubernetes"**
5. **Cliquer sur "Apply & Restart"**
6. **Attendre 1-2 minutes** que Kubernetes démarre

### Vérification

Une fois démarré, dans un terminal PowerShell :

```powershell
kubectl cluster-info
kubectl get nodes
```

Vous devriez voir quelque chose comme :
```
Kubernetes control plane is running at https://kubernetes.docker.internal:6443
```

### Déploiement

Une fois Kubernetes prêt :

```powershell
cd infra/k8s
kubectl apply -f .
```

### Construire les images Docker

Les images doivent être construites avant le déploiement :

```powershell
# Depuis la racine du projet
cd services

# Construire toutes les images
docker build -t docker-generator:latest generator/
docker build -t docker-keyword-filter:latest keyword-filter/
docker build -t docker-url-inspector:latest url-inspector/
docker build -t docker-format-checker:latest format-checker/
docker build -t docker-aggregator:latest aggregator/
docker build -t docker-final-router:latest final-router/
docker build -t docker-ui-dashboard:latest ui-dashboard/
```

### Accès au Dashboard

Une fois déployé :

```powershell
# Port-forward vers le dashboard
kubectl port-forward svc/ui-dashboard 5000:5000 -n mqtt-filtering
```

Puis ouvrir http://localhost:5000 dans votre navigateur.

## Alternative : Minikube

Si Docker Desktop ne fonctionne pas, vous pouvez utiliser Minikube :

```powershell
# Installer Minikube (avec Chocolatey)
choco install minikube

# Démarrer Minikube
minikube start

# Configurer l'environnement Docker
minikube docker-env | Invoke-Expression

# Construire les images (dans l'environnement Minikube)
cd services
docker build -t docker-generator:latest generator/
# ... (construire toutes les autres images)

# Déployer
cd ../infra/k8s
kubectl apply -f .
```

## Vérification du déploiement

```powershell
# Voir tous les pods
kubectl get pods -n mqtt-filtering

# Voir les services
kubectl get svc -n mqtt-filtering

# Voir les logs
kubectl logs -f deployment/generator -n mqtt-filtering
```

## Dépannage

### "Unable to connect to the server"

➡️ Kubernetes n'est pas démarré. Vérifiez Docker Desktop → Settings → Kubernetes

### "ImagePullBackOff" ou "ErrImagePull"

➡️ Les images Docker ne sont pas construites. Construisez-les avec `docker build`

### Pods en "CrashLoopBackOff"

➡️ Vérifiez les logs : `kubectl logs <pod-name> -n mqtt-filtering`


