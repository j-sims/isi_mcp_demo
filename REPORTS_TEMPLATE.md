# PowerScale MCP Report Templates

## Overview

This file contains reusable HTML templates for generating reports from PowerScale MCP server data. Each template includes:
- **Purpose**: What the report communicates
- **Data Sources**: Which MCP tools to query
- **File Naming**: Standard naming convention with report type and timestamp
- **Output Location**: Save to current working directory (`./`)
- **Template Structure**: HTML format ready to render in browser
- **Customization Notes**: How to modify for your needs

## File Naming Convention

Reports should be saved with the following naming pattern:

```
Single cluster:     powerscale_report_[TYPE]_[YYYYMMDD]_[HHMMSS].html
Multiple clusters:  powerscale_report_[TYPE]_multi_[YYYYMMDD]_[HHMMSS].html
```

**Single Cluster Examples**:
- `powerscale_report_health_20260320_143022.html` — Single cluster health report
- `powerscale_report_quota_20260320_093015.html` — Single cluster quota report

**Multi-Cluster Examples**:
- `powerscale_report_health_multi_20260320_143022.html` — Multi-cluster health report with tabs
- `powerscale_report_quota_multi_20260320_093015.html` — Multi-cluster quota report with tabs

**Report type codes**:
- `health` — Cluster Health & Status Report
- `quota` — Quota & User Management Report
- `dataprotection` — Data Protection & Snapshots Report
- `fileservices` — File Services Activity Report
- `capacity` — Capacity Planning & Performance Report
- `compliance` — Compliance & Audit Report

**Multi-Cluster Feature**: All templates support tabbed navigation for comparing data across multiple clusters. Each cluster's data is isolated in its own tab.

---

## 1. Cluster Health & Status Report

**Purpose**: Executive summary of cluster health, capacity, and operational status

**Data Sources**:
- `powerscale_health_check` — Overall cluster health
- `powerscale_capacity_get` — Storage capacity and utilization
- `powerscale_snapshots_get` — Snapshot statistics
- `powerscale_quota_get` — Quota usage

**File Name**: `powerscale_report_health_[YYYYMMDD]_[HHMMSS].html` (single) or `powerscale_report_health_multi_[YYYYMMDD]_[HHMMSS].html` (multi)

**Template**:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PowerScale Cluster Health Report</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'segoe ui', helvetica, arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; color: #454545; }
        .header { background: linear-gradient(135deg, #0076CE 0%, #0059a3 100%); color: white; padding: 30px; border-radius: 8px; margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0, 118, 206, 0.15); }
        .header h1 { margin: 0 0 15px 0; font-size: 28px; font-weight: 600; }
        .header p { margin: 8px 0; font-size: 14px; opacity: 0.95; }
        .tabs { display: flex; gap: 8px; margin-bottom: 20px; border-bottom: 2px solid #e0e0e0; flex-wrap: wrap; }
        .tab-button { background-color: white; border: 2px solid #e0e0e0; padding: 12px 20px; cursor: pointer; border-radius: 6px 6px 0 0; transition: all 0.3s ease; font-weight: 500; color: #454545; }
        .tab-button:hover { background-color: #f0f0f0; border-color: #0076CE; }
        .tab-button.active { background-color: #0076CE; color: white; border-color: #0076CE; box-shadow: 0 -2px 8px rgba(0, 118, 206, 0.1); }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .section { background-color: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; border-left: 4px solid #0076CE; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08); }
        .section h2 { color: #0076CE; margin-top: 0; margin-bottom: 15px; font-size: 20px; font-weight: 600; }
        .section h3 { color: #244739; font-size: 16px; font-weight: 600; margin-top: 15px; }
        .summary { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 15px; }
        .summary-item { background: linear-gradient(135deg, #f8f9fa 0%, #efefef 100%); padding: 15px; border-radius: 6px; border-left: 3px solid #0076CE; }
        .summary-item .label { font-size: 12px; color: #666; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
        .summary-item .value { font-size: 24px; font-weight: 600; color: #0076CE; margin-top: 8px; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 14px; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #e0e0e0; }
        th { background-color: #f0f0f0; font-weight: 600; color: #454545; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px; }
        tr:hover { background-color: #f8f9fa; }
        td { color: #666; }
        .healthy { color: #7ab800; font-weight: 600; }
        .warning { color: #f2af00; font-weight: 600; }
        .critical { color: #dc5034; font-weight: 600; }
        .recommendations { background: linear-gradient(135deg, #e8f4ff 0%, #f0f9ff 100%); padding: 15px; border-radius: 6px; border-left: 3px solid #0076CE; margin-top: 10px; }
        .recommendations p { margin: 0; color: #454545; font-size: 14px; line-height: 1.6; }
        .footer { text-align: center; color: #999; font-size: 13px; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e0e0e0; }
        .footer a { color: #0076CE; text-decoration: none; }
        .cluster-info { background: linear-gradient(135deg, #f0f9ff 0%, #e8f4ff 100%); padding: 12px 15px; border-radius: 6px; margin-bottom: 15px; border-left: 3px solid #0076CE; font-size: 14px; color: #454545; }
    </style>
    <script>
        function openTab(event, tabName) {
            var i, tabcontent, tabbuttons;
            tabcontent = document.getElementsByClassName("tab-content");
            for (i = 0; i < tabcontent.length; i++) {
                tabcontent[i].classList.remove("active");
            }
            tabbuttons = document.getElementsByClassName("tab-button");
            for (i = 0; i < tabbuttons.length; i++) {
                tabbuttons[i].classList.remove("active");
            }
            document.getElementById(tabName).classList.add("active");
            event.currentTarget.classList.add("active");
        }
    </script>
</head>
<body>
    <div class="header">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 16px;">
                <svg width="52" height="36" viewBox="0 0 52 36" xmlns="http://www.w3.org/2000/svg">
                    <rect x="0"  y="0" width="10" height="36" fill="white" rx="2"/>
                    <rect x="14" y="0" width="10" height="36" fill="white" rx="2"/>
                    <rect x="28" y="0" width="10" height="36" fill="white" rx="2"/>
                    <rect x="42" y="0" width="10" height="36" fill="white" rx="2"/>
                </svg>
                <div style="line-height: 1.2;">
                    <div style="font-size: 22px; font-weight: 700; letter-spacing: 0.5px;">Dell Technologies</div>
                    <div style="font-size: 14px; font-weight: 400; opacity: 0.85; letter-spacing: 1px; text-transform: uppercase;">PowerScale</div>
                </div>
            </div>
        </div>
        <h1>PowerScale Cluster Health Report</h1>
        <p><strong>Generated:</strong> [DATE_TIME]</p>
        <p><strong>Report Period:</strong> [START_DATE] to [END_DATE]</p>
    </div>

    <!-- TAB NAVIGATION -->
    <div class="tabs">
        <button class="tab-button active" onclick="openTab(event, 'cluster-1')">Cluster 1: [CLUSTER_NAME_1]</button>
        <button class="tab-button" onclick="openTab(event, 'cluster-2')">Cluster 2: [CLUSTER_NAME_2]</button>
        <!-- DUPLICATE TAB BUTTONS FOR ADDITIONAL CLUSTERS -->
    </div>

    <!-- CLUSTER 1 TAB CONTENT -->
    <div id="cluster-1" class="tab-content active">
        <div class="cluster-info">
            <strong>Cluster:</strong> [CLUSTER_NAME_1] | <strong>Host:</strong> [CLUSTER_HOST_1]
        </div>

        <div class="section">
            <h2>Executive Summary</h2>
            <div class="summary">
                <div class="summary-item">
                    <div class="label">Overall Health Status</div>
                    <div class="value healthy">[HEALTHY/WARNING/CRITICAL]</div>
                </div>
                <div class="summary-item">
                    <div class="label">Uptime</div>
                    <div class="value">[DAYS] days</div>
                </div>
                <div class="summary-item">
                    <div class="label">Storage Utilization</div>
                    <div class="value">[PERCENT]%</div>
                </div>
                <div class="summary-item">
                    <div class="label">Active Users</div>
                    <div class="value">[COUNT]</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Cluster Status</h2>
            <h3>Health Metrics</h3>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Status</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Quorum</td>
                        <td class="healthy">✓</td>
                        <td>All nodes participating</td>
                    </tr>
                    <tr>
                        <td>Service Lights</td>
                        <td class="healthy">✓</td>
                        <td>No hardware alerts</td>
                    </tr>
                    <tr>
                        <td>Critical Events</td>
                        <td class="healthy">✓</td>
                        <td>0 unresolved critical alerts</td>
                    </tr>
                    <tr>
                        <td>Network Connectivity</td>
                        <td class="healthy">✓</td>
                        <td>All gateways reachable</td>
                    </tr>
                    <tr>
                        <td>Free Capacity</td>
                        <td class="healthy">✓</td>
                        <td>&gt;20% available</td>
                    </tr>
                </tbody>
            </table>

            <h3>Capacity Summary</h3>
            <table>
                <tr>
                    <td><strong>Total Capacity</strong></td>
                    <td>[SIZE]</td>
                </tr>
                <tr>
                    <td><strong>Used Capacity</strong></td>
                    <td>[SIZE] ([PERCENT]%)</td>
                </tr>
                <tr>
                    <td><strong>Available Capacity</strong></td>
                    <td>[SIZE] ([PERCENT]%)</td>
                </tr>
                <tr>
                    <td><strong>Deduplicated</strong></td>
                    <td>[PERCENT]%</td>
                </tr>
                <tr>
                    <td><strong>Compressed</strong></td>
                    <td>[PERCENT]%</td>
                </tr>
            </table>
        </div>

        <div class="section">
            <h2>Recommendations</h2>
            <div class="recommendations">
                <p>[Add operational recommendations based on health metrics]</p>
            </div>
        </div>

        <div class="section">
            <p><strong>Next Review Date:</strong> [DATE]</p>
        </div>
    </div>

    <!-- CLUSTER 2 TAB CONTENT -->
    <div id="cluster-2" class="tab-content">
        <div class="cluster-info">
            <strong>Cluster:</strong> [CLUSTER_NAME_2] | <strong>Host:</strong> [CLUSTER_HOST_2]
        </div>

        <div class="section">
            <h2>Executive Summary</h2>
            <div class="summary">
                <div class="summary-item">
                    <div class="label">Overall Health Status</div>
                    <div class="value healthy">[HEALTHY/WARNING/CRITICAL]</div>
                </div>
                <div class="summary-item">
                    <div class="label">Uptime</div>
                    <div class="value">[DAYS] days</div>
                </div>
                <div class="summary-item">
                    <div class="label">Storage Utilization</div>
                    <div class="value">[PERCENT]%</div>
                </div>
                <div class="summary-item">
                    <div class="label">Active Users</div>
                    <div class="value">[COUNT]</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Cluster Status</h2>
            <h3>Health Metrics</h3>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Status</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Quorum</td>
                        <td class="healthy">✓</td>
                        <td>All nodes participating</td>
                    </tr>
                    <tr>
                        <td>Service Lights</td>
                        <td class="healthy">✓</td>
                        <td>No hardware alerts</td>
                    </tr>
                    <tr>
                        <td>Critical Events</td>
                        <td class="healthy">✓</td>
                        <td>0 unresolved critical alerts</td>
                    </tr>
                    <tr>
                        <td>Network Connectivity</td>
                        <td class="healthy">✓</td>
                        <td>All gateways reachable</td>
                    </tr>
                    <tr>
                        <td>Free Capacity</td>
                        <td class="healthy">✓</td>
                        <td>&gt;20% available</td>
                    </tr>
                </tbody>
            </table>

            <h3>Capacity Summary</h3>
            <table>
                <tr>
                    <td><strong>Total Capacity</strong></td>
                    <td>[SIZE]</td>
                </tr>
                <tr>
                    <td><strong>Used Capacity</strong></td>
                    <td>[SIZE] ([PERCENT]%)</td>
                </tr>
                <tr>
                    <td><strong>Available Capacity</strong></td>
                    <td>[SIZE] ([PERCENT]%)</td>
                </tr>
                <tr>
                    <td><strong>Deduplicated</strong></td>
                    <td>[PERCENT]%</td>
                </tr>
                <tr>
                    <td><strong>Compressed</strong></td>
                    <td>[PERCENT]%</td>
                </tr>
            </table>
        </div>

        <div class="section">
            <h2>Recommendations</h2>
            <div class="recommendations">
                <p>[Add operational recommendations based on health metrics]</p>
            </div>
        </div>

        <div class="section">
            <p><strong>Next Review Date:</strong> [DATE]</p>
        </div>
    </div>

    <!-- DUPLICATE CLUSTER TAB CONTENT BLOCKS FOR MORE CLUSTERS -->

    <div class="footer">
        <p>This report was automatically generated by PowerScale MCP Server</p>
    </div>
</body>
</html>
```

---

## 2. Quota & User Management Report

**Purpose**: Track quota utilization by user/group and identify over-quota situations

**Data Sources**:
- `powerscale_quota_get` — All quotas and current usage
- `powerscale_quota_list_by_type` — Quotas organized by type (user/group/directory)

**File Name**: `powerscale_report_quota_[YYYYMMDD]_[HHMMSS].html` (single) or `powerscale_report_quota_multi_[YYYYMMDD]_[HHMMSS].html` (multi)

**Template**:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PowerScale Quota Utilization Report</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'segoe ui', helvetica, arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; color: #454545; }
        .header { background: linear-gradient(135deg, #0076CE 0%, #0059a3 100%); color: white; padding: 30px; border-radius: 8px; margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0, 118, 206, 0.15); }
        .header h1 { margin: 0 0 15px 0; font-size: 28px; font-weight: 600; }
        .header p { margin: 8px 0; font-size: 14px; opacity: 0.95; }
        .tabs { display: flex; gap: 8px; margin-bottom: 20px; border-bottom: 2px solid #e0e0e0; flex-wrap: wrap; }
        .tab-button { background-color: white; border: 2px solid #e0e0e0; padding: 12px 20px; cursor: pointer; border-radius: 6px 6px 0 0; transition: all 0.3s ease; font-weight: 500; color: #454545; }
        .tab-button:hover { background-color: #f0f0f0; border-color: #0076CE; }
        .tab-button.active { background-color: #0076CE; color: white; border-color: #0076CE; box-shadow: 0 -2px 8px rgba(0, 118, 206, 0.1); }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .section { background-color: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; border-left: 4px solid #0076CE; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08); }
        .section h2 { color: #0076CE; margin-top: 0; margin-bottom: 15px; font-size: 20px; font-weight: 600; }
        .summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 15px; }
        .summary-item { background: linear-gradient(135deg, #f8f9fa 0%, #efefef 100%); padding: 15px; border-radius: 6px; text-align: center; border-top: 3px solid #0076CE; }
        .summary-item .label { font-size: 12px; color: #666; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
        .summary-item .value { font-size: 24px; font-weight: 600; color: #0076CE; margin-top: 8px; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 14px; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #e0e0e0; }
        th { background-color: #f0f0f0; font-weight: 600; color: #454545; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px; }
        tr:hover { background-color: #f8f9fa; }
        .critical { color: #dc5034; font-weight: 600; }
        .warning { color: #f2af00; font-weight: 600; }
        .progress-bar { width: 100%; height: 20px; background-color: #e9ecef; border-radius: 4px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #7ab800 0%, #5a8000 100%); }
        .progress-fill.warning { background: linear-gradient(90deg, #f2af00 0%, #d99000 100%); }
        .progress-fill.critical { background: linear-gradient(90deg, #dc5034 0%, #a83a26 100%); }
        .footer { text-align: center; color: #999; font-size: 13px; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e0e0e0; }
        .footer a { color: #0076CE; text-decoration: none; }
        .cluster-info { background: linear-gradient(135deg, #f0f9ff 0%, #e8f4ff 100%); padding: 12px 15px; border-radius: 6px; margin-bottom: 15px; border-left: 3px solid #0076CE; font-size: 14px; color: #454545; }
    </style>
    <script>
        function openTab(event, tabName) {
            var i, tabcontent, tabbuttons;
            tabcontent = document.getElementsByClassName("tab-content");
            for (i = 0; i < tabcontent.length; i++) {
                tabcontent[i].classList.remove("active");
            }
            tabbuttons = document.getElementsByClassName("tab-button");
            for (i = 0; i < tabbuttons.length; i++) {
                tabbuttons[i].classList.remove("active");
            }
            document.getElementById(tabName).classList.add("active");
            event.currentTarget.classList.add("active");
        }
    </script>
</head>
<body>
    <div class="header">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 16px;">
                <svg width="52" height="36" viewBox="0 0 52 36" xmlns="http://www.w3.org/2000/svg">
                    <rect x="0"  y="0" width="10" height="36" fill="white" rx="2"/>
                    <rect x="14" y="0" width="10" height="36" fill="white" rx="2"/>
                    <rect x="28" y="0" width="10" height="36" fill="white" rx="2"/>
                    <rect x="42" y="0" width="10" height="36" fill="white" rx="2"/>
                </svg>
                <div style="line-height: 1.2;">
                    <div style="font-size: 22px; font-weight: 700; letter-spacing: 0.5px;">Dell Technologies</div>
                    <div style="font-size: 14px; font-weight: 400; opacity: 0.85; letter-spacing: 1px; text-transform: uppercase;">PowerScale</div>
                </div>
            </div>
        </div>
        <h1>PowerScale Quota Utilization Report</h1>
        <p><strong>Generated:</strong> [DATE_TIME]</p>
        <p><strong>Report Period:</strong> [START_DATE] to [END_DATE]</p>
    </div>

    <!-- TAB NAVIGATION -->
    <div class="tabs">
        <button class="tab-button active" onclick="openTab(event, 'cluster-quota-1')">Cluster 1: [CLUSTER_NAME_1]</button>
        <button class="tab-button" onclick="openTab(event, 'cluster-quota-2')">Cluster 2: [CLUSTER_NAME_2]</button>
        <!-- DUPLICATE TAB BUTTONS FOR ADDITIONAL CLUSTERS -->
    </div>

    <!-- CLUSTER 1 TAB CONTENT -->
    <div id="cluster-quota-1" class="tab-content active">
        <div class="cluster-info">
            <strong>Cluster:</strong> [CLUSTER_NAME_1] | <strong>Host:</strong> [CLUSTER_HOST_1]
        </div>

        <div class="section">
            <h2>Summary</h2>
            <div class="summary">
                <div class="summary-item">
                    <div class="label">Total Quotas</div>
                    <div class="value">[COUNT]</div>
                </div>
                <div class="summary-item">
                    <div class="label">User Quotas</div>
                    <div class="value">[COUNT]</div>
                </div>
                <div class="summary-item">
                    <div class="label">Group Quotas</div>
                    <div class="value">[COUNT]</div>
                </div>
                <div class="summary-item">
                    <div class="label">Over-Quota Users</div>
                    <div class="value critical">[COUNT]</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Critical Issues</h2>
            <table>
                <thead>
                    <tr>
                        <th>User/Group</th>
                        <th>Type</th>
                        <th>Quota</th>
                        <th>Used</th>
                        <th>Utilization</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>[NAME]</td>
                        <td>User</td>
                        <td>[SIZE]</td>
                        <td>[SIZE]</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill critical" style="width: 105%;"></div>
                            </div>
                            105%
                        </td>
                        <td><span class="critical">⚠️ Over quota</span></td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Top 10 Quota Consumers</h2>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>User/Group</th>
                        <th>Type</th>
                        <th>Quota</th>
                        <th>Used</th>
                        <th>Utilization</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>1</td>
                        <td>[NAME]</td>
                        <td>User</td>
                        <td>[SIZE]</td>
                        <td>[SIZE]</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: [PERCENT]%;"></div>
                            </div>
                            [PERCENT]%
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Recommendations</h2>
            <ul>
                <li>[Action items for over-quota situations]</li>
                <li>[Suggested quota adjustments]</li>
                <li>[Retention policy recommendations]</li>
            </ul>
        </div>
    </div>

    <!-- CLUSTER 2 TAB CONTENT -->
    <div id="cluster-quota-2" class="tab-content">
        <div class="cluster-info">
            <strong>Cluster:</strong> [CLUSTER_NAME_2] | <strong>Host:</strong> [CLUSTER_HOST_2]
        </div>

        <div class="section">
            <h2>Summary</h2>
            <div class="summary">
                <div class="summary-item">
                    <div class="label">Total Quotas</div>
                    <div class="value">[COUNT]</div>
                </div>
                <div class="summary-item">
                    <div class="label">User Quotas</div>
                    <div class="value">[COUNT]</div>
                </div>
                <div class="summary-item">
                    <div class="label">Group Quotas</div>
                    <div class="value">[COUNT]</div>
                </div>
                <div class="summary-item">
                    <div class="label">Over-Quota Users</div>
                    <div class="value critical">[COUNT]</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Critical Issues</h2>
            <table>
                <thead>
                    <tr>
                        <th>User/Group</th>
                        <th>Type</th>
                        <th>Quota</th>
                        <th>Used</th>
                        <th>Utilization</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>[NAME]</td>
                        <td>User</td>
                        <td>[SIZE]</td>
                        <td>[SIZE]</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill critical" style="width: 105%;"></div>
                            </div>
                            105%
                        </td>
                        <td><span class="critical">⚠️ Over quota</span></td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Top 10 Quota Consumers</h2>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>User/Group</th>
                        <th>Type</th>
                        <th>Quota</th>
                        <th>Used</th>
                        <th>Utilization</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>1</td>
                        <td>[NAME]</td>
                        <td>User</td>
                        <td>[SIZE]</td>
                        <td>[SIZE]</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: [PERCENT]%;"></div>
                            </div>
                            [PERCENT]%
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Recommendations</h2>
            <ul>
                <li>[Action items for over-quota situations]</li>
                <li>[Suggested quota adjustments]</li>
                <li>[Retention policy recommendations]</li>
            </ul>
        </div>
    </div>

    <!-- DUPLICATE CLUSTER TAB CONTENT BLOCKS FOR MORE CLUSTERS -->

    <div class="footer">
        <p>This report was automatically generated by PowerScale MCP Server</p>
    </div>
</body>
</html>
```

---

## 3. Data Protection & Snapshots Report

**Purpose**: Monitor snapshot coverage and replication status

**Data Sources**:
- `powerscale_snapshots_get` — All snapshots
- `powerscale_snapshot_schedules_get` — Snapshot schedules
- `powerscale_synciq_get` — Replication policy status

**File Name**: `powerscale_report_dataprotection_[YYYYMMDD]_[HHMMSS].html` (single) or `powerscale_report_dataprotection_multi_[YYYYMMDD]_[HHMMSS].html` (multi)

**Template**:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PowerScale Data Protection Report</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'segoe ui', helvetica, arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; color: #454545; }
        .header { background: linear-gradient(135deg, #0076CE 0%, #0059a3 100%); color: white; padding: 30px; border-radius: 8px; margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0, 118, 206, 0.15); }
        .header h1 { margin: 0 0 15px 0; font-size: 28px; font-weight: 600; }
        .header p { margin: 8px 0; font-size: 14px; opacity: 0.95; }
        .tabs { display: flex; gap: 8px; margin-bottom: 20px; border-bottom: 2px solid #e0e0e0; flex-wrap: wrap; }
        .tab-button { background-color: white; border: 2px solid #e0e0e0; padding: 12px 20px; cursor: pointer; border-radius: 6px 6px 0 0; transition: all 0.3s ease; font-weight: 500; color: #454545; }
        .tab-button:hover { background-color: #f0f0f0; border-color: #0076CE; }
        .tab-button.active { background-color: #0076CE; color: white; border-color: #0076CE; box-shadow: 0 -2px 8px rgba(0, 118, 206, 0.1); }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .section { background-color: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; border-left: 4px solid #0076CE; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08); }
        .section h2 { color: #0076CE; margin-top: 0; margin-bottom: 15px; font-size: 20px; font-weight: 600; }
        .section h3 { color: #244739; font-size: 16px; font-weight: 600; margin-top: 15px; }
        .summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 15px; }
        .summary-item { background: linear-gradient(135deg, #f8f9fa 0%, #efefef 100%); padding: 15px; border-radius: 6px; text-align: center; border-top: 3px solid #0076CE; }
        .summary-item .label { font-size: 12px; color: #666; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
        .summary-item .value { font-size: 24px; font-weight: 600; color: #0076CE; margin-top: 8px; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 14px; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #e0e0e0; }
        th { background-color: #f0f0f0; font-weight: 600; color: #454545; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px; }
        tr:hover { background-color: #f8f9fa; }
        .healthy { color: #7ab800; font-weight: 600; }
        .warning { color: #f2af00; font-weight: 600; }
        .critical { color: #dc5034; font-weight: 600; }
        .footer { text-align: center; color: #999; font-size: 13px; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e0e0e0; }
        .footer a { color: #0076CE; text-decoration: none; }
        .cluster-info { background: linear-gradient(135deg, #f0f9ff 0%, #e8f4ff 100%); padding: 12px 15px; border-radius: 6px; margin-bottom: 15px; border-left: 3px solid #0076CE; font-size: 14px; color: #454545; }
    </style>
    <script>
        function openTab(event, tabName) {
            var i, tabcontent, tabbuttons;
            tabcontent = document.getElementsByClassName("tab-content");
            for (i = 0; i < tabcontent.length; i++) {
                tabcontent[i].classList.remove("active");
            }
            tabbuttons = document.getElementsByClassName("tab-button");
            for (i = 0; i < tabbuttons.length; i++) {
                tabbuttons[i].classList.remove("active");
            }
            document.getElementById(tabName).classList.add("active");
            event.currentTarget.classList.add("active");
        }
    </script>
</head>
<body>
    <div class="header">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 16px;">
                <svg width="52" height="36" viewBox="0 0 52 36" xmlns="http://www.w3.org/2000/svg">
                    <rect x="0"  y="0" width="10" height="36" fill="white" rx="2"/>
                    <rect x="14" y="0" width="10" height="36" fill="white" rx="2"/>
                    <rect x="28" y="0" width="10" height="36" fill="white" rx="2"/>
                    <rect x="42" y="0" width="10" height="36" fill="white" rx="2"/>
                </svg>
                <div style="line-height: 1.2;">
                    <div style="font-size: 22px; font-weight: 700; letter-spacing: 0.5px;">Dell Technologies</div>
                    <div style="font-size: 14px; font-weight: 400; opacity: 0.85; letter-spacing: 1px; text-transform: uppercase;">PowerScale</div>
                </div>
            </div>
        </div>
        <h1>PowerScale Data Protection Status Report</h1>
        <p><strong>Generated:</strong> [DATE_TIME]</p>
        <p><strong>Report Period:</strong> [START_DATE] to [END_DATE]</p>
    </div>

    <!-- TAB NAVIGATION -->
    <div class="tabs">
        <button class="tab-button active" onclick="openTab(event, 'cluster-dp-1')">Cluster 1: [CLUSTER_NAME_1]</button>
        <button class="tab-button" onclick="openTab(event, 'cluster-dp-2')">Cluster 2: [CLUSTER_NAME_2]</button>
        <!-- DUPLICATE TAB BUTTONS FOR ADDITIONAL CLUSTERS -->
    </div>

    <!-- CLUSTER 1 TAB CONTENT -->
    <div id="cluster-dp-1" class="tab-content active">
        <div class="cluster-info">
            <strong>Cluster:</strong> [CLUSTER_NAME_1] | <strong>Host:</strong> [CLUSTER_HOST_1]
        </div>

    <div class="section">
        <h2>Snapshot Status</h2>
        <h3>Active Snapshots</h3>
        <div class="summary">
            <div class="summary-item">
                <div class="label">Total Snapshots</div>
                <div class="value">[COUNT]</div>
            </div>
            <div class="summary-item">
                <div class="label">Scheduled Snapshots</div>
                <div class="value">[COUNT]</div>
            </div>
            <div class="summary-item">
                <div class="label">Manual Snapshots</div>
                <div class="value">[COUNT]</div>
            </div>
            <div class="summary-item">
                <div class="label">Space Used</div>
                <div class="value">[SIZE]</div>
            </div>
        </div>

        <h3>Snapshot Schedules</h3>
        <table>
            <thead>
                <tr>
                    <th>Schedule</th>
                    <th>Interval</th>
                    <th>Retention</th>
                    <th>Last Run</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>[NAME]</td>
                    <td>Daily at [TIME]</td>
                    <td>[DURATION]</td>
                    <td>[TIMESTAMP]</td>
                    <td><span class="healthy">✓ OK</span></td>
                </tr>
                <tr>
                    <td>[NAME]</td>
                    <td>Weekly on [DAY]</td>
                    <td>[DURATION]</td>
                    <td>[TIMESTAMP]</td>
                    <td><span class="healthy">✓ OK</span></td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>Replication Status (SyncIQ)</h2>
        <table>
            <thead>
                <tr>
                    <th>Policy</th>
                    <th>Source</th>
                    <th>Target</th>
                    <th>Last Sync</th>
                    <th>Status</th>
                    <th>Next Scheduled</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>[NAME]</td>
                    <td>[CLUSTER]</td>
                    <td>[CLUSTER]</td>
                    <td>[TIME]</td>
                    <td><span class="healthy">✓ In Sync</span></td>
                    <td>[TIME]</td>
                </tr>
                <tr>
                    <td>[NAME]</td>
                    <td>[CLUSTER]</td>
                    <td>[CLUSTER]</td>
                    <td>[TIME]</td>
                    <td><span class="warning">⚠️ Running</span></td>
                    <td>[TIME]</td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>Recovery Point Objectives</h2>
        <table>
            <thead>
                <tr>
                    <th>Application</th>
                    <th>RTO</th>
                    <th>RPO</th>
                    <th>Current RPO</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>[APP]</td>
                    <td>[TIME]</td>
                    <td>[TIME]</td>
                    <td>[TIME]</td>
                    <td><span class="healthy">✓ Met</span></td>
                </tr>
                <tr>
                    <td>[APP]</td>
                    <td>[TIME]</td>
                    <td>[TIME]</td>
                    <td>[TIME]</td>
                    <td><span class="critical">⚠️ At Risk</span></td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>Recommendations</h2>
        <p>[Actions to improve snapshot coverage or replication lag]</p>
    </div>
    </div>

    <!-- CLUSTER 2 TAB CONTENT -->
    <div id="cluster-dp-2" class="tab-content">
        <div class="cluster-info">
            <strong>Cluster:</strong> [CLUSTER_NAME_2] | <strong>Host:</strong> [CLUSTER_HOST_2]
        </div>

        <div class="section">
            <h2>Snapshot Status</h2>
            <h3>Active Snapshots</h3>
            <div class="summary">
                <div class="summary-item">
                    <div class="label">Total Snapshots</div>
                    <div class="value">[COUNT]</div>
                </div>
                <div class="summary-item">
                    <div class="label">Scheduled Snapshots</div>
                    <div class="value">[COUNT]</div>
                </div>
                <div class="summary-item">
                    <div class="label">Manual Snapshots</div>
                    <div class="value">[COUNT]</div>
                </div>
                <div class="summary-item">
                    <div class="label">Space Used</div>
                    <div class="value">[SIZE]</div>
                </div>
            </div>

            <h3>Snapshot Schedules</h3>
            <table>
                <thead>
                    <tr>
                        <th>Schedule</th>
                        <th>Interval</th>
                        <th>Retention</th>
                        <th>Last Run</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>[NAME]</td>
                        <td>Daily at [TIME]</td>
                        <td>[DURATION]</td>
                        <td>[TIMESTAMP]</td>
                        <td><span class="healthy">✓ OK</span></td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Replication Status (SyncIQ)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Policy</th>
                        <th>Source</th>
                        <th>Target</th>
                        <th>Last Sync</th>
                        <th>Status</th>
                        <th>Next Scheduled</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>[NAME]</td>
                        <td>[CLUSTER]</td>
                        <td>[CLUSTER]</td>
                        <td>[TIME]</td>
                        <td><span class="healthy">✓ In Sync</span></td>
                        <td>[TIME]</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Recovery Point Objectives</h2>
            <table>
                <thead>
                    <tr>
                        <th>Application</th>
                        <th>RTO</th>
                        <th>RPO</th>
                        <th>Current RPO</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>[APP]</td>
                        <td>[TIME]</td>
                        <td>[TIME]</td>
                        <td>[TIME]</td>
                        <td><span class="healthy">✓ Met</span></td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Recommendations</h2>
            <p>[Actions to improve snapshot coverage or replication lag]</p>
        </div>
    </div>

    <!-- DUPLICATE CLUSTER TAB CONTENT BLOCKS FOR MORE CLUSTERS -->

    <div class="footer">
        <p>This report was automatically generated by PowerScale MCP Server</p>
    </div>
</body>
</html>
```

---

## 4. File Services Activity Report

**Purpose**: Track SMB/NFS share usage and access patterns

**Data Sources**:
- `powerscale_smb_shares_get` — SMB shares and settings
- `powerscale_nfs_exports_get` — NFS exports and settings
- `powerscale_s3_buckets_get` — S3 buckets

**File Name**: `powerscale_report_fileservices_[YYYYMMDD]_[HHMMSS].html` (single) or `powerscale_report_fileservices_multi_[YYYYMMDD]_[HHMMSS].html` (multi)

**Template**:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PowerScale File Services Report</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'segoe ui', helvetica, arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; color: #454545; }
        .header { background: linear-gradient(135deg, #0076CE 0%, #0059a3 100%); color: white; padding: 30px; border-radius: 8px; margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0, 118, 206, 0.15); }
        .header h1 { margin: 0 0 15px 0; font-size: 28px; font-weight: 600; }
        .header p { margin: 8px 0; font-size: 14px; opacity: 0.95; }
        .tabs { display: flex; gap: 8px; margin-bottom: 20px; border-bottom: 2px solid #e0e0e0; flex-wrap: wrap; }
        .tab-button { background-color: white; border: 2px solid #e0e0e0; padding: 12px 20px; cursor: pointer; border-radius: 6px 6px 0 0; transition: all 0.3s ease; font-weight: 500; color: #454545; }
        .tab-button:hover { background-color: #f0f0f0; border-color: #0076CE; }
        .tab-button.active { background-color: #0076CE; color: white; border-color: #0076CE; box-shadow: 0 -2px 8px rgba(0, 118, 206, 0.1); }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .section { background-color: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; border-left: 4px solid #0076CE; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08); }
        .section h2 { color: #0076CE; margin-top: 0; margin-bottom: 15px; font-size: 20px; font-weight: 600; }
        .summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 15px; }
        .summary-item { background: linear-gradient(135deg, #f8f9fa 0%, #efefef 100%); padding: 15px; border-radius: 6px; text-align: center; border-top: 3px solid #0076CE; }
        .summary-item .label { font-size: 12px; color: #666; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
        .summary-item .value { font-size: 24px; font-weight: 600; color: #0076CE; margin-top: 8px; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 14px; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #e0e0e0; }
        th { background-color: #f0f0f0; font-weight: 600; color: #454545; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px; }
        tr:hover { background-color: #f8f9fa; }
        .enabled { color: #7ab800; font-weight: 600; }
        .disabled { color: #dc5034; font-weight: 600; }
        .security-box { background: linear-gradient(135deg, #f0f9ff 0%, #e8f4ff 100%); padding: 15px; border-radius: 6px; margin-bottom: 10px; border-left: 3px solid #0076CE; }
        .security-box ul { margin: 0; padding-left: 20px; }
        .security-box li { margin: 8px 0; color: #454545; }
        .footer { text-align: center; color: #999; font-size: 13px; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e0e0e0; }
        .footer a { color: #0076CE; text-decoration: none; }
        .cluster-info { background: linear-gradient(135deg, #f0f9ff 0%, #e8f4ff 100%); padding: 12px 15px; border-radius: 6px; margin-bottom: 15px; border-left: 3px solid #0076CE; font-size: 14px; color: #454545; }
    </style>
    <script>
        function openTab(event, tabName) {
            var i, tabcontent, tabbuttons;
            tabcontent = document.getElementsByClassName("tab-content");
            for (i = 0; i < tabcontent.length; i++) {
                tabcontent[i].classList.remove("active");
            }
            tabbuttons = document.getElementsByClassName("tab-button");
            for (i = 0; i < tabbuttons.length; i++) {
                tabbuttons[i].classList.remove("active");
            }
            document.getElementById(tabName).classList.add("active");
            event.currentTarget.classList.add("active");
        }
    </script>
</head>
<body>
    <div class="header">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 16px;">
                <svg width="52" height="36" viewBox="0 0 52 36" xmlns="http://www.w3.org/2000/svg">
                    <rect x="0"  y="0" width="10" height="36" fill="white" rx="2"/>
                    <rect x="14" y="0" width="10" height="36" fill="white" rx="2"/>
                    <rect x="28" y="0" width="10" height="36" fill="white" rx="2"/>
                    <rect x="42" y="0" width="10" height="36" fill="white" rx="2"/>
                </svg>
                <div style="line-height: 1.2;">
                    <div style="font-size: 22px; font-weight: 700; letter-spacing: 0.5px;">Dell Technologies</div>
                    <div style="font-size: 14px; font-weight: 400; opacity: 0.85; letter-spacing: 1px; text-transform: uppercase;">PowerScale</div>
                </div>
            </div>
        </div>
        <h1>PowerScale File Services Report</h1>
        <p><strong>Generated:</strong> [DATE_TIME]</p>
        <p><strong>Report Period:</strong> [START_DATE] to [END_DATE]</p>
    </div>

    <!-- TAB NAVIGATION -->
    <div class="tabs">
        <button class="tab-button active" onclick="openTab(event, 'cluster-fs-1')">Cluster 1: [CLUSTER_NAME_1]</button>
        <button class="tab-button" onclick="openTab(event, 'cluster-fs-2')">Cluster 2: [CLUSTER_NAME_2]</button>
        <!-- DUPLICATE TAB BUTTONS FOR ADDITIONAL CLUSTERS -->
    </div>

    <!-- CLUSTER 1 TAB CONTENT -->
    <div id="cluster-fs-1" class="tab-content active">
        <div class="cluster-info">
            <strong>Cluster:</strong> [CLUSTER_NAME_1] | <strong>Host:</strong> [CLUSTER_HOST_1]
        </div>

    <div class="section">
        <h2>Protocol Summary</h2>
        <table>
            <thead>
                <tr>
                    <th>Protocol</th>
                    <th>Shares/Exports</th>
                    <th>Status</th>
                    <th>Utilization</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>SMB</td>
                    <td>[COUNT]</td>
                    <td><span class="enabled">Enabled</span></td>
                    <td>[PERCENT]%</td>
                </tr>
                <tr>
                    <td>NFS</td>
                    <td>[COUNT]</td>
                    <td><span class="enabled">Enabled</span></td>
                    <td>[PERCENT]%</td>
                </tr>
                <tr>
                    <td>S3</td>
                    <td>[COUNT]</td>
                    <td><span class="enabled">Enabled</span></td>
                    <td>[PERCENT]%</td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>SMB Shares</h2>
        <table>
            <thead>
                <tr>
                    <th>Share Name</th>
                    <th>Path</th>
                    <th>Encryption</th>
                    <th>Signing</th>
                    <th>Size</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>[NAME]</td>
                    <td>[PATH]</td>
                    <td>[YES/NO]</td>
                    <td>[YES/NO]</td>
                    <td>[SIZE]</td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>NFS Exports</h2>
        <table>
            <thead>
                <tr>
                    <th>Export</th>
                    <th>Path</th>
                    <th>NFSv3</th>
                    <th>NFSv4</th>
                    <th>Access Control</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>[NAME]</td>
                    <td>[PATH]</td>
                    <td>[YES/NO]</td>
                    <td>[YES/NO]</td>
                    <td>[RESTRICTION]</td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>S3 Buckets</h2>
        <table>
            <thead>
                <tr>
                    <th>Bucket</th>
                    <th>Versioning</th>
                    <th>Lifecycle</th>
                    <th>Objects</th>
                    <th>Size</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>[NAME]</td>
                    <td>[YES/NO]</td>
                    <td>[POLICY]</td>
                    <td>[COUNT]</td>
                    <td>[SIZE]</td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>Security Posture</h2>
        <div class="security-box">
            <ul>
                <li><strong>Encrypted Shares:</strong> [COUNT] / [TOTAL]</li>
                <li><strong>Signed Shares:</strong> [COUNT] / [TOTAL]</li>
                <li><strong>Access Controlled:</strong> [YES/NO]</li>
            </ul>
        </div>
    </div>

    <div class="section">
        <h2>Recommendations</h2>
        <p>[Security and access control improvements]</p>
    </div>
    </div>

    <!-- CLUSTER 2 TAB CONTENT -->
    <div id="cluster-fs-2" class="tab-content">
        <div class="cluster-info">
            <strong>Cluster:</strong> [CLUSTER_NAME_2] | <strong>Host:</strong> [CLUSTER_HOST_2]
        </div>

        <div class="section">
            <h2>Protocol Summary</h2>
            <table>
                <thead>
                    <tr>
                        <th>Protocol</th>
                        <th>Shares/Exports</th>
                        <th>Status</th>
                        <th>Utilization</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>SMB</td>
                        <td>[COUNT]</td>
                        <td><span class="enabled">Enabled</span></td>
                        <td>[PERCENT]%</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>SMB Shares</h2>
            <table>
                <thead>
                    <tr>
                        <th>Share Name</th>
                        <th>Path</th>
                        <th>Encryption</th>
                        <th>Signing</th>
                        <th>Size</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>[NAME]</td>
                        <td>[PATH]</td>
                        <td>[YES/NO]</td>
                        <td>[YES/NO]</td>
                        <td>[SIZE]</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Recommendations</h2>
            <p>[Security and access control improvements]</p>
        </div>
    </div>

    <!-- DUPLICATE CLUSTER TAB CONTENT BLOCKS FOR MORE CLUSTERS -->

    <div class="footer">
        <p>This report was automatically generated by PowerScale MCP Server</p>
    </div>
</body>
</html>
```

---

## 5. Performance & Capacity Planning Report

**Purpose**: Identify trends and plan for capacity growth

**Data Sources**:
- `powerscale_capacity_get` — Historical capacity trends
- `powerscale_hardware_get` — Hardware inventory and health
- `powerscale_performance_get` — Performance metrics (if available)

**File Name**: `powerscale_report_capacity_[YYYYMMDD]_[HHMMSS].html` (single) or `powerscale_report_capacity_multi_[YYYYMMDD]_[HHMMSS].html` (multi)

**Template**:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PowerScale Capacity Planning Report</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'segoe ui', helvetica, arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; color: #454545; }
        .header { background: linear-gradient(135deg, #0076CE 0%, #0059a3 100%); color: white; padding: 30px; border-radius: 8px; margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0, 118, 206, 0.15); }
        .header h1 { margin: 0 0 15px 0; font-size: 28px; font-weight: 600; }
        .header p { margin: 8px 0; font-size: 14px; opacity: 0.95; }
        .tabs { display: flex; gap: 8px; margin-bottom: 20px; border-bottom: 2px solid #e0e0e0; flex-wrap: wrap; }
        .tab-button { background-color: white; border: 2px solid #e0e0e0; padding: 12px 20px; cursor: pointer; border-radius: 6px 6px 0 0; transition: all 0.3s ease; font-weight: 500; color: #454545; }
        .tab-button:hover { background-color: #f0f0f0; border-color: #0076CE; }
        .tab-button.active { background-color: #0076CE; color: white; border-color: #0076CE; box-shadow: 0 -2px 8px rgba(0, 118, 206, 0.1); }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .section { background-color: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; border-left: 4px solid #0076CE; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08); }
        .section h2 { color: #0076CE; margin-top: 0; margin-bottom: 15px; font-size: 20px; font-weight: 600; }
        .summary { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 15px; }
        .summary-item { background: linear-gradient(135deg, #f8f9fa 0%, #efefef 100%); padding: 15px; border-radius: 6px; border-left: 3px solid #0076CE; }
        .summary-item .label { font-size: 12px; color: #666; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
        .summary-item .value { font-size: 24px; font-weight: 600; color: #0076CE; margin-top: 8px; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 14px; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #e0e0e0; }
        th { background-color: #f0f0f0; font-weight: 600; color: #454545; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px; }
        tr:hover { background-color: #f8f9fa; }
        .healthy { color: #7ab800; font-weight: 600; }
        .warning { color: #f2af00; font-weight: 600; }
        .critical { color: #dc5034; font-weight: 600; }
        .action-box { background: linear-gradient(135deg, #fff9e6 0%, #fff0e6 100%); padding: 15px; border-radius: 6px; margin-bottom: 10px; border-left: 3px solid #f2af00; }
        .timeline { margin: 20px 0; }
        .timeline-item { margin-bottom: 20px; padding: 15px; background: linear-gradient(135deg, #f8f9fa 0%, #efefef 100%); border-radius: 6px; border-left: 3px solid #0076CE; }
        .timeline-item h4 { margin: 0 0 10px 0; color: #0076CE; font-size: 16px; }
        .timeline-item ul { margin: 0; padding-left: 20px; }
        .timeline-item li { margin: 5px 0; color: #454545; }
        .footer { text-align: center; color: #999; font-size: 13px; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e0e0e0; }
        .footer a { color: #0076CE; text-decoration: none; }
        .cluster-info { background: linear-gradient(135deg, #f0f9ff 0%, #e8f4ff 100%); padding: 12px 15px; border-radius: 6px; margin-bottom: 15px; border-left: 3px solid #0076CE; font-size: 14px; color: #454545; }
    </style>
    <script>
        function openTab(event, tabName) {
            var i, tabcontent, tabbuttons;
            tabcontent = document.getElementsByClassName("tab-content");
            for (i = 0; i < tabcontent.length; i++) {
                tabcontent[i].classList.remove("active");
            }
            tabbuttons = document.getElementsByClassName("tab-button");
            for (i = 0; i < tabbuttons.length; i++) {
                tabbuttons[i].classList.remove("active");
            }
            document.getElementById(tabName).classList.add("active");
            event.currentTarget.classList.add("active");
        }
    </script>
</head>
<body>
    <div class="header">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 16px;">
                <svg width="52" height="36" viewBox="0 0 52 36" xmlns="http://www.w3.org/2000/svg">
                    <rect x="0"  y="0" width="10" height="36" fill="white" rx="2"/>
                    <rect x="14" y="0" width="10" height="36" fill="white" rx="2"/>
                    <rect x="28" y="0" width="10" height="36" fill="white" rx="2"/>
                    <rect x="42" y="0" width="10" height="36" fill="white" rx="2"/>
                </svg>
                <div style="line-height: 1.2;">
                    <div style="font-size: 22px; font-weight: 700; letter-spacing: 0.5px;">Dell Technologies</div>
                    <div style="font-size: 14px; font-weight: 400; opacity: 0.85; letter-spacing: 1px; text-transform: uppercase;">PowerScale</div>
                </div>
            </div>
        </div>
        <h1>PowerScale Capacity Planning & Performance Report</h1>
        <p><strong>Generated:</strong> [DATE_TIME]</p>
        <p><strong>Report Period:</strong> [START_DATE] to [END_DATE]</p>
    </div>

    <!-- TAB NAVIGATION -->
    <div class="tabs">
        <button class="tab-button active" onclick="openTab(event, 'cluster-cap-1')">Cluster 1: [CLUSTER_NAME_1]</button>
        <button class="tab-button" onclick="openTab(event, 'cluster-cap-2')">Cluster 2: [CLUSTER_NAME_2]</button>
        <!-- DUPLICATE TAB BUTTONS FOR ADDITIONAL CLUSTERS -->
    </div>

    <!-- CLUSTER 1 TAB CONTENT -->
    <div id="cluster-cap-1" class="tab-content active">
        <div class="cluster-info">
            <strong>Cluster:</strong> [CLUSTER_NAME_1] | <strong>Host:</strong> [CLUSTER_HOST_1]
        </div>

    <div class="section">
        <h2>Capacity Trend Analysis</h2>
        <div class="summary">
            <div class="summary-item">
                <div class="label">Current Utilization</div>
                <div class="value">[PERCENT]%</div>
            </div>
            <div class="summary-item">
                <div class="label">Growth Rate (Monthly)</div>
                <div class="value">[PERCENT]%</div>
            </div>
            <div class="summary-item">
                <div class="label">Projected Full Date</div>
                <div class="value">[DATE]</div>
            </div>
            <div class="summary-item">
                <div class="label">Recommended Action</div>
                <div class="value">[EXPAND/OPTIMIZE/REPLACE]</div>
            </div>
        </div>

        <h3>Capacity Timeline</h3>
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Used</th>
                    <th>Available</th>
                    <th>Utilization</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>[DATE]</td>
                    <td>[SIZE]</td>
                    <td>[SIZE]</td>
                    <td>[PERCENT]%</td>
                </tr>
                <tr>
                    <td>[DATE]</td>
                    <td>[SIZE]</td>
                    <td>[SIZE]</td>
                    <td>[PERCENT]%</td>
                </tr>
                <tr>
                    <td>[DATE]</td>
                    <td>[SIZE]</td>
                    <td>[SIZE]</td>
                    <td>[PERCENT]%</td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>Hardware Health</h2>
        <table>
            <thead>
                <tr>
                    <th>Component</th>
                    <th>Total</th>
                    <th>Healthy</th>
                    <th>Degraded</th>
                    <th>Failed</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Nodes</td>
                    <td>[N]</td>
                    <td><span class="healthy">[N]</span></td>
                    <td>[N]</td>
                    <td>[N]</td>
                </tr>
                <tr>
                    <td>Drives</td>
                    <td>[N]</td>
                    <td><span class="healthy">[N]</span></td>
                    <td>[N]</td>
                    <td>[N]</td>
                </tr>
                <tr>
                    <td>Power Supplies</td>
                    <td>[N]</td>
                    <td><span class="healthy">[N]</span></td>
                    <td>[N]</td>
                    <td>[N]</td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>Recommendations</h2>
        <div class="timeline">
            <div class="timeline-item">
                <h4>📅 Near-term (30 days)</h4>
                <ul>
                    <li>[Actions]</li>
                </ul>
            </div>
            <div class="timeline-item">
                <h4>📅 Mid-term (90 days)</h4>
                <ul>
                    <li>[Actions]</li>
                </ul>
            </div>
            <div class="timeline-item">
                <h4>📅 Long-term (12 months)</h4>
                <ul>
                    <li>[Actions]</li>
                </ul>
            </div>
        </div>
    </div>
    </div>

    <!-- CLUSTER 2 TAB CONTENT -->
    <div id="cluster-cap-2" class="tab-content">
        <div class="cluster-info">
            <strong>Cluster:</strong> [CLUSTER_NAME_2] | <strong>Host:</strong> [CLUSTER_HOST_2]
        </div>

        <div class="section">
            <h2>Capacity Trend Analysis</h2>
            <div class="summary">
                <div class="summary-item">
                    <div class="label">Current Utilization</div>
                    <div class="value">[PERCENT]%</div>
                </div>
                <div class="summary-item">
                    <div class="label">Growth Rate (Monthly)</div>
                    <div class="value">[PERCENT]%</div>
                </div>
                <div class="summary-item">
                    <div class="label">Projected Full Date</div>
                    <div class="value">[DATE]</div>
                </div>
                <div class="summary-item">
                    <div class="label">Recommended Action</div>
                    <div class="value">[EXPAND/OPTIMIZE/REPLACE]</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Recommendations</h2>
            <div class="timeline">
                <div class="timeline-item">
                    <h4>📅 Near-term (30 days)</h4>
                    <ul>
                        <li>[Actions]</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>

    <!-- DUPLICATE CLUSTER TAB CONTENT BLOCKS FOR MORE CLUSTERS -->

    <div class="footer">
        <p>This report was automatically generated by PowerScale MCP Server</p>
    </div>
</body>
</html>
```

## 6. Compliance & Audit Report

**Purpose**: Document configurations for compliance verification

**Data Sources**:
- `powerscale_smb_settings_get` — SMB security settings
- `powerscale_nfs_settings_get` — NFS configurations
- `powerscale_hardening_get` — Security hardening status
- `powerscale_quota_get` — Data governance quotas

**File Name**: `powerscale_report_compliance_[YYYYMMDD]_[HHMMSS].html` (single) or `powerscale_report_compliance_multi_[YYYYMMDD]_[HHMMSS].html` (multi)

**Template**:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PowerScale Compliance & Audit Report</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'segoe ui', helvetica, arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; color: #454545; }
        .header { background: linear-gradient(135deg, #0076CE 0%, #0059a3 100%); color: white; padding: 30px; border-radius: 8px; margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0, 118, 206, 0.15); }
        .header h1 { margin: 0 0 15px 0; font-size: 28px; font-weight: 600; }
        .header p { margin: 8px 0; font-size: 14px; opacity: 0.95; }
        .tabs { display: flex; gap: 8px; margin-bottom: 20px; border-bottom: 2px solid #e0e0e0; flex-wrap: wrap; }
        .tab-button { background-color: white; border: 2px solid #e0e0e0; padding: 12px 20px; cursor: pointer; border-radius: 6px 6px 0 0; transition: all 0.3s ease; font-weight: 500; color: #454545; }
        .tab-button:hover { background-color: #f0f0f0; border-color: #0076CE; }
        .tab-button.active { background-color: #0076CE; color: white; border-color: #0076CE; box-shadow: 0 -2px 8px rgba(0, 118, 206, 0.1); }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .section { background-color: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; border-left: 4px solid #0076CE; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08); }
        .section h2 { color: #0076CE; margin-top: 0; margin-bottom: 15px; font-size: 20px; font-weight: 600; }
        .checklist { background: linear-gradient(135deg, #f8f9fa 0%, #efefef 100%); padding: 15px; border-radius: 6px; }
        .checklist-item { margin: 12px 0; display: flex; align-items: center; }
        .checklist-item input[type="checkbox"] { margin-right: 12px; width: 18px; height: 18px; cursor: pointer; accent-color: #0076CE; }
        .checklist-item label { color: #454545; cursor: pointer; font-size: 14px; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 14px; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #e0e0e0; }
        th { background-color: #f0f0f0; font-weight: 600; color: #454545; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px; }
        tr:hover { background-color: #f8f9fa; }
        .pass { color: #7ab800; font-weight: 600; }
        .fail { color: #dc5034; font-weight: 600; }
        .high { background-color: #fde8ea; }
        .medium { background-color: #fff9e6; }
        .low { background-color: #e8f5f7; }
        .signoff-box { background: linear-gradient(135deg, #f0f9ff 0%, #e8f4ff 100%); padding: 20px; border-radius: 8px; border: 2px solid #b3d9ff; margin-top: 20px; border-left: 4px solid #0076CE; }
        .signoff-box h2 { color: #0076CE; margin-top: 0; }
        .signoff-item { margin: 12px 0; font-size: 14px; color: #454545; }
        .footer { text-align: center; color: #999; font-size: 13px; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e0e0e0; }
        .footer a { color: #0076CE; text-decoration: none; }
        .cluster-info { background: linear-gradient(135deg, #f0f9ff 0%, #e8f4ff 100%); padding: 12px 15px; border-radius: 6px; margin-bottom: 15px; border-left: 3px solid #0076CE; font-size: 14px; color: #454545; }
    </style>
    <script>
        function openTab(event, tabName) {
            var i, tabcontent, tabbuttons;
            tabcontent = document.getElementsByClassName("tab-content");
            for (i = 0; i < tabcontent.length; i++) {
                tabcontent[i].classList.remove("active");
            }
            tabbuttons = document.getElementsByClassName("tab-button");
            for (i = 0; i < tabbuttons.length; i++) {
                tabbuttons[i].classList.remove("active");
            }
            document.getElementById(tabName).classList.add("active");
            event.currentTarget.classList.add("active");
        }
    </script>
</head>
<body>
    <div class="header">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 16px;">
                <svg width="52" height="36" viewBox="0 0 52 36" xmlns="http://www.w3.org/2000/svg">
                    <rect x="0"  y="0" width="10" height="36" fill="white" rx="2"/>
                    <rect x="14" y="0" width="10" height="36" fill="white" rx="2"/>
                    <rect x="28" y="0" width="10" height="36" fill="white" rx="2"/>
                    <rect x="42" y="0" width="10" height="36" fill="white" rx="2"/>
                </svg>
                <div style="line-height: 1.2;">
                    <div style="font-size: 22px; font-weight: 700; letter-spacing: 0.5px;">Dell Technologies</div>
                    <div style="font-size: 14px; font-weight: 400; opacity: 0.85; letter-spacing: 1px; text-transform: uppercase;">PowerScale</div>
                </div>
            </div>
        </div>
        <h1>PowerScale Compliance & Security Audit Report</h1>
        <p><strong>Generated:</strong> [DATE_TIME]</p>
        <p><strong>Audit Period:</strong> [START_DATE] to [END_DATE]</p>
    </div>

    <!-- TAB NAVIGATION -->
    <div class="tabs">
        <button class="tab-button active" onclick="openTab(event, 'cluster-comp-1')">Cluster 1: [CLUSTER_NAME_1]</button>
        <button class="tab-button" onclick="openTab(event, 'cluster-comp-2')">Cluster 2: [CLUSTER_NAME_2]</button>
        <!-- DUPLICATE TAB BUTTONS FOR ADDITIONAL CLUSTERS -->
    </div>

    <!-- CLUSTER 1 TAB CONTENT -->
    <div id="cluster-comp-1" class="tab-content active">
        <div class="cluster-info">
            <strong>Cluster:</strong> [CLUSTER_NAME_1] | <strong>Host:</strong> [CLUSTER_HOST_1]
        </div>

    <div class="section">
        <h2>Configuration Compliance Checklist</h2>
        <div class="checklist">
            <div class="checklist-item">
                <input type="checkbox" id="smb_enc" [CHECKED]>
                <label for="smb_enc">SMB encryption enabled: <strong>[YES/NO]</strong></label>
            </div>
            <div class="checklist-item">
                <input type="checkbox" id="smb_sign" [CHECKED]>
                <label for="smb_sign">SMB signing enabled: <strong>[YES/NO]</strong></label>
            </div>
            <div class="checklist-item">
                <input type="checkbox" id="nfs_secure" [CHECKED]>
                <label for="nfs_secure">NFS secure mounts enforced: <strong>[YES/NO]</strong></label>
            </div>
            <div class="checklist-item">
                <input type="checkbox" id="anon_access" [CHECKED]>
                <label for="anon_access">Anonymous access disabled: <strong>[YES/NO]</strong></label>
            </div>
            <div class="checklist-item">
                <input type="checkbox" id="audit_log" [CHECKED]>
                <label for="audit_log">Audit logging enabled: <strong>[YES/NO]</strong></label>
            </div>
            <div class="checklist-item">
                <input type="checkbox" id="antivirus" [CHECKED]>
                <label for="antivirus">Antivirus scanning enabled: <strong>[YES/NO]</strong></label>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Security Hardening Status</h2>
        <table>
            <thead>
                <tr>
                    <th>Control</th>
                    <th>Status</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Access Control</td>
                    <td><span class="pass">✓</span></td>
                    <td>[DETAILS]</td>
                </tr>
                <tr>
                    <td>Encryption</td>
                    <td><span class="pass">✓</span></td>
                    <td>[DETAILS]</td>
                </tr>
                <tr>
                    <td>Audit Trail</td>
                    <td><span class="pass">✓</span></td>
                    <td>[DETAILS]</td>
                </tr>
                <tr>
                    <td>User Management</td>
                    <td><span class="pass">✓</span></td>
                    <td>[DETAILS]</td>
                </tr>
                <tr>
                    <td>Data Retention</td>
                    <td><span class="pass">✓</span></td>
                    <td>[DETAILS]</td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>Identified Issues</h2>
        <table>
            <thead>
                <tr>
                    <th>Issue</th>
                    <th>Severity</th>
                    <th>Status</th>
                    <th>Due Date</th>
                </tr>
            </thead>
            <tbody>
                <tr class="high">
                    <td>[ISSUE]</td>
                    <td>HIGH</td>
                    <td>[OPEN/IN PROGRESS]</td>
                    <td>[DATE]</td>
                </tr>
                <tr class="medium">
                    <td>[ISSUE]</td>
                    <td>MEDIUM</td>
                    <td>[OPEN/IN PROGRESS]</td>
                    <td>[DATE]</td>
                </tr>
                <tr class="low">
                    <td>[ISSUE]</td>
                    <td>LOW</td>
                    <td>[OPEN/IN PROGRESS]</td>
                    <td>[DATE]</td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="section">
        <div class="signoff-box">
            <h2 style="margin-top: 0;">Sign-Off</h2>
            <div class="signoff-item"><strong>Auditor:</strong> [NAME]</div>
            <div class="signoff-item"><strong>Date:</strong> [DATE]</div>
            <div class="signoff-item"><strong>Signature:</strong> ___________________________</div>
            <div class="signoff-item"><strong>Next Audit:</strong> [DATE]</div>
        </div>
    </div>
    </div>

    <!-- CLUSTER 2 TAB CONTENT -->
    <div id="cluster-comp-2" class="tab-content">
        <div class="cluster-info">
            <strong>Cluster:</strong> [CLUSTER_NAME_2] | <strong>Host:</strong> [CLUSTER_HOST_2]
        </div>

        <div class="section">
            <h2>Configuration Compliance Checklist</h2>
            <div class="checklist">
                <div class="checklist-item">
                    <input type="checkbox" id="smb_enc_2" [CHECKED]>
                    <label for="smb_enc_2">SMB encryption enabled: <strong>[YES/NO]</strong></label>
                </div>
                <div class="checklist-item">
                    <input type="checkbox" id="smb_sign_2" [CHECKED]>
                    <label for="smb_sign_2">SMB signing enabled: <strong>[YES/NO]</strong></label>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Security Hardening Status</h2>
            <table>
                <thead>
                    <tr>
                        <th>Control</th>
                        <th>Status</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Access Control</td>
                        <td><span class="pass">✓</span></td>
                        <td>[DETAILS]</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Identified Issues</h2>
            <table>
                <thead>
                    <tr>
                        <th>Issue</th>
                        <th>Severity</th>
                        <th>Status</th>
                        <th>Due Date</th>
                    </tr>
                </thead>
                <tbody>
                    <tr class="high">
                        <td>[ISSUE]</td>
                        <td>HIGH</td>
                        <td>[OPEN/IN PROGRESS]</td>
                        <td>[DATE]</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <div class="signoff-box">
                <h2 style="margin-top: 0;">Sign-Off</h2>
                <div class="signoff-item"><strong>Auditor:</strong> [NAME]</div>
                <div class="signoff-item"><strong>Date:</strong> [DATE]</div>
                <div class="signoff-item"><strong>Signature:</strong> ___________________________</div>
                <div class="signoff-item"><strong>Next Audit:</strong> [DATE]</div>
            </div>
        </div>
    </div>

    <!-- DUPLICATE CLUSTER TAB CONTENT BLOCKS FOR MORE CLUSTERS -->

    <div class="footer">
        <p>This report was automatically generated by PowerScale MCP Server</p>
    </div>
</body>
</html>
```

---

## Dell Technologies Branding

All templates now include **Dell Technologies branding** with the following design elements:

### Logo

Each report includes an embedded **Dell + PowerScale logo** in the header:
- **Format**: Scalable SVG (self-contained, no external images needed)
- **Location**: Top-left of header with "Dell Technologies" badge
- **Design**: Stylized Dell rectangles + "PowerScale" text
- **Colors**: White on Dell Blue gradient background
- **Responsive**: Automatically scales on all devices

### Dell Brand Colors
- **Primary Blue**: `#0076CE` (Dell Official Blue)
- **Accent Colors**:
  - Success Green: `#7ab800`
  - Warning Orange: `#f2af00`
  - Critical Red: `#dc5034`
  - Crimson: `#ce1126`
  - Dark Teal: `#244739`
- **Neutral**: Dark Gray `#454545`, Light Gray `#EFEFEF`, White `#FFFFFF`

### Typography
- **Font**: Roboto (Dell's official digital typeface)
- **Fallback**: -apple-system, BlinkMacSystemFont, segoe ui, helvetica, arial, sans-serif
- **Font Weights**: 400 (regular), 500 (medium), 600 (semi-bold), 700 (bold)

### Design Patterns
- **Header**: Dell Blue gradient background with white text
- **Tabs**: Rounded corners, smooth transitions, hover effects
- **Cards/Sections**: Subtle shadow, left border accent in Dell Blue
- **Status Indicators**: Color-coded (green=healthy, orange=warning, red=critical)
- **Spacing**: Consistent 15-20px padding, 15px gaps between sections
- **Border Radius**: 5px for cards and buttons

### Branding Notice
Reports include optional Dell Technologies branding footer. To add logo/watermark, include this HTML in the footer section:
```html
<div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd;">
    <p style="font-size: 0.85em; color: #666;">
        <strong>Dell PowerScale Report</strong> — Powered by Dell Technologies |
        <a href="https://www.delltechnologies.com" style="color: #0076CE; text-decoration: none;">delltechnologies.com</a>
    </p>
</div>
```

---

## Customization Guide

### File Naming & Storage
1. **Location**: Save all reports to current working directory (`./`)
2. **Naming Pattern (Single Cluster)**: `powerscale_report_[TYPE]_[YYYYMMDD]_[HHMMSS].html`
3. **Naming Pattern (Multi-Cluster)**: `powerscale_report_[TYPE]_multi_[YYYYMMDD]_[HHMMSS].html`
4. **Auto-timestamp**: Use current date/time when generating reports
5. **File Type**: Always use `.html` extension for browser viewing
6. **Cluster Tabs**: All templates support 1+ clusters. Create tabs for each cluster in the HTML (see examples below)

### Multi-Cluster Reports (Tabbed Interface)

Each template includes a **tabbed interface** that allows displaying data from multiple clusters in the same report. Tabs make it easy to compare metrics across clusters.

**How to add/modify clusters**:

1. **For 1 cluster** (default): Just fill in placeholders under `cluster-1` tab content
2. **For 2+ clusters**:
   - Copy the `<button class="tab-button">` line and create new buttons (change cluster number and name)
   - Copy the entire `<div id="cluster-X" class="tab-content">` block and duplicate for each cluster
   - Update placeholders (`[CLUSTER_NAME_N]`, `[CLUSTER_HOST_N]`, data values)
   - Each cluster's data goes in its own `<div id="cluster-X">` block
   - Comment: `<!-- DUPLICATE CLUSTER TAB CONTENT BLOCKS FOR MORE CLUSTERS -->` shows where to add more

**Example**: Adding Cluster 3
```html
<!-- In tabs section, add button: -->
<button class="tab-button" onclick="openTab(event, 'cluster-1')">Cluster 3: [CLUSTER_NAME_3]</button>

<!-- In content, duplicate and update: -->
<div id="cluster-3" class="tab-content">
    <div class="cluster-info">
        <strong>Cluster:</strong> [CLUSTER_NAME_3] | <strong>Host:</strong> [CLUSTER_HOST_3]
    </div>
    <!-- ... rest of content ... -->
</div>
```

### How to Modify Templates
1. **Replace Placeholders**: `[PLACEHOLDER]` with actual values from MCP tool responses
2. **Add/Remove Sections**: Keep what's relevant to your use case
3. **Adjust Metrics**: Focus on KPIs that matter for your organization
4. **Set Thresholds**: Update warning/critical levels for your environment
5. **Styling**: Edit CSS in the `<style>` block to match your organization's colors/branding
6. **Multi-Cluster**: Duplicate cluster content blocks for each cluster being reported

### Placeholder Reference
| Placeholder | Source | Example |
|------------|--------|---------|
| `[DATE]` | Current date | 2026-03-20 |
| `[DATE_TIME]` | Full timestamp | 2026-03-20 14:30:22 |
| `[YYYYMMDD]` | Filename date format | 20260320 |
| `[HHMMSS]` | Filename time format | 143022 |
| `[CLUSTER_NAME_1]` | First cluster from vault | PowerScale-Prod-01 |
| `[CLUSTER_NAME_2]` | Second cluster from vault | PowerScale-Prod-02 |
| `[CLUSTER_HOST_1]` | First cluster IP/hostname | 192.168.1.10 |
| `[CLUSTER_HOST_2]` | Second cluster IP/hostname | 192.168.1.11 |
| `[SIZE]` | From capacity_get | 50.5 TiB |
| `[PERCENT]` | Calculated % | 75 |
| `[COUNT]` | From tool response | 42 |
| `[NAME]` | Resource name | data-share |
| `[PATH]` | File path | /ifs/data |
| `[DETAILS]` | Tool output | All nodes participating |
| `[HEALTHY/WARNING/CRITICAL]` | Health status | HEALTHY |

### Example Integration Prompt
```
Generate a Cluster Health Report for [CLUSTER_NAME]:

1. Call powerscale_health_check() to get overall health
2. Call powerscale_capacity_get() to get storage utilization
3. Call powerscale_snapshots_get() to get snapshot count
4. Call powerscale_quota_get(limit=5) to get top quota consumers

Format results into the Cluster Health & Status Report HTML template.
Add a Recommendations section based on findings.

Save as: powerscale_report_health_[YYYYMMDD]_[HHMMSS].html in current directory
```

### MCP Tools by Report Type
| Report Type | Primary Tools | Secondary Tools |
|-------------|---------------|-----------------|
| **Health & Status** | health_check, capacity_get | snapshots_get, quota_get |
| **Quota Management** | quota_get, quota_list_by_type | — |
| **Data Protection** | snapshots_get, snapshot_schedules_get | synciq_get |
| **File Services** | smb_shares_get, nfs_exports_get | s3_buckets_get |
| **Capacity Planning** | capacity_get, hardware_get | performance_get |
| **Compliance** | smb_settings_get, nfs_settings_get | hardening_get |

### Batch Report Generation
To generate all reports at once:
```
1. powerscale_report_health_[TS].html      (use health_check, capacity_get)
2. powerscale_report_quota_[TS].html       (use quota_get)
3. powerscale_report_dataprotection_[TS].html (use snapshots_get, snapshot_schedules_get)
4. powerscale_report_fileservices_[TS].html   (use smb_shares_get, nfs_exports_get)
5. powerscale_report_capacity_[TS].html    (use capacity_get, hardware_get)
6. powerscale_report_compliance_[TS].html  (use smb_settings_get, nfs_settings_get)
```

### Tab Navigation Features

All templates include **JavaScript-powered tab switching** for seamless cluster comparison:

- **Click tabs** to instantly switch between clusters
- **Active tab** is highlighted in blue with white text
- **Smooth transitions** between cluster data
- **Works offline** — no external dependencies required
- **Print-friendly** — prints the currently active tab

**Tab Styling**:
- Active tab: `#1a5490` (blue background, white text)
- Inactive tab: `#f0f0f0` (gray background, dark text)
- Hover effect: Slightly darker gray
- Mobile-friendly: Tabs wrap to new line if needed

### HTML Best Practices
- **Color Scheme**: Primary (#1a5490 blue), Success (#28a745 green), Warning (#ffc107 yellow), Critical (#dc3545 red)
- **Responsive**: All templates use `meta viewport` and CSS Grid for mobile compatibility
- **Print-Friendly**: Tables and sections are designed to print cleanly to PDF
- **Accessibility**: Use semantic HTML and color + text indicators (not color-only)
- **Data Freshness**: Always include generated timestamp in header for audit trail
- **Cluster Isolation**: Each cluster's data is fully contained in its own tab — no cross-cluster data bleed

### Opening Reports
- Double-click `.html` file to open in default browser
- Reports are fully self-contained (all CSS inline, no external dependencies)
- Can be emailed, archived, or printed to PDF directly from browser

---

## Dell Technologies Branding Implementation Summary

All six report templates have been fully updated with Dell Technologies enterprise branding, design system, and corporate identity standards.

### Visual Design Changes

**Colors Applied**:
- **Primary**: Dell Blue (`#0076CE`) — Header, section accents, links
- **Success**: Limeade Green (`#7ab800`) — Healthy status indicators
- **Warning**: Yellow Sea (`#f2af00`) — Caution/approach threshold alerts
- **Critical**: Punch Red (`#dc5034`) — Error/critical status indicators
- **Neutral**: Dark Gray (`#454545`), Light Gray (`#EFEFEF`), White (`#FFFFFF`)

**Typography Applied**:
- **Font Family**: Roboto (Dell's official digital typeface) with fallbacks to system fonts
- **Font Weights**: 400 (regular), 500 (medium), 600 (semi-bold for headings)
- **Font Scaling**: Modern hierarchy with 28px headers, 20px section titles, 14px body text

**Design Elements**:
- **Header**: Gradient background (Dell Blue to darker blue) with subtle shadow
- **Sections**: White cards with left border accent, light shadow, 8px border-radius
- **Tabs**: Rounded navigation with active state highlighting, smooth transitions
- **Summary Cards**: Gradient background with top border accent, uppercase labels
- **Tables**: Clean styling with hover effects, uppercase column headers
- **Status Indicators**: Color-coded with font-weight emphasis (not color-only)
- **Spacing**: Consistent 15-20px padding, 15px gaps between sections

### Accessibility & Standards

✅ **WCAG Compliance**: Color + text indicators (not color-only)
✅ **Contrast Ratios**: Meet AA standards for readability
✅ **Print-Friendly**: Reports print cleanly to PDF, preserving branding
✅ **Responsive**: Mobile-friendly with flexible grid layouts
✅ **No External Dependencies**: All CSS is inline, fully self-contained

### Branding Footer (Optional)

To add Dell Technologies branding footer to any report:

```html
<div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd;">
    <p style="font-size: 0.85em; color: #666;">
        <strong>Dell PowerScale Report</strong> — Powered by Dell Technologies |
        <a href="https://www.delltechnologies.com" style="color: #0076CE; text-decoration: none;">delltechnologies.com</a>
    </p>
</div>
```

### Customizing the Logo

The logo is an embedded SVG in each report header. To modify it:

**Edit the SVG directly**:
```html
<svg width="120" height="40" viewBox="0 0 120 40" xmlns="http://www.w3.org/2000/svg">
    <!-- Dell Logo (4 white rectangles) -->
    <rect x="5" y="10" width="8" height="20" fill="white" rx="1"/>
    <rect x="18" y="10" width="8" height="20" fill="white" rx="1"/>
    <rect x="31" y="10" width="8" height="20" fill="white" rx="1"/>
    <rect x="44" y="10" width="8" height="20" fill="white" rx="1"/>
    <!-- PowerScale Text -->
    <text x="60" y="28" font-family="Roboto, sans-serif" font-size="16" font-weight="600" fill="white">PowerScale</text>
</svg>
```

**Customization options**:
- Change `width="120"` and `height="40"` to scale logo size
- Modify `fill="white"` to change color (e.g., `fill="#0076CE"` for solid blue)
- Edit `PowerScale` text to use a different product name
- Adjust `x` and `y` coordinates to reposition elements
- Remove "Dell Technologies" badge div for logo-only design

**Remove the logo entirely**:
Delete the entire `<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">` block before the `<h1>` tag.

### Updating Brand Colors

To apply different colors across all templates:

1. Find and replace in CSS:
   - `#0076CE` (primary blue) → your color
   - `#7ab800` (success green) → your color
   - `#f2af00` (warning orange) → your color
   - `#dc5034` (critical red) → your color
   - `#454545` (text dark) → your color

2. Update gradient overlays:
   - Search for `linear-gradient(135deg, #0076CE 0%, #0059a3 100%)` and adjust both colors

3. Update logo colors:
   - Change `fill="white"` in SVG rectangles to match your color scheme

### Design System References

- **Color System**: [Dell Design System - Color](https://www.delldesignsystem.com/foundations/color/)
- **Typography**: [Dell Design System - Typography](https://www.delldesignsystem.com/foundations/typography/)
- **Brand Portal**: [Dell Technologies Brand](https://brand.delltechnologies.com)

### Logo Implementation Notes

✅ **Embedded SVG Format**
- All logos are self-contained (no external image files needed)
- Scales perfectly on any device (retina displays, mobile, print)
- No performance impact (SVG is lightweight)

✅ **Header Integration**
- Logo appears in top-left corner of gradient header
- "Dell Technologies" company badge in top-right
- Responsive flexbox layout adjusts on mobile

✅ **Customization**
- Change logo size by modifying SVG `width` and `height` attributes
- Change logo color by modifying `fill` attributes
- Replace "PowerScale" text with your product name
- See "Customizing the Logo" section above for code examples

✅ **Print-Ready**
- Logo prints clearly to PDF
- Maintains quality at any size
- Works with all browsers and PDF viewers

---
