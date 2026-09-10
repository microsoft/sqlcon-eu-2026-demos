#!/usr/bin/env bash
# Recreate the research-replica named replica, and finish wiring it up.
#
# The replica already exists. This script is the record of how it was made and what
# still has to happen before the application can query it.
#
# A named replica shares the primary's storage. No data is copied, the corpus stays in
# one place, and the replica is read-only and sized independently. Because storage is
# shared, the vector index the team builds on the primary shows up here automatically.

set -euo pipefail

SUBSCRIPTION="44fefc06-f7c7-4326-9471-1852e148b8bb"
GROUP="vector-benchmark"
SERVER="vbnech-large-server"
PRIMARY="vbench_large"
REPLICA="research-replica"

# az sql db replica create cannot make a serverless named replica: it demands -e for a
# serverless SKU and then rejects -e as an unrecognised argument. ARM takes it directly.
cat > /tmp/research-replica.json <<EOF
{
  "location": "eastus2",
  "sku": { "name": "HS_S_Gen5", "tier": "Hyperscale", "family": "Gen5", "capacity": 8 },
  "properties": {
    "createMode": "Secondary",
    "secondaryType": "Named",
    "sourceDatabaseId": "/subscriptions/${SUBSCRIPTION}/resourceGroups/${GROUP}/providers/Microsoft.Sql/servers/${SERVER}/databases/${PRIMARY}",
    "minCapacity": 1,
    "autoPauseDelay": 60
  }
}
EOF

az rest --method PUT \
  --url "https://management.azure.com/subscriptions/${SUBSCRIPTION}/resourceGroups/${GROUP}/providers/Microsoft.Sql/servers/${SERVER}/databases/${REPLICA}?api-version=2023-08-01-preview" \
  --body @/tmp/research-replica.json \
  --headers Content-Type=application/json -o json

az sql db show --subscription "$SUBSCRIPTION" -g "$GROUP" -s "$SERVER" -n "$REPLICA" \
  --query '{name:name,status:status,objective:currentServiceObjectiveName,secondaryType:secondaryType,minCapacity:minCapacity,autoPauseDelay:autoPauseDelay}' -o json
