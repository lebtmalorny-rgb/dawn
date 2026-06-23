# E08 lab portal policy for synthetic Cloud UI secrets.
# This file contains no secret values.

path "kv/data/cloud-ui/local/*" {
  capabilities = ["read"]
}

path "kv/metadata/cloud-ui/local/*" {
  capabilities = ["read", "list"]
}
