// Portfolio Command Center - Logic Engine
document.addEventListener("DOMContentLoaded", () => {
    let rawData = null;
    let pnlChart = null;
    let equityChart = null;
    let selectedSymbol = "US30";
    let globalMultiplier = 1.0;

    // Tab switching setup
    const navItems = {
        "nav-dashboard": "tab-content-dashboard",
        "nav-assets": "tab-content-assets",
        "nav-risk": "tab-content-risk",
        "nav-architecture": "tab-content-architecture"
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
    
    // Slider & Guard Elements
    const allocationSlider = document.getElementById("allocation-slider");
    const globalMultiplierVal = document.getElementById("global-multiplier-val");
    const guardSymbolTitle = document.getElementById("selected-symbol-guard");
    
    // Guard statuses
    const guardSpreadEl = document.getElementById("guard-spread");
    const guardSlippageEl = document.getElementById("guard-slippage");
    const guardAtrEl = document.getElementById("guard-atr");
    const guardDailyLimitEl = document.getElementById("guard-daily-limit");
    const guardWeeklyLimitEl = document.getElementById("guard-weekly-limit");
    const guardHardLimitEl = document.getElementById("guard-hard-limit");

    // Clock
    setInterval(() => {
        const d = new Date();
        serverTimeEl.textContent = d.toLocaleTimeString();
    }, 1000);

    // Initial load
    fetchData();
    loadArchitectureTab();

    // Slider listener
    allocationSlider.addEventListener("input", (e) => {
        globalMultiplier = parseFloat(e.target.value);
        globalMultiplierVal.textContent = `${globalMultiplier.toFixed(1)}x`;
        updateUI();
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

    function updateUI() {
        if (!rawData) return;

        const approvedAssets = rawData.assets.filter(a => a.verdict === "APPROVED" || a.verdict === "INSTITUTIONAL_READY");
        
        // 1. Calculate weighted AUM & PnL based on global multiplier
        const baseAum = approvedAssets.length * 10000;
        const adjustedAum = baseAum * globalMultiplier;
        const adjustedPnl = rawData.summary.total_pnl * globalMultiplier;

        // Calculate VaR (weighted portfolio DD * global multiplier)
        const avgDrawdown = rawData.summary.portfolio_max_dd;
        const portfolioVaR = avgDrawdown * globalMultiplier;

        // Render KPIs
        valAumEl.textContent = `$${adjustedAum.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        valPnlEl.textContent = `$${adjustedPnl.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        valVarEl.textContent = `${portfolioVaR.toFixed(2)}%`;
        valChannelsEl.textContent = `${approvedAssets.length} / ${rawData.assets.length}`;
        
        const activePct = (approvedAssets.length / rawData.assets.length) * 100;
        valChannelsPctEl.textContent = `${activePct.toFixed(0)}% active rate`;

        // 2. Render Table
        renderTable();

        // 3. Render Guards
        updateGuardsDisplay();

        // 4. Render Charts
        renderPnlPieChart(approvedAssets);
        renderEquityChart(approvedAssets);
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

            row.innerHTML = `
                <td class="asset-symbol">${asset.symbol}</td>
                <td><span style="text-transform: capitalize;">${asset.type}</span></td>
                <td><span class="asset-badge ${verdictClass}">${asset.verdict}</span></td>
                <td>${asset.sharpe_ratio.toFixed(2)}</td>
                <td>${asset.profit_factor === null || asset.profit_factor > 1000 ? "inf" : asset.profit_factor.toFixed(2)}</td>
                <td>${allocationText}</td>
                <td><span class="badge badge-info">${weightText}</span></td>
            `;

            row.addEventListener("click", () => {
                selectedSymbol = asset.symbol;
                document.querySelectorAll("#assets-body tr").forEach(r => r.classList.remove("selected"));
                row.classList.add("selected");
                updateGuardsDisplay();
            });

            assetsBodyEl.appendChild(row);
        });
    }

    function updateGuardsDisplay() {
        const asset = rawData.assets.find(a => a.symbol === selectedSymbol);
        if (!asset) return;

        guardSymbolTitle.textContent = asset.symbol;

        // Update indicators
        setGuardStatus(guardSpreadEl, asset.guards.spread_guard_enabled);
        setGuardStatus(guardSlippageEl, asset.guards.slippage_guard_enabled);
        setGuardStatus(guardAtrEl, asset.guards.atr_shock_block_enabled);

        guardDailyLimitEl.textContent = `${asset.guards.daily_loss_limit_pct.toFixed(1)}%`;
        guardWeeklyLimitEl.textContent = `${asset.guards.weekly_soft_stop_pct.toFixed(1)}%`;
        guardHardLimitEl.textContent = `${asset.guards.hard_drawdown_pct.toFixed(1)}%`;
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
                        "#06b6d4", "#6366f1", "#10b981", "#eab308", 
                        "#ec4899", "#8b5cf6", "#f97316", "#a855f7"
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
                            color: "#94a3b8",
                            font: { family: "Outfit", size: 11 }
                        }
                    }
                }
            }
        });
    }

    function renderEquityChart(approvedAssets) {
        const ctx = document.getElementById("equityChart").getContext("2d");
        
        if (equityChart) {
            equityChart.destroy();
        }

        // Generate synthetic daily points (20 steps) to simulate historical equity curve
        // compound interest curve with slight fluctuations
        const points = 20;
        const labels = Array.from({length: points}, (_, i) => `Day ${i + 1}`);
        
        // Sum total portfolio returns
        let currentEquity = approvedAssets.length * 10000 * globalMultiplier;
        const totalNetPnl = rawData.summary.total_pnl * globalMultiplier;
        const incrementalProfit = totalNetPnl / points;

        const dataPoints = [currentEquity - totalNetPnl];
        
        // Generate values with small fluctuations
        for (let i = 1; i < points; i++) {
            const randomVolatility = (Math.random() - 0.2) * (incrementalProfit * 0.4); // slightly upward trend
            const prev = dataPoints[i - 1];
            dataPoints.push(prev + incrementalProfit + randomVolatility);
        }
        dataPoints.push(currentEquity); // end at adjusted value

        // Setup smooth gradient background
        const gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, "rgba(6, 182, 212, 0.35)");
        gradient.addColorStop(1, "rgba(6, 182, 212, 0)");

        equityChart = new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: [{
                    label: "Combined Simulated Portfolio Equity ($)",
                    data: dataPoints,
                    fill: true,
                    backgroundColor: gradient,
                    borderColor: "#06b6d4",
                    borderWidth: 3,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: "#fff",
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: { color: "#94a3b8", font: { family: "Outfit" } }
                    },
                    y: {
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: { 
                            color: "#94a3b8", 
                            font: { family: "Outfit" },
                            callback: (val) => `$${val.toLocaleString()}`
                        }
                    }
                }
            }
        });
    }

    function streamConsoleLogs(logs) {
        consoleOutputEl.innerHTML = "";
        let index = 0;
        
        function appendNextLog() {
            if (index >= logs.length) return;
            const log = logs[index];
            const line = document.createElement("div");
            line.className = "console-line";
            line.innerHTML = `
                <span class="console-timestamp">[${log.timestamp.split(" ")[1]}]</span>
                <span class="console-sym">${log.symbol}:</span>
                <span>${log.message}</span>
            `;
            consoleOutputEl.appendChild(line);
            consoleOutputEl.scrollTop = consoleOutputEl.scrollHeight;
            index++;
            
            // Random delay to simulate real stream
            setTimeout(appendNextLog, 400 + Math.random() * 800);
        }

        appendNextLog();
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
                    
                    const statusDotColor = m.status === "active" ? "#10b981" : "#eab308";
                    
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

            // Load Asset Registry
            const assetRes = await fetch("/architecture/asset_registry.json");
            const assets = await assetRes.json();
            
            const fullAssetBody = document.getElementById("asset-matrix-full-body");
            if (fullAssetBody) {
                fullAssetBody.innerHTML = "";
                assets.forEach(a => {
                    const row = document.createElement("tr");
                    
                    const verdictClass = a.status === "APPROVED" ? "APPROVED" : "DISABLED";
                    const statusDotColor = a.status === "APPROVED" ? "#10b981" : "#f43f5e";
                    
                    row.innerHTML = `
                        <td class="asset-symbol">${a.symbol}</td>
                        <td style="text-transform: capitalize;">${a.asset_class}</td>
                        <td><span class="asset-badge ${verdictClass}">${a.status}</span></td>
                        <td style="font-family: monospace; font-size: 12px; color: ${a.data_status === 'synced' ? '#10b981' : '#f43f5e'};">${a.data_status}</td>
                        <td style="font-family: monospace; font-size: 12px; color: ${a.model_status === 'trained' ? '#10b981' : '#94a3b8'};">${a.model_status}</td>
                        <td style="font-family: monospace; font-size: 12px; color: ${a.risk_status === 'nominal' ? '#10b981' : '#eab308'};">${a.risk_status}</td>
                        <td style="font-family: monospace; font-size: 12px; color: ${a.dashboard_status === 'active' ? '#10b981' : '#94a3b8'};">${a.dashboard_status}</td>
                    `;
                    fullAssetBody.appendChild(row);
                });
            }
        } catch (err) {
            console.error("Failed to load architecture registries:", err);
        }
    }
});
