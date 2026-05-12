output "service_url" {
  description = "URL of the Cloud Run service."
  value       = google_cloud_run_v2_service.agent.uri
}

output "gateway_url" {
  description = "URL of the a2a-gateway Cloud Run service."
  value       = google_cloud_run_v2_service.gateway.uri
}

output "scheduler_job" {
  description = "Cloud Scheduler job for periodic nudge."
  value       = google_cloud_scheduler_job.nudge.name
}
