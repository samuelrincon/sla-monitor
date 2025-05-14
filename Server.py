from flask import Flask, render_template_string, request, make_response
import requests
from bs4 import BeautifulSoup
import threading
import time
from datetime import datetime
import uuid
import os

app = Flask(__name__)

# Configuration
API_URL = "https://reports.intouchcx.com/reports/lib/getRealtimeManagementFull.asp"
REFRESH_INTERVAL = 15000  # 15 seconds

# User sessions storage
user_sessions = {}

# HTML Template for the main interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Levi's - Real-Time Call Monitoring</title>
    <style>
        :root {
            --primary-color: #6A0DAD;
            --secondary-color: #c41230;
            --background-color: #F6F0FF;
            --card-bg: #FFFFFF;
            --text-color: #333333;
            --error-color: #d9534f;
            --warning-color: #f0ad4e;
            --success-color: #5cb85c;
            --info-color: #5bc0de;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: var(--background-color);
            color: var(--text-color);
        }
        
        .header {
            background-color: var(--primary-color);
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .header-title {
            font-size: 24px;
            font-weight: bold;
        }
        
        .header-brand {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .levis-badge {
            background-color: var(--secondary-color);
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
        }
        
        .main-container {
            padding: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .dashboard-card {
            background-color: var(--card-bg);
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .card-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
            color: var(--primary-color);
            border-bottom: 2px solid var(--primary-color);
            padding-bottom: 8px;
        }
        
        .notification {
            background-color: var(--warning-color);
            color: white;
            padding: 12px;
            border-radius: 5px;
            margin-bottom: 20px;
            text-align: center;
            font-weight: bold;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 14px;
        }
        
        th {
            background-color: var(--primary-color);
            color: white;
            padding: 12px;
            text-align: left;
            position: sticky;
            top: 0;
        }
        
        td {
            padding: 10px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        
        tr:hover {
            background-color: #f1f1f1;
        }
        
        .normal-row {
            background-color: #DAC8FF;
        }
        
        .alternate-row {
            background-color: #D0B5FF;
        }
        
        .calls-warning {
            background-color: #E66F6F;
        }
        
        .sl-warning {
            background-color: #CE2424;
            color: white;
        }
        
        .both-warning {
            background-color: #660002;
            color: white;
        }
        
        .button-group {
            display: flex;
            gap: 10px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        
        .button {
            display: inline-block;
            padding: 10px 20px;
            background-color: var(--primary-color);
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            transition: background-color 0.3s;
            border: none;
            cursor: pointer;
            font-size: 14px;
        }
        
        .button:hover {
            background-color: #5a0b9d;
        }
        
        .button-warning {
            background-color: var(--warning-color);
        }
        
        .button-warning:hover {
            background-color: #ec971f;
        }
        
        .button-danger {
            background-color: var(--error-color);
        }
        
        .button-danger:hover {
            background-color: #c9302c;
        }
        
        .last-update {
            text-align: right;
            font-style: italic;
            color: #666;
            margin-top: 10px;
            font-size: 12px;
        }
        
        .status-badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }
        
        .status-acd {
            background-color: #5cb85c;
            color: white;
        }
        
        .status-aux {
            background-color: #f0ad4e;
            color: white;
        }
        
        .status-acw {
            background-color: #5bc0de;
            color: white;
        }
        
        .status-other {
            background-color: #d9534f;
            color: white;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-brand">
            <div class="header-title">IntouchCX</div>
            <div class="levis-badge">Levi's</div>
        </div>
        <div>
            <a href="/queue-dashboard" class="button">Switch to Queue Dashboard</a>
        </div>
    </div>
    
    <div class="main-container">
        {% if notification %}
        <div class="notification">{{ notification }}</div>
        {% endif %}
        
        <div class="dashboard-card">
            <div class="card-title">Agent Status</div>
            
            <table>
                <thead>
                    <tr>
                        <th>Avaya ID</th>
                        <th>Full Name</th>
                        <th>State</th>
                        <th>Reason Code</th>
                        <th>Active Call</th>
                        <th>Call Duration</th>
                        <th>Skill Name</th>
                        <th>Time in State</th>
                    </tr>
                </thead>
                <tbody>
                    {% for agent in agents %}
                    <tr class="{{ agent.row_class }}">
                        <td>{{ agent.avaya_id }}</td>
                        <td>{{ agent.full_name }}</td>
                        <td>
                            <span class="status-badge status-{{ agent.state_class }}">{{ agent.state }}</span>
                        </td>
                        <td>{{ agent.reason_code }}</td>
                        <td>{{ agent.active_call }}</td>
                        <td>{{ agent.call_duration }}</td>
                        <td>{{ agent.skill_name }}</td>
                        <td>{{ agent.time_in_state }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            
            <div class="button-group">
                <a href="/alerts" class="button button-warning">View Alerts ({{ alerts_count }})</a>
                <a href="/aux" class="button button-warning">View AUX Status ({{ aux_count }})</a>
                <a href="/queue" class="button button-danger">View Queue ({{ queue_count }})</a>
                <a href="/settings" class="button">Settings</a>
            </div>
            
            <div class="last-update">Last updated: {{ update_time }}</div>
        </div>
    </div>
    
    <script>
        // Auto-refresh the page every 15 seconds
        setTimeout(function() {
            window.location.reload();
        }, {{ refresh_interval }});
    </script>
</body>
</html>
"""

# Template for alerts page
ALERTS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Active Alerts</title>
    <style>
        :root {
            --primary-color: #6A0DAD;
            --error-color: #d9534f;
            --warning-color: #f0ad4e;
            --background-color: #FFB6C1;
            --card-bg: #FFFFFF;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: var(--background-color);
        }
        
        .header {
            background-color: var(--primary-color);
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .header-title {
            font-size: 24px;
            font-weight: bold;
        }
        
        .main-container {
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
        }
        
        .alert-card {
            background-color: var(--card-bg);
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .alert-title {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 15px;
            color: var(--error-color);
        }
        
        .alert-item {
            padding: 10px;
            border-bottom: 1px solid #eee;
        }
        
        .alert-type {
            font-weight: bold;
            color: var(--error-color);
            margin-top: 15px;
            font-size: 16px;
        }
        
        .no-alerts {
            text-align: center;
            padding: 20px;
            color: #666;
            font-style: italic;
        }
        
        .button {
            display: inline-block;
            padding: 10px 20px;
            background-color: var(--primary-color);
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            transition: background-color 0.3s;
        }
        
        .button:hover {
            background-color: #5a0b9d;
        }
        
        .button-container {
            text-align: center;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-title">⚠️ ACTIVE ALERTS ⚠️</div>
    </div>
    
    <div class="main-container">
        <div class="alert-card">
            {% if alerts %}
                {% for alert_type, items in alerts.items() %}
                    <div class="alert-type">{{ alert_type }}</div>
                    {% for item in items %}
                        <div class="alert-item">{{ item }}</div>
                    {% endfor %}
                {% endfor %}
            {% else %}
                <div class="no-alerts">No active alerts at this time</div>
            {% endif %}
            
            <div class="button-container">
                <a href="/" class="button">Back to Dashboard</a>
            </div>
        </div>
    </div>
    
    <script>
        // Auto-refresh the page every 15 seconds
        setTimeout(function() {
            window.location.reload();
        }, {{ refresh_interval }});
    </script>
</body>
</html>
"""

# Template for AUX status page
AUX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AUX Status</title>
    <style>
        :root {
            --primary-color: #6A0DAD;
            --warning-color: #f0ad4e;
            --background-color: #FFB6C1;
            --card-bg: #FFFFFF;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: var(--background-color);
        }
        
        .header {
            background-color: var(--primary-color);
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .header-title {
            font-size: 24px;
            font-weight: bold;
        }
        
        .main-container {
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
        }
        
        .aux-card {
            background-color: var(--card-bg);
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .aux-title {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 15px;
            color: var(--warning-color);
        }
        
        .aux-item {
            padding: 10px;
            border-bottom: 1px solid #eee;
        }
        
        .aux-type {
            font-weight: bold;
            color: var(--warning-color);
            margin-top: 15px;
            font-size: 16px;
        }
        
        .no-aux {
            text-align: center;
            padding: 20px;
            color: #666;
            font-style: italic;
        }
        
        .button {
            display: inline-block;
            padding: 10px 20px;
            background-color: var(--primary-color);
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            transition: background-color 0.3s;
        }
        
        .button:hover {
            background-color: #5a0b9d;
        }
        
        .button-container {
            text-align: center;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-title">AUX Status</div>
    </div>
    
    <div class="main-container">
        <div class="aux-card">
            {% if aux_list %}
                {% for aux_type, items in aux_list.items() %}
                    <div class="aux-type">{{ aux_type }}</div>
                    {% for item in items %}
                        <div class="aux-item">{{ item }}</div>
                    {% endfor %}
                {% endfor %}
            {% else %}
                <div class="no-aux">No agents in AUX status</div>
            {% endif %}
            
            <div class="button-container">
                <a href="/" class="button">Back to Dashboard</a>
            </div>
        </div>
    </div>
    
    <script>
        // Auto-refresh the page every 15 seconds
        setTimeout(function() {
            window.location.reload();
        }, {{ refresh_interval }});
    </script>
</body>
</html>
"""

# Template for queue page
QUEUE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Calls in Queue</title>
    <style>
        :root {
            --primary-color: #6A0DAD;
            --error-color: #d9534f;
            --warning-color: #f0ad4e;
            --background-color: #FFB6C1;
            --card-bg: #FFFFFF;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: var(--background-color);
        }
        
        .header {
            background-color: var(--primary-color);
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .header-title {
            font-size: 24px;
            font-weight: bold;
        }
        
        .main-container {
            padding: 20px;
            max-width: 1000px;
            margin: 0 auto;
        }
        
        .queue-card {
            background-color: var(--card-bg);
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .queue-title {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 15px;
            color: var(--error-color);
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 14px;
        }
        
        th {
            background-color: var(--primary-color);
            color: white;
            padding: 12px;
            text-align: left;
        }
        
        td {
            padding: 10px;
            border-bottom: 1px solid #eee;
        }
        
        .has-calls {
            background-color: #ffcccc;
        }
        
        .no-queue {
            text-align: center;
            padding: 20px;
            color: #666;
            font-style: italic;
        }
        
        .button {
            display: inline-block;
            padding: 10px 20px;
            background-color: var(--primary-color);
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            transition: background-color 0.3s;
        }
        
        .button:hover {
            background-color: #5a0b9d;
        }
        
        .button-container {
            text-align: center;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-title">Calls in Queue</div>
    </div>
    
    <div class="main-container">
        <div class="queue-card">
            {% if queue_list %}
                <table>
                    <thead>
                        <tr>
                            <th>Skill Name</th>
                            <th>Calls in Queue</th>
                            <th>Oldest Call</th>
                            <th>Staffed</th>
                            <th>Available</th>
                            <th>RT SL %</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for skill in queue_list %}
                            {% if skill.calls_in_queue != '0' %}
                            <tr class="has-calls">
                                <td>{{ skill.skill_name }}</td>
                                <td>{{ skill.calls_in_queue }}</td>
                                <td>{{ skill.oldest_call }}</td>
                                <td>{{ skill.staffed }}</td>
                                <td>{{ skill.available }}</td>
                                <td>{{ skill.rt_sl }}</td>
                            </tr>
                            {% endif %}
                        {% endfor %}
                    </tbody>
                </table>
            {% else %}
                <div class="no-queue">No calls currently in queue</div>
            {% endif %}
            
            <div class="button-container">
                <a href="/" class="button">Back to Dashboard</a>
            </div>
        </div>
    </div>
    
    <script>
        // Auto-refresh the page every 15 seconds
        setTimeout(function() {
            window.location.reload();
        }, {{ refresh_interval }});
    </script>
</body>
</html>
"""

# Template for queue dashboard
# Template for queue dashboard (corregido)
QUEUE_DASHBOARD_TEMPLATE = r"""
<!DOCTYPE html>
<html>
<head>
    <title>Queue Monitoring Dashboard</title>
    <style>
        :root {
            --primary-color: #6A0DAD;
            --secondary-color: #c41230;
            --background-color: #6a0dad;
            --card-bg: #FFFFFF;
            --text-color: #333333;
            --error-color: #d9534f;
            --warning-color: #f0ad4e;
            --success-color: #5cb85c;
            --info-color: #5bc0de;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: var(--background-color);
            color: white;
        }
        
        .header {
            background-color: var(--primary-color);
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }
        
        .header-title {
            font-size: 24px;
            font-weight: bold;
        }
        
        .header-brand {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .levis-badge {
            background-color: var(--secondary-color);
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
        }
        
        .main-container {
            padding: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .dashboard-card {
            background-color: var(--card-bg);
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            padding: 20px;
            margin-bottom: 20px;
            color: var(--text-color);
        }
        
        .card-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
            color: var(--primary-color);
            border-bottom: 2px solid var(--primary-color);
            padding-bottom: 8px;
        }
        
        .control-panel {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
            background-color: rgba(255, 255, 255, 0.1);
            padding: 15px;
            border-radius: 5px;
        }
        
        .view-buttons {
            display: flex;
            gap: 10px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 14px;
        }
        
        th {
            background-color: var(--primary-color);
            color: white;
            padding: 12px;
            text-align: left;
            position: sticky;
            top: 0;
        }
        
        td {
            padding: 10px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .normal-row {
            background-color: #DAC8FF;
        }
        
        .alternate-row {
            background-color: #D0B5FF;
        }
        
        .calls-warning {
            background-color: #E66F6F;
        }
        
        .sl-warning {
            background-color: #CE2424;
            color: white;
        }
        
        .both-warning {
            background-color: #660002;
            color: white;
        }
        
        .button {
            display: inline-block;
            padding: 10px 20px;
            background-color: var(--primary-color);
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            transition: background-color 0.3s;
            border: none;
            cursor: pointer;
            font-size: 14px;
        }
        
        .button:hover {
            background-color: #5a0b9d;
        }
        
        .button-active {
            background-color: #8a2be2;
        }
        
        .button-warning {
            background-color: var(--warning-color);
        }
        
        .button-warning:hover {
            background-color: #ec971f;
        }
        
        .button-danger {
            background-color: var(--error-color);
        }
        
        .button-danger:hover {
            background-color: #c9302c;
        }
        
        .last-update {
            text-align: right;
            font-style: italic;
            color: #666;
            margin-top: 10px;
            font-size: 12px;
        }
        
        .action-buttons {
            display: flex;
            gap: 10px;
        }
        
        .toast {
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: #4CAF50;
            color: white;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            z-index: 1000;
            display: none;
            animation: fadein 0.5s, fadeout 0.5s 2.5s;
        }
        
        .toast.error {
            background-color: #f44336;
        }
        
        @keyframes fadein {
            from {top: 0; opacity: 0;}
            to {top: 20px; opacity: 1;}
        }
        
        @keyframes fadeout {
            from {top: 20px; opacity: 1;}
            to {top: 0; opacity: 0;}
        }
        
        .copy-help {
            margin-top: 10px;
            font-size: 12px;
            color: #666;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-brand">
            <div class="header-title">Queue Monitoring Dashboard</div>
            <div class="levis-badge">Levi's</div>
        </div>
        <div class="action-buttons">
            <a href="/" class="button">Back to Agent Dashboard</a>
            <button id="copySlaBtn" class="button button-warning">Copy SLA Data</button>
        </div>
    </div>
    
    <div id="toast" class="toast"></div>
    
    <div class="main-container">
        <div class="dashboard-card">
            <div class="control-panel">
                <div class="view-buttons">
                    <a href="?view=main" class="button {% if view == 'main' %}button-active{% endif %}">Main View</a>
                    <a href="?view=agents" class="button {% if view == 'agents' %}button-active{% endif %}">Agents View</a>
                </div>
            </div>
            
            <table id="skillsTable">
                <thead>
                    <tr>
                        {% if view == 'main' %}
                            <th>Skill Name</th>
                            <th>Calls in Queue</th>
                            <th>Offered</th>
                            <th>Answered</th>
                            <th>Transfers</th>
                            <th>True Abn</th>
                            <th>Short Abn</th>
                            <th>Oldest Call</th>
                            <th>Max Delay</th>
                            <th>ASA</th>
                            <th>AQT</th>
                            <th>Service Level %</th>
                            <th>RT SL %</th>
                        {% else %}
                            <th>Skill Name</th>
                            <th>Staffed</th>
                            <th>Available</th>
                            <th>ACW</th>
                            <th>ACD</th>
                            <th>AUX</th>
                            <th>Other</th>
                        {% endif %}
                    </tr>
                </thead>
                <tbody>
                    {% for skill in skills %}
                    <tr class="{{ skill.row_class }}">
                        {% if view == 'main' %}
                            <td>{{ skill.skill_name }}</td>
                            <td>{{ skill.calls_in_queue }}</td>
                            <td>{{ skill.offered }}</td>
                            <td>{{ skill.answered }}</td>
                            <td>{{ skill.transfers }}</td>
                            <td>{{ skill.true_abn }}</td>
                            <td>{{ skill.short_abn }}</td>
                            <td>{{ skill.oldest_call }}</td>
                            <td>{{ skill.max_delay }}</td>
                            <td>{{ skill.asa }}</td>
                            <td>{{ skill.aqt }}</td>
                            <td class="sla-value">{{ skill.service_level }}</td>
                            <td>{{ skill.rt_sl }}</td>
                        {% else %}
                            <td>{{ skill.skill_name }}</td>
                            <td>{{ skill.staffed }}</td>
                            <td>{{ skill.available }}</td>
                            <td>{{ skill.acw }}</td>
                            <td>{{ skill.acd }}</td>
                            <td>{{ skill.aux }}</td>
                            <td>{{ skill.other }}</td>
                        {% endif %}
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            
            <div class="last-update">Last updated: {{ update_time }}</div>
            <div class="copy-help">Click "Copy SLA Data" to copy the SLA information to clipboard</div>
        </div>
    </div>
    
    <script>
        // Auto-refresh the page every 15 seconds
        setTimeout(function() {
            window.location.reload();
        }, {{ refresh_interval }});
        
        function showToast(message, isError = false) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = isError ? 'toast error' : 'toast';
            toast.style.display = 'block';
            setTimeout(() => {
                toast.style.display = 'none';
            }, 3000);
        }
        
        function copyToClipboard(text) {
            return new Promise((resolve, reject) => {
                // Try modern clipboard API first
                if (navigator.clipboard) {
                    navigator.clipboard.writeText(text).then(() => {
                        resolve(true);
                    }).catch(err => {
                        console.error('Modern clipboard failed:', err);
                        reject(err);
                    });
                } else {
                    // Fallback for older browsers
                    const textarea = document.createElement('textarea');
                    textarea.value = text;
                    textarea.style.position = 'fixed';
                    textarea.style.top = '0';
                    textarea.style.left = '0';
                    textarea.style.width = '2em';
                    textarea.style.height = '2em';
                    textarea.style.padding = '0';
                    textarea.style.border = 'none';
                    textarea.style.outline = 'none';
                    textarea.style.boxShadow = 'none';
                    textarea.style.background = 'transparent';
                    document.body.appendChild(textarea);
                    textarea.select();
                    
                    try {
                        const successful = document.execCommand('copy');
                        document.body.removeChild(textarea);
                        if (successful) {
                            resolve(true);
                        } else {
                            reject(new Error('Copy command failed'));
                        }
                    } catch (err) {
                        document.body.removeChild(textarea);
                        reject(err);
                    }
                }
            });
        }
        
        async function copySlaDataToClipboard() {
            try {
                const lowSlaSkills = [];
                const rows = document.querySelectorAll('#skillsTable tbody tr');
                
                // Collect SLA data
                rows.forEach(row => {
                    const skillName = row.querySelector('td:nth-child(1)')?.textContent.trim();
                    const slaText = row.querySelector('td.sla-value')?.textContent.trim();
                    
                    if (skillName && slaText) {
                        // Extract numeric value from SLA text
                        const slaValue = parseFloat(slaText.replace(/[^\d.]/g, ''));
                        if (!isNaN(slaValue) && slaValue < 80) {
                            lowSlaSkills.push({
                                name: skillName,
                                value: slaText
                            });
                        }
                    }
                });
                
                // Build the text to copy
                let textToCopy = "Voice - Queue\n\n";
                
                if (lowSlaSkills.length > 0) {
                    textToCopy += "Team, this is our current SLA view and listed you'll find the impacted skills so far:\n\n";
                    lowSlaSkills.forEach(skill => {
                        textToCopy += `-${skill.name} = ${skill.value}\n`;
                    });
                    textToCopy += "\nThe other skills are on target.";
                } else {
                    textToCopy += "All skills are meeting SLA targets (80% or above)";
                }
                
                // Copy to clipboard
                try {
                    await copyToClipboard(textToCopy);
                    showToast('SLA data copied to clipboard!');
                    console.log('Copied to clipboard:', textToCopy);
                } catch (error) {
                    console.error('Failed to copy:', error);
                    showToast('Failed to copy. Please copy manually:', true);
                    prompt('Copy this text:', textToCopy);
                }
            } catch (error) {
                console.error('Error generating SLA data:', error);
                showToast('Error generating SLA data', true);
            }
        }
        
        // Initialize after DOM is loaded
        document.addEventListener('DOMContentLoaded', function() {
            const copyBtn = document.getElementById('copySlaBtn');
            if (copyBtn) {
                copyBtn.addEventListener('click', copySlaDataToClipboard);
            }
        });
    </script>
</body>
</html>
"""

# Template for settings page
SETTINGS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Alert Settings</title>
    <style>
        :root {
            --primary-color: #6A0DAD;
            --error-color: #d9534f;
            --warning-color: #f0ad4e;
            --success-color: #5cb85c;
            --background-color: #F6F0FF;
            --card-bg: #FFFFFF;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: var(--background-color);
        }
        
        .header {
            background-color: var(--primary-color);
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .header-title {
            font-size: 24px;
            font-weight: bold;
        }
        
        .main-container {
            padding: 20px;
            max-width: 600px;
            margin: 0 auto;
        }
        
        .settings-card {
            background-color: var(--card-bg);
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .settings-title {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 20px;
            color: var(--primary-color);
            text-align: center;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        
        input {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }
        
        .message {
            padding: 10px;
            margin-bottom: 20px;
            border-radius: 5px;
            text-align: center;
        }
        
        .success {
            background-color: #d4edda;
            color: #155724;
        }
        
        .error {
            background-color: #f8d7da;
            color: #721c24;
        }
        
        .button-group {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 20px;
        }
        
        .button {
            display: inline-block;
            padding: 10px 20px;
            background-color: var(--primary-color);
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            transition: background-color 0.3s;
            border: none;
            cursor: pointer;
        }
        
        .button:hover {
            background-color: #5a0b9d;
        }
        
        .button-secondary {
            background-color: #6c757d;
        }
        
        .button-secondary:hover {
            background-color: #5a6268;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-title">Alert Settings</div>
    </div>
    
    <div class="main-container">
        <div class="settings-card">
            <div class="settings-title">Alert Threshold Settings</div>
            
            {% if message %}
            <div class="message {{ message.type }}">{{ message.text }}</div>
            {% endif %}
            
            <form method="POST" action="/settings">
                {% for alert, time in alert_times.items() %}
                <div class="form-group">
                    <label for="{{ alert }}">{{ alert }} (seconds):</label>
                    <input type="number" id="{{ alert }}" name="{{ alert }}" value="{{ time }}" min="1">
                </div>
                {% endfor %}
                
                <div class="button-group">
                    <button type="submit" class="button">Apply Changes</button>
                    <a href="/" class="button button-secondary">Cancel</a>
                    <button type="button" onclick="resetDefaults()" class="button button-secondary">Reset Defaults</button>
                </div>
            </form>
        </div>
    </div>
    
    <script>
        function resetDefaults() {
            document.getElementById('Long Call').value = 360;
            document.getElementById('Extended Lunch').value = 3600;
            document.getElementById('Long ACW').value = 120;
            document.getElementById('Extended Break').value = 900;
            document.getElementById('IT Issue').value = 30;
            document.getElementById('Long Hold').value = 120;
        }
    </script>
</body>
</html>
"""

class UserSession:
    def __init__(self):
        self.alert_times = {
            "Long Call": 360,
            "Extended Lunch": 3600,
            "Long ACW": 120,
            "Extended Break": 900,
            "IT Issue": 30,
            "Long Hold": 120
        }
        self.alert_list = []
        self.aux_list = []
        self.queue_list = []
        self.agents = []
        self.total_calls_in_queue = 0
        self.all_skills = {
            '1400': 'Levis EN (1400)',
            '1401': 'Levis FR (1401)',
            '1402': 'Levis Existing Order (1402)',
            '1403': 'Dockers EN (1403)',
            '1404': 'Dockers Existing Order EN (1404)',
            '1405': 'Dockers Place Order EN (1405)',
            '1406': 'Dockers Other Question EN (1406)',
            '1407': 'Dockers SP (1407)',
            '1408': 'Dockers Existing Order SP (1408)',
            '1409': 'Dockers Place Order SP (1409)',
            '1410': 'Dockers Other Question SP (1410)',
            '1411': 'Dockers Retail Express EN (1411)',
            '1412': 'Dockers Retail Express SP (1412)',
            '1413': 'Dockers CB EN (1413)',
            '1414': 'Dockers Existing Order CB EN (1414)',
            '1415': 'Dockers Place Order CB EN (1415)',
            '1416': 'Dockers Other CB EN (1416)',
            '1451': 'Levis Escalation Sup (1451)',
            '1452': 'Levis SP (1452)',
            '1453': 'Levis Existing Order SP (1453)',
            '1454': 'Levis Place Order EN (1454)',
            '1455': 'Levis Other EN (1455)',
            '1456': 'Levis Track Order SP (1456)',
            '1457': 'Levis Place Order SP (1457)',
            '1458': 'Levis Other SP (1458)',
            '1459': 'Levis Retail Express EN (1459)',
            '1460': 'Levis Retail Express SP (1460)',
            '1461': 'Levis CB EN (1461)',
            '1462': 'Levis Existing Order CB EN (1462)',
            '1463': 'Levis Place Order CB EN (1463)',
            '1464': 'Levis Retail Express CB EN (1464)',
            '1465': 'Levis Other CB EN (1465)'
        }
        
        # Start data update thread
        self.running = True
        self.update_thread = threading.Thread(target=self.update_data_loop, daemon=True)
        self.update_thread.start()
    
    def update_data_loop(self):
        while self.running:
            self.fetch_data()
            time.sleep(15)
    
    def fetch_data(self):
        try:
            payload = {
                'split': '1400,1401,1402,1403,1404,1405,1406,1407,1408,1409,1410,1411,1412,1413,1414,1415,1416,1450,1451,1452,1453,1454,1455,1456,1457,1458,1459,1460,1461,1462,1463,1464,1465',
                'firstSortCol': 'FullName',
                'firstSortDir': 'ASC',
                'secondSortCol': 'FullName',
                'secondSortDir': 'ASC',
                'reason': 'all',
                'state': 'all',
                'timezone': '0',
                'altSL': '',
                'threshold': '6',
                'altSLThreshold': '20',
                'acdAlert': '',
                'acwAlert': '',
                'holdAlert': '',
                'slAlert': '',
                'asaAlert': ''
            }

            headers = {
                'Accept': 'text/html, */*; q=0.01',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
                'Connection': 'keep-alive',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Cookie': '__adroll_fpc=c91374194297467eaf8d0b0867c5a19b-1736283603830; _ga_6Z70JWFY43=GS1.2.1738076373.1.1.1738076449.60.0.0; _clck=1cw5u6k|2|fvi|0|1833; _gcl_au=1.1.722387643.1746035415; _ga_8K57FD29VY=GS1.1.1746035412.3.1.1746036041.60.0.0; _ga_ZD2XJ0W0N5=GS2.2.s1746820075$o26$g0$t1746820075$j0$l0$h0; _ga=GA1.1.2034792510.1736283603; _ga_H56SEZF415=GS2.1.s1746824894$o169$g0$t1746824902$j0$l0$h0; ASPSESSIONIDCAQCAAAQ=JAOFBCMAFABLFPKJMGAJFENN',
                'Host': 'reports.intouchcx.com',
                'Origin': 'https://reports.intouchcx.com',
                'Referer': 'https://reports.intouchcx.com/reports/custom/levis/realtimemanagementfull.asp?altSLThreshold=20&threshold=6',
                'Sec-Ch-Ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
                'X-Requested-With': 'XMLHttpRequest'
            }

            response = requests.post(API_URL, headers=headers, data=payload, timeout=10)
            response.raise_for_status()
            
            self.process_response(response.text)
        except Exception as e:
            print(f"Error fetching data: {str(e)}")
    
    def time_to_seconds(self, time_str):
        try:
            parts = list(map(int, time_str.split(":")))
            if len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            elif len(parts) == 2:
                return parts[0] * 60 + parts[1]
            return 0
        except (ValueError, AttributeError):
            return 0
    
    def parse_queue_data(self, soup):
        data = []
        total_calls_in_queue = 0
        
        rows = soup.find_all('tr', class_='data')
        
        for row in rows:
            skill_cell = row.find('td', colspan='3', class_='nowrap')
            if skill_cell and 'Skill Name' not in skill_cell.get_text():
                skill_name = skill_cell.get_text(strip=True)
                skill_id = ""
                
                if "(" in skill_name and ")" in skill_name:
                    skill_id = skill_name.split("(")[-1].split(")")[0].strip()
                
                if skill_id in self.all_skills:
                    calls_in_queue_cell = skill_cell.find_next_sibling('td')
                    if calls_in_queue_cell:
                        calls_in_queue = calls_in_queue_cell.get_text(strip=True)
                        
                        # Get staffed and available counts
                        staffed_cell = calls_in_queue_cell
                        for _ in range(12):
                            staffed_cell = staffed_cell.find_next_sibling('td')
                        
                        available_cell = staffed_cell.find_next_sibling('td')
                        
                        # Get oldest call
                        oldest_call_cell = calls_in_queue_cell
                        for _ in range(7):
                            oldest_call_cell = oldest_call_cell.find_next_sibling('td')
                        oldest_call = oldest_call_cell.get_text(strip=True) if oldest_call_cell else '00:00'
                        
                        # Get RT SL
                        rt_sl_cell = calls_in_queue_cell
                        for _ in range(15):
                            rt_sl_cell = rt_sl_cell.find_next_sibling('td')
                        rt_sl = rt_sl_cell.get_text(strip=True) if rt_sl_cell else '100.00%'
                        
                        if calls_in_queue.isdigit():
                            calls_int = int(calls_in_queue)
                            total_calls_in_queue += calls_int
                            
                            data.append({
                                'skill_id': skill_id,
                                'skill_name': self.all_skills[skill_id],
                                'calls_in_queue': calls_in_queue,
                                'staffed': staffed_cell.get_text(strip=True) if staffed_cell else '0',
                                'available': available_cell.get_text(strip=True) if available_cell else '0',
                                'oldest_call': oldest_call,
                                'rt_sl': rt_sl
                            })
        
        return data, total_calls_in_queue
    
    def process_response(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Clear previous data
        self.alert_list = []
        self.aux_list = []
        self.queue_list = []
        self.agents = []
        self.total_calls_in_queue = 0

        # Process agent data
        rows = soup.find_all('tr', class_='data')
        for i, row in enumerate(rows):
            cols = row.find_all('td')
            if len(cols) >= 9:
                avaya_id = cols[0].text.strip()
                full_name = cols[1].text.strip()
                state = cols[2].text.strip().upper()
                reason_code = cols[3].text.strip().upper()
                active_call = cols[4].text.strip()
                call_duration = cols[5].text.strip()
                skill_name = cols[6].text.strip()
                time_in_state = cols[7].text.strip()

                call_duration_sec = self.time_to_seconds(call_duration)
                time_in_state_sec = self.time_to_seconds(time_in_state)

                # Determine row class for alternating colors
                row_class = "normal-row" if i % 2 == 0 else "alternate-row"
                
                # Determine state class for badge styling
                state_class = "other"
                if state == "ACD":
                    state_class = "acd"
                elif state == "AUX":
                    state_class = "aux"
                elif state == "ACW":
                    state_class = "acw"
                elif "HOLD" in state:
                    state_class = "other"

                # Add agent to display list
                self.agents.append({
                    'avaya_id': avaya_id,
                    'full_name': full_name,
                    'state': state,
                    'state_class': state_class,
                    'reason_code': reason_code,
                    'active_call': active_call,
                    'call_duration': call_duration,
                    'skill_name': skill_name,
                    'time_in_state': time_in_state,
                    'row_class': row_class
                })

                # Check for AUX states
                aux_codes = ["EMAIL 1", "EMAIL 2", "CSR LEVEL II", "QUALITY COACHING",
                           "TL INTERN", "FLOOR SUPPORT", "CHAT", "BRAND SPECIALIST", "PERFORMANCE ANALYST",
                            "BACK OFFICE", "TRAINING"]
                if state == "AUX" and reason_code in aux_codes:
                    self.aux_list.append((reason_code, avaya_id, full_name, time_in_state))

                # Check for alerts
                alert = ""
                if state == "ACD" and call_duration_sec > self.alert_times["Long Call"]:
                    alert = "Long Call"
                elif "LUNCH" in reason_code and time_in_state_sec > self.alert_times["Extended Lunch"]:
                    alert = "Extended Lunch"
                elif state == "ACW" and time_in_state_sec > self.alert_times["Long ACW"]:
                    alert = "Long ACW"
                elif state == "AUX" and "BREAK" in reason_code and time_in_state_sec > self.alert_times["Extended Break"]:
                    alert = "Extended Break"
                elif state == "AUX" and "IT ISSUE" in reason_code and time_in_state_sec > self.alert_times["IT Issue"]:
                    alert = "IT Issue"
                elif state == "AUX" and "DEFAULT" in reason_code:
                    alert = "Default Detected"
                elif state == "OTHER (HOLD)" and time_in_state_sec > self.alert_times["Long Hold"]:
                    alert = "Long Hold"

                if alert:
                    self.alert_list.append((alert, avaya_id, full_name, call_duration if "Call" in alert else time_in_state))

        # Process queue data
        queue_data, self.total_calls_in_queue = self.parse_queue_data(soup)
        
        # Ensure all skills are represented
        skills_in_data = {item['skill_id'] for item in queue_data}
        for skill_id, skill_name in self.all_skills.items():
            if skill_id not in skills_in_data:
                queue_data.append({
                    'skill_id': skill_id,
                    'skill_name': skill_name,
                    'calls_in_queue': "0",
                    'oldest_call': "00:00",
                    'rt_sl': "100.00%",
                    'staffed': "0",
                    'available': "0"
                })
        
        # Sort by skill name
        self.queue_list = sorted(queue_data, key=lambda x: x['skill_name'])

        # Process skills data for queue dashboard
        self.skills_data = []
        skill_rows = soup.find_all('tr', class_='data')[2:]
        for row in skill_rows:
            cells = row.find_all('td')
            if len(cells) >= 19:
                try:
                    skill_info = cells[0]
                    strong_tag = skill_info.find('strong')
                    if not strong_tag:
                        continue
                        
                    skill_name = strong_tag.text.strip()
                    skill_id = cells[0].text.strip().split('(')[-1].split(')')[0].strip()
                    
                    # Get SLA value for warning classes
                    service_level = cells[11].text.strip() if len(cells) > 11 else '0%'
                    try:
                        sl_value = float(service_level.rstrip('%'))
                    except ValueError:
                        sl_value = 0
                    
                    calls_in_queue = cells[1].text.strip() if len(cells) > 1 else '0'
                    has_calls = calls_in_queue.isdigit() and int(calls_in_queue) > 0
                    
                    # Determine row class for warnings
                    row_class = ""
                    if has_calls and sl_value < 80:
                        row_class = "both-warning"
                    elif has_calls:
                        row_class = "calls-warning"
                    elif sl_value < 80:
                        row_class = "sl-warning"
                    else:
                        row_class = "normal-row" if len(self.skills_data) % 2 == 0 else "alternate-row"
                    
                    self.skills_data.append({
                        'skill_name': f"{skill_name} ({skill_id})",
                        'calls_in_queue': calls_in_queue,
                        'offered': cells[2].text.strip() if len(cells) > 2 else '',
                        'answered': cells[3].text.strip() if len(cells) > 3 else '',
                        'transfers': cells[4].text.strip() if len(cells) > 4 else '',
                        'true_abn': cells[5].text.strip() if len(cells) > 5 else '',
                        'short_abn': cells[6].text.strip() if len(cells) > 6 else '',
                        'oldest_call': cells[7].text.strip() if len(cells) > 7 else '',
                        'max_delay': cells[8].text.strip() if len(cells) > 8 else '',
                        'asa': cells[9].text.strip() if len(cells) > 9 else '',
                        'aqt': cells[10].text.strip() if len(cells) > 10 else '',
                        'service_level': service_level,
                        'rt_sl': cells[12].text.strip() if len(cells) > 12 else '',
                        'staffed': cells[13].text.strip() if len(cells) > 13 else '',
                        'available': cells[14].text.strip() if len(cells) > 14 else '',
                        'acw': cells[15].text.strip() if len(cells) > 15 else '',
                        'acd': cells[16].text.strip() if len(cells) > 16 else '',
                        'aux': cells[17].text.strip() if len(cells) > 17 else '',
                        'other': cells[18].text.strip() if len(cells) > 18 else '',
                        'row_class': row_class
                    })
                except (IndexError, AttributeError) as e:
                    print(f"Error processing skill row: {str(e)}")
                    continue

@app.route('/')
def index():
    session_id = request.cookies.get('session_id')
    if not session_id or session_id not in user_sessions:
        session_id = str(uuid.uuid4())
        user_sessions[session_id] = UserSession()
    
    session = user_sessions[session_id]
    
    # Notification for calls in queue
    notification = None
    if session.total_calls_in_queue > 0:
        notification = f"Warning: {session.total_calls_in_queue} calls in queue! Click 'View Queue' for details."
    
    response = make_response(render_template_string(
        HTML_TEMPLATE,
        agents=session.agents,
        alerts_count=len(session.alert_list),
        aux_count=len(session.aux_list),
        queue_count=session.total_calls_in_queue,
        notification=notification,
        update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        refresh_interval=REFRESH_INTERVAL
    ))
    
    if not request.cookies.get('session_id'):
        response.set_cookie('session_id', session_id)
    
    return response

@app.route('/alerts')
def show_alerts():
    session_id = request.cookies.get('session_id')
    if not session_id or session_id not in user_sessions:
        return "Invalid session", 400
    
    session = user_sessions[session_id]
    
    # Organize alerts by type
    alert_dict = {}
    for alert, avaya_id, full_name, alert_time in session.alert_list:
        if alert not in alert_dict:
            alert_dict[alert] = []
        alert_dict[alert].append(f"{avaya_id} - {full_name} ({alert_time})")
    
    return render_template_string(
        ALERTS_TEMPLATE,
        alerts=alert_dict,
        refresh_interval=REFRESH_INTERVAL
    )

@app.route('/aux')
def show_aux():
    session_id = request.cookies.get('session_id')
    if not session_id or session_id not in user_sessions:
        return "Invalid session", 400
    
    session = user_sessions[session_id]
    
    # Organize AUX by type
    aux_dict = {}
    for aux_type, avaya_id, full_name, time_in_state in session.aux_list:
        if aux_type not in aux_dict:
            aux_dict[aux_type] = []
        aux_dict[aux_type].append(f"{avaya_id} - {full_name} ({time_in_state})")
    
    return render_template_string(
        AUX_TEMPLATE,
        aux_list=aux_dict,
        refresh_interval=REFRESH_INTERVAL
    )

@app.route('/queue')
def show_queue():
    session_id = request.cookies.get('session_id')
    if not session_id or session_id not in user_sessions:
        return "Invalid session", 400
    
    session = user_sessions[session_id]
    
    # Filter to only show skills with calls in queue
    queue_with_calls = [skill for skill in session.queue_list if skill['calls_in_queue'] != '0']
    
    return render_template_string(
        QUEUE_TEMPLATE,
        queue_list=queue_with_calls if queue_with_calls else None,
        refresh_interval=REFRESH_INTERVAL
    )

@app.route('/queue-dashboard')
def queue_dashboard():
    session_id = request.cookies.get('session_id')
    if not session_id or session_id not in user_sessions:
        return "Invalid session", 400
    
    session = user_sessions[session_id]
    view = request.args.get('view', 'main')
    
    return render_template_string(
        QUEUE_DASHBOARD_TEMPLATE,
        skills=session.skills_data,
        view=view,
        update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        refresh_interval=REFRESH_INTERVAL
    )

@app.route('/settings', methods=['GET', 'POST'])
def show_settings():
    session_id = request.cookies.get('session_id')
    if not session_id or session_id not in user_sessions:
        return "Invalid session", 400
    
    session = user_sessions[session_id]
    
    message = None
    
    if request.method == 'POST':
        try:
            for alert in session.alert_times:
                session.alert_times[alert] = int(request.form.get(alert, session.alert_times[alert]))
            message = {'type': 'success', 'text': 'Alert settings updated successfully'}
        except ValueError:
            message = {'type': 'error', 'text': 'Please enter valid numbers for all fields'}
    
    return render_template_string(
        SETTINGS_TEMPLATE,
        alert_times=session.alert_times,
        message=message,
        refresh_interval=REFRESH_INTERVAL
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))