#!/usr/bin/env bash
set -e
if [[ -z $PROJECT_PREFIX ]]; then
  PROJECT_NAME=vincent-$(date +%s)
else
  PROJECT_NAME=${PROJECT_PREFIX}-$(date +%s)
fi
if [[ -z $REGION ]]; then
  REGION=us-west2
fi

QUEUES="message-created message-notify ack-connection request-connection comment-created"
# create project
gcloud projects create ${PROJECT_NAME} --name="Social Media" --quiet
gcloud config set project ${PROJECT_NAME}
beta_installed=$(gcloud components list 2>&1|grep "gcloud Beta Commands")
if [[ -z $beta_installed ]]; then
  gcloud components install beta
fi
gcloud services enable cloudbilling.googleapis.com
BILLING_ACCOUNT=$(gcloud beta billing accounts list --format=config|grep name|cut -d' ' -f3|cut -d'/' -f2)
gcloud beta billing projects link ${PROJECT_NAME} --billing-account $BILLING_ACCOUNT
gcloud services enable cloudbuild.googleapis.com
gcloud services enable cloudtasks.googleapis.com
gcloud app create --region=$REGION --quiet
gcloud iam service-accounts keys create service-account-creds.json --iam-account ${PROJECT_NAME}@appspot.gserviceaccount.com
echo "waiting to ensure app is completely created"
sleep 20
gcloud app deploy --quiet
gcloud datastore indexes create index.yaml --quiet
for queue in $QUEUES
  do gcloud tasks queues create $queue
done

echo "Deployed to ${PROJECT_NAME}. Visit https://${PROJECT_NAME}.wl.r.appspot.com"
