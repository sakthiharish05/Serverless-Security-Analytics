// ══════════════════════════════════════════════════════════
// Enterprise Security Log Analysis Platform — Frontend
// Cloud-Native Event-Driven Pipeline UI
// ══════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', function () {
    // ── Tab Navigation ──
    const navTabs = document.querySelectorAll('.nav-tab');
    const tabContents = document.querySelectorAll('.tab-content');

    navTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            navTabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            tab.classList.add('active');
            const tabName = tab.dataset.tab;
            document.getElementById(tabName + 'Tab').classList.add('active');

            // Load data when switching tabs
            if (tabName === 'incidents') loadIncidents();
            if (tabName === 'pipeline') { loadLogGroups(); loadPipelineHistory(); }
            if (tabName === 'dashboard') loadDashboard();
        });
    });

    // ── Event Listeners ──
    document.getElementById('refreshIncidentsBtn').addEventListener('click', loadIncidents);
    document.getElementById('statusFilter').addEventListener('change', filterIncidents);
    document.getElementById('severityFilter').addEventListener('change', filterIncidents);
    document.querySelector('.modal-close').addEventListener('click', closeModal);
    document.getElementById('incidentModal').addEventListener('click', (e) => {
        if (e.target === document.getElementById('incidentModal')) closeModal();
    });

    // Pipeline tab listeners
    document.getElementById('refreshHistoryBtn').addEventListener('click', loadPipelineHistory);

    // Dashboard tab listeners
    document.getElementById('refreshCloudStatusBtn').addEventListener('click', loadCloudStatus);
    document.getElementById('refreshAlertsBtn').addEventListener('click', loadAlertHistory);

    // File upload
    setupFileUpload();

    // Load cloud status indicator
    loadCloudIndicator();

    // Focus on input
    document.getElementById('logInput').focus();
});


// ══════════════════════════════════════════════════════════
// Cloud Status Indicator (Header)
// ══════════════════════════════════════════════════════════

async function loadCloudIndicator() {
    try {
        const response = await fetch('/cloud/status');
        const data = await response.json();
        const text = document.getElementById('cloudProviderText');
        const provider = data.provider || 'local';

        const healthyCount = Object.values(data.services || {}).filter(s => s.status === 'healthy').length;
        const totalCount = Object.keys(data.services || {}).length;

        if (provider === 'aws') {
            text.textContent = `AWS ${data.region} • ${healthyCount}/${totalCount} services healthy`;
        } else {
            text.textContent = `Local Mode • ${healthyCount}/${totalCount} services healthy`;
        }
    } catch {
        document.getElementById('cloudProviderText').textContent = 'Connecting...';
    }
}


// ══════════════════════════════════════════════════════════
// Tab 1: Log Analysis (Original)
// ══════════════════════════════════════════════════════════

document.getElementById('analyzeForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const logs = document.getElementById('logInput').value.trim();
    if (!logs) {
        showError('Please enter logs to analyze');
        return;
    }

    const logSizeMB = new Blob([logs]).size / (1024 * 1024);
    if (logSizeMB > 10) {
        if (!confirm(`Warning: Log size is ${logSizeMB.toFixed(2)}MB. This may take a moment. Continue?`)) return;
    }

    showSpinner(true);
    hideError();
    document.getElementById('resultSection').style.display = 'none';
    document.getElementById('createIncidentBtn').style.display = 'none';

    try {
        const response = await fetch('/analyze_logs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ logs }),
        });

        const result = await response.json();

        if (result.status === 'error') {
            showError(`Analysis Error: ${result.error || 'Unknown error occurred'}`);
            return;
        }

        if (!response.ok) {
            throw new Error(result.detail || `HTTP ${response.status}: ${response.statusText}`);
        }

        displayResults(result, logs);

        if (result.status === 'threat_detected') {
            document.getElementById('createIncidentBtn').style.display = 'inline-block';
            document.getElementById('createIncidentBtn').onclick = () => createIncidentFromAnalysis(result, logs);
        }
    } catch (error) {
        showError(`Error analyzing logs: ${error.message}`);
    } finally {
        showSpinner(false);
    }
});

function displayResults(result, logs) {
    hideError();
    document.getElementById('resultSection').style.display = 'block';

    const statusCard = document.getElementById('statusCard');
    const statusTitle = document.getElementById('statusTitle');
    const statusValue = document.getElementById('statusValue');
    const threatType = document.getElementById('threatType');
    const severity = document.getElementById('severity');
    const threatsCountInfo = document.getElementById('threatsCountInfo');

    const isClean = result.status === 'clean';
    statusCard.className = `status-card ${isClean ? 'clean' : 'threat-detected'}`;

    if (isClean) {
        statusTitle.textContent = '✓ ANALYSIS COMPLETE — NO THREATS';
        statusValue.textContent = 'CLEAN';
        threatType.textContent = 'No malicious patterns detected';
        severity.className = 'severity LOW';
        severity.textContent = 'Risk Level: LOW';
        threatsCountInfo.textContent = `Analyzed ${Math.round(new Blob([logs]).size / 1024)}KB of logs`;
    } else {
        statusTitle.textContent = '⚠ ANALYSIS COMPLETE — THREATS DETECTED';
        statusValue.textContent = 'THREAT FOUND';
        threatType.textContent = `Primary Threat: ${result.type || 'Unknown'}`;
        severity.className = `severity ${result.severity}`;
        severity.textContent = `Risk Level: ${result.severity || 'UNKNOWN'}`;
        const threatCount = result.matchedRules ? result.matchedRules.length : 0;
        threatsCountInfo.textContent = `${threatCount} threat signature${threatCount !== 1 ? 's' : ''} detected`;
    }

    const matchesContainer = document.getElementById('matchesContainer');
    const noThreatsMessage = document.getElementById('noThreatsMessage');

    if (result.matchedRules && result.matchedRules.length > 0) {
        matchesContainer.style.display = 'block';
        noThreatsMessage.style.display = 'none';
        populateRulesTable(result.matchedRules);
    } else {
        matchesContainer.style.display = 'none';
        noThreatsMessage.style.display = 'block';
    }

    document.getElementById('resultSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function populateRulesTable(rules) {
    const tbody = document.getElementById('rulesTableBody');
    tbody.innerHTML = '';

    const severityOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
    const sortedRules = [...rules].sort((a, b) => {
        return (severityOrder[a.severity] ?? 99) - (severityOrder[b.severity] ?? 99);
    });

    sortedRules.forEach(rule => {
        const row = document.createElement('tr');
        const severityClass = rule.severity ? rule.severity.toUpperCase() : 'UNKNOWN';
        row.innerHTML = `
            <td><code>${escapeHtml(rule.id || '--')}</code></td>
            <td><strong>${escapeHtml(rule.type || '--')}</strong></td>
            <td><span class="severity ${severityClass}">${escapeHtml(rule.severity || '--')}</span></td>
            <td><strong style="color: ${getSeverityColor(rule.severity)}">${rule.count || 0}</strong></td>
            <td>${escapeHtml(rule.description || '--')}</td>
        `;
        tbody.appendChild(row);
    });
}

function getSeverityColor(severity) {
    const colors = { 'CRITICAL': '#fecaca', 'HIGH': '#fca5a5', 'MEDIUM': '#fbbf24', 'LOW': '#6ee7b7' };
    return colors[severity] || '#cbd5e1';
}


// ══════════════════════════════════════════════════════════
// Tab 2: Cloud Pipeline
// ══════════════════════════════════════════════════════════

function setupFileUpload() {
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');

    // Click to browse
    uploadZone.addEventListener('click', () => fileInput.click());

    // Drag events
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('drag-over');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('drag-over');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) uploadLogFile(files[0]);
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) uploadLogFile(e.target.files[0]);
    });
}

async function uploadLogFile(file) {
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
        showError('File too large. Maximum size is 50MB.');
        return;
    }

    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const uploadResult = document.getElementById('uploadResult');

    // Show progress
    uploadProgress.style.display = 'block';
    uploadResult.style.display = 'none';
    progressFill.style.width = '10%';
    progressText.textContent = `Uploading ${file.name} (${(file.size / 1024).toFixed(1)}KB)...`;

    try {
        const formData = new FormData();
        formData.append('file', file);

        progressFill.style.width = '30%';
        progressText.textContent = 'Storing in S3...';

        const response = await fetch('/pipeline/upload', {
            method: 'POST',
            body: formData,
        });

        progressFill.style.width = '70%';
        progressText.textContent = 'Analyzing threats...';

        const result = await response.json();

        progressFill.style.width = '100%';

        if (result.status === 'error') {
            progressText.textContent = 'Pipeline failed';
            showUploadResult(uploadResult, 'error', result);
        } else {
            const analysis = result.stages?.analysis;
            if (analysis?.threat_status === 'threat_detected') {
                progressText.textContent = '🚨 Threats detected! Alert sent via SNS.';
                showUploadResult(uploadResult, 'threat', result);
            } else {
                progressText.textContent = '✅ Pipeline completed — No threats found.';
                showUploadResult(uploadResult, 'success', result);
            }
        }

        // Refresh history
        loadPipelineHistory();

    } catch (error) {
        progressFill.style.width = '100%';
        progressText.textContent = 'Upload failed';
        uploadResult.style.display = 'block';
        uploadResult.className = 'upload-result error';
        uploadResult.innerHTML = `<strong>Error:</strong> ${escapeHtml(error.message)}`;
    }
}

function showUploadResult(container, type, result) {
    container.style.display = 'block';
    container.className = `upload-result ${type}`;

    const stages = result.stages || {};
    const analysis = stages.analysis || {};
    const s3 = stages.s3_upload || {};
    const sns = stages.sns_alert || {};
    const incident = stages.auto_incident || {};

    let stagesHtml = '';

    // S3 stage
    if (s3.status === 'success') {
        stagesHtml += `<div>📦 <strong>S3:</strong> Stored at <code>${escapeHtml(s3.key || '')}</code> (${formatBytes(s3.size || 0)})</div>`;
    }

    // Analysis stage
    if (analysis.status === 'success') {
        stagesHtml += `<div>⚡ <strong>Analysis:</strong> ${analysis.threat_status === 'threat_detected'
            ? `<span style="color:#fca5a5">${analysis.matched_rules_count} threats found [${analysis.severity}]</span>`
            : '<span style="color:#6ee7b7">Clean — no threats</span>'
            }</div>`;
    }

    // DynamoDB stage
    if (stages.dynamodb_store?.status === 'success') {
        stagesHtml += `<div>🗄️ <strong>DynamoDB:</strong> Results stored in ${escapeHtml(stages.dynamodb_store.table)}</div>`;
    }

    // SNS stage
    if (sns.status === 'success') {
        stagesHtml += `<div>🔔 <strong>SNS:</strong> Alert sent [${escapeHtml(sns.severity)}]</div>`;
    } else if (sns.status === 'skipped') {
        stagesHtml += `<div>🔔 <strong>SNS:</strong> Skipped (no threats)</div>`;
    }

    // Auto-incident
    if (incident.status === 'success') {
        stagesHtml += `<div>📋 <strong>Incident:</strong> Auto-created ${escapeHtml(incident.incident_id)}</div>`;
    }

    container.innerHTML = `
        <div style="margin-bottom: 10px;"><strong>Pipeline ${escapeHtml(result.pipeline_id || '')}</strong></div>
        <div style="display: flex; flex-direction: column; gap: 6px; font-size: 0.9em;">
            ${stagesHtml}
        </div>
    `;
}

async function loadLogGroups() {
    const container = document.getElementById('logGroupsList');
    try {
        const response = await fetch('/cloud/log-groups');
        const groups = await response.json();

        if (groups.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📡</div><div class="empty-state-text">No log groups found</div></div>';
            return;
        }

        container.innerHTML = groups.map(group => `
            <div class="log-group-item">
                <div class="log-group-info">
                    <div class="log-group-name">📁 ${escapeHtml(group.name)}</div>
                    <div class="log-group-meta">
                        ${group.log_file_count ? `${group.log_file_count} files` : ''}
                        ${group.total_size_bytes ? ` • ${formatBytes(group.total_size_bytes)}` : ''}
                    </div>
                </div>
                <button class="btn-ingest" onclick="ingestLogGroup('${escapeHtml(group.name)}', this)">
                    Ingest & Analyze
                </button>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = `<div class="empty-state"><div class="empty-state-text">Failed to load log groups</div></div>`;
    }
}

async function ingestLogGroup(logGroup, button) {
    button.disabled = true;
    button.textContent = 'Processing...';

    try {
        const response = await fetch('/cloud/ingest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ log_group: logGroup }),
        });

        const result = await response.json();

        if (result.status === 'completed') {
            const threats = result.threats_found || 0;
            if (threats > 0) {
                button.textContent = `🚨 ${threats} threats!`;
                button.style.background = 'linear-gradient(135deg, #ef4444, #f59e0b)';
            } else {
                button.textContent = '✅ Clean';
                button.style.background = 'linear-gradient(135deg, #10b981, #06b6d4)';
            }
        } else {
            button.textContent = '❌ Failed';
            button.style.background = '#ef4444';
        }

        // Refresh history and dashboard
        loadPipelineHistory();

    } catch (error) {
        button.textContent = '❌ Error';
        button.style.background = '#ef4444';
    }

    // Reset button after 3 seconds
    setTimeout(() => {
        button.disabled = false;
        button.textContent = 'Ingest & Analyze';
        button.style.background = '';
    }, 3000);
}

async function loadPipelineHistory() {
    const container = document.getElementById('historyList');
    try {
        const response = await fetch('/pipeline/history?limit=20');
        const history = await response.json();

        if (history.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📜</div><div class="empty-state-text">No processing history yet. Upload a log file to get started.</div></div>';
            return;
        }

        container.innerHTML = history.map(item => {
            const isClean = item.status === 'clean';
            const source = item.type === 'cloudwatch_ingest' ? '📡 CloudWatch' : '📦 Upload';
            const name = item.filename || item.log_group || item.id;

            return `
                <div class="history-item">
                    <div class="history-info">
                        <div class="history-title">${source} — ${escapeHtml(name)}</div>
                        <div class="history-meta">
                            <span>${escapeHtml(item.severity || 'N/A')}</span>
                            <span>${item.matched_rules_count || 0} rules matched</span>
                            <span>${formatTime(item.processed_at)}</span>
                        </div>
                    </div>
                    <span class="history-status ${isClean ? 'clean' : 'threat_detected'}">
                        ${isClean ? 'Clean' : 'Threat'}
                    </span>
                </div>
            `;
        }).join('');
    } catch {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">Failed to load history</div></div>';
    }
}


// ══════════════════════════════════════════════════════════
// Tab 3: Dashboard
// ══════════════════════════════════════════════════════════

async function loadDashboard() {
    loadPipelineStats();
    loadCloudStatus();
    loadAlertHistory();
}

async function loadPipelineStats() {
    try {
        const response = await fetch('/pipeline/stats');
        const stats = await response.json();

        animateCounter('statLogsValue', stats.total_logs_processed || 0);
        animateCounter('statThreatsValue', stats.total_threats_detected || 0);
        animateCounter('statAlertsValue', stats.total_alerts_sent || 0);
        animateCounter('statIncidentsValue', stats.total_incidents || 0);
    } catch {
        // Keep showing 0s
    }
}

function animateCounter(elementId, targetValue) {
    const el = document.getElementById(elementId);
    const startValue = parseInt(el.textContent) || 0;
    const duration = 800;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
        const currentValue = Math.round(startValue + (targetValue - startValue) * eased);
        el.textContent = currentValue;
        if (progress < 1) requestAnimationFrame(update);
    }

    requestAnimationFrame(update);
}

async function loadCloudStatus() {
    const container = document.getElementById('servicesGrid');
    try {
        const response = await fetch('/cloud/status');
        const data = await response.json();

        const services = data.services || {};
        const serviceOrder = ['storage', 'database', 'notifications', 'log_source'];
        const serviceIcons = {
            storage: '📦',
            database: '🗄️',
            notifications: '🔔',
            log_source: '📡',
        };

        container.innerHTML = serviceOrder.map(key => {
            const service = services[key];
            if (!service) return '';

            const isHealthy = service.status === 'healthy';
            let detail = '';
            if (service.endpoint) detail = service.endpoint;
            else if (service.tables) detail = `Tables: ${service.tables.join(', ')}`;
            else if (service.total_alerts !== undefined) detail = `${service.total_alerts} alerts sent`;
            else if (service.log_groups !== undefined) detail = `${service.log_groups} log groups`;

            return `
                <div class="service-status-card ${isHealthy ? 'healthy' : 'error'}">
                    <div style="font-size: 1.8em; margin-bottom: 10px;">${serviceIcons[key] || '☁️'}</div>
                    <div class="service-name">${escapeHtml(service.name)}</div>
                    <div class="service-health ${isHealthy ? 'healthy' : 'error'}">
                        ${isHealthy ? '● Healthy' : '● Error'}
                    </div>
                    ${detail ? `<div class="service-detail">${escapeHtml(detail)}</div>` : ''}
                </div>
            `;
        }).join('');
    } catch {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">Failed to load cloud status</div></div>';
    }
}

async function loadAlertHistory() {
    const container = document.getElementById('alertsList');
    try {
        const response = await fetch('/alerts?limit=20');
        const alerts = await response.json();

        if (alerts.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🔔</div><div class="empty-state-text">No alerts yet. Alerts are sent via SNS when threats are detected.</div></div>';
            return;
        }

        const severityIcons = { CRITICAL: '🔴', HIGH: '🟠', MEDIUM: '🟡', LOW: '🟢', INFO: '🔵' };

        container.innerHTML = alerts.map(alert => `
            <div class="alert-item">
                <div class="alert-severity-icon">${severityIcons[alert.severity] || '⚪'}</div>
                <div class="alert-content">
                    <div class="alert-subject">${escapeHtml(alert.subject)}</div>
                    <div class="alert-message">${escapeHtml(alert.message)}</div>
                </div>
                <div class="alert-time">${formatTime(alert.timestamp)}</div>
            </div>
        `).join('');
    } catch {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">Failed to load alerts</div></div>';
    }
}


// ══════════════════════════════════════════════════════════
// Tab 4: Incident Management (Original)
// ══════════════════════════════════════════════════════════

async function loadIncidents() {
    try {
        showSpinner(true);
        const response = await fetch('/incidents');
        const incidents = await response.json();
        displayIncidents(incidents);
    } catch (error) {
        showError('Failed to load incidents');
    } finally {
        showSpinner(false);
    }
}

function displayIncidents(incidents) {
    const container = document.getElementById('incidentsList');
    container.innerHTML = '';

    if (incidents.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📋</div><div class="empty-state-text">No incidents found.</div></div>';
        return;
    }

    incidents.forEach(incident => {
        const card = document.createElement('div');
        card.className = 'incident-card';
        card.onclick = () => showIncidentDetails(incident);

        const tagsHtml = incident.tags.map(tag => `<span class="incident-tag">${escapeHtml(tag)}</span>`).join('');

        card.innerHTML = `
            <div class="incident-header">
                <div>
                    <h3 class="incident-title">${escapeHtml(incident.title)}</h3>
                    <div class="incident-id">${incident.id}</div>
                </div>
            </div>
            <div class="incident-meta">
                <span class="incident-severity ${incident.severity.toLowerCase()}">${incident.severity}</span>
                <span class="incident-status ${incident.status}">${incident.status}</span>
            </div>
            <p class="incident-description">${escapeHtml(incident.description)}</p>
            <div class="incident-footer">
                <div class="incident-tags">${tagsHtml}</div>
                <div>Updated: ${new Date(incident.updated_at).toLocaleDateString()}</div>
            </div>
        `;

        container.appendChild(card);
    });
}

function filterIncidents() {
    const statusFilter = document.getElementById('statusFilter').value;
    const severityFilter = document.getElementById('severityFilter').value;
    const cards = document.querySelectorAll('.incident-card');

    cards.forEach(card => {
        const severity = card.querySelector('.incident-severity').textContent.toLowerCase();
        const status = card.querySelector('.incident-status').textContent.toLowerCase();
        const matchesStatus = !statusFilter || status === statusFilter;
        const matchesSeverity = !severityFilter || severity === severityFilter.toLowerCase();
        card.style.display = matchesStatus && matchesSeverity ? 'block' : 'none';
    });
}

function showIncidentDetails(incident) {
    const modal = document.getElementById('incidentModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');

    modalTitle.textContent = `${incident.id}: ${incident.title}`;

    const tagsHtml = incident.tags.map(tag => `<span class="incident-tag">${escapeHtml(tag)}</span>`).join('');
    const logEntriesHtml = incident.log_entries.map(entry => escapeHtml(entry)).join('\n');

    modalBody.innerHTML = `
        <div class="incident-detail-section">
            <h4>Description</h4>
            <p>${escapeHtml(incident.description)}</p>
        </div>
        <div class="incident-detail-section">
            <h4>Status & Severity</h4>
            <p><strong>Severity:</strong> <span class="incident-severity ${incident.severity.toLowerCase()}">${incident.severity}</span></p>
            <p><strong>Status:</strong> <span class="incident-status ${incident.status}">${incident.status}</span></p>
            <p><strong>Assigned to:</strong> ${incident.assigned_to || 'Unassigned'}</p>
        </div>
        <div class="incident-detail-section">
            <h4>Tags</h4>
            <div class="incident-tags">${tagsHtml}</div>
        </div>
        <div class="incident-detail-section">
            <h4>Matched Rules</h4>
            <ul>${incident.matched_rules.map(rule => `<li><code>${escapeHtml(rule)}</code></li>`).join('')}</ul>
        </div>
        <div class="incident-detail-section">
            <h4>Log Entries</h4>
            <div class="incident-log-entries">${logEntriesHtml}</div>
        </div>
        <div class="incident-detail-section">
            <h4>Timeline</h4>
            <p><strong>Created:</strong> ${new Date(incident.created_at).toLocaleString()}</p>
            <p><strong>Last Updated:</strong> ${new Date(incident.updated_at).toLocaleString()}</p>
        </div>
        ${incident.resolution ? `
        <div class="incident-detail-section">
            <h4>Resolution</h4>
            <p>${escapeHtml(incident.resolution)}</p>
        </div>` : ''}
        <div class="incident-actions">
            <button class="btn btn-secondary" onclick="editIncident('${incident.id}')">Edit Incident</button>
            <button class="btn btn-danger" onclick="deleteIncident('${incident.id}')">Delete Incident</button>
            ${incident.status !== 'resolved' && incident.status !== 'closed'
            ? `<button class="btn btn-success" onclick="resolveIncident('${incident.id}')">Mark as Resolved</button>` : ''}
        </div>
    `;

    modal.style.display = 'flex';
}

function closeModal() {
    document.getElementById('incidentModal').style.display = 'none';
}

async function createIncidentFromAnalysis(result, logs) {
    const title = `Security Threat Detected: ${result.type}`;
    const description = `Automated incident created from log analysis. ${result.matchedRules.length} threat signatures detected with severity ${result.severity}.`;
    const severity = result.severity;
    const tags = ['automated', 'log-analysis', result.type.toLowerCase().replace(/\s+/g, '-')];
    const logEntries = logs.split('\n').slice(0, 10);
    const matchedRules = result.matchedRules.map(rule => rule.id).filter(id => id);

    try {
        const response = await fetch('/incidents', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, description, severity, tags, log_entries: logEntries, matched_rules: matchedRules }),
        });

        if (response.ok) {
            alert('Incident created successfully!');
            document.querySelector('[data-tab="incidents"]').click();
        } else {
            throw new Error('Failed to create incident');
        }
    } catch (error) {
        alert('Failed to create incident');
    }
}

async function deleteIncident(incidentId) {
    if (!confirm('Are you sure you want to delete this incident?')) return;

    try {
        const response = await fetch(`/incidents/${incidentId}`, { method: 'DELETE' });
        if (response.ok) {
            closeModal();
            loadIncidents();
        } else {
            throw new Error('Failed to delete incident');
        }
    } catch {
        alert('Failed to delete incident');
    }
}

async function resolveIncident(incidentId) {
    try {
        const response = await fetch(`/incidents/${incidentId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: 'resolved', resolution: 'Marked as resolved by user' }),
        });

        if (response.ok) {
            closeModal();
            loadIncidents();
        } else {
            throw new Error('Failed to resolve incident');
        }
    } catch {
        alert('Failed to resolve incident');
    }
}

function editIncident(incidentId) {
    // Open inline edit form in the modal
    const modalBody = document.getElementById('modalBody');
    const actions = modalBody.querySelector('.incident-actions');
    if (!actions) return;

    actions.innerHTML = `
        <div style="width:100%;">
            <h4 style="color: var(--accent-blue); margin-bottom: 12px;">Edit Incident</h4>
            <div style="display:flex; flex-direction:column; gap:12px;">
                <select id="editStatus" style="padding:10px; background:var(--tertiary-dark); color:var(--text-primary); border:1px solid var(--border-color); border-radius:8px; font-family:Inter,sans-serif;">
                    <option value="open">Open</option>
                    <option value="investigating">Investigating</option>
                    <option value="resolved">Resolved</option>
                    <option value="closed">Closed</option>
                </select>
                <input id="editAssignee" placeholder="Assign to..." style="padding:10px; background:var(--tertiary-dark); color:var(--text-primary); border:1px solid var(--border-color); border-radius:8px; font-family:Inter,sans-serif;">
                <textarea id="editResolution" placeholder="Resolution notes..." rows="3" style="padding:10px; background:var(--tertiary-dark); color:var(--text-primary); border:1px solid var(--border-color); border-radius:8px; font-family:Inter,sans-serif; resize:none;"></textarea>
                <div style="display:flex; gap:12px;">
                    <button class="btn btn-primary" style="width:auto;" onclick="saveIncidentEdit('${incidentId}')">Save Changes</button>
                    <button class="btn btn-secondary" onclick="closeModal(); loadIncidents();">Cancel</button>
                </div>
            </div>
        </div>
    `;
}

async function saveIncidentEdit(incidentId) {
    const status = document.getElementById('editStatus').value;
    const assignedTo = document.getElementById('editAssignee').value.trim() || null;
    const resolution = document.getElementById('editResolution').value.trim() || null;

    try {
        const body = { status };
        if (assignedTo) body.assigned_to = assignedTo;
        if (resolution) body.resolution = resolution;

        const response = await fetch(`/incidents/${incidentId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (response.ok) {
            closeModal();
            loadIncidents();
        } else {
            throw new Error('Failed to update');
        }
    } catch {
        alert('Failed to update incident');
    }
}


// ══════════════════════════════════════════════════════════
// Utility Functions
// ══════════════════════════════════════════════════════════

function showSpinner(show) {
    document.getElementById('loadingSpinner').style.display = show ? 'block' : 'none';
}

function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

function hideError() {
    document.getElementById('errorMessage').style.display = 'none';
}

function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(text).replace(/[&<>"']/g, (m) => map[m]);
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
}

function formatTime(isoString) {
    if (!isoString) return 'N/A';
    try {
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
        return date.toLocaleDateString();
    } catch {
        return 'N/A';
    }
}
