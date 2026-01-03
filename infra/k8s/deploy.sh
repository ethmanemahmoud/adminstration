#!/bin/bash
# Script de déploiement Kubernetes pour le système de filtrage MQTT

set -e

echo "🚀 Déploiement du système de filtrage MQTT sur Kubernetes"
echo ""

# Vérifier que kubectl est disponible
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl n'est pas installé"
    exit 1
fi

# Créer le namespace
echo "📦 Création du namespace..."
kubectl apply -f namespace.yaml

# Créer les ConfigMaps
echo "⚙️  Création des ConfigMaps..."
kubectl apply -f configmaps.yaml

# Déployer Mosquitto
echo "📡 Déploiement de Mosquitto..."
kubectl apply -f mosquitto-deployment.yaml

# Attendre que Mosquitto soit prêt
echo "⏳ Attente de Mosquitto..."
kubectl wait --for=condition=ready pod -l app=mosquitto -n mqtt-filtering --timeout=60s || true

# Déployer les inspecteurs
echo "🔍 Déploiement des inspecteurs..."
kubectl apply -f keyword-filter-deployment.yaml
kubectl apply -f url-inspector-deployment.yaml
kubectl apply -f format-checker-deployment.yaml

# Déployer le generator
echo "📝 Déploiement du generator..."
kubectl apply -f generator-deployment.yaml

# Déployer l'aggregator
echo "📊 Déploiement de l'aggregator..."
kubectl apply -f aggregator-deployment.yaml

# Déployer le router
echo "⚖️  Déploiement du router..."
kubectl apply -f final-router-deployment.yaml

# Déployer le dashboard
echo "🎨 Déploiement du dashboard..."
kubectl apply -f ui-dashboard-deployment.yaml

echo ""
echo "✅ Déploiement terminé!"
echo ""
echo "📊 Vérification du statut:"
kubectl get pods -n mqtt-filtering

echo ""
echo "🌐 Pour accéder au dashboard:"
echo "   kubectl port-forward svc/ui-dashboard 5000:5000 -n mqtt-filtering"
echo "   Puis ouvrir http://localhost:5000"
echo ""
echo "   Ou avec minikube:"
echo "   minikube service ui-dashboard -n mqtt-filtering"

