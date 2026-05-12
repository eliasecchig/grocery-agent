variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run and related resources."
  type        = string
  default     = "us-east1"
}

variable "service_name" {
  description = "Name of the Cloud Run service."
  type        = string
  default     = "grocery-agent"
}

variable "image" {
  description = "Container image URI for the Cloud Run service."
  type        = string
}

variable "gateway_image" {
  description = "Container image URI for the a2a-gateway service."
  type        = string
}

variable "store_graphql_url" {
  description = "GraphQL endpoint URL for the grocery store."
  type        = string
}

variable "store_code" {
  description = "Store code header for multi-store setups (leave empty if not needed)."
  type        = string
  default     = ""
}

variable "store_cart_url" {
  description = "URL to the store's cart page (used in email notifications)."
  type        = string
  default     = ""
}

variable "nudge_timezone" {
  description = "Timezone for the scheduled nudge job."
  type        = string
  default     = "UTC"
}

