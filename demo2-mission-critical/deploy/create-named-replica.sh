#!/usr/bin/env bash
# Create a serverless Hyperscale named replica of the large corpus and point the app at it.
#
# NOT RUN AUTOMATICALLY. The primary lives on a shared benchmark server in another
# subscription, and a named replica adds compute cost, so this needs a human decision.
#
# A named replica shares the primary's storage. No data is copied, the corpus stays in
# one place, and the replica is read-only and sized independently. That is what makes it
# the right way to offload the search workload.

set -euo pipefail

# Primary (read-only for this work)
PRIMARY_SUBSCRIPTION="44fefc06-f7c7-4326-9471-1852e148b8bb"
PRIMARY_GROUP="vector-benchmark"
PRIMARY_SERVER="vbnech-large-server"
PRIMARY_DATABASE="vbench_large"

# Replica. Must sit on a different logical server than the primary.
REPLICA_SERVER="${REPLICA_SERVER:-vbench-large-replica}"
REPLICA_DATABASE="${REPLICA_DATABASE:-vbench_large_read}"
REPLICA_GROUP="${REPLICA_GROUP:-$PRIMARY_GROUP}"
REPLICA_LOCATION="${REPLICA_LOCATION:-eastus2}"

# Serverless sizing. Keep the ceiling low; the point is that the replica is sized
# independently of the 192-vCore primary.
CAPACITY="${CAPACITY:-8}"
MIN_CAPACITY="${MIN_CAPACITY:-1}"
AUTO_PAUSE_DELAY="${AUTO_PAUSE_DELAY:-60}"

echo "Creating replica server ${REPLICA_SERVER} in ${REPLICA_LOCATION}"
az sql server create \
  --subscription "$PRIMARY_SUBSCRIPTION" \
  --resource-group "$REPLICA_GROUP" \
  --name "$REPLICA_SERVER" \
  --location "$REPLICA_LOCATION" \
  --enable-ad-only-auth \
  --external-admin-principal-type User \
  --external-admin-name "$(az ad signed-in-user show --query displayName -o tsv)" \
  --external-admin-sid "$(az ad signed-in-user show --query id -o tsv)" \
  --only-show-errors -o none

echo "Creating serverless named replica ${REPLICA_DATABASE}"
az sql db replica create \
  --subscription "$PRIMARY_SUBSCRIPTION" \
  --resource-group "$PRIMARY_GROUP" \
  --server "$PRIMARY_SERVER" \
  --name "$PRIMARY_DATABASE" \
  --partner-resource-group "$REPLICA_GROUP" \
  --partner-server "$REPLICA_SERVER" \
  --partner-database "$REPLICA_DATABASE" \
  --secondary-type Named \
  --edition Hyperscale \
  --family Gen5 \
  --capacity "$CAPACITY" \
  --compute-model Serverless \
  --min-capacity "$MIN_CAPACITY" \
  --auto-pause-delay "$AUTO_PAUSE_DELAY" \
  --only-show-errors -o none

echo "Replica created. Verifying:"
az sql db show \
  --subscription "$PRIMARY_SUBSCRIPTION" \
  --resource-group "$REPLICA_GROUP" \
  --server "$REPLICA_SERVER" \
  --name "$REPLICA_DATABASE" \
  --query '{name:name,location:location,sku:sku.name,objective:currentServiceObjectiveName,minCapacity:minCapacity,autoPauseDelay:autoPauseDelay,status:status}' \
  -o json

cat <<EOF

Next steps:

1. Grant the application identity read access on the replica:

     CREATE USER [caldova-workload-id] FROM EXTERNAL PROVIDER;
     ALTER ROLE db_datareader ADD MEMBER [caldova-workload-id];

2. Point the app at it:

     az containerapp update -g antho-rg -n caldova-app --set-env-vars \\
       AZURE_SQL_REPLICA_SERVER=${REPLICA_SERVER}.database.windows.net \\
       AZURE_SQL_REPLICA_DATABASE=${REPLICA_DATABASE}

3. Select "Replica" in the app. The statement does not change.

Caveats worth checking before the keynote:

- Auto-pause does not persist in every region. It reverts to -1 in eastus and uksouth.
  If the replica lands in a region without it, autoPauseDelay will read -1 above.
- The replica is read-only, which suits search but means no writes.
- A named replica needs the primary's vector and full-text indexes to exist. The corpus
  is still loading, so build those on the primary first.
EOF
