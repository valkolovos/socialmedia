#!/usr/bin/env bash
set -e
PROJECT_NAME=eduardo-$(date +%s)
QUEUES="message-created message-notify ack-connection request-connection comment-created"
gcloud projects create ${PROJECT_NAME} --name="Social Media" --quiet
gcloud config set project ${PROJECT_NAME}
BILLING_ACCOUNT=$(gcloud beta billing accounts list --format=config|grep name|cut -d' ' -f3|cut -d'/' -f2)
gcloud beta billing projects link ${PROJECT_NAME} --billing-account $BILLING_ACCOUNT
gcloud services enable cloudbuild.googleapis.com
gcloud services enable cloudbilling.googleapis.com
gcloud services enable cloudtasks.googleapis.com
gcloud app create --region=us-west2 --quiet
gcloud iam service-accounts keys create service-account-creds.json --iam-account ${PROJECT_NAME}@appspot.gserviceaccount.com
echo "waiting to ensure app is completely created"
sleep 20
gcloud app deploy --quiet
gcloud datastore indexes create index.yaml --quiet
for queue in $QUEUES
  do gcloud tasks queues create $queue
done
