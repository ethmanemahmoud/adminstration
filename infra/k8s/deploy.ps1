# Script de déploiement PowerShell pour Kubernetes
# Déploie tous les manifests dans le bon ordre

Write-Host "🚀 Déploiement du système de filtrage MQTT sur Kubernetes" -ForegroundColor Cyan
Write-Host ""

# Vérifier que kubectl est disponible
if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "❌ kubectl n'est pas installé" -ForegroundColor Red
    exit 1
}

# Vérifier la connexion au cluster
Write-Host "📡 Vérification de la connexion au cluster..." -ForegroundColor Yellow
try {
    kubectl cluster-info | Out-Null
} catch {
    Write-Host "❌ Impossible de se connecter au cluster Kubernetes" -ForegroundColor Red
    Write-Host "   Vérifiez que Kubernetes est activé dans Docker Desktop" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Cluster accessible" -ForegroundColor Green
Write-Host ""

# Créer le namespace
Write-Host "📦 Création du namespace..." -ForegroundColor Yellow
kubectl apply -f namespace.yaml
Start-Sleep -Seconds 2

# Créer les ConfigMaps
Write-Host "⚙️  Création des ConfigMaps..." -ForegroundColor Yellow
kubectl apply -f configmaps.yaml

# Déployer Mosquitto
Write-Host "📡 Déploiement de Mosquitto..." -ForegroundColor Yellow
kubectl apply -f mosquitto-deployment.yaml

# Attendre que Mosquitto soit prêt
Write-Host "⏳ Attente de Mosquitto..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Déployer les inspecteurs
Write-Host "🔍 Déploiement des inspecteurs..." -ForegroundColor Yellow
kubectl apply -f keyword-filter-deployment.yaml
kubectl apply -f url-inspector-deployment.yaml
kubectl apply -f format-checker-deployment.yaml

# Déployer le generator
Write-Host "📝 Déploiement du generator..." -ForegroundColor Yellow
kubectl apply -f generator-deployment.yaml

# Déployer l'aggregator
Write-Host "📊 Déploiement de l'aggregator..." -ForegroundColor Yellow
kubectl apply -f aggregator-deployment.yaml

# Déployer le router
Write-Host "⚖️  Déploiement du router..." -ForegroundColor Yellow
kubectl apply -f final-router-deployment.yaml

# Déployer le dashboard
Write-Host "🎨 Déploiement du dashboard..." -ForegroundColor Yellow
kubectl apply -f ui-dashboard-deployment.yaml

Write-Host ""
Write-Host "✅ Déploiement terminé!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Statut des pods:" -ForegroundColor Cyan
kubectl get pods -n mqtt-filtering

Write-Host ""
Write-Host "🌐 Pour accéder au dashboard:" -ForegroundColor Cyan
Write-Host "   kubectl port-forward svc/ui-dashboard 5000:5000 -n mqtt-filtering" -ForegroundColor White
Write-Host "   Puis ouvrir http://localhost:5000" -ForegroundColor White
Write-Host ""


