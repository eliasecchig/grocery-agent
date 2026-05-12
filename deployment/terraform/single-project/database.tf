resource "random_password" "db_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "google_sql_database_instance" "main" {
  name             = "${var.service_name}-db"
  database_version = "POSTGRES_15"
  region           = var.region
  project          = var.project_id

  settings {
    tier              = "db-f1-micro"
    edition           = "ENTERPRISE"
    availability_type = "ZONAL"

    ip_configuration {
      ipv4_enabled = true
    }

    backup_configuration {
      enabled = false
    }

    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }

    disk_size = 10
  }

  deletion_protection = false
  depends_on          = [google_project_service.apis]
}

resource "google_sql_database" "agent" {
  name     = "grocery_agent"
  instance = google_sql_database_instance.main.name
  project  = var.project_id
}

resource "google_sql_user" "agent" {
  name     = "grocery_agent"
  instance = google_sql_database_instance.main.name
  project  = var.project_id
  password = google_secret_manager_secret_version.db_password.secret_data
}

resource "google_secret_manager_secret" "db_password" {
  secret_id = "${var.service_name}-db-password"
  project   = var.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

resource "google_project_iam_member" "agent_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.agent.email}"

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_iam_member" "agent_db_password" {
  secret_id = google_secret_manager_secret.db_password.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent.email}"
}
