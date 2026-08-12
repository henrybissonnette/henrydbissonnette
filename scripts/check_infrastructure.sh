#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
terraform_root="$repository_root/infra/aws/terraform/main"

if [ -n "${TERRAFORM_BIN:-}" ]; then
    terraform_binary=$TERRAFORM_BIN
else
    terraform_binary=$(python3 "$repository_root/scripts/install_tool.py" terraform)
fi

if [ -n "${NODE_BIN:-}" ]; then
    node_binary=$NODE_BIN
else
    node_binary=$(python3 "$repository_root/scripts/install_tool.py" node)
fi

python3 "$repository_root/scripts/check_infra.py"
"$terraform_binary" -chdir="$terraform_root" fmt -check -recursive
"$terraform_binary" -chdir="$terraform_root" init -backend=false -input=false -lockfile=readonly
"$terraform_binary" -chdir="$terraform_root" validate
"$terraform_binary" -chdir="$terraform_root" test
"$node_binary" --test "$repository_root/tests/edge_redirects.test.js"
