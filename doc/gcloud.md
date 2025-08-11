# Google Cloud Infrastructure Administration Guide

This document provides comprehensive documentation of our Google Cloud setup, including organizations, accounts, authentication methods, and administration capabilities. It captures the knowledge gained through our setup process to enable future AI agents to effectively administer Google Cloud resources.

## Quick Start Guide for AI Agents

1. The Google Cloud SDK is pre-installed via apt package manager and available in the system PATH
2. Authentication credentials are persisted at `/host/.persist/gcloud-config`
3. Verify authentication is working with:
   ```bash
   gcloud auth list --quiet              # List all authenticated accounts
   gcloud projects list --quiet          # List projects for current account
   ```
4. Switch between accounts with:
   ```bash
   gcloud config set account [EMAIL]
   ```

**Note for AI agents:** You should NOT attempt to authenticate accounts. If authentication is needed, request the human operator to perform this task using the SSH terminal workflow described in this document.

## Account Structure & Relationships

## Authentication Setup

### Authentication Methods

#### Browser-Based Authentication (Primary Method)

> **CRITICAL NOTE FOR AI AGENTS:** Authentication should ALWAYS be performed by the human operator, not by AI agents. If authentication is needed, request the human operator to follow the workflow below.

```bash
gcloud auth login
```

**Authentication Command Options:**

- **`gcloud auth login`**: Standard command that automatically detects the environment. In a terminal-only environment like SSH, it will provide a URL rather than trying to launch a browser.
- **`gcloud auth login --no-browser`**: Generates a long command to run on a second machine with both browser AND gcloud CLI installed.
- **`gcloud auth login --no-launch-browser`**: Provides a URL to open in any browser, then you copy the resulting code back.

**Important Notes About Authentication:**
- The `gcloud auth login` command is smart enough to detect when it's running in a headless/SSH session
- Firefox-ESR in the container may show JS errors but authentication can still complete
- Organization admin accounts (like sap@ient.ai) require more frequent re-authentication (maximum session length is 24 hours)
- Regular user accounts typically have longer token lifetimes

**Recommended Human Authentication Workflow:**
1. Execute `/host/ssh.sh` from the host machine to terminal into the running container
2. Execute `gcloud auth login` which outputs an authentication URL
3. Use cmd+click on the URL in iTerm (on Mac) to open it in Chrome on the host machine
4. Complete authentication in Chrome and obtain the verification code
5. Paste the code back into the container terminal

This approach avoids browser issues in the container and provides a reliable authentication experience.

#### Service Account Authentication
For automated access (limited to specific projects):

```bash
gcloud auth activate-service-account --key-file=/host/.persist/gcloud/[KEY_FILE.json]
```

**Important Security Constraint:**
By default, Google Cloud has an organization policy that prevents creating service account keys (`constraints/iam.disableServiceAccountKeyCreation`). This security measure was encountered when attempting to create a key for the AI organization admin account. While this is a security best practice, it can create challenges for automation that requires service account keys.

If key creation is absolutely necessary, this constraint can be disabled with:
```bash
gcloud resource-manager org-policies disable-enforce constraints/iam.disableServiceAccountKeyCreation --organization=ORGANIZATION_ID
```
However, this is not recommended without careful security consideration.

# Set up gcloud persistent authentication
if [ ! -L /root/.config/gcloud ]; then
  # Remove any existing gcloud directory
  rm -rf /root/.config/gcloud
  # Create parent directory if needed
  mkdir -p /root/.config
  # Create symbolic link to persistent storage
  ln -sf /host/.persist/gcloud-config /root/.config/gcloud
  echo "Set up gcloud persistent authentication"
fi
```

## Project Information

## Gemini API Usage Monitoring

### Quota Limits Checking

To check what quota limits are available (maximum allowed usage):

```bash
gcloud alpha services quota list --service=cloudaicompanion.googleapis.com --consumer=projects/PROJECT_ID --format=json --quiet
```

This reveals quota limits such as:
- Chat API requests: 1500 per day per project/user
- API requests: 120 per minute per project/user
- Code API requests: 4500 per day per project/user

### Important Flags and Parameters

- Always use `--quiet` flag for non-interactive commands to avoid timeout errors
- Use `--format=json` for machine-readable output

**Critical Commands That Will Hang Without `--quiet` Flag:**
```bash
# These commands will hang waiting for interactive prompts:
gcloud services enable [SERVICE]                       # Prompts for confirmation
gcloud projects list                                   # May prompt for API enablement
gcloud billing projects describe PROJECT_ID           # Prompts for billing API enablement
gcloud organizations add-iam-policy-binding           # Prompts for IAM policy confirmation
gcloud alpha services quota list                       # Prompts for API enablement

# Correct pattern that won't hang:
gcloud services enable [SERVICE] --quiet
gcloud alpha services quota list --service=cloudaicompanion.googleapis.com --consumer=projects/PROJECT_ID --format=json --quiet
```

This knowledge was painfully gained through trial and error - many commands silently hang waiting for input in container environments, causing timeouts and broken automation workflows.

### Usage Monitoring Options

1. **Web Interface (Most Reliable)**:
   - URL: https://aistudio.google.com/usage?project=PROJECT_ID
   - Shows detailed graphs for token usage and request count

2. **CLI Monitoring (Limited)**:
   - Can check quota limits but not current usage
   - No direct API endpoint exists to check remaining quota programmatically

3. **Per-Request Tracking**:
   - Each API response includes token usage:
   ```json
   "usageMetadata": {
     "promptTokenCount": 10,
     "candidatesTokenCount": 1,
     "totalTokenCount": 31
   }
   ```

## Google Cloud Organization

### Organization vs. Project-Level Administration

- **Project-Level**: Permissions limited to specific projects
- **Organization-Level**: Permissions inherited by all resources in the organization

### Organization Administrator Permissions

The Organization Administrator role provides:
- View of the entire organization structure
- Creation/deletion/management of all projects
- IAM policy control at all levels
- Organization policy enforcement
- Centralized billing management

### Creating a Google Cloud Organization

1. **Requirements**:
   - Domain ownership
   - Cloud Identity Free or Google Workspace

2. **Process**:
   - Sign up for Cloud Identity Free
   - Verify domain ownership via DNS TXT records
   - Initialize Google Cloud for the organization
   - First user becomes Organization Admin

## Environment Setup Notes

### Key File Locations

- gcloud SDK: Installed via apt package manager and available in the standard system PATH
- Service account keys: `/host/.persist/gcloud/`
- Authentication data: `/host/.persist/gcloud-config/`

## Verifying Project Billing Status

To definitively check if a project has billing enabled:

```bash
gcloud alpha billing projects describe PROJECT_ID --quiet
```

This returns the billing status and associated billing account (if any). The response includes:
- `billingEnabled`: Whether billing is enabled (true/false)
- `billingAccountName`: The billing account ID if attached

### Billing-Related Authentication

When accessing sensitive billing information, you may encounter a "Please enter your password" prompt even when already authenticated. This is a security measure for high-risk operations.

**Working around authentication prompts:**
- For project-level billing status, use `gcloud alpha billing projects describe` which typically works with existing authentication
- For organization-wide billing commands that prompt for a password, the human operator will need to perform these operations

### Exploring Billing Relationships

To explore relationships between projects and billing accounts:

- **List billing accounts accessible to current user:**
  ```bash
  gcloud billing accounts list --quiet
  ```

- **Check which projects use a specific billing account:**
  ```bash
  gcloud billing projects list --billing-account=ACCOUNT_ID --quiet
  ```

- **View which users have access to a billing account:**
  ```bash
  gcloud billing accounts get-iam-policy ACCOUNT_ID --quiet
  ```

## Gemini API Tier Differences

The Gemini API has different usage tiers which significantly affect available quota:

1. **Free Tier** (no billing account linked):
   - Lower quota limits for Gemini API requests
   - Basic access to API features

2. **Paid Tier** (billing account linked but may still be free with usage below thresholds):
   - Approximately 4x higher free quota limits compared to the free tier
   - No charges incurred until exceeding the higher free allowance
   - Access to additional API capabilities

This distinction is critical - simply linking a billing account (even with minimal funds) allows access to the higher tier limits without actually incurring charges until exceeding the expanded free allowance.

## Role Assignment Commands

To grant Organization Admin role to a user or service account:

```bash
# Grant to a user
gcloud organizations add-iam-policy-binding ORGANIZATION_ID \
    --member="user:EMAIL_ADDRESS" \
    --role="roles/resourcemanager.organizationAdmin" \
    --quiet

# Grant to a service account
gcloud organizations add-iam-policy-binding ORGANIZATION_ID \
    --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
    --role="roles/resourcemanager.organizationAdmin" \
    --quiet
```

1. **Verify the SDK Installation**:
   ```bash
   which gcloud
   ```
   Should return: `/usr/bin/gcloud`

2. **Verify Authenticated Accounts**:
   ```bash
   gcloud auth list --quiet
   ```
   Should list all authenticated accounts (should include the 4 user accounts plus service accounts)

3. **Verify Account Access**:
   ```bash
   # Test with each account
   gcloud projects list --quiet

   gcloud projects list --quiet

   # Service account example
   gcloud projects list --quiet
   ```

4. **Verify Symlink Setup**:
   ```bash
   ls -la /root/.config/gcloud
   ```
   Should show a symlink to `/host/.persist/gcloud-config`

## BigQuery Billing Monitoring System

The programmatic billing monitoring system enables detailed cost analysis without manual CSV exports. This system was established in August 2025 to provide programmatic access to granular, SKU-level billing data.

### System Architecture

**Components:**
- **BigQuery Dataset**: `billing-test-1753902558:cloud_billing_export`
- **Service Account**: `billing-data-accessor@billing-test-1753902558.iam.gserviceaccount.com`
- **Required Roles**: `roles/billing.viewer` + `roles/bigquery.user` + `roles/bigquery.dataViewer`
- **Billing Exports**: Standard usage cost, Detailed usage cost, Pricing data

### Setup Process

1. **Enable Required APIs:**
   ```bash
   gcloud services enable cloudbilling.googleapis.com bigquery.googleapis.com bigquerydatatransfer.googleapis.com --project=PROJECT_ID --quiet
   ```

2. **Create Service Account:**
   ```bash
   gcloud iam service-accounts create billing-data-accessor --display-name="Service Account for Billing Data Access" --project=PROJECT_ID --quiet
   ```

3. **Grant Permissions:**
   ```bash
   # Billing account access
   gcloud billing accounts add-iam-policy-binding BILLING_ACCOUNT_ID --member="serviceAccount:billing-data-accessor@PROJECT_ID.iam.gserviceaccount.com" --role="roles/billing.viewer" --quiet

   # BigQuery permissions (project-level approach)
   gcloud projects add-iam-policy-binding PROJECT_ID --member="serviceAccount:billing-data-accessor@PROJECT_ID.iam.gserviceaccount.com" --role="roles/bigquery.user" --quiet
   gcloud projects add-iam-policy-binding PROJECT_ID --member="serviceAccount:billing-data-accessor@PROJECT_ID.iam.gserviceaccount.com" --role="roles/bigquery.dataViewer" --quiet
   ```

4. **Create Credentials:**
   ```bash
   gcloud iam service-accounts keys create /host/.persist/gcloud/billing-key.json --iam-account="billing-data-accessor@PROJECT_ID.iam.gserviceaccount.com" --quiet
   ```

### Authentication Persistence

**Current Credentials Location**: `/host/.persist/gcloud/billing-key.json`

**If Credentials Are Missing (Container Restart/Corruption):**
```bash
# Recreate service account key (requires existing service account)
gcloud iam service-accounts keys create /host/.persist/gcloud/billing-key.json --iam-account="billing-data-accessor@billing-test-1753902558.iam.gserviceaccount.com" --quiet

# Verify credentials work
export GOOGLE_APPLICATION_CREDENTIALS="/host/.persist/gcloud/billing-key.json"
python3 -c "from google.cloud import billing_v1; client = billing_v1.CloudBillingClient(); print('✅ Authentication working')"
```

**Complete Service Account Recreation (If Service Account Deleted):**
```bash
# Recreate entire service account and permissions
gcloud iam service-accounts create billing-data-accessor --display-name="Service Account for Billing Data Access" --project=billing-test-1753902558 --quiet

# Re-grant all required permissions
gcloud billing accounts add-iam-policy-binding 01725E-BCD828-07978B --member="serviceAccount:billing-data-accessor@billing-test-1753902558.iam.gserviceaccount.com" --role="roles/billing.viewer" --quiet
gcloud projects add-iam-policy-binding billing-test-1753902558 --member="serviceAccount:billing-data-accessor@billing-test-1753902558.iam.gserviceaccount.com" --role="roles/bigquery.user" --quiet
gcloud projects add-iam-policy-binding billing-test-1753902558 --member="serviceAccount:billing-data-accessor@billing-test-1753902558.iam.gserviceaccount.com" --role="roles/bigquery.dataViewer" --quiet

# Create credentials
gcloud iam service-accounts keys create /host/.persist/gcloud/billing-key.json --iam-account="billing-data-accessor@billing-test-1753902558.iam.gserviceaccount.com" --quiet
```

5. **Create BigQuery Dataset:**
   ```bash
   bq mk --dataset --location=US PROJECT_ID:cloud_billing_export
   ```

6. **Configure Billing Export (Browser Required):**
   - Navigate to Google Cloud Console > Billing > Billing export
   - Enable: Standard usage cost, Detailed usage cost, Pricing
   - Target dataset: `PROJECT_ID:cloud_billing_export`

### Programmatic Usage

#### BillingMonitor Python Class

```python
import os
from google.cloud import bigquery, billing_v1

class BillingMonitor:
    def __init__(self, credentials_path='/host/.persist/gcloud/billing-key.json'):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        self.bq_client = bigquery.Client()
        self.billing_client = billing_v1.CloudBillingClient()
        self.dataset_id = 'billing-test-1753902558.cloud_billing_export'

    def get_daily_costs(self, days_back=7):
        '''Get daily costs for the last N days'''
        query = f'''
            SELECT
                DATE(usage_start_time) as usage_date,
                SUM(cost) as daily_cost,
                currency
            FROM `{self.dataset_id}.gcp_billing_export_v1_*`
            WHERE usage_start_time >= DATE_SUB(CURRENT_DATE(), INTERVAL {days_back} DAY)
            GROUP BY usage_date, currency
            ORDER BY usage_date DESC
        '''
        return list(self.bq_client.query(query))

    def get_gemini_usage(self, days_back=30):
        '''Get detailed Gemini API usage'''
        query = f'''
            SELECT
                DATE(usage_start_time) as usage_date,
                sku.description,
                SUM(usage.amount) as total_tokens,
                SUM(cost) as total_cost
            FROM `{self.dataset_id}.gcp_billing_export_v1_*`
            WHERE service.description = 'Gemini API'
                AND usage_start_time >= DATE_SUB(CURRENT_DATE(), INTERVAL {days_back} DAY)
            GROUP BY usage_date, sku.description
            ORDER BY usage_date DESC, total_cost DESC
        '''
        return list(self.bq_client.query(query))

    def check_cost_alerts(self, daily_threshold=1.00):
        '''Check if costs exceed threshold'''
        query = f'''
            SELECT
                DATE(usage_start_time) as usage_date,
                SUM(cost) as daily_cost
            FROM `{self.dataset_id}.gcp_billing_export_v1_*`
            WHERE usage_start_time >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
            GROUP BY usage_date
            HAVING daily_cost > {daily_threshold}
        '''
        alerts = list(self.bq_client.query(query))
        return len(alerts) > 0, alerts

# Usage example:
# monitor = BillingMonitor()
# costs = monitor.get_daily_costs()
# gemini_usage = monitor.get_gemini_usage()
# has_alerts, alert_data = monitor.check_cost_alerts()
```

#### Basic Query Examples

```python
import os
from google.cloud import bigquery

# Set authentication
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/host/.persist/gcloud/billing-key.json'

# Daily cost monitoring
client = bigquery.Client()
query = '''
    SELECT
        project.id,
        service.description,
        DATE(usage_start_time) as usage_date,
        SUM(cost) as daily_cost,
        currency
    FROM `billing-test-1753902558.cloud_billing_export.gcp_billing_export_v1_*`
    WHERE usage_start_time >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
    GROUP BY project.id, service.description, usage_date, currency
    ORDER BY usage_date DESC, daily_cost DESC
'''
results = client.query(query)
```

### gcloud CLI Billing Limitations

**Critical Architectural Insight:** `gcloud billing` commands are limited to account management functions and **cannot access granular usage data** (token counts, detailed costs, SKU-level information).

**What gcloud billing CAN do:**
- List billing accounts (`gcloud billing accounts list`)
- Show project-billing associations (`gcloud billing projects list`)
- Check if billing is enabled (`gcloud alpha billing projects describe`)

**What gcloud billing CANNOT do:**
- Show token usage or detailed costs
- Access SKU-level billing data
- Provide usage breakdowns by service
- Show historical spending patterns

**Root Cause:** Google architecturally separates account management (gcloud CLI) from usage analysis (BigQuery export/web console). The web console uses internal APIs not available externally.

**Solution:** BigQuery billing export is the authoritative programmatic approach for detailed cost analysis.

## Troubleshooting Common Issues

### API Enablement Failures
- **Problem**: "API X is not enabled on project Y" errors
- **Solution**: Use `gcloud services enable [API_NAME] --quiet` and be aware that some APIs require billing to be enabled
- **Example**: When accessing quota information, you may need to enable the Service Usage API first: `gcloud services enable serviceusage.googleapis.com --quiet`

### Authentication Failures
- **Problem**: Browser authentication appears to hang or fail with Firefox-ESR
- **Solution**: Use the SSH terminal workflow described in the Authentication Methods section
- **Problem**: "You do not have access to project X" despite service account having permissions
- **Solution**: Ensure you've added `--quiet` flag to avoid interactive prompts that cause timeouts
- **Problem**: Account name corruption (e.g., "account@domain.comstderr")
- **Solution**: This can happen if output redirection corrupts credential storage. Revoke the affected account and request human operator to re-authenticate:
  ```bash
  gcloud auth revoke corrupted.account@domain.com
  ```

### Persistence Issues
- **Problem**: Despite existing authentication in `/host/.persist/gcloud-config`, commands fail with "No credentialed accounts"
- **Solution**: Verify the symlink is correctly set up. If `/root/.config/gcloud` is a directory instead of a symlink, fix it:
  ```bash
  rm -rf /root/.config/gcloud
  ln -sf /host/.persist/gcloud-config /root/.config/gcloud
  ```

### Organization Access Issues
- **Problem**: Created a service account but can't access organization resources
- **Solution**: Ensure the service account has been explicitly granted organization-level roles
- **Problem**: No organizations visible despite domain verification
- **Solution**: The organization isn't created until you explicitly initialize Google Cloud for the domain in the web console

### Billing-Related Issues
- **Problem**: Unable to access certain APIs or features
- **Solution**: Some APIs require a billing account to be linked, even if you stay within free tier limits
- **Problem**: "This API requires billing to be enabled" errors
- **Solution**: Link a billing account to the project, even with minimal funds
