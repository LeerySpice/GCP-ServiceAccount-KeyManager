import functions_framework
from google.oauth2 import service_account
import googleapiclient.discovery  # type: ignore
from google.cloud import secretmanager
import json

@functions_framework.http
def main(request):
    """HTTP Cloud Function."""

    request_json = request.get_json(silent=True)
    print(f"Configuration to process {request_json}")

    try:
        if request_json['operation'] == 'create':
            create(request_json)
        elif request_json['operation'] == 'delete':
            delete(request_json)
        else: 
            print("Operation not defined. Action not recognized.")

    except Exception as e:
        print("Error:", e)

    return ("Process completed successfully", 200)


def create(request):
    """Creates new keys and stores them in Secret Manager."""

    for service_account in request['service_account_email']:

        project_id = service_account.split('@')[1].split('.')[0]
        secret_name = service_account.split('@')[0]

        # GCP project where the service is located
        service = googleapiclient.discovery.build("iam", "v1")

        # Create a new key
        key = (
            service.projects()
            .serviceAccounts()
            .keys()
            .create(name="projects/-/serviceAccounts/" + service_account, body={})
            .execute()
        )
        print(f"New key for {service_account}!")

        # Upload the new key to Secret Manager
        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{project_id}"
        secret_id = secret_name
        secret_path = client.secret_path(project_id, secret_id)

        response = client.add_secret_version(
            request={"parent": secret_path, "payload": {"data": key['privateKeyData']}}
        )

        version_id = response.name.split('/')[-1]
        print(f"New version of secret {service_account} version: {version_id}")

        # Delete previous versions
        versions_to_delete = client.list_secret_versions(request={"parent": secret_path})
        # Check previous versions if they exist and are in ENABLED state
        for version in versions_to_delete:
            if version.name != response.name:
                if version.state == secretmanager.SecretVersion.State.ENABLED:
                    # Delete the previous version
                    client.destroy_secret_version(request={"name": version.name})
                    print(f"Old secret version deleted: {version.name}")
                    
        print(f"OK. SA Updated {service_account} in Secret Manager")

    return ("Key creation process completed successfully")


def delete(request):
    """Deletes old keys from Secret Manager and IAM."""

    for service_account in request['service_account_email']:
      
        project_id = service_account.split('@')[1].split('.')[0]
        secret_name = service_account.split('@')[0]

        # GCP project where the service is located
        service = googleapiclient.discovery.build("iam", "v1")

        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{project_id}/secrets/{secret_name}"
        response = client.access_secret_version(request={"name": f"{parent}/versions/latest"})

        key_id = json.loads(response.payload.data)['private_key_id']
        print(f"Valid secret manager key: {key_id}")

        # List current IAM keys
        key = (
            service.projects()
            .serviceAccounts()
            .keys()
            .list(name="projects/-/serviceAccounts/" + service_account)
            .execute()
        )

        key_list = key.get('keys', [])

        for k in key_list:
            key_private_id = k['name'].split('/')[-1]
            if key_private_id != key_id and k.get('keyType') != 'SYSTEM_MANAGED':
                print(f"IAM key to delete: {k['name']}")
                service.projects().serviceAccounts().keys().delete(name=k['name']).execute()
    
        print(f"OK: keys deleted for {service_account}")
    
    return ("Key deletion process completed successfully")
