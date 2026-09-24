#!/usr/bin/env bash
set -euo pipefail
: "${GOOGLE_PROJECT_ID:?Set GOOGLE_PROJECT_ID first}"
: "${PUBSUB_AUDIENCE:?Set PUBSUB_AUDIENCE first}"
: "${PUBSUB_SERVICE_ACCOUNT:?Set PUBSUB_SERVICE_ACCOUNT first}"
gcloud config set project "$GOOGLE_PROJECT_ID"
gcloud services enable gmail.googleapis.com pubsub.googleapis.com
 gcloud pubsub topics describe gmail-notifications >/dev/null 2>&1 || gcloud pubsub topics create gmail-notifications
gcloud pubsub subscriptions describe gmail-push >/dev/null 2>&1 || gcloud pubsub subscriptions create gmail-push --topic=gmail-notifications --push-endpoint="${PUBSUB_AUDIENCE}/gmail/webhook" --push-auth-service-account="$PUBSUB_SERVICE_ACCOUNT"
gcloud pubsub topics add-iam-policy-binding gmail-notifications --member="serviceAccount:gmail-api-push@system.gserviceaccount.com" --role="roles/pubsub.publisher"
printf 'Pub/Sub is configured. Complete Gmail OAuth and register users.watch() next.\n'
