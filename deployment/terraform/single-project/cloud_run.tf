resource "google_service_account" "agent" {
  account_id   = "${var.service_name}-sa"
  display_name = "grocery-agent Cloud Run SA"
  project      = var.project_id
}

resource "google_cloud_run_v2_service" "agent" {
  name                = var.service_name
  location            = var.region
  project             = var.project_id
  deletion_protection = false

  template {
    service_account = google_service_account.agent.email

    scaling {
      min_instance_count = 1
    }

    containers {
      image = var.image

      resources {
        cpu_idle = false
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = "global"
      }
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "True"
      }
      env {
        name  = "APP_URL"
        value = "https://${var.service_name}-${data.google_project.project.number}.${var.region}.run.app"
      }
      env {
        name  = "GATEWAY_URL"
        value = "https://a2a-gateway-${data.google_project.project.number}.${var.region}.run.app"
      }
      env {
        name  = "STORE_GRAPHQL_URL"
        value = var.store_graphql_url
      }
      env {
        name  = "STORE_CODE"
        value = var.store_code
      }
      env {
        name  = "STORE_CART_URL"
        value = var.store_cart_url
      }
      env {
        name = "NUDGE_RECIPIENT_ID"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.nudge_recipient_id.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "STORE_USERNAME"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.store_username.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "STORE_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.store_password.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "GROCERY_BRAIN_DOC_ID"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.grocery_brain_doc_id.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "GOOGLE_OAUTH_CLIENT_ID"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_oauth_client_id.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "GOOGLE_OAUTH_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_oauth_client_secret.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "GOOGLE_OAUTH_REFRESH_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_oauth_refresh_token.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "DB_CONNECTION_NAME"
        value = google_sql_database_instance.main.connection_name
      }
      env {
        name  = "DB_NAME"
        value = google_sql_database.agent.name
      }
      env {
        name  = "DB_USER"
        value = google_sql_user.agent.name
      }
      env {
        name = "DB_PASS"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.main.connection_name]
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret_iam_member.store_username_access,
    google_secret_manager_secret_iam_member.store_password_access,
    google_secret_manager_secret_iam_member.agent_oauth_client_id,
    google_secret_manager_secret_iam_member.agent_oauth_client_secret,
    google_secret_manager_secret_iam_member.agent_oauth_refresh_token,
    google_secret_manager_secret_iam_member.agent_brain_doc_id,
    google_secret_manager_secret_iam_member.agent_nudge_recipient_id,
    google_project_iam_member.agent_cloudsql,
    google_sql_user.agent,
    google_secret_manager_secret_version.db_password,
    google_secret_manager_secret_iam_member.agent_db_password,
  ]
}

resource "google_secret_manager_secret" "store_username" {
  secret_id = "STORE_USERNAME"
  project   = var.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "store_password" {
  secret_id = "STORE_PASSWORD"
  project   = var.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_iam_member" "store_username_access" {
  secret_id = google_secret_manager_secret.store_username.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent.email}"
}

resource "google_secret_manager_secret_iam_member" "store_password_access" {
  secret_id = google_secret_manager_secret.store_password.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent.email}"
}

# ---------------------------------------------------------------------------
# Google OAuth secrets (brain doc + Gmail)
# ---------------------------------------------------------------------------

resource "google_secret_manager_secret" "grocery_brain_doc_id" {
  secret_id = "GROCERY_BRAIN_DOC_ID"
  project   = var.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "google_oauth_client_id" {
  secret_id = "GOOGLE_OAUTH_CLIENT_ID"
  project   = var.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "google_oauth_client_secret" {
  secret_id = "GOOGLE_OAUTH_CLIENT_SECRET"
  project   = var.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "google_oauth_refresh_token" {
  secret_id = "GOOGLE_OAUTH_REFRESH_TOKEN"
  project   = var.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_iam_member" "agent_brain_doc_id" {
  secret_id = google_secret_manager_secret.grocery_brain_doc_id.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent.email}"
}

resource "google_secret_manager_secret_iam_member" "agent_oauth_client_id" {
  secret_id = google_secret_manager_secret.google_oauth_client_id.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent.email}"
}

resource "google_secret_manager_secret_iam_member" "agent_oauth_client_secret" {
  secret_id = google_secret_manager_secret.google_oauth_client_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent.email}"
}

resource "google_secret_manager_secret_iam_member" "agent_oauth_refresh_token" {
  secret_id = google_secret_manager_secret.google_oauth_refresh_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent.email}"
}

# ---------------------------------------------------------------------------
# a2a-gateway  –  Telegram ↔ A2A bridge
# ---------------------------------------------------------------------------

resource "google_service_account" "gateway" {
  account_id   = "a2a-gateway"
  display_name = "a2a-gateway – Telegram bridge"
  project      = var.project_id
}

resource "google_cloud_run_v2_service" "gateway" {
  name                = "a2a-gateway"
  location            = var.region
  project             = var.project_id
  deletion_protection = false

  template {
    service_account = google_service_account.gateway.email

    scaling {
      min_instance_count = 1
      max_instance_count = 2
    }

    containers {
      image = var.gateway_image

      ports {
        container_port = 8000
      }

      env {
        name  = "A2A_SERVER_URL"
        value = "${google_cloud_run_v2_service.agent.uri}/a2a/app"
      }
      env {
        name  = "A2A_AUTH"
        value = "google_id_token"
      }
      env {
        name  = "A2A_AUDIENCE"
        value = google_cloud_run_v2_service.agent.uri
      }

      env {
        name = "TELEGRAM_BOT_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.telegram_bot_token.secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "DEBUG"
        value = "true"
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret_iam_member.gateway_telegram_bot_token,
  ]
}

# Gateway SA → can invoke the agent (A2A calls with OIDC)
resource "google_cloud_run_v2_service_iam_member" "gateway_invokes_agent" {
  name     = google_cloud_run_v2_service.agent.name
  location = var.region
  project  = var.project_id
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.gateway.email}"
}

# Agent SA → can invoke the gateway (/push for nudges)
resource "google_cloud_run_v2_service_iam_member" "agent_invokes_gateway" {
  name     = google_cloud_run_v2_service.gateway.name
  location = var.region
  project  = var.project_id
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.agent.email}"
}

# ---------------------------------------------------------------------------
# Telegram secret
# ---------------------------------------------------------------------------

resource "google_secret_manager_secret" "telegram_bot_token" {
  secret_id = "TELEGRAM_BOT_TOKEN"
  project   = var.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_iam_member" "gateway_telegram_bot_token" {
  secret_id = google_secret_manager_secret.telegram_bot_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.gateway.email}"
}

# ---------------------------------------------------------------------------
# Nudge recipient
# ---------------------------------------------------------------------------

resource "google_secret_manager_secret" "nudge_recipient_id" {
  secret_id = "NUDGE_RECIPIENT_ID"
  project   = var.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_iam_member" "agent_nudge_recipient_id" {
  secret_id = google_secret_manager_secret.nudge_recipient_id.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent.email}"
}
