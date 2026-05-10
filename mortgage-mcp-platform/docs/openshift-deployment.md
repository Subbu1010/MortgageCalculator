# OpenShift deployment — Mortgage MCP platform

This guide assumes a shared PostgreSQL instance with the `pgvector` extension enabled and network policies that allow pods in the deployment namespace to reach the database service on port 5432.

## Build images

From the **`mortgage-mcp-platform`** directory (server) and sibling **`mcp-http-client`** (client):

```bash
cd mortgage-mcp-platform/mcp-server
podman build -t quay.io/your-org/mcp-server:latest .
podman push quay.io/your-org/mcp-server:latest

cd ../../mcp-http-client
podman build -t quay.io/your-org/mcp-client:latest .
podman push quay.io/your-org/mcp-client:latest
```

## Create secrets

```bash
oc new-project mortgage-mcp
oc create secret generic mortgage-mcp-server-secret \
  --from-literal=DATABASE_PASSWORD='***' \
  --from-literal=GOOGLE_API_KEY='***'
```

## Helm (preferred)

Run from the **`Study/MortgageCalculator`** (workspace) root so paths resolve.

```bash
cd mortgage-mcp-platform
helm upgrade --install mcp-server ./helm/mcp-server \
  --set image.repository=quay.io/your-org/mcp-server \
  --set image.tag=latest \
  --set database.host=postgresql.mortgage-mcp.svc.cluster.local \
  --set database.password="$DB_PASS" \
  --set secrets.googleApiKey="$GOOGLE_API_KEY" \
  --set route.host=mortgage-mcp.apps.cluster.domain

cd ../mcp-http-client
helm upgrade --install mcp-client ./helm/mcp-client \
  --set image.repository=quay.io/your-org/mcp-client \
  --set image.tag=latest
```

## Raw manifests (illustrative)

Apply files under `openshift/raw/` after substituting image references and wiring ConfigMaps/Secrets.

```bash
oc apply -f openshift/raw/
```

## Routes

The Helm chart creates an OpenShift `Route` when `route.enabled=true`. For vanilla Kubernetes, disable the route and use `Ingress` or a service mesh gateway.

## Non-root security

Container images run as UID `1001` (server) and `1002` (client). Ensure namespace SCC defaults (restricted-v2) permit those UIDs or assign an appropriate `SecurityContextConstraints` binding to the `ServiceAccount`.

## Document volume

Mount a PVC or build sample documents into the image at `/data/documents` so startup ingestion can populate vectors when `GOOGLE_API_KEY` is present.

Example volume snippet:

```yaml
volumeMounts:
  - name: docs
    mountPath: /data/documents
    readOnly: true
volumes:
  - name: docs
    persistentVolumeClaim:
      claimName: mortgage-policy-library
```

## Client pod usage

```bash
POD=$(oc get pod -l app.kubernetes.io/name=mcp-client -o jsonpath='{.items[0].metadata.name}')
oc exec -it "$POD" -- python -m mcp_client.cli health
oc exec -it "$POD" -- python -m mcp_client.cli rag "What is the FHA case binder requirement?" --top-k 4
```
