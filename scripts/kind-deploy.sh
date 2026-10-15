#!/usr/bin/env bash
# Create a kind cluster (if needed), build and load the images, and install the Helm chart.
#
#   ./scripts/kind-deploy.sh
#   KIND_HOST_PORT=8090 MISTRAL_API_KEY=... ./scripts/kind-deploy.sh
#
# Needs docker, kind and kubectl. Helm is used if installed, otherwise it runs from the
# alpine/helm image on kind's Docker network.
set -euo pipefail

CLUSTER="${CLUSTER:-maintainai}"
NAMESPACE="${NAMESPACE:-maintainai}"
RELEASE="${RELEASE:-maintainai}"
HOST_PORT="${KIND_HOST_PORT:-8080}"
HELM_IMAGE="alpine/helm:3.16.3"
TAG=local
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Docker on Windows (Git Bash) wants Windows paths for bind mounts.
host_path() { if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else echo "$1"; fi; }

for tool in docker kind kubectl; do
  command -v "$tool" >/dev/null 2>&1 || { echo "error: $tool is not installed" >&2; exit 1; }
done

if kind get clusters 2>/dev/null | grep -qx "$CLUSTER"; then
  echo "==> Using existing kind cluster '$CLUSTER'"
else
  echo "==> Creating kind cluster '$CLUSTER' (web UI on localhost:$HOST_PORT)"
  config="$(mktemp)"
  sed -e "s/hostPort: 8080/hostPort: $HOST_PORT/" -e "s/^name: .*/name: $CLUSTER/" \
    "$ROOT/deploy/kind/cluster.yaml" > "$config"
  kind create cluster --config "$config" --wait 120s
  rm -f "$config"
fi
kubectl config use-context "kind-$CLUSTER" >/dev/null

echo "==> Building images"
docker build -q --target api -t "maintainai-api:$TAG" "$ROOT" >/dev/null
docker build -q --target mcp-server -t "maintainai-mcp-server:$TAG" "$ROOT" >/dev/null
docker build -q --target worker -t "maintainai-worker:$TAG" "$ROOT" >/dev/null
docker build -q -t "maintainai-web:$TAG" "$ROOT/web" >/dev/null

# Only the locally built images are loaded; the node pulls public ones (pgvector) itself.
echo "==> Loading images into the cluster"
for image in api mcp-server worker web; do
  kind load docker-image "maintainai-$image:$TAG" --name "$CLUSTER" >/dev/null
done

echo "==> Installing the Helm chart"
args=(upgrade --install "$RELEASE" --namespace "$NAMESPACE" --create-namespace
  --wait --wait-for-jobs --timeout 10m)
if [[ -n "${MISTRAL_API_KEY:-}" ]]; then
  args+=(--set-string "secrets.mistralApiKey=$MISTRAL_API_KEY")
fi

if command -v helm >/dev/null 2>&1; then
  chart="$ROOT/deploy/helm/maintainai"
  helm "${args[@]}" "$chart" -f "$chart/values-kind.yaml"
else
  echo "    (helm not found locally, running $HELM_IMAGE)"
  kubeconfig="$(mktemp)"
  kind get kubeconfig --internal --name "$CLUSTER" > "$kubeconfig"
  MSYS_NO_PATHCONV=1 docker run --rm --network kind \
    -v "$(host_path "$kubeconfig"):/root/.kube/config:ro" \
    -v "$(host_path "$ROOT/deploy/helm"):/charts:ro" \
    "$HELM_IMAGE" "${args[@]}" /charts/maintainai -f /charts/maintainai/values-kind.yaml
  rm -f "$kubeconfig"
fi

kubectl -n "$NAMESPACE" get pods

echo
echo "MaintainAI is running: http://localhost:$HOST_PORT"
echo "Remove it with: kind delete cluster --name $CLUSTER"
