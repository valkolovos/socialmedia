import os
import re
import sys
import time

from datetime import datetime

import pexpect

def retry_command(cmd, timeout=None):
    retries = 0
    while retries < 5:
        print(f'Executing command "{cmd}"')
        script = pexpect.spawn(cmd, encoding='utf-8', timeout=timeout)
        script.logfile = sys.stdout
        script.expect(pexpect.EOF)
        script.close()
        if script.exitstatus == 0:
            return script.before
        time.sleep(3)
        retries += 1
    raise Exception(f'{cmd} exceeded retry count')

def main():
    try:
        try:
            check_for_queues_response = retry_command('gcloud tasks queues list --quiet')
        except Exception:
            check_for_queues_response = ''
        print('Creating task queues...')
        for queue in ['post-created','post-notify','ack-connection','request-connection','comment-created']:
            if queue not in check_for_queues_response:
                print(f'Creating {queue}')
                retry_command(f'gcloud tasks queues create {queue}')
        print('Done creating task queues')

        print('Cloning code to deploy...')
        retry_command('rm -rf socialmedia')
        retry_command('git clone https://github.com/valkolovos/socialmedia.git')
        print('Done cloning code')

        print('Creating datastore indexes...')
        retry_command('gcloud datastore indexes create socialmedia/index.yaml --quiet')
        print('Done creating datastore indexes')

        print('Deploying app...')
        retry_command('./deploy_app.sh')
        print('Done deploying app')

        secrets_list = retry_command('gcloud secrets list --format="value(name)"')
        if not 'backend-sha' in secrets_list:
            print('Creating backend-sha secret...')
            retry_command('gcloud secrets create backend-sha')
            print('Done creating backend-sha secret')

        print('Writing current SHA to GCP secrets...')
        backend_sha_result = retry_command(
            'git ls-remote https://github.com/valkolovos/socialmedia.git main',
            timeout=30
        )
        backend_sha = backend_sha_result.split('\t')[0]
        with open('backend-sha.json', 'w') as shas:
            shas.write(f'{{"serverSHA":"{backend_sha}"}}')
        retry_command('gcloud secrets versions add backend-sha --data-file="backend-sha.json"')
        print('Done writing current SHA to GCP secrets')

        existing_jobs = retry_command('gcloud beta run jobs list')
        job_region = 'us-central1'
        backend_image = 'us-central1-docker.pkg.dev/freme-2022/freme-backend-update/freme-backend-update:latest'
        if 'freme-backend-update' not in existing_jobs:
            backend_cmd = 'create'
        else:
            backend_cmd = 'update'
        print(f'{"Creating" if backend_cmd=="create" else "Updating"} backend update job...')
        retry_command(
            f'gcloud beta run jobs {backend_cmd} freme-backend-update '
            f'--image={backend_image} '
            f'--region={job_region} --service-account={project_name}@appspot.gserviceaccount.com --quiet'
        )
        print(f'Done {"creating" if backend_cmd=="create" else "updating"} backend update job')

    except Exception as e:
        raise e
    finally:
        print('all done')


if __name__ == "__main__":
    main()

