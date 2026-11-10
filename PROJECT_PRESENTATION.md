# URL Shortener Project

## 1. Project Overview
This project is a URL shortener service built to convert long web links into short, easy-to-share URLs. It is designed for speed, security, and tracking. Users can create custom short links, manage them, and view traffic statistics for each shortened URL.

The system is implemented using FastAPI, PostgreSQL, Redis, and ClickHouse. It follows a practical backend architecture used in real-world web applications.

## 2. Problem It Solves
Long URLs are difficult to share in messages, social media, emails, and presentations. A URL shortener solves this problem by creating compact links that are easier to remember and easier to distribute.

In addition to shortening links, the project also provides:
- security checks for unsafe destinations
- click tracking and analytics
- expiry dates and click limits
- API-based link management

## 3. Key Features
- Create short links from long URLs
- Use custom slug names like `my-event` or `promo2026`
- Set expiration dates for links
- Limit the number of clicks allowed
- Disable or update old links
- Protect against malicious URLs with validation and safe-browsing checks
- Track user traffic with country, city, device information, and referrer data
- Apply rate limiting and API key authentication for secure access

## 4. Technology Stack
- Python with FastAPI for the API and redirect service
- PostgreSQL for persistent link metadata
- Redis for caching and click counting
- ClickHouse for analytics and reporting
- Docker Compose for running the full environment

## 5. System Design
The project has three main parts:

1. API Layer
   - Handles creating, updating, deleting, and listing links
   - Validates user input and enforces rules

2. Redirect Layer
   - Takes a short code like `/abc1234`
   - Checks whether the link is valid, active, and not expired
   - Redirects the user to the original destination

3. Analytics Layer
   - Records click events
   - Stores visitor metadata such as country, city, referrer, and user agent
   - Provides statistics for each short link

## 6. How the Application Works
1. A user sends a long URL to the API.
2. The system validates the URL and checks if it is safe.
3. A unique short code is generated and stored in the database.
4. The user receives a short link.
5. When someone clicks the short URL, it redirects to the original page.
6. The system records the click for analytics and monitoring.

## 7. Why This Project Is Useful
This project demonstrates how real web services combine backend logic, databases, caching, and tracking in a single application. It is useful for:
- marketing campaigns
- academic project demos
- link sharing in communities
- analytics-driven digital campaigns

## 8. Project Outcome
The project is a complete backend service for link shortening with strong security and data tracking. It shows practical web development skills, database design, API integration, and system architecture.

## 9. Short Class Summary
This project is a URL shortener service that helps users shorten long links while also tracking usage statistics. It uses FastAPI, PostgreSQL, Redis, and ClickHouse to create a scalable and secure application. The project highlights backend development, database management, caching, and analytics in a simple but real-world system.

## 10. Run the Project
To run the project locally with Docker:

```bash
docker compose up --build
```

Then open the application in a browser or use the API endpoints on port 8000.

---
Prepared for class presentation.
