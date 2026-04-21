# Azure Function Design — Reference Links

Authoritative URLs for best practices and design patterns. Use these when generating or reviewing Azure Function designs.

---

## Best Practices

| Topic | URL |
|---|---|
| Azure Functions best practices (overview) | https://learn.microsoft.com/en-us/azure/azure-functions/functions-best-practices |
| Performance and reliability best practices | https://learn.microsoft.com/en-us/azure/azure-functions/performance-reliability |
| Improve throughput performance of Python apps | https://learn.microsoft.com/en-us/azure/azure-functions/python-scale-performance-reference |
| Manage connections (avoid socket exhaustion) | https://learn.microsoft.com/en-us/azure/azure-functions/manage-connections |
| Error handling and retry guidance | https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-error-pages |
| Host.json reference (timeouts, concurrency, logging) | https://learn.microsoft.com/en-us/azure/azure-functions/functions-host-json |
| Timer trigger — useMonitor and missed executions | https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-timer |
| Reliable Azure Functions (idempotency guide) | https://learn.microsoft.com/en-us/azure/azure-functions/functions-idempotent |
| Retry policies | https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-error-pages#retry-policies |
| Storage considerations (host vs. app storage) | https://learn.microsoft.com/en-us/azure/azure-functions/storage-considerations |

---

## Security Best Practices

| Topic | URL |
|---|---|
| Securing Azure Functions | https://learn.microsoft.com/en-us/azure/azure-functions/security-concepts |
| Use Managed Identity in Azure Functions | https://learn.microsoft.com/en-us/azure/app-service/overview-managed-identity |
| Key Vault references in App Settings | https://learn.microsoft.com/en-us/azure/app-service/app-service-key-vault-references |
| Function access keys and auth levels | https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-http-webhook-trigger#authorization-keys |
| Network security options | https://learn.microsoft.com/en-us/azure/azure-functions/functions-networking-options |

---

## Design Patterns

| Topic | URL |
|---|---|
| Durable Functions patterns (fan-out, chaining, async HTTP) | https://learn.microsoft.com/en-us/azure/azure-functions/durable/durable-functions-overview |
| Event-driven architecture with Azure Functions | https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/event-driven |
| Azure Functions in microservices | https://learn.microsoft.com/en-us/azure/architecture/microservices/design/compute-options |
| Async request-reply pattern | https://learn.microsoft.com/en-us/azure/architecture/patterns/async-request-reply |
| Competing consumers pattern | https://learn.microsoft.com/en-us/azure/architecture/patterns/competing-consumers |
| Claim-check pattern (large message offload) | https://learn.microsoft.com/en-us/azure/architecture/patterns/claim-check |
| Retry pattern | https://learn.microsoft.com/en-us/azure/architecture/patterns/retry |
| Circuit breaker pattern | https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker |
| Queue-based load leveling | https://learn.microsoft.com/en-us/azure/architecture/patterns/queue-based-load-leveling |
| Scheduler Agent Supervisor pattern | https://learn.microsoft.com/en-us/azure/architecture/patterns/scheduler-agent-supervisor |

---

## Observability & Operations

| Topic | URL |
|---|---|
| Monitor Azure Functions | https://learn.microsoft.com/en-us/azure/azure-functions/monitor-functions |
| Application Insights for Azure Functions | https://learn.microsoft.com/en-us/azure/azure-functions/functions-monitoring |
| Configure Application Insights sampling | https://learn.microsoft.com/en-us/azure/azure-functions/configure-monitoring#configure-sampling |
| Structured logging with ILogger | https://learn.microsoft.com/en-us/azure/azure-functions/functions-dotnet-dependency-injection#logging |
| Alerts and diagnostics | https://learn.microsoft.com/en-us/azure/azure-monitor/alerts/alerts-overview |

---

## Hosting & Scaling

| Topic | URL |
|---|---|
| Hosting plan comparison (Consumption vs. Flex vs. Premium vs. Dedicated) | https://learn.microsoft.com/en-us/azure/azure-functions/functions-scale |
| Event-driven scaling | https://learn.microsoft.com/en-us/azure/azure-functions/event-driven-scaling |
| Set scale limits (`functionAppScaleLimit`) | https://learn.microsoft.com/en-us/azure/azure-functions/event-driven-scaling#limit-scale-out |
| Cold start mitigation | https://learn.microsoft.com/en-us/azure/azure-functions/functions-scale#cold-start-behavior |

---

## Deployment & Infrastructure

| Topic | URL |
|---|---|
| Deployment best practices | https://learn.microsoft.com/en-us/azure/azure-functions/functions-deployment-technologies |
| Deployment slots (blue/green) | https://learn.microsoft.com/en-us/azure/azure-functions/functions-deployment-slots |
| Infrastructure as Code with Bicep | https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/overview |
| GitHub Actions for Azure Functions | https://learn.microsoft.com/en-us/azure/azure-functions/functions-how-to-github-actions |
| Federated identity / OIDC for GitHub Actions | https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect |
