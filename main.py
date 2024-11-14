from flask import Flask, request, jsonify
from google.oauth2 import service_account
import googleapiclient.discovery
from google.cloud import secretmanager
import json

app = Flask(__name__)

@app.route('/create', methods=['POST'])
def create_key():
    """Creates a new IAM key for the service account, uploads it to Secret Manager as a new version, 
    and deletes previous versions in Secret Manager.
    """
    request_json = request.get_json()
    service_account_emails = request_json.get('service_account_email')
    
    try:
        for service_account_email in service_account_emails:
            create_and_upload_key(service_account_email)
        return jsonify({"message": "Key creation process completed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/delete', methods=['POST'])
def delete_key():
    """Deletes IAM keys that do not match the latest key version stored in Secret Manager."""
    request_json = request.get_json()
    service_account_emails = request_json.get('service_account_email')
    
    try:
        for service_account_email in service_account_emails:
            delete_old_keys(service_account_email)
        return jsonify({"message": "Key deletion process completed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/all', methods=['POST'])
def create_and_delete_key():
    """Performs both 'create' and 'delete' operations in sequence:
    Creates a new IAM key, uploads it to Secret Manager, then deletes older IAM keys.
    """
    request_json = request.get_json()
    service_account_emails = request_json.get('service_account_email')
    
    try:
        for service_account_email in service_account_emails:
            create_and_upload_key(service_account_email)
            delete_old_keys(service_account_email)
        return jsonify({"message": "All operations (create and delete) completed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def create_and_upload_key(service_account_email):
    """Helper function to create a new key in IAM and upload it to Secret Manager."""
    project_id = service_account_email.split('@')[1].split('.')[0]
    secret_name = service_account_email.split('@')[0]

    # Initialize IAM and Secret Manager services
    iam_service = googleapiclient.discovery.build("iam", "v1")
    secret_client = secretmanager.SecretManagerServiceClient()

    # Create a new IAM key
    key = (
        iam_service.projects()
        .serviceAccounts()
        .keys()
        .create(name=f"projects/-/serviceAccounts/{service_account_email}", body={})
        .execute()
    )
    print(f"New key created for {service_account_email}")

    # Upload the new key to Secret Manager
    parent = f"projects/{project_id}"
    secret_path = secret_client.secret_path(project_id, secret_name)

    response = secret_client.add_secret_version(
        request={"parent": secret_path, "payload": {"data": key['privateKeyData']}}
    )
    version_id = response.name.split('/')[-1]
    print(f"New secret version for {service_account_email} version: {version_id}")

    # Delete previous secret versions
    versions_to_delete = secret_client.list_secret_versions(request={"parent": secret_path})
    for version in versions_to_delete:
        if version.name != response.name:
            if version.state == secretmanager.SecretVersion.State.ENABLED:
                secret_client.destroy_secret_version(request={"name": version.name})
                print(f"Old secret version deleted: {version.name}")

    print(f"Service Account updated in Secret Manager for {service_account_email}")

def delete_old_keys(service_account_email):
    """Helper function to delete old IAM keys that do not match the latest Secret Manager version."""
    project_id = service_account_email.split('@')[1].split('.')[0]
    secret_name = service_account_email.split('@')[0]

    # Initialize IAM and Secret Manager services
    iam_service = googleapiclient.discovery.build("iam", "v1")
    secret_client = secretmanager.SecretManagerServiceClient()

    # Access the latest secret version to get the current key ID
    parent = f"projects/{project_id}/secrets/{secret_name}"
    response = secret_client.access_secret_version(request={"name": f"{parent}/versions/latest"})
    latest_key_id = json.loads(response.payload.data)['private_key_id']
    print(f"Valid key ID from Secret Manager: {latest_key_id}")

    # List current IAM keys and delete those not matching the latest key ID
    key_list = iam_service.projects().serviceAccounts().keys().list(
        name=f"projects/-/serviceAccounts/{service_account_email}"
    ).execute().get('keys', [])

    for key in key_list:
        key_id = key['name'].split('/')[-1]
        if key_id != latest_key_id and key.get('keyType') != 'SYSTEM_MANAGED':
            iam_service.projects().serviceAccounts().keys().delete(name=key['name']).execute()
            print(f"IAM key deleted: {key['name']}")
    
    print(f"Old keys deleted for {service_account_email}")

if __name__ == "__main__":
    app.run(debug=True)
