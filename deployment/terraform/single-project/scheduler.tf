resource "google_service_account" "scheduler_invoker" {
  account_id   = "grocery-agent-scheduler"
  display_name = "Grocery Agent - Cloud Scheduler Invoker"
  project      = var.project_id
}

resource "google_cloud_run_v2_service_iam_member" "scheduler_invoker" {
  name     = google_cloud_run_v2_service.agent.name
  location = var.region
  project  = var.project_id
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler_invoker.email}"
}

resource "google_cloud_scheduler_job" "nudge" {
  name             = "grocery-agent-nudge"
  description      = "Trigger grocery agent nudge every 2 days at 8am Rome time"
  schedule         = "0 8 */2 * *"
  time_zone        = var.nudge_timezone
  attempt_deadline = "320s"
  region           = var.region
  project          = var.project_id

  http_target {
    uri         = "${google_cloud_run_v2_service.agent.uri}/trigger/nudge"
    http_method = "POST"

    oidc_token {
      service_account_email = google_service_account.scheduler_invoker.email
      audience              = google_cloud_run_v2_service.agent.uri
    }
  }

  depends_on = [
    google_project_service.apis,
    google_cloud_run_v2_service_iam_member.scheduler_invoker,
  ]
}
