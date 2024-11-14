# Google Cloud Service Account Key Manager

This project is a Google Cloud Function designed to manage the lifecycle of service account keys in a secure and automated way. It supports creating new keys, storing them in Secret Manager, and deleting outdated or unused keys to enhance security and simplify key management for service accounts.

## Overview

This code is intended for use in a Google Cloud Function, which can be invoked through an HTTP request. The Cloud Function operates using an embedded service account with the necessary permissions to create JSON tokens for service accounts and securely store them in Secret Manager vaults.

### Required Service Account

The Cloud Function should embed a service account, such as `sa-key-rotation@your-project.iam.gserviceaccount.com`, which has the following roles:

- **Secret Manager Secret Accessor**
- **Secret Manager Secret Version Manager**
- **Service Account Key Admin**

These roles grant the Cloud Function the necessary permissions to manage service account keys and securely store them in Secret Manager.

## Features

- **Create Keys**: Automatically generates new keys for specified service accounts, uploads them to Google Secret Manager, and securely stores them under the appropriate project and secret ID.
- **Delete Keys**: Identifies and deletes unused or expired keys for a specified service account, ensuring only the latest key version remains active.
- **Secret Manager Integration**: Uses Google Secret Manager to securely store, version, and manage access to service account keys, reducing the risk of unauthorized access.
- **IAM Management**: Uses Google IAM to manage service accounts and streamline access and security processes.

## Setup

1. Deploy this function on Google Cloud using the functions framework.
2. Ensure that the Cloud Function is configured to run under the service account with the roles mentioned above.
3. Configure the function with a JSON payload specifying the `operation` (`create` or `delete`) and the `service_account_email` to manage.

## Usage

- Send an HTTP request to the deployed function with a JSON payload. Example:
  ```json
  {
    "operation": "create",
    "service_account_email": ["your-service-account@your-project.iam.gserviceaccount.com"]
  }
