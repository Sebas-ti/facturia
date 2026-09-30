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
// schema check) — it has NOT been deployed against a real subscription.
// Deploying provisions billable resources; do that deliberately. Every
// parameter except these two secrets has a workable default:
//
//   az deployment group create -g rg-facturia -f infra/main.bicep \
//     --parameters postgresAdminPassword=<secret> apiKey=<secret>
//
// The backend image (`backendImage`) defaults to a placeholder — the real
// one is built and pushed to the ACR created here by the CI/CD workflow
// (task 5.4), then the Container App is updated to point at it.

@description('Region for most resources — Document Intelligence/OpenAI already live here (PROGRESS.md).')
param location string = 'eastus'

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

@description('Container image the backend Container App runs. Placeholder until task 5.4\'s CI/CD pushes the real one to the ACR created here.')
param backendImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

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
  location: location
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
      registries: [
        { server: acr.properties.loginServer, identity: 'system' }
      ]
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
          image: backendImage
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

// Grants the Container App's managed identity pull access to the ACR.
// Bicep deploys the Container App before this (it depends on the app's
// principalId), so the very first image pull can race the role assignment
// and fail once — Container Apps retries automatically and the next
// reconciliation succeeds once the role is in place. This is the same
// ordering trade-off Microsoft's own quickstarts accept for this pattern.
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
