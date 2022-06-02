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

QUEUES=("post-created" "post-notify" "ack-connection" "request-connection" "comment-created")
gcloud components update --quiet
# create project
echo "Creating Project ${PROJECT_NAME}..."
gcloud projects create ${PROJECT_NAME} --name="Social Media" --quiet
gcloud config set project ${PROJECT_NAME}

# check to see if gcloud beta component is installed
beta_installed=$(gcloud components list 2>&1|grep "gcloud Beta Commands")
if [[ -z $beta_installed ]]; then
  echo
  echo "Installing beta components..."
  gcloud components install beta
fi

# need to link billing account to project in order to
# be able to enable cloudbuild and cloudtasks

# billing account setup
echo
echo "Linking billing account to project..."
gcloud services enable cloudbilling.googleapis.com
BILLING_ACCOUNT=$(gcloud beta billing accounts list --format=config 2>&1|grep "name = "|cut -d' ' -f3|cut -d'/' -f2)
gcloud beta billing projects link ${PROJECT_NAME} --billing-account=$BILLING_ACCOUNT

# install services
echo
echo "Enabling cloudbuild and cloudtasks services..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable cloudtasks.googleapis.com

echo
echo "Creating app..."
gcloud app create --region=$REGION --quiet

# wait for service account to be created
echo
echo "Waiting for service account to be created..."
service_account_created=$(gcloud iam service-accounts list|grep "${PROJECT_NAME}@appspot.gserviceaccount.com")
while [[ -z $service_account_created ]]
do
  service_account_created=$(gcloud iam service-accounts list|grep "${PROJECT_NAME}@appspot.gserviceaccount.com")
done
echo
echo "Creating and downloading service account credentials..."
gcloud iam service-accounts keys create service-account-creds.json --iam-account=${PROJECT_NAME}@appspot.gserviceaccount.com

echo
echo "Creating task queues..."
for queue in "${QUEUES[@]}"
  do gcloud tasks queues create $queue
done

echo
echo "Creating datastore indexes..."
gcloud datastore indexes create index.yaml --quiet

#echo "waiting to ensure app is completely created"
#sleep 20
echo
echo "Deploying app..."

function keep_trying {
  echo
  echo "App deploy failed. Sleeping for 60 seconds then trying again"
  sleep 60
  gcloud app deploy --quiet
}
trap keep_trying ERR
gcloud app deploy --quiet

echo "Deployed to ${PROJECT_NAME}. Visit https://${PROJECT_NAME}.wl.r.appspot.com"
