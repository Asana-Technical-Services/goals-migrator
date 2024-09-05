# goals-migrator
Goals migration scripts for migrating Ally.io OKR goals data from a CSV into an Asana workspace (domain).

## Overview
The script is designed to migrate goals from a CSV file and load them into the Asana Goals API. It reads goal mappings, handles CSV column names, and performs API operations to create or update goals in Asana.

## Pre-requisites
Before you begin, ensure you have the following:

Python 3.6+

Asana API token - we recommend using a [service account](https://asana.com/guide/help/premium/service-accounts)

Required Python packages (asana, pandas, numpy)

## Setup
Step 1: Clone the Repository
```
git clone https://github.com/username/repository.git
cd repository
```
Step 2: Install Requirements
pip install -r requirements.txt

Step 3: Set Environment Variables
Export the required environment variables

```
export ASANA_TOKEN=your_asana_token
export WORKSPACE_GID=your_workspace_gid
export SUPER_ADMIN_GID=your_super_admin_gid
```

Alternatively, you can use a .env file to load these variables.

##  Running the Script
To run the script, navigate to the src directory and use the following command:
```
python migrator.py
```

To process all goals regardless of previously processed entries, add an optional flag:
```
python migrator.py --all
```
