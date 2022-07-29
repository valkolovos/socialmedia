# As-yet-to-be-named social media kinda thing
The idea here is to create a peer-to-peer social networking platform that can run in multiple environments. Each node is owned and operated individually and communicates with other individually-owned nodes, removing any centralized company or organization. Communcation is secured using private/public key encryption.

For now, the only supported platform is Google Cloud. Documentation is spotty at best but is on the list of things to improve over time.

# Prerequisites
You'll need to have python3.8 or higher installed.

You'll need to have a [Google Cloud](https://cloud.google.com) account.

You'll also need to have an active billing account, which will require a credit card. Add and activate a billing account through the [Google Cloud Console](https://console.cloud.google.com) using the Billing menu option. Google Cloud currently provides a free trial with $300 credit.

If you want to develop and run locally, you'll need the `gcloud` command-line tool - [installation instructions](https://cloud.google.com/sdk/docs/install).

# Install
You'll need to ensure you've cloned this repo and that you're logged in to Google Cloud with the credentials you used to set up your account:
`gcloud login auth`

You'll also probably want to have a python3 virtual environment set up:
`python3 -m venv venv`
and activated
`. venv/bin/activate`

The default project name will be `vincent-[current date in seconds]`. You can override the default project prefix by setting `PROJECT_PREFIX`. The default region will be `us-west2`. This can be overridden by setting `REGION`.

Once you're logged in, from the directory where you've cloned this repo, run:
`./install_app.sh`

Example with overrides: `PROJECT_PREFIX=my-prefix REGION=us-east4 ./install_app.sh`.

The install script will provide you with a URL you can visit to set up your first account, but in case you lose that, it will be `[project_name].wl.r.appspot.com`. You can find project name by running `gcloud projects list` from the command line.

You can use the command line tool to create a new user once your app is deployed:
`cli/freme.py signup`

# Command line tool (freme.py pronounced "free me")
The project comes with a command-line tool to interact with your server. To see documentation (such as it is), simply run the command: `./cli/freme.py`.

# Running the app locally
To run the app locally:
`ASYNC_TASKS=false GOOGLE_APPLICATION_CREDENTIALS=service-account-creds.json python main.py`

Running the app locally will still utilize the cloud-based resources. You can sign up and interact with the local application using the command line tool. Be sure to specify `--protocol=http` when using either `login` or `signup` commands. You can also view the web-based app at `http://localhost:8080`

# Deployment after initial installation
To deploy the app after you've made changes, run `gcloud app deploy`.

# Google Cloud Specifics
The application is deployed as a Google App Engine application. You can find details about your application on the [Google Cloud Console](https://console.cloud.google.com) under Compute -> App Engine

Storage is done in Firestore running in Datastore mode. You can find details about data stored within your application on the [Google Cloud Console](https://console.cloud.google.com) under Databases -> Datastore

Asynchronous operations (such as notifications) are implemented as Cloud Tasks. There are several queues that get created with the application installation. You can see details about these queues on the [Google Cloud Console](https://console.cloud.google.com) under Tools -> Cloud Tasks

# Web-based App
All the HTML for the web-based app is contained in the `templates` directory. Javascript is in `static`.

# Code coverage
Code coverage is stored in the `htmlcov` directory. To view, you can go to https://htmlpreview.github.io/. Here is a link for [coverage for the main branch](https://htmlpreview.github.io/?https://github.com/valkolovos/socialmedia/blob/main/htmlcov/index.html)

# TODO
* Document APIs
* Provide approval mechanism for new users
* Abstract data storage to allow for different types of storage (RDBMS, other No-SQL implementations, etc)
* Make the web-based interface actually usable
* Allow for public posts
* Implement connection grouping to allow for more targeted permissions
* So much more

