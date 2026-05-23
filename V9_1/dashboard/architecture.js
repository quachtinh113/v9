// Architecture Panel Logic
document.addEventListener("DOMContentLoaded", () => {
    const serverTimeEl = document.getElementById("server-time");

    // Clock
    setInterval(() => {
        const d = new Date();
        serverTimeEl.textContent = d.toLocaleTimeString();
    }, 1000);

    loadArchitectureRegistries();

    async function loadArchitectureRegistries() {
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

            // Load Asset Registry
            const assetRes = await fetch("/architecture/asset_registry.json");
            const assets = await assetRes.json();
            
            const fullAssetBody = document.getElementById("asset-matrix-full-body");
            if (fullAssetBody) {
                fullAssetBody.innerHTML = "";
                assets.forEach(a => {
                    const row = document.createElement("tr");
                    const verdictClass = a.status === "APPROVED" ? "APPROVED" : "DISABLED";
                    
                    row.innerHTML = `
                        <td class="asset-symbol">${a.symbol}</td>
                        <td style="text-transform: capitalize;">${a.asset_class}</td>
                        <td><span class="asset-badge ${verdictClass}">${a.status}</span></td>
                        <td style="font-family: 'Space Grotesk', monospace; font-size: 12px; color: ${a.data_status === 'synced' ? 'var(--accent-emerald)' : 'var(--accent-rose)'};">${a.data_status}</td>
                        <td style="font-family: 'Space Grotesk', monospace; font-size: 12px; color: ${a.model_status === 'trained' ? 'var(--accent-emerald)' : 'var(--text-secondary)'};">${a.model_status}</td>
                        <td style="font-family: 'Space Grotesk', monospace; font-size: 12px; color: ${a.risk_status === 'nominal' ? 'var(--accent-emerald)' : 'var(--accent-yellow)'};">${a.risk_status}</td>
                        <td style="font-family: 'Space Grotesk', monospace; font-size: 12px; color: ${a.dashboard_status === 'active' ? 'var(--accent-emerald)' : 'var(--text-secondary)'};">${a.dashboard_status}</td>
                    `;
                    fullAssetBody.appendChild(row);
                });
            }
        } catch (err) {
            console.error("Failed to load architecture registries:", err);
        }
    }
});
