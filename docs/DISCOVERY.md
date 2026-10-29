# Phase 1 — Westminster source discovery

Status: live extraction remains unverified. On 2026-10-29 after publication, the current official guidance page returned 200 and confirmed the Idox portal link. Portal robots and advanced search returned HTTP 503 with an upstream connection-termination message from the proxy. The current environment reports unrestricted enforced HTTP policy. This observation does not establish that the council is down, that the policy blocks access, or that Codespaces has the same connectivity. No live applications were collected. See VERIFICATION.md.

Candidate sources (verify from council site before production):

- Council guidance: https://www.westminster.gov.uk/planning-building-control-and-environmental-regulations/planning-applications/search-and-comment-planning-applications-and-register-email-notifications
- Idox Public Access: https://idoxpa.westminster.gov.uk/online-applications/
- Robots: https://idoxpa.westminster.gov.uk/robots.txt

## Required investigation when access is enabled

1. Follow the current council search link; verify the portal host and system.
2. Read current council copyright, website terms, planning data reuse/privacy policy and robots.txt. Record source URL, date, intended use and restrictions. Do not infer Westminster rights from the Essex statements in the PDF.
3. Check for an official API, downloadable register, open-data feed or licensed bulk data. No assertion is made here that no API exists. Prefer a documented permitted structured feed over scraping.
4. Verify advanced-search form action, hidden tokens, received/decision date fields, result pagination, detail tabs and exact field labels. The adapter is based on conventional Idox HTML, not live captured Westminster fixtures.
5. Check one known result against the portal manually, then a one-week search. Verify dates, counts, empty results and pagination before a four-week extraction.
6. If detail information lives in another tab, add an adapter only after inspecting the public HTML. Never collect documents or bypass a login, challenge, CAPTCHA or access refusal.

## Lifecycle

Submitted/received means filed; validated means the council has accepted the application for processing, not granted permission; decided means an outcome exists and may be refusal or withdrawal. Explicit grant/approval decisions provide a stronger lead signal. Listed-building consents, conditions and multiple applications at one site are not interchangeable with permission to start construction. The digest excludes refusals and condition discharges conservatively; further live decision vocabulary validation is required.

Only published metadata should be collected. Minimise applicant data, review retention and contact policy, and provide council attribution and links. Research access is not evidence of permission to resell contact data.
