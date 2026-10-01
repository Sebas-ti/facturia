// Azure infrastructure for FacturIA (docs/spec.md §2, Fase 5 in PROGRESS.md).
//
// Provisions what spec.md §2's architecture needs beyond what already exists
// manually in rg-facturia — Document Intelligence (`docintel-facturia`) and
// Azure OpenAI (`openai-facturia`), per PROGRESS.md's Decisiones. Those are
// referenced as `existing` resources (endpoint + key pulled via listKeys()),
// never re-provisioned here.
//
// New resources: Container Registry, PostgreSQL Flexible Server, Storage
// Account (blob), Container Apps Environment + the backend Container App,
// and a Static Web App for the frontend.
//
// This file has only been validated locally with `az bicep build` (syntax +
// schema check) and `az deployment group what-if` — a real `create` against
// rg-facturia is what's tracked in PROGRESS.md's Decisiones (including two
// real bugs it caught: a Postgres API version that didn't support v16, and
// the subscription's `eastus` region being provisioning-restricted for
// Flexible Server). Deploying provisions billable resources; do that
// deliberately.
//
// The Container App always starts on a public bootstrap image (python's
// stdlib http.server — no backendImage parameter, see below) instead of the
// real backend, and deliberately *not* from the ACR this template creates.
// Two real deploy failures led here:
//   1. A public placeholder (`mcr.microsoft.com/k8se/quickstart`) listens on
//      port 80, not the 8000 this template's ingress expects — the revision
//      never passed its health check ("Operation expired").
//   2. Pointing the first revision at a real image in the ACR instead: the
//      Container App needs `AcrPull` via its own managed identity to pull
//      it, but that role assignment (below) depends on the Container App's
//      principalId, which only exists once the Container App itself
//      succeeds — and it can't succeed without the pull working. A genuine
//      deadlock (confirmed via the Container App's logs in Log Analytics:
//      repeated 401s from the ACR token exchange endpoint), not a brief,
//      self-healing race like an earlier version of this comment assumed.
//   3. Still failed even once the bootstrap image needed no ACR auth: having
//      the ACR listed under `configuration.registries` at all makes
//      Container Apps try to resolve its credentials for every new
//      revision, regardless of which registry that revision's image
//      actually comes from — so the same 401 deadlock reproduced even
//      though nothing was pulling from the ACR yet. There's no
//      `registries` entry on the Container App below for this reason.
// Roll out the real backend after this deploys — task 5.4's CI/CD does this
// on every push to main; to do it once by hand right after this deploys:
//
//   az acr build --registry <acrLoginServer, no ".azurecr.io" suffix> \
//     --image facturia-api:bootstrap backend
//   az containerapp registry set -g rg-facturia -n facturia-api \
//     --server <acrLoginServer> --identity system
//   az containerapp update -g rg-facturia -n facturia-api \
//     --image <acrLoginServer>/facturia-api:bootstrap
//
// That `update` only changes `image` — it leaves the bootstrap container's
// `command`/`args` (python3 -m http.server 8000) in place, so the real
// image would run that instead of its own Dockerfile CMD. `--command ""
// --args ""` does NOT clear them (it sets them to a list holding one empty
// string, which is worse). Strip them for real with a full YAML round-trip,
// once, right after the `containerapp update` above:
//
//   az containerapp show -g rg-facturia -n facturia-api -o yaml > ca.yaml
//   python3 -c "
//     import yaml
//     d = yaml.safe_load(open('ca.yaml'))
//     for c in d['properties']['template']['containers']:
//         c.pop('command', None); c.pop('args', None)
//     yaml.safe_dump(d, open('ca.yaml', 'w'))"
//   az containerapp update -g rg-facturia -n facturia-api --yaml ca.yaml
//
// Not needed again after this: once command/args are gone from the
// container spec, later `az containerapp update --image ...` calls (task
// 5.4's CI/CD) don't reintroduce them.

@description('Region for most resources — Document Intelligence/OpenAI already live here (PROGRESS.md).')
param location string = 'eastus'

@description('Region for PostgreSQL Flexible Server. Separate from `location`: some subscriptions have Flexible Server provisioning restricted per-region (confirmed with `az postgres flexible-server list-skus -l <region>` — eastus was restricted for this subscription, eastus2 is not), independent of whether other resource types are restricted there.')
param postgresLocation string = 'eastus2'

@description('Region for the Static Web App — only a subset of regions support it (eastus2 is one).')
param staticWebAppLocation string = 'eastus2'

@description('Existing Document Intelligence account name (provisioned manually, not by this template).')
param docIntelAccountName string = 'docintel-facturia'

@description('Existing Azure OpenAI account name (provisioned manually, not by this template).')
param openAiAccountName string = 'openai-facturia'

@description('Azure OpenAI deployment name the backend calls.')
param openAiDeployment string = 'gpt-4o'

@description('Admin username for the PostgreSQL Flexible Server.')
param postgresAdminUser string = 'facturia'

@secure()
@description('Admin password for the PostgreSQL Flexible Server. No default — must be supplied at deploy time.')
param postgresAdminPassword string

@secure()
@description('Shared API key the backend requires on POST /api/invoices (docs/spec.md §6, PROGRESS.md 5.1). No default — must be supplied at deploy time.')
param apiKey string

@description('Container App min replicas. 0 scales to zero between demo visits (cold start on the next request) to save cost — set to 1 to avoid that for a live demo/interview.')
@minValue(0)
@maxValue(1)
param minReplicas int = 0

var resourcePrefix = 'facturia'
var uniqueSuffix = uniqueString(resourceGroup().id)
var acrName = '${resourcePrefix}acr${uniqueSuffix}'
var postgresServerName = '${resourcePrefix}-pg-${uniqueSuffix}'
var storageAccountName = '${resourcePrefix}st${uniqueSuffix}'
var databaseName = 'facturia'
var blobContainerName = 'invoices'

resource docIntel 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: docIntelAccountName
}

resource openAi 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: openAiAccountName
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: postgresServerName
  location: postgresLocation
  sku: { name: 'Standard_B1ms', tier: 'Burstable' }
  properties: {
    version: '16'
    administratorLogin: postgresAdminUser
    administratorLoginPassword: postgresAdminPassword
    storage: { storageSizeGB: 32 }
    backup: { backupRetentionDays: 7, geoRedundantBackup: 'Disabled' }
    highAvailability: { mode: 'Disabled' }
  }
}

resource postgresDb 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: databaseName
  properties: { charset: 'UTF8', collation: 'en_US.utf8' }
}

// Flexible Server has no VNet integration here (keeps this demo simple), so
// Container Apps reaches it over the public endpoint — this named rule
// (0.0.0.0-0.0.0.0) is Azure's documented convention for "allow Azure
// services", not a real open-to-everyone range.
resource postgresFirewallAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: postgres
  name: 'AllowAzureServices'
  properties: { startIpAddress: '0.0.0.0', endIpAddress: '0.0.0.0' }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: { minimumTlsVersion: 'TLS1_2', allowBlobPublicAccess: false }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storage
  name: 'default'
}

resource invoicesContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: blobContainerName
  properties: { publicAccess: 'None' }
}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${resourcePrefix}-logs'
  location: location
  properties: { sku: { name: 'PerGB2018' }, retentionInDays: 30 }
}

resource containerAppEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${resourcePrefix}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource staticWebApp 'Microsoft.Web/staticSites@2023-01-01' = {
  name: '${resourcePrefix}-web'
  location: staticWebAppLocation
  sku: { name: 'Free', tier: 'Free' }
  properties: {
    buildProperties: {
      // task 5.4's GitHub Actions workflow deploys the build directly — no
      // auto-generated workflow needed from this resource.
      skipGithubActionWorkflowGeneration: true
    }
  }
}

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${resourcePrefix}-api'
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
      }
      // No `registries` entry here on purpose — see the header comment.
      // Container Apps tries to resolve credentials for every configured
      // registry when a revision is created, even ones no container in
      // that revision actually pulls from, so listing the ACR here from
      // the start reproduces the exact deadlock a bootstrap image without
      // ACR auth was meant to avoid. Added later with `az containerapp
      // registry set`, once AcrPull is actually granted.
      secrets: [
        {
          name: 'database-url'
          value: 'postgresql+psycopg://${postgresAdminUser}:${postgresAdminPassword}@${postgres.properties.fullyQualifiedDomainName}:5432/${databaseName}?sslmode=require'
        }
        {
          name: 'storage-connection-string'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
        }
        { name: 'doc-intel-key', value: docIntel.listKeys().key1 }
        { name: 'openai-key', value: openAi.listKeys().key1 }
        { name: 'api-key', value: apiKey }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          // Public bootstrap image (no ACR auth needed) — see the header
          // comment for why, and how to roll out the real backend after.
          image: 'docker.io/library/python:3.12-slim'
          command: ['python3']
          args: ['-m', 'http.server', '8000']
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'APP_ENV', value: 'production' }
            { name: 'DATABASE_URL', secretRef: 'database-url' }
            { name: 'AZURE_STORAGE_CONNECTION_STRING', secretRef: 'storage-connection-string' }
            { name: 'AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT', value: docIntel.properties.endpoint }
            { name: 'AZURE_DOCUMENT_INTELLIGENCE_KEY', secretRef: 'doc-intel-key' }
            { name: 'AZURE_OPENAI_ENDPOINT', value: openAi.properties.endpoint }
            { name: 'AZURE_OPENAI_KEY', secretRef: 'openai-key' }
            { name: 'AZURE_OPENAI_DEPLOYMENT', value: openAiDeployment }
            { name: 'API_KEY', secretRef: 'api-key' }
            { name: 'CORS_ORIGINS', value: '["https://${staticWebApp.properties.defaultHostname}"]' }
          ]
        }
      ]
      scale: { minReplicas: minReplicas, maxReplicas: 1 }
    }
  }
}

// Grants the Container App's managed identity pull access to the ACR, so
// `az containerapp update --image <acr>/...` (see header comment) works
// once this deployment finishes. Only reachable because the Container App
// above no longer needs this role to succeed itself (see header comment).
resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, containerApp.id, 'AcrPull')
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: containerApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

output acrLoginServer string = acr.properties.loginServer
output containerAppFqdn string = containerApp.properties.configuration.ingress.fqdn
output staticWebAppDefaultHostname string = staticWebApp.properties.defaultHostname
output postgresFqdn string = postgres.properties.fullyQualifiedDomainName
