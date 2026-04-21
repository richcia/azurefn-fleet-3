# Azure Storage Design — Reference Links

Authoritative URLs for Azure Storage best practices and design patterns.

---

## General Best Practices

| Topic | URL |
|---|---|
| Azure Storage overview | https://learn.microsoft.com/en-us/azure/storage/common/storage-introduction |
| Performance and scalability checklist for Blob Storage | https://learn.microsoft.com/en-us/azure/storage/blobs/storage-performance-checklist |
| Performance and scalability checklist for Queue Storage | https://learn.microsoft.com/en-us/azure/storage/queues/storage-performance-checklist |
| Performance and scalability checklist for Table Storage | https://learn.microsoft.com/en-us/azure/storage/tables/storage-performance-checklist |
| Azure Storage redundancy options (LRS, ZRS, GRS, GZRS) | https://learn.microsoft.com/en-us/azure/storage/common/storage-redundancy |
| Choose the right storage account type | https://learn.microsoft.com/en-us/azure/storage/common/storage-account-overview |
| Scalability and performance targets for Blob Storage | https://learn.microsoft.com/en-us/azure/storage/blobs/scalability-targets |
| Scalability targets for standard storage accounts | https://learn.microsoft.com/en-us/azure/storage/common/scalability-targets-standard-account |

---

## Blob Storage Best Practices

| Topic | URL |
|---|---|
| Blob Storage best practices | https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blobs-introduction |
| Access tiers (Hot, Cool, Cold, Archive) | https://learn.microsoft.com/en-us/azure/storage/blobs/access-tiers-overview |
| Lifecycle management policies | https://learn.microsoft.com/en-us/azure/storage/blobs/lifecycle-management-overview |
| Soft delete for blobs | https://learn.microsoft.com/en-us/azure/storage/blobs/soft-delete-blob-overview |
| Blob versioning | https://learn.microsoft.com/en-us/azure/storage/blobs/versioning-overview |
| Immutable storage (WORM) | https://learn.microsoft.com/en-us/azure/storage/blobs/immutable-storage-overview |
| Optimizing costs with access tiers | https://learn.microsoft.com/en-us/azure/storage/blobs/access-tiers-best-practices |
| Conditional requests (ETags, If-None-Match) | https://learn.microsoft.com/en-us/rest/api/storageservices/specifying-conditional-headers-for-blob-service-operations |
| Blob naming and listing best practices | https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blobs-list |
| Large-scale blob upload (block blobs, parallel upload) | https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-upload-best-practices |

---

## Security Best Practices

| Topic | URL |
|---|---|
| Security recommendations for Blob Storage | https://learn.microsoft.com/en-us/azure/storage/blobs/security-recommendations |
| Azure Storage security guide | https://learn.microsoft.com/en-us/azure/storage/common/storage-security-guide |
| Authorize access with Azure AD / Managed Identity | https://learn.microsoft.com/en-us/azure/storage/blobs/authorize-access-azure-active-directory |
| Azure RBAC for Storage (built-in roles) | https://learn.microsoft.com/en-us/azure/storage/common/storage-auth-aad-rbac-portal |
| Disable anonymous (public) blob access | https://learn.microsoft.com/en-us/azure/storage/blobs/anonymous-read-access-prevent |
| Require secure transfer (HTTPS only) | https://learn.microsoft.com/en-us/azure/storage/common/storage-require-secure-transfer |
| Storage firewall and virtual network rules | https://learn.microsoft.com/en-us/azure/storage/common/storage-network-security |
| Customer-managed keys (CMK) with Key Vault | https://learn.microsoft.com/en-us/azure/storage/common/customer-managed-keys-overview |
| Shared Access Signatures (SAS) best practices | https://learn.microsoft.com/en-us/azure/storage/common/storage-sas-overview |
| Microsoft Defender for Storage | https://learn.microsoft.com/en-us/azure/defender-for-cloud/defender-for-storage-introduction |

---

## Design Patterns

| Topic | URL |
|---|---|
| Claim-check pattern (offload large messages to blob) | https://learn.microsoft.com/en-us/azure/architecture/patterns/claim-check |
| Static content hosting pattern | https://learn.microsoft.com/en-us/azure/architecture/patterns/static-content-hosting |
| Valet key pattern (delegated access via SAS) | https://learn.microsoft.com/en-us/azure/architecture/patterns/valet-key |
| Event-driven architecture with Blob Storage events | https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-event-overview |
| Data partitioning guidance for Table Storage | https://learn.microsoft.com/en-us/azure/architecture/best-practices/data-partitioning-strategies |
| Queue-based load leveling with Storage Queues | https://learn.microsoft.com/en-us/azure/architecture/patterns/queue-based-load-leveling |
| Geode pattern (multi-region storage) | https://learn.microsoft.com/en-us/azure/architecture/patterns/geodes |

---

## Reliability & Operations

| Topic | URL |
|---|---|
| Disaster recovery and failover | https://learn.microsoft.com/en-us/azure/storage/common/storage-disaster-recovery-guidance |
| Point-in-time restore for block blobs | https://learn.microsoft.com/en-us/azure/storage/blobs/point-in-time-restore-overview |
| Monitor Azure Blob Storage | https://learn.microsoft.com/en-us/azure/storage/blobs/monitor-blob-storage |
| Storage metrics and logging (Azure Monitor) | https://learn.microsoft.com/en-us/azure/storage/common/storage-analytics |
| Handle transient errors and retry (Azure SDK) | https://learn.microsoft.com/en-us/azure/architecture/best-practices/retry-service-specific#azure-storage |
| Storage account failover (geo-redundancy) | https://learn.microsoft.com/en-us/azure/storage/common/storage-initiate-account-failover |

---

## Cost Optimization

| Topic | URL |
|---|---|
| Optimize costs for Blob Storage | https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-storage-tiers |
| Plan and manage costs for Azure Blob Storage | https://learn.microsoft.com/en-us/azure/storage/common/storage-plan-manage-costs |
| Azure Storage reserved capacity | https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-reserved-capacity |
