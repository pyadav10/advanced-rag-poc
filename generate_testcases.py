"""
generate_testcases.py
─────────────────────
Generates 5000 realistic VWO test cases in Jira format and saves
them as testcases_vwo.csv in the data/ folder.

Run:  python generate_testcases.py
"""

import os
import csv
import random

OUTPUT_DIR  = "./data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "testcases_vwo.csv")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Columns ───────────────────────────────────────────────
HEADERS = [
    "Issue_ID", "Issue_Type", "Summary", "Description",
    "Priority", "Status", "Component", "Labels",
    "Preconditions", "Test_Steps", "Expected_Result",
    "Actual_Result", "Test_Data"
]

# ── Test case templates per area ─────────────────────────
AREAS = {
    "Login & Authentication": {
        "component": "Authentication",
        "labels": "login,auth,security",
        "cases": [
            {
                "summary": "Verify login with valid credentials",
                "steps": "1. Navigate to app.vwo.com/login\n2. Enter valid email {email}\n3. Enter valid password {password}\n4. Click 'Sign In' button",
                "expected": "User is redirected to VWO dashboard. Welcome message displayed.",
                "data": "email: test@vwo.com, password: Test@1234",
                "priority": "High"
            },
            {
                "summary": "Verify login with invalid password",
                "steps": "1. Navigate to app.vwo.com/login\n2. Enter valid email {email}\n3. Enter wrong password 'wrongpass'\n4. Click 'Sign In'",
                "expected": "Error message 'Invalid credentials' shown. User stays on login page.",
                "data": "email: test@vwo.com, password: wrongpass",
                "priority": "High"
            },
            {
                "summary": "Verify login with unregistered email",
                "steps": "1. Go to app.vwo.com/login\n2. Enter unregistered email 'notexist@vwo.com'\n3. Enter any password\n4. Click 'Sign In'",
                "expected": "Error: 'No account found with this email'. Login blocked.",
                "data": "email: notexist@vwo.com, password: Test@1234",
                "priority": "High"
            },
            {
                "summary": "Verify 'Forgot Password' link is visible and functional",
                "steps": "1. Navigate to login page\n2. Click 'Forgot Password' link\n3. Enter registered email\n4. Click 'Send Reset Link'",
                "expected": "Password reset email sent. Confirmation message displayed.",
                "data": "email: test@vwo.com",
                "priority": "Medium"
            },
            {
                "summary": "Verify Google SSO login",
                "steps": "1. Go to app.vwo.com/login\n2. Click 'Sign in with Google'\n3. Select Google account\n4. Authorize permissions",
                "expected": "User logged in via Google OAuth. Redirected to VWO dashboard.",
                "data": "Google account: qa@company.com",
                "priority": "High"
            },
            {
                "summary": "Verify login session timeout after inactivity",
                "steps": "1. Login to VWO\n2. Leave session idle for {timeout} minutes\n3. Attempt to navigate to another page",
                "expected": "Session expired. User redirected to login page with message 'Session expired'.",
                "data": "Timeout: 30 minutes",
                "priority": "High"
            },
            {
                "summary": "Verify MFA via TOTP authenticator",
                "steps": "1. Login with valid credentials\n2. When prompted, open authenticator app\n3. Enter 6-digit TOTP code\n4. Click Verify",
                "expected": "TOTP verified. User lands on dashboard.",
                "data": "TOTP code from Google Authenticator",
                "priority": "High"
            },
            {
                "summary": "Verify MFA with expired OTP",
                "steps": "1. Login with credentials\n2. Wait for OTP to expire (>30 seconds)\n3. Enter expired OTP",
                "expected": "Error: 'OTP has expired. Please request a new one.'",
                "data": "Expired TOTP code",
                "priority": "Medium"
            },
            {
                "summary": "Verify account lockout after 5 failed attempts",
                "steps": "1. Enter wrong password 5 times consecutively\n2. Observe account behavior",
                "expected": "Account locked for 15 minutes. Message: 'Too many failed attempts.'",
                "data": "email: test@vwo.com, wrong passwords x5",
                "priority": "High"
            },
            {
                "summary": "Verify 'Remember Me' checkbox on login",
                "steps": "1. Go to login page\n2. Enter credentials\n3. Check 'Remember Me'\n4. Login and close browser\n5. Reopen browser and navigate to app.vwo.com",
                "expected": "User is automatically logged in without re-entering credentials.",
                "data": "email: test@vwo.com",
                "priority": "Medium"
            },
        ]
    },
    "Dashboard": {
        "component": "Dashboard",
        "labels": "dashboard,ui,widgets",
        "cases": [
            {
                "summary": "Verify dashboard loads within 3 seconds",
                "steps": "1. Login to VWO\n2. Start timer\n3. Observe dashboard load completion",
                "expected": "Dashboard fully loads in under 3 seconds on standard connection.",
                "data": "Network: 50 Mbps, Browser: Chrome latest",
                "priority": "High"
            },
            {
                "summary": "Verify campaign summary widget displays correct data",
                "steps": "1. Login to VWO\n2. Navigate to dashboard\n3. Check 'Campaign Summary' widget",
                "expected": "Widget shows correct count of active, paused, and completed campaigns.",
                "data": "Pre-configured account with 5 active campaigns",
                "priority": "High"
            },
            {
                "summary": "Verify date range filter on dashboard",
                "steps": "1. Open dashboard\n2. Click date range picker\n3. Select custom range: last 30 days\n4. Apply filter",
                "expected": "All dashboard widgets refresh and show data for selected range.",
                "data": "Date range: last 30 days",
                "priority": "Medium"
            },
            {
                "summary": "Verify dashboard is responsive on mobile viewport",
                "steps": "1. Open app.vwo.com on mobile (375px)\n2. Login\n3. Observe dashboard layout",
                "expected": "Dashboard adapts to mobile view. Widgets stack vertically. No horizontal scroll.",
                "data": "Viewport: 375x812 (iPhone 14)",
                "priority": "Medium"
            },
            {
                "summary": "Verify quick action buttons on dashboard",
                "steps": "1. Login to VWO\n2. On dashboard, click 'Create Test' quick action\n3. Observe behavior",
                "expected": "Test creation wizard opens.",
                "data": "N/A",
                "priority": "Medium"
            },
            {
                "summary": "Verify notification bell shows unread count",
                "steps": "1. Login to VWO\n2. Observe notification bell icon in header",
                "expected": "Bell shows numeric badge with count of unread notifications.",
                "data": "Account with 3 unread notifications",
                "priority": "Low"
            },
            {
                "summary": "Verify dashboard recent activity feed",
                "steps": "1. Login\n2. Scroll to 'Recent Activity' section\n3. Verify entries",
                "expected": "Feed shows last 10 actions with timestamps, user names, and action descriptions.",
                "data": "Account with recent activity",
                "priority": "Low"
            },
            {
                "summary": "Verify conversion rate widget chart renders correctly",
                "steps": "1. Login\n2. Go to dashboard\n3. Find conversion rate chart widget\n4. Hover over data points",
                "expected": "Line chart renders. Hover tooltips show date and conversion % values.",
                "data": "Account with 30-day conversion data",
                "priority": "Medium"
            },
        ]
    },
    "A/B Testing": {
        "component": "AB Testing",
        "labels": "ab-test,campaigns,experiment",
        "cases": [
            {
                "summary": "Verify creation of A/B test with URL targeting",
                "steps": "1. Click 'Create' > 'A/B Test'\n2. Enter test name 'Homepage CTA Test'\n3. Set URL: app.vwo.com/home\n4. Configure variation\n5. Set goals\n6. Save and run",
                "expected": "A/B test created and running. Appears in campaign list with 'Running' status.",
                "data": "URL: https://testsite.com, Variation: Change CTA color",
                "priority": "High"
            },
            {
                "summary": "Verify traffic split configuration for A/B test",
                "steps": "1. Create new A/B test\n2. Go to traffic allocation step\n3. Set Control: 50%, Variation: 50%\n4. Save",
                "expected": "Traffic split saved as 50/50. Visual indicator updated.",
                "data": "Split: 50% control, 50% variation",
                "priority": "High"
            },
            {
                "summary": "Verify adding multiple variations to A/B test",
                "steps": "1. Open test creation\n2. Add variation B and variation C\n3. Set traffic 34/33/33\n4. Save",
                "expected": "Three variations saved. Traffic totals 100%. Test runs correctly.",
                "data": "3 variations, split: 34/33/33",
                "priority": "Medium"
            },
            {
                "summary": "Verify pausing a running A/B test",
                "steps": "1. Open a running A/B test\n2. Click 'Pause' button\n3. Confirm dialog",
                "expected": "Test status changes to 'Paused'. Variations stop serving.",
                "data": "Running test: 'Homepage CTA Test'",
                "priority": "High"
            },
            {
                "summary": "Verify stopping an A/B test",
                "steps": "1. Open a running test\n2. Click 'Stop'\n3. Select winner variation\n4. Confirm",
                "expected": "Test stops. Winner variation noted. Status: 'Completed'.",
                "data": "Running test with 2 variations",
                "priority": "High"
            },
            {
                "summary": "Verify test statistics update in real time",
                "steps": "1. Open a running A/B test\n2. Observe statistics panel\n3. Wait 60 seconds\n4. Refresh stats",
                "expected": "Visitor count, conversions, and conversion rate update with latest data.",
                "data": "Test with live traffic",
                "priority": "Medium"
            },
            {
                "summary": "Verify confidence level indicator in test results",
                "steps": "1. Open completed A/B test\n2. View results section\n3. Check confidence level indicator",
                "expected": "Confidence percentage displayed. Visual indicator shows statistical significance.",
                "data": "Test with sufficient sample size",
                "priority": "Medium"
            },
            {
                "summary": "Verify goal configuration for A/B test",
                "steps": "1. Create A/B test\n2. Go to Goals step\n3. Add goal: 'Click on CTA button'\n4. Configure goal URL\n5. Save",
                "expected": "Goal saved. Test tracks clicks on CTA as conversion events.",
                "data": "Goal type: Click, Element: #cta-btn",
                "priority": "High"
            },
        ]
    },
    "Heatmaps": {
        "component": "Heatmaps",
        "labels": "heatmap,analytics,recordings",
        "cases": [
            {
                "summary": "Verify heatmap loads for a configured page",
                "steps": "1. Go to Heatmaps section\n2. Select a configured page\n3. Click 'View Heatmap'",
                "expected": "Click heatmap renders with color gradient overlay on page screenshot.",
                "data": "Page: /home, Min clicks: 100",
                "priority": "High"
            },
            {
                "summary": "Verify scroll heatmap shows fold position",
                "steps": "1. Open heatmap for a page\n2. Switch to 'Scroll' view",
                "expected": "Scroll heatmap shows percentage of users who scrolled to each position. Fold line visible.",
                "data": "Page: /pricing",
                "priority": "Medium"
            },
            {
                "summary": "Verify move heatmap tracks cursor movement",
                "steps": "1. Open heatmap\n2. Toggle to 'Move' view",
                "expected": "Move heatmap shows areas where users hovered most. Hot zones highlighted in red.",
                "data": "Page with move data",
                "priority": "Low"
            },
            {
                "summary": "Verify heatmap device filter (desktop/mobile/tablet)",
                "steps": "1. Open heatmap\n2. Click device filter dropdown\n3. Select 'Mobile'",
                "expected": "Heatmap updates to show only mobile user data. Page screenshot changes to mobile viewport.",
                "data": "Mixed device traffic data",
                "priority": "Medium"
            },
            {
                "summary": "Verify heatmap date range filter",
                "steps": "1. Open heatmap\n2. Change date range to 'Last 7 days'\n3. Apply",
                "expected": "Heatmap refreshes showing data only for selected date range.",
                "data": "Date range: last 7 days",
                "priority": "Medium"
            },
        ]
    },
    "Session Recordings": {
        "component": "Session Recordings",
        "labels": "recordings,sessions,replay",
        "cases": [
            {
                "summary": "Verify session recording playback",
                "steps": "1. Navigate to Session Recordings\n2. Click on a recording\n3. Press Play",
                "expected": "Session replays accurately showing mouse movement, clicks, and scrolls.",
                "data": "Recording with 5+ minute session",
                "priority": "High"
            },
            {
                "summary": "Verify session recording speed controls",
                "steps": "1. Open a recording\n2. Click speed control\n3. Select 2x speed",
                "expected": "Recording plays at 2x speed. Speed indicator updates.",
                "data": "Recording: 3 min session",
                "priority": "Medium"
            },
            {
                "summary": "Verify filter recordings by page URL",
                "steps": "1. Go to Recordings\n2. Click filter\n3. Enter URL contains '/pricing'\n4. Apply",
                "expected": "Only recordings where user visited /pricing page are shown.",
                "data": "Filter: URL contains /pricing",
                "priority": "Medium"
            },
        ]
    },
    "Reports & Analytics": {
        "component": "Reports",
        "labels": "reports,analytics,export",
        "cases": [
            {
                "summary": "Verify test report export to CSV",
                "steps": "1. Open a completed test\n2. Go to Reports tab\n3. Click 'Export' > 'CSV'\n4. Download file",
                "expected": "CSV file downloaded with test data: visitors, conversions, rates per variation.",
                "data": "Completed test with data",
                "priority": "Medium"
            },
            {
                "summary": "Verify test report export to PDF",
                "steps": "1. Open test results\n2. Click 'Export' > 'PDF'\n3. Wait for generation",
                "expected": "PDF report generated with charts, summary, and variation comparison.",
                "data": "Test with 30+ days data",
                "priority": "Medium"
            },
            {
                "summary": "Verify revenue impact metric in test report",
                "steps": "1. Open A/B test with revenue goal configured\n2. Navigate to Reports\n3. Check revenue impact row",
                "expected": "Revenue impact shows estimated lift per variation with confidence interval.",
                "data": "Test with revenue goal: $",
                "priority": "High"
            },
        ]
    },
    "Navigation": {
        "component": "Navigation",
        "labels": "navigation,sidebar,ui",
        "cases": [
            {
                "summary": "Verify sidebar collapses on click",
                "steps": "1. Login to VWO\n2. Click the sidebar collapse/expand icon",
                "expected": "Sidebar collapses to icon-only view. Main content area expands.",
                "data": "N/A",
                "priority": "Low"
            },
            {
                "summary": "Verify breadcrumb navigation is correct",
                "steps": "1. Navigate to a campaign\n2. Open a variation\n3. Check breadcrumb at top",
                "expected": "Breadcrumb shows: Dashboard > Campaigns > [Campaign Name] > Variations",
                "data": "Campaign: 'Homepage Test'",
                "priority": "Low"
            },
            {
                "summary": "Verify global search finds campaigns by name",
                "steps": "1. Click search icon in header\n2. Type campaign name 'Homepage CTA'\n3. Observe results",
                "expected": "Search results show matching campaigns, tests, and pages.",
                "data": "Search query: 'Homepage CTA'",
                "priority": "Medium"
            },
        ]
    },
    "Settings & Profile": {
        "component": "Settings",
        "labels": "settings,profile,account",
        "cases": [
            {
                "summary": "Verify user can update display name",
                "steps": "1. Go to Profile Settings\n2. Click Edit on Display Name\n3. Enter new name 'QA Tester'\n4. Save",
                "expected": "Display name updated. Header shows new name. Success toast shown.",
                "data": "New name: QA Tester",
                "priority": "Low"
            },
            {
                "summary": "Verify timezone setting updates dashboard data",
                "steps": "1. Go to Settings > Account\n2. Change timezone to 'America/New_York'\n3. Save\n4. Check dashboard timestamps",
                "expected": "All timestamps in dashboard reflect the new timezone.",
                "data": "Timezone: America/New_York",
                "priority": "Medium"
            },
            {
                "summary": "Verify password change with correct current password",
                "steps": "1. Go to Settings > Security\n2. Enter current password\n3. Enter new password 'NewPass@123'\n4. Confirm new password\n5. Save",
                "expected": "Password updated. Success message shown. Old password no longer works.",
                "data": "Current: Test@1234, New: NewPass@123",
                "priority": "High"
            },
        ]
    },
    "API & Integrations": {
        "component": "Integrations",
        "labels": "api,integration,webhook",
        "cases": [
            {
                "summary": "Verify API key generation",
                "steps": "1. Go to Settings > API\n2. Click 'Generate API Key'\n3. Copy key",
                "expected": "Unique API key generated and displayed. Option to copy or revoke.",
                "data": "N/A",
                "priority": "Medium"
            },
            {
                "summary": "Verify Google Analytics integration setup",
                "steps": "1. Go to Integrations\n2. Select Google Analytics\n3. Enter GA Tracking ID\n4. Connect",
                "expected": "GA integration active. VWO experiment data flows to GA.",
                "data": "GA Tracking ID: UA-XXXXXX-X",
                "priority": "High"
            },
            {
                "summary": "Verify webhook fires on test completion",
                "steps": "1. Configure webhook endpoint\n2. Stop a running test\n3. Check webhook receiver",
                "expected": "POST request sent to webhook URL with test completion payload.",
                "data": "Webhook URL: https://requestbin.com/test",
                "priority": "Medium"
            },
        ]
    },
    "Performance": {
        "component": "Performance",
        "labels": "performance,load,speed",
        "cases": [
            {
                "summary": "Verify campaign list page loads under 2 seconds",
                "steps": "1. Login\n2. Navigate to Campaigns\n3. Measure page load time",
                "expected": "Campaign list renders in under 2 seconds with 50+ campaigns.",
                "data": "Account with 50+ campaigns",
                "priority": "High"
            },
            {
                "summary": "Verify chart data loads asynchronously",
                "steps": "1. Open a test report\n2. Observe loading behavior",
                "expected": "Page skeleton shown first. Charts load asynchronously without blocking UI.",
                "data": "Test with 90 days data",
                "priority": "Medium"
            },
        ]
    },
    "Security": {
        "component": "Security",
        "labels": "security,xss,csrf",
        "cases": [
            {
                "summary": "Verify XSS protection in test name input",
                "steps": "1. Create new A/B test\n2. Enter test name: <script>alert('xss')</script>\n3. Save",
                "expected": "Script tag sanitized. Name saved as plain text. No JS executed.",
                "data": "Input: <script>alert('xss')</script>",
                "priority": "High"
            },
            {
                "summary": "Verify CSRF token present in form submissions",
                "steps": "1. Login\n2. Submit any form\n3. Inspect network request headers",
                "expected": "CSRF token present in request headers or form payload.",
                "data": "Chrome DevTools Network tab",
                "priority": "High"
            },
            {
                "summary": "Verify SQL injection protection in search",
                "steps": "1. Go to global search\n2. Enter: ' OR 1=1 --\n3. Submit",
                "expected": "No database error. Results are empty or show 'No results found'.",
                "data": "Search input: ' OR 1=1 --",
                "priority": "High"
            },
        ]
    },
    "Accessibility": {
        "component": "Accessibility",
        "labels": "accessibility,aria,a11y",
        "cases": [
            {
                "summary": "Verify login form is keyboard navigable",
                "steps": "1. Open login page\n2. Use Tab key to navigate through fields\n3. Use Enter to submit",
                "expected": "Focus moves through Email > Password > Login button. Form submits on Enter.",
                "data": "N/A",
                "priority": "Medium"
            },
            {
                "summary": "Verify ARIA labels on interactive elements",
                "steps": "1. Open dashboard\n2. Use screen reader\n3. Navigate through buttons and links",
                "expected": "All buttons, inputs, and links have descriptive ARIA labels.",
                "data": "Screen reader: NVDA",
                "priority": "Medium"
            },
        ]
    },
}

def generate_testcases(total=5000):
    rows = []
    counter = 1

    # Flatten all base cases
    base_cases = []
    for area_name, area_data in AREAS.items():
        for case in area_data["cases"]:
            base_cases.append({
                "area": area_name,
                "component": area_data["component"],
                "labels": area_data["labels"],
                **case
            })

    priorities = ["High", "Medium", "Low"]
    priority_weights = [0.35, 0.45, 0.20]

    # Variation suffixes to diversify repeated cases
    browsers   = ["Chrome 124", "Firefox 126", "Safari 17", "Edge 124", "Chrome Mobile"]
    oses       = ["Windows 11", "macOS Sonoma", "Ubuntu 22.04", "iOS 17", "Android 14"]
    envs       = ["Production", "Staging", "QA Environment", "Pre-prod"]
    user_roles = ["Admin", "Editor", "Viewer", "Account Owner", "Team Member"]

    while len(rows) < total:
        base = random.choice(base_cases)
        idx  = counter
        pid  = f"VWO-TC-{idx:04d}"

        browser = random.choice(browsers)
        os_name = random.choice(oses)
        env     = random.choice(envs)
        role    = random.choice(user_roles)

        # Vary priority slightly
        priority = random.choices(priorities, weights=priority_weights, k=1)[0]

        # Add variation suffix to summary
        variant_suffix = f" [{browser} / {env}]" if idx > len(base_cases) else ""
        summary = base["summary"] + (variant_suffix if random.random() > 0.5 else "")

        preconditions = (
            f"1. VWO account is active ({role} role)\n"
            f"2. Browser: {browser}, OS: {os_name}\n"
            f"3. Environment: {env}\n"
            f"4. User is logged in to app.vwo.com"
        )

        row = {
            "Issue_ID":       pid,
            "Issue_Type":     "Test",
            "Summary":        summary[:200],
            "Description":    f"Test covers: {base['area']}. {base['summary']}. Validates correct system behavior under {env} environment.",
            "Priority":       priority,
            "Status":         "To Do",
            "Component":      base["component"],
            "Labels":         base["labels"],
            "Preconditions":  preconditions,
            "Test_Steps":     base["steps"],
            "Expected_Result": base["expected"],
            "Actual_Result":  "",
            "Test_Data":      base["data"],
        }
        rows.append(row)
        counter += 1

    return rows[:total]


def main():
    print(f"Generating 5000 VWO test cases…")
    rows = generate_testcases(5000)

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅  Saved {len(rows)} test cases → {os.path.abspath(OUTPUT_FILE)}")


if __name__ == "__main__":
    main()
