# Architecture Documentation Template

## 1. System Overview
**System Name:** [Client System Name]
**Purpose:** [Brief description of what the system does]
**Users:** [Who uses it - internal/external/both]

## 2. Components List
List each component with:
- **Name:** Component name
- **Type:** (Frontend/Backend/Database/API/Service/etc.)
- **Technology:** (React/Node.js/PostgreSQL/etc.)
- **Purpose:** What it does
- **Location:** (URL/Server/Cloud service)

### Example:
```
- Name: Customer Portal
  Type: Frontend
  Technology: React + Material-UI
  Purpose: Customer self-service interface
  Location: https://portal.example.com

- Name: Order API
  Type: Backend API
  Technology: Node.js Express
  Purpose: Handles order processing
  Location: AWS Lambda (us-east-1)
```

## 3. Data Flow / Connections
Describe how components connect:
```
[Component A] --[connection type]--> [Component B]
```

### Example:
```
Customer Portal --[HTTPS/REST]--> API Gateway
API Gateway --[authorizes with]--> Auth0
API Gateway --[forwards to]--> Order API
Order API --[reads/writes]--> PostgreSQL Database
Order API --[publishes events]--> Kafka
Order API --[sends emails via]--> SendGrid
```

## 4. Infrastructure Details
- **Cloud Provider:** AWS/Azure/GCP/On-premise
- **Regions:** Where components are deployed
- **Key Services Used:** (S3, RDS, Lambda, etc.)

## 5. Security & Authentication
- **Auth Method:** OAuth/SAML/JWT/etc.
- **Auth Provider:** Cognito/Auth0/Okta/etc.
- **API Security:** API keys/OAuth/etc.

## 6. External Integrations
List any third-party services:
- Payment: Stripe/PayPal
- Email: SendGrid/SES
- Analytics: Google Analytics/Mixpanel
- Monitoring: DataDog/New Relic

## 7. Data Storage
For each data store:
- **Name:** Database/Storage name
- **Type:** SQL/NoSQL/Object/File
- **Technology:** PostgreSQL/MongoDB/S3/etc.
- **Purpose:** What data it stores
- **Backup:** How it's backed up

## 8. Key Identifiers (Optional)
Any specific IDs, ARNs, or resource names:
```
- Cognito Pool: us-east-1_ABC123
- S3 Buckets: prod-data-bucket, prod-logs-bucket
- API Domain: api.example.com
```

## 9. Visual Sketch (Optional)
Even a rough ASCII diagram helps:
```
[Users] --> [CDN] --> [Load Balancer]
                           |
                           v
                    [Web Servers]
                           |
                           v
                      [API Layer]
                      /    |    \
                     v     v     v
                  [DB] [Cache] [Queue]
```

## Quick Example - E-commerce Platform:
```
Components:
- React SPA (https://shop.example.com)
- CloudFront CDN
- API Gateway (https://api.example.com)
- Order Service (Lambda)
- Inventory Service (Lambda)
- PostgreSQL RDS (orders, products)
- Redis ElastiCache (session cache)
- S3 (product images)
- Stripe (payments)
- SendGrid (emails)

Flow:
React SPA --> CloudFront --> API Gateway --> Lambda Functions
Lambda Functions --> RDS PostgreSQL
Lambda Functions --> Redis Cache
Lambda Functions --> Stripe API
Lambda Functions --> SendGrid API
```