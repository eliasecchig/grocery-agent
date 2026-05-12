resource "google_project_iam_member" "agent_vertex_ai" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.agent.email}"

  depends_on = [google_project_service.apis]
}

resource "google_project_iam_member" "agent_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.agent.email}"

  depends_on = [google_project_service.apis]
}

resource "google_project_iam_member" "agent_tracing" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.agent.email}"

  depends_on = [google_project_service.apis]
}
