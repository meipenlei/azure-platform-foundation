locals {
  storage_prefix = replace(var.name_prefix, "-", "")

  storage_account_name = substr(
    "${local.storage_prefix}st${substr(md5("${var.tenant_id}:${var.subscription_id}:${var.name_prefix}"), 0, 8)}",
    0,
    24
  )

  resource_group_name = "${var.name_prefix}-rg-l0-bootstrap"

  state_container_name = "tfstate"

  plan_identity_name  = "${var.name_prefix}-id-l0-plan"
  apply_identity_name = "${var.name_prefix}-id-l0-apply"

  github_subject_prefix = "repo:${var.github_owner}@${var.github_owner_id}/${var.github_repository}@${var.github_repository_id}"

  github_plan_subject = "${local.github_subject_prefix}:pull_request"

  github_apply_subject = "${local.github_subject_prefix}:environment:${var.github_apply_environment}"

  tags = merge(
    {
      "managed-by" = "azure-platform-foundation"
      "apf-level"  = "0"
      "apf-scope"  = "bootstrap"
    },
    var.tags
  )
}