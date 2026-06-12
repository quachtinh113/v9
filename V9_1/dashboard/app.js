// Portfolio Command Center - Logic Engine (Antigravity 2.0)
document.addEventListener("DOMContentLoaded", () => {
    let rawData = null;
    let pnlChart = null;
    let equityChart = null;
    let selectedSymbol = "US30";
    let globalMultiplier = 1.0;
    
    // Stress Test States
    let stressVol = 1.0;
    let stressSlip = 1.0;
    let stressBlackSwan = false;

    // Tab switching setup
    const navItems = {
        "nav-dashboard": "tab-content-dashboard",
        "nav-assets": "tab-content-assets",
        "nav-risk": "tab-content-risk",
        "nav-architecture": "tab-content-architecture",
        "nav-gcp": "tab-content-gcp"
    };

    Object.keys(navItems).forEach(navId => {
        const btn = document.getElementById(navId);
        if (btn) {
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                // Reset active nav
                document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
                btn.classList.add("active");

                // Hide all tabs
                document.querySelectorAll(".tab-content").forEach(el => {
                    el.style.display = "none";
                    el.classList.remove("active");
                });

                // Show target tab
                const targetId = navItems[navId];
                const targetEl = document.getElementById(targetId);
                if (targetEl) {
                    targetEl.style.display = "block";
                    setTimeout(() => targetEl.classList.add("active"), 10);
                }
            });
        }
    });

    // UI Elements
    const serverTimeEl = document.getElementById("server-time");
    const valAumEl = document.getElementById("val-aum");
    const valPnlEl = document.getElementById("val-pnl");
    const valVarEl = document.getElementById("val-var");
    const valChannelsEl = document.getElementById("val-channels");
    const valChannelsPctEl = document.getElementById("val-channels-pct");
    const assetsBodyEl = document.getElementById("assets-body");
    const consoleOutputEl = document.getElementById("console-output");
    
    // Sliders
    const allocationSlider = document.getElementById("allocation-slider");
    const globalMultiplierVal = document.getElementById("global-multiplier-val");
    const stressVolSlider = document.getElementById("stress-vol-slider");
    const stressVolVal = document.getElementById("stress-vol-val");
    const stressSlipSlider = document.getElementById("stress-slip-slider");
    const stressSlipVal = document.getElementById("stress-slip-val");
    const stressBlackswanCheck = document.getElementById("stress-blackswan");

    // Guard Display Elements
    const guardSymbolTitle = document.getElementById("selected-symbol-guard");
    const guardSpreadEl = document.getElementById("guard-spread");
    const guardSlippageEl = document.getElementById("guard-slippage");
    const guardAtrEl = document.getElementById("guard-atr");
    const guardDailyLimitEl = document.getElementById("guard-daily-limit");
    const guardWeeklyLimitEl = document.getElementById("guard-weekly-limit");
    const guardHardLimitEl = document.getElementById("guard-hard-limit");

    // Config Tuning Form Elements
    const configSymbolTitle = document.getElementById("selected-symbol-config");
    const cfgRiskPctInput = document.getElementById("cfg-risk-pct");
    const cfgDailyLimitInput = document.getElementById("cfg-daily-limit");
    const cfgStopAtrInput = document.getElementById("cfg-stop-atr");
    const cfgTpAtrInput = document.getElementById("cfg-tp-atr");
    const cfgMlEnabledCheck = document.getElementById("cfg-ml-enabled");
    const btnSaveConfig = document.getElementById("btn-save-config");
    const btnGcpDeploySimulate = document.getElementById("btn-gcp-deploy-simulate");

    // Clock
    setInterval(() => {
        const d = new Date();
        serverTimeEl.textContent = d.toLocaleTimeString();
    }, 1000);

    // Initial load
    fetchData();
    loadArchitectureTab();

    // Periodically poll backend API every 10 seconds for live heartbeats, status & logs
    setInterval(fetchData, 10000);

    // Telemetry Slider listeners
    allocationSlider.addEventListener("input", (e) => {
        globalMultiplier = parseFloat(e.target.value);
        globalMultiplierVal.textContent = `${globalMultiplier.toFixed(1)}x`;
        updateUI();
    });

    // Stress testing listeners
    stressVolSlider.addEventListener("input", (e) => {
        stressVol = parseFloat(e.target.value);
        stressVolVal.textContent = `${stressVol.toFixed(1)}x`;
        updateUI();
    });

    stressSlipSlider.addEventListener("input", (e) => {
        stressSlip = parseFloat(e.target.value);
        stressSlipVal.textContent = `${stressSlip.toFixed(1)}x`;
        updateUI();
    });

    stressBlackswanCheck.addEventListener("change", (e) => {
        stressBlackSwan = e.target.checked;
        if (stressBlackSwan) {
            showToast("Black Swan Event Enabled! Extreme portfolio safety guards triggered.", "error");
        } else {
            showToast("Black Swan Veto released. Resuming nominal bounds.", "success");
        }
        updateUI();
    });

    // Save configurations back to backend API
    btnSaveConfig.addEventListener("click", async () => {
        if (!rawData) return;
        
        const payload = {
            symbol: selectedSymbol,
            risk_per_trade_pct: parseFloat(cfgRiskPctInput.value),
            daily_loss_limit_pct: parseFloat(cfgDailyLimitInput.value),
            stop_atr_mult: parseFloat(cfgStopAtrInput.value),
            tp_atr_mult: parseFloat(cfgTpAtrInput.value),
            ml_enabled: cfgMlEnabledCheck.checked
        };

        try {
            btnSaveConfig.disabled = true;
            btnSaveConfig.textContent = "Saving...";
            
            const res = await fetch("/api/update_config", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            
            if (res.ok && data.status === "success") {
                showToast(`Settings applied to ${selectedSymbol} config successfully!`, "success");
                
                // Write a log in the console
                appendConsoleLine("SYS", `Configuration for ${selectedSymbol} updated: Risk=${payload.risk_per_trade_pct}%, DailyLimit=${payload.daily_loss_limit_pct}%`);
                
                // Fetch fresh values
                await fetchData();
            } else {
                showToast(`Error: ${data.message || "Failed to update configuration"}`, "error");
            }
        } catch (err) {
            console.error(err);
            showToast(`Connection error: ${err.message}`, "error");
        } finally {
            btnSaveConfig.disabled = false;
            btnSaveConfig.innerHTML = "<span>💾</span> Apply Config";
        }
    });

    // GCP simulation trigger
    btnGcpDeploySimulate.addEventListener("click", () => {
        btnGcpDeploySimulate.disabled = true;
        btnGcpDeploySimulate.textContent = "Deploying...";
        
        appendConsoleLine("GCP", "Deploying release package V9_3_1_LAPTOP_TEST to Compute Engine VM...");
        showToast("Step 1/3: Compiling NowTrading release package...", "info");
        
        setTimeout(() => {
            appendConsoleLine("GCP", "Uploading compressed tarball (87.5 MB) via gcloud compute scp...");
            showToast("Step 2/3: Pushing package to GCP Remote VM...", "info");
            
            setTimeout(() => {
                appendConsoleLine("GCP", "Connection established. SSH systemd service restart initiated...");
                showToast("Step 3/3: Activating remote bot workers...", "info");
                
                setTimeout(() => {
                    appendConsoleLine("GCP", "GCP VM Server status: READY. 10 channels listening on Paper Fallback adapter.");
                    showToast("Deployment Complete! NowTrading Quant VPS online.", "success");
                    btnGcpDeploySimulate.disabled = false;
                    btnGcpDeploySimulate.innerHTML = "<span>🚀</span> Run Deployment Pipeline";
                }, 1500);
            }, 1500);
        }, 1500);
    });

    async function fetchData() {
        try {
            const res = await fetch("/api/portfolio_status");
            rawData = await res.json();
            updateUI();
            streamConsoleLogs(rawData.audit_logs);
        } catch (err) {
            console.error("Failed to load portfolio stats:", err);
            consoleOutputEl.innerHTML = `<div class="console-line"><span class="console-timestamp">[ERROR]</span> Connection failed: ${err.message}</div>`;
        }
    }

    // System Status UI Selection
    const statusDot = document.querySelector(".status-dot");
    const statusLabel = document.querySelector(".status-label");

    function updateSystemHealth() {
        if (!rawData || !rawData.system_status) return;
        const state = rawData.system_status.state;
        const reason = rawData.system_status.reason;
        
        statusLabel.textContent = `${state} - ${reason}`;
        
        statusDot.className = "status-dot pulsing";
        if (state === "GREEN") {
            statusDot.style.backgroundColor = "var(--accent-emerald)";
            statusDot.style.boxShadow = "0 0 12px var(--accent-emerald)";
        } else if (state === "YELLOW") {
            statusDot.style.backgroundColor = "var(--accent-yellow)";
            statusDot.style.boxShadow = "0 0 12px var(--accent-yellow)";
        } else {
            statusDot.style.backgroundColor = "var(--accent-rose)";
            statusDot.style.boxShadow = "0 0 12px var(--accent-rose)";
        }
    }

    function renderAssetMatrix() {
        const fullAssetBody = document.getElementById("asset-matrix-full-body");
        if (!fullAssetBody || !rawData) return;
        
        fullAssetBody.innerHTML = "";
        rawData.assets.forEach(a => {
            const row = document.createElement("tr");
            
            const isApproved = a.verdict === "APPROVED" || a.verdict === "INSTITUTIONAL_READY";
            const verdictClass = a.verdict === "INSTITUTIONAL_READY" ? "APPROVED" : (a.verdict === "OFFLINE" ? "DISABLED" : a.verdict);
            
            const symbolStatusColor = a.symbol_status === "ACTIVE" ? "var(--accent-emerald)" : "var(--accent-rose)";
            const dataStatusColor = a.data_status === "synced" ? "var(--accent-emerald)" : (a.data_status === "stale" ? "var(--accent-yellow)" : "var(--accent-rose)");
            const modelStatusColor = a.model_status === "trained" ? "var(--accent-emerald)" : "var(--accent-rose)";
            const riskStatusColor = a.risk_status === "nominal" ? "var(--accent-emerald)" : "var(--accent-rose)";
            const dashboardStatusColor = a.dashboard_status === "active" ? "var(--accent-emerald)" : "var(--text-secondary)";

            row.innerHTML = `
                <td class="asset-symbol">${a.symbol}</td>
                <td style="text-transform: capitalize;">${a.type}</td>
                <td><span class="asset-badge ${verdictClass}">${a.verdict}</span></td>
                <td style="font-family: 'Space Grotesk', monospace; font-size: 12px; font-weight: 700; color: ${symbolStatusColor};">${a.symbol_status}</td>
                <td style="font-family: 'Space Grotesk', monospace; font-size: 12px; font-weight: 700; color: ${dataStatusColor};">${a.data_status.toUpperCase()}</td>
                <td style="font-family: 'Space Grotesk', monospace; font-size: 12px; font-weight: 700; color: ${modelStatusColor};">${a.model_status.toUpperCase()}</td>
                <td style="font-family: 'Space Grotesk', monospace; font-size: 12px; font-weight: 700; color: ${riskStatusColor};">${a.risk_status.toUpperCase()}</td>
                <td style="font-family: 'Space Grotesk', monospace; font-size: 12px; font-weight: 700; color: ${dashboardStatusColor};">${a.dashboard_status.toUpperCase()}</td>
            `;
            fullAssetBody.appendChild(row);
        });
    }

    function updateFleetStatus() {
        if (!rawData || !rawData.fleet_status) return;
        const fs = rawData.fleet_status;
        
        // 1. Fleet state
        const fleetStateEl = document.getElementById("fleet-state");
        if (fleetStateEl) {
            if (fs.running) {
                fleetStateEl.textContent = "🟢 Fleet Running";
                fleetStateEl.style.color = "var(--accent-emerald)";
            } else {
                fleetStateEl.textContent = "🔴 Fleet Stopped";
                fleetStateEl.style.color = "var(--accent-rose)";
            }
        }
        
        // 2. Agents alive
        const fleetAgentsAliveEl = document.getElementById("fleet-agents-alive");
        if (fleetAgentsAliveEl) {
            fleetAgentsAliveEl.textContent = `Agents Alive: ${fs.agents_alive}`;
        }
        
        // 3. Last telemetry
        const fleetLastTelemetryEl = document.getElementById("fleet-last-telemetry");
        if (fleetLastTelemetryEl) {
            fleetLastTelemetryEl.textContent = fs.last_telemetry;
        }
        
        // 4. Heartbeat status
        const fleetHeartbeatStatusEl = document.getElementById("fleet-heartbeat-status");
        if (fleetHeartbeatStatusEl) {
            if (fs.heartbeat_ok) {
                fleetHeartbeatStatusEl.textContent = "Heartbeat: Healthy";
                fleetHeartbeatStatusEl.className = "badge badge-success";
            } else {
                fleetHeartbeatStatusEl.textContent = "Heartbeat: Lagging";
                fleetHeartbeatStatusEl.className = "badge badge-warning";
            }
        }
        
        // 5. Key ticks
        const keyTicksDisplayEl = document.getElementById("key-ticks-display");
        if (keyTicksDisplayEl) {
            keyTicksDisplayEl.innerHTML = "";
            Object.keys(fs.key_ticks).forEach(symbol => {
                const val = fs.key_ticks[symbol];
                let valColor = "#fff";
                
                if (val === "Market Closed") valColor = "var(--text-secondary)";
                else if (val === "Offline") valColor = "var(--accent-rose)";
                else if (val.includes("s ago")) {
                    const secs = parseFloat(val);
                    if (secs > 10) valColor = "var(--accent-yellow)";
                    else valColor = "var(--accent-emerald)";
                }
                
                const div = document.createElement("div");
                div.style.display = "flex";
                div.style.justify = "space-between";
                div.style.borderBottom = "1px solid rgba(255,255,255,0.05)";
                div.style.paddingBottom = "4px";
                div.innerHTML = `
                    <span style="color: var(--accent-cyan);">${symbol}:</span>
                    <span style="color: ${valColor};">${val}</span>
                `;
                keyTicksDisplayEl.appendChild(div);
            });
        }
    }

    function updateUI() {
        if (!rawData) return;
        updateSystemHealth();
        renderAssetMatrix();
        updateFleetStatus();

        const approvedAssets = rawData.assets.filter(a => a.verdict === "APPROVED" || a.verdict === "INSTITUTIONAL_READY");
        
        // 1. Calculate AUM based on global multiplier
        const baseAum = approvedAssets.length * 10000;
        const adjustedAum = baseAum * globalMultiplier;

        // Apply stress multipliers to metrics
        let totalPnlMultiplier = globalMultiplier;
        
        // Volatility stress reduces overall net expectancy (transaction costs increase)
        totalPnlMultiplier *= Math.max(0.1, 1 - (stressVol - 1) * 0.15);
        // Slippage stress eats directly into the profit factor and Net returns
        totalPnlMultiplier *= Math.max(0.05, 1 - (stressSlip - 1) * 0.2);

        if (stressBlackSwan) {
            // Black Swan wipes out the gains
            totalPnlMultiplier *= -0.4; // heavy drawdown PnL
        }

        const adjustedPnl = rawData.summary.total_pnl * totalPnlMultiplier;

        // Calculate VaR (weighted portfolio DD * global multiplier * stress factors)
        const avgDrawdown = rawData.summary.portfolio_max_dd;
        let portfolioVaR = avgDrawdown * globalMultiplier * (1 + (stressVol - 1) * 0.5 + (stressSlip - 1) * 0.3);
        
        if (stressBlackSwan) {
            portfolioVaR = Math.max(portfolioVaR, 8.0); // Hard Drawdown hit
        }

        // Render KPIs
        valAumEl.textContent = `$${adjustedAum.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        valPnlEl.textContent = `$${adjustedPnl.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        
        // Visual indicator class for PnL
        if (adjustedPnl < 0) {
            valPnlEl.className = "kpi-value kpi-trend trend-down";
        } else {
            valPnlEl.className = "kpi-value pnl-positive";
        }

        valVarEl.textContent = `${portfolioVaR.toFixed(2)}%`;
        if (portfolioVaR >= 8.0 || stressBlackSwan) {
            valVarEl.style.color = "var(--accent-rose)";
        } else {
            valVarEl.style.color = "var(--text-primary)";
        }

        valChannelsEl.textContent = `${approvedAssets.length} / ${rawData.assets.length}`;
        
        const activePct = (approvedAssets.length / rawData.assets.length) * 100;
        valChannelsPctEl.textContent = `${activePct.toFixed(0)}% active rate`;

        // 2. Render Table
        renderTable();

        // Render Pipeline Status Table and Counters
        renderPipelineStatus();

        // 3. Render Guards
        updateGuardsDisplay();

        // 4. Update configuration values for selected symbol
        populateConfigPanel();

        // 5. Render Charts
        renderPnlPieChart(approvedAssets);
        renderEquityChart(approvedAssets, totalPnlMultiplier, portfolioVaR);
    }

    function renderTable() {
        assetsBodyEl.innerHTML = "";
        
        rawData.assets.forEach(asset => {
            const isApproved = asset.verdict === "APPROVED" || asset.verdict === "INSTITUTIONAL_READY";
            const row = document.createElement("tr");
            
            if (asset.symbol === selectedSymbol) {
                row.classList.add("selected");
            }
            
            // Allocation description
            const allocationText = isApproved ? `$${(10000 * globalMultiplier).toLocaleString()} USD` : "$0.00 (Flat)";
            const weightText = isApproved ? `${(100 / rawData.summary.approved_count).toFixed(1)}%` : "0.0%";

            // Custom verdict badge classes
            const verdictClass = asset.verdict === "INSTITUTIONAL_READY" ? "APPROVED" : asset.verdict;

            // Apply stress to profit factor displayed
            let displayPF = asset.profit_factor;
            if (displayPF && displayPF < 999) {
                displayPF = displayPF * Math.max(0.2, 1 - (stressVol - 1) * 0.1 - (stressSlip - 1) * 0.15);
                if (stressBlackSwan) displayPF = displayPF * 0.3;
            }

            row.innerHTML = `
                <td class="asset-symbol">${asset.symbol}</td>
                <td><span style="text-transform: capitalize;">${asset.type}</span></td>
                <td><span class="asset-badge ${verdictClass}">${asset.verdict}</span></td>
                <td>${asset.sharpe_ratio.toFixed(2)}</td>
                <td>${displayPF === null || displayPF > 50 ? "inf" : displayPF.toFixed(2)}</td>
                <td>${allocationText}</td>
                <td><span class="badge badge-info">${weightText}</span></td>
            `;

            row.addEventListener("click", () => {
                selectedSymbol = asset.symbol;
                document.querySelectorAll("#assets-body tr").forEach(r => r.classList.remove("selected"));
                row.classList.add("selected");
                updateGuardsDisplay();
                populateConfigPanel();
            });

            assetsBodyEl.appendChild(row);
        });
    }

    function updateGuardsDisplay() {
        const asset = rawData.assets.find(a => a.symbol === selectedSymbol);
        if (!asset) return;

        guardSymbolTitle.textContent = asset.symbol;

        // If Black Swan or high stress is enabled, we simulate spread and atr shock triggers
        const spreadGuardTriggered = stressSlip >= 4.0 || stressBlackSwan;
        const slippageGuardTriggered = stressSlip >= 3.5 || stressBlackSwan;
        const atrShockTriggered = stressVol >= 3.0 || stressBlackSwan;

        // Show active or warning states in guards
        if (spreadGuardTriggered) {
            guardSpreadEl.textContent = "BLOCKED / VETOED";
            guardSpreadEl.className = "guard-status status-disabled";
        } else {
            setGuardStatus(guardSpreadEl, asset.guards.spread_guard_enabled);
        }

        if (slippageGuardTriggered) {
            guardSlippageEl.textContent = "BLOCKED / VETOED";
            guardSlippageEl.className = "guard-status status-disabled";
        } else {
            setGuardStatus(guardSlippageEl, asset.guards.slippage_guard_enabled);
        }

        if (atrShockTriggered) {
            guardAtrEl.textContent = "BLOCKED / VETOED";
            guardAtrEl.className = "guard-status status-disabled";
        } else {
            setGuardStatus(guardAtrEl, asset.guards.atr_shock_block_enabled);
        }

        guardDailyLimitEl.textContent = `${asset.guards.daily_loss_limit_pct.toFixed(1)}%`;
        guardWeeklyLimitEl.textContent = `${asset.guards.weekly_soft_stop_pct.toFixed(1)}%`;
        guardHardLimitEl.textContent = `${asset.guards.hard_drawdown_pct.toFixed(1)}%`;
    }

    function populateConfigPanel() {
        const asset = rawData.assets.find(a => a.symbol === selectedSymbol);
        if (!asset) return;

        configSymbolTitle.textContent = asset.symbol;
        cfgRiskPctInput.value = asset.config.risk_per_trade_pct;
        cfgDailyLimitInput.value = asset.guards.daily_loss_limit_pct;
        cfgStopAtrInput.value = asset.config.stop_atr_mult;
        cfgTpAtrInput.value = asset.config.tp_atr_mult;
        cfgMlEnabledCheck.checked = asset.config.ml_enabled;
    }

    function setGuardStatus(element, isEnabled) {
        if (isEnabled) {
            element.textContent = "ACTIVE";
            element.className = "guard-status status-active";
        } else {
            element.textContent = "DISABLED";
            element.className = "guard-status status-disabled";
        }
    }

    function renderPnlPieChart(approvedAssets) {
        const ctx = document.getElementById("pnlPieChart").getContext("2d");
        
        if (pnlChart) {
            pnlChart.destroy();
        }

        const labels = approvedAssets.map(a => a.symbol);
        const data = approvedAssets.map(a => Math.max(0, a.net_pnl * globalMultiplier));

        pnlChart = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: [
                        "#06b6d4", "#6366f1", "#10b981", "#f59e0b", 
                        "#f43f5e", "#a855f7", "#3b82f6", "#ec4899"
                    ],
                    borderColor: "rgba(10, 15, 30, 0.8)",
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "right",
                        labels: {
                            color: "#8e9bb3",
                            font: { family: "Plus Jakarta Sans", size: 11, weight: 600 }
                        }
                    }
                }
            }
        });
    }

    function renderEquityChart(approvedAssets, totalPnlMultiplier, portfolioVaR) {
        const ctx = document.getElementById("equityChart").getContext("2d");
        
        if (equityChart) {
            equityChart.destroy();
        }

        const points = 20;
        const labels = Array.from({length: points}, (_, i) => `Day ${i + 1}`);
        
        let currentEquity = approvedAssets.length * 10000 * globalMultiplier;
        const totalNetPnl = rawData.summary.total_pnl * totalPnlMultiplier;
        const incrementalProfit = totalNetPnl / points;

        const dataPoints = [currentEquity - totalNetPnl];
        
        for (let i = 1; i < points; i++) {
            // Apply higher randomness and downward fluctuations if volatility/slippage is high
            const shockFactor = (stressVol + stressSlip) * 0.15;
            const randomVal = (Math.random() - 0.25 - (stressBlackSwan ? 0.6 : 0)) * (incrementalProfit * shockFactor);
            const prev = dataPoints[i - 1];
            dataPoints.push(prev + incrementalProfit + randomVal);
        }
        dataPoints.push(currentEquity); 

        // Dynamic chart gradient colors (Red if losing, Blue if winning)
        const gradient = ctx.createLinearGradient(0, 0, 0, 300);
        if (totalNetPnl < 0) {
            gradient.addColorStop(0, "rgba(244, 63, 94, 0.35)");
            gradient.addColorStop(1, "rgba(244, 63, 94, 0)");
        } else {
            gradient.addColorStop(0, "rgba(6, 182, 212, 0.35)");
            gradient.addColorStop(1, "rgba(6, 182, 212, 0)");
        }

        equityChart = new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: [{
                    label: "Combined Simulated Portfolio Equity ($)",
                    data: dataPoints,
                    fill: true,
                    backgroundColor: gradient,
                    borderColor: totalNetPnl < 0 ? "#f43f5e" : "#06b6d4",
                    borderWidth: 3,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: "#fff",
                    tension: 0.35
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { color: "rgba(255, 255, 255, 0.03)" },
                        ticks: { color: "#8e9bb3", font: { family: "Plus Jakarta Sans", size: 10 } }
                    },
                    y: {
                        grid: { color: "rgba(255, 255, 255, 0.03)" },
                        ticks: { 
                            color: "#8e9bb3", 
                            font: { family: "Plus Jakarta Sans", size: 10 },
                            callback: (val) => `$${val.toLocaleString()}`
                        }
                    }
                }
            }
        });
    }

    let printedLogs = new Set();

    function streamConsoleLogs(logs) {
        // Go through logs backwards to print oldest first
        for (let i = logs.length - 1; i >= 0; i--) {
            const log = logs[i];
            const logKey = `${log.timestamp}-${log.symbol}-${log.message}`;
            if (!printedLogs.has(logKey)) {
                printedLogs.add(logKey);
                appendConsoleLine(log.symbol, log.message, log.timestamp);
            }
        }
    }

    function appendConsoleLine(symbol, message, timestampStr = null) {
        if (!timestampStr) {
            const now = new Date();
            timestampStr = now.toTimeString().split(" ")[0];
        } else if (timestampStr.includes(" ")) {
            timestampStr = timestampStr.split(" ")[1];
        }
        
        const line = document.createElement("div");
        line.className = "console-line";
        line.innerHTML = `
            <span class="console-timestamp">[${timestampStr}]</span>
            <span class="console-sym">${symbol}:</span>
            <span>${message}</span>
        `;
        consoleOutputEl.appendChild(line);
        consoleOutputEl.scrollTop = consoleOutputEl.scrollHeight;
    }

    // Custom Toast alert visual system
    function showToast(message, type = "success") {
        const container = document.getElementById("toast-container");
        if (!container) return;

        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        
        let icon = "✓";
        if (type === "error") icon = "⚠️";
        if (type === "info") icon = "ℹ️";

        toast.innerHTML = `<span>${icon}</span> ${message}`;
        container.appendChild(toast);

        // Slide out and remove toast
        setTimeout(() => {
            toast.style.animation = "slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) reverse forwards";
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 3500);
    }

    async function loadArchitectureTab() {
        try {
            // Load Module Registry
            const modRes = await fetch("/architecture/module_registry.json");
            const modules = await modRes.json();
            
            const moduleGrid = document.getElementById("module-health-grid");
            if (moduleGrid) {
                moduleGrid.innerHTML = "";
                modules.forEach(m => {
                    const card = document.createElement("div");
                    card.className = "module-card";
                    
                    const statusDotColor = m.status === "active" ? "var(--accent-emerald)" : "var(--accent-yellow)";
                    
                    card.innerHTML = `
                        <div class="module-header">
                            <span class="module-name-title">${m.module_name}</span>
                            <div style="display: flex; align-items: center; gap: 6px;">
                                <span style="width: 8px; height: 8px; border-radius: 50%; background-color: ${statusDotColor}; display: inline-block;"></span>
                                <span style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: ${statusDotColor};">${m.status}</span>
                            </div>
                        </div>
                        <span class="module-path">${m.file_path}</span>
                        <p class="module-desc">${m.responsibility}</p>
                        <div class="module-meta">
                            <span>Layer: <strong style="color: #fff; text-transform: capitalize;">${m.owner_layer}</strong></span>
                            <span class="risk-badge ${m.risk_level}">${m.risk_level} risk</span>
                        </div>
                    `;
                    moduleGrid.appendChild(card);
                });
            }

            // Dynamic asset matrix rendering handles the fullAssetBody tab
        } catch (err) {
            console.error("Failed to load architecture registries:", err);
        }
    }

    function renderPipelineStatus() {
        const pipelineBodyEl = document.getElementById("pipeline-body");
        if (!pipelineBodyEl || !rawData || !rawData.pipeline_status) return;

        pipelineBodyEl.innerHTML = "";
        rawData.pipeline_status.forEach(p => {
            const row = document.createElement("tr");

            let colorClass = "gray";
            if (p.color) {
                colorClass = p.color;
            }

            const scoreStr = p.ml_score !== null && p.ml_score !== undefined ? p.ml_score.toFixed(4) : "0.0000";

            let statusColor = "var(--text-secondary)";
            if (p.color === "green") statusColor = "var(--accent-emerald)";
            else if (p.color === "cyan") statusColor = "var(--accent-cyan)";
            else if (p.color === "yellow") statusColor = "var(--accent-yellow)";
            else if (p.color === "red") statusColor = "var(--accent-rose)";
            else if (p.color === "purple") statusColor = "#a855f7";
            else if (p.color === "blue") statusColor = "#3b82f6";
            else if (p.color === "orange") statusColor = "#f97316";

            row.innerHTML = `
                <td class="asset-symbol" style="font-weight: 700;">${p.symbol}</td>
                <td style="font-family: 'Space Grotesk', monospace; font-size: 12px; color: #fff;">${p.order_name}</td>
                <td style="font-family: 'Space Grotesk', monospace; font-weight: 700; font-size: 12px; color: ${statusColor};">
                    <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: ${statusColor}; margin-right: 6px; box-shadow: 0 0 8px ${statusColor};"></span>
                    ${p.stage}
                </td>
                <td style="color: var(--text-secondary); font-size: 13px; font-family: 'Space Grotesk', monospace; font-weight: 500;">${p.block_reason}</td>
                <td style="font-family: 'Space Grotesk', monospace; font-size: 12px; font-weight: 600;">${scoreStr}</td>
                <td style="font-family: 'Space Grotesk', monospace; font-weight: 700; font-size: 11px;">
                    <span class="badge" style="background-color: ${p.risk_action === "ALLOW" ? "rgba(16, 185, 129, 0.1)" : (p.risk_action === "N/A" ? "rgba(255, 255, 255, 0.05)" : "rgba(244, 63, 94, 0.1)")}; color: ${p.risk_action === "ALLOW" ? "var(--accent-emerald)" : (p.risk_action === "N/A" ? "var(--text-secondary)" : "var(--accent-rose)")}; border: 1px solid ${p.risk_action === "ALLOW" ? "rgba(16, 185, 129, 0.2)" : (p.risk_action === "N/A" ? "rgba(255, 255, 255, 0.1)" : "rgba(244, 63, 94, 0.2)")}; padding: 2px 6px;">
                        ${p.risk_action}
                    </span>
                </td>
                <td style="font-family: 'Space Grotesk', monospace; font-size: 12px; color: var(--text-secondary);">${p.last_update}</td>
            `;
            pipelineBodyEl.appendChild(row);
        });

        // Render summary counters
        if (rawData.pipeline_summary) {
            const s = rawData.pipeline_summary;
            document.getElementById("pipeline-total-symbols").textContent = s.total_symbols;
            document.getElementById("pipeline-signal-blocked").textContent = s.signal_blocked;
            document.getElementById("pipeline-ml-blocked").textContent = s.ml_blocked;
            document.getElementById("pipeline-risk-blocked").textContent = s.risk_blocked;
            document.getElementById("pipeline-execution-waiting").textContent = s.execution_waiting;
            document.getElementById("pipeline-orders-sent").textContent = s.orders_sent;
        }
    }
});
