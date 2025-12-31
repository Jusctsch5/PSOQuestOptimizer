/**
 * Renderer for quest optimization results
 */

/**
 * Render quest rankings as an HTML table
 */
function renderResults(rankings, params) {
    const container = document.getElementById('results-table');
    
    if (!rankings || rankings.length === 0) {
        container.innerHTML = '<p>No results found.</p>';
        return;
    }
    
    // Determine if we need to show Section ID column
    const showSectionId = rankings.length > 0 && rankings.some(r => 
        r.section_id !== rankings[0].section_id
    );
    
    // Check if any quests have completion items
    const hasCompletionItems = rankings.some(r => 
        r.completion_items_pd > 0 && r.completion_items_breakdown
    );
    
    const notableItemsCount = params.notable_items || 5;
    const showDetails = params.show_details || false;
    
    // Create table
    let html = '<table class="results-table">';
    
    // Header row
    html += '<thead><tr>';
    html += '<th>Rank</th>';
    html += '<th>Quest Name</th>';
    if (showSectionId) {
        html += '<th>Section ID</th>';
    }
    html += '<th>Episode</th>';
    html += '<th>PD/Quest</th>';
    html += '<th>Enemies</th>';
    html += '<th>Raw PD/Quest</th>';
    if (hasCompletionItems) {
        html += '<th>Quest Reward</th>';
    }
    for (let i = 1; i <= notableItemsCount; i++) {
        html += `<th>Notable Item ${i}</th>`;
    }
    html += '</tr></thead>';
    
    // Body rows
    html += '<tbody>';
    rankings.forEach((ranking, index) => {
        const rank = index + 1;
        const questName = ranking.long_name 
            ? `${ranking.long_name} (${ranking.quest_name})`
            : ranking.quest_name;
        const episode = ranking.episode || 'N/A';
        const sectionId = ranking.section_id || 'Unknown';
        const totalPd = ranking.total_pd.toFixed(4);
        const enemies = ranking.total_enemies || 0;
        const rawPd = ranking.total_pd_drops.toFixed(4);
        
        html += '<tr>';
        html += `<td>${rank}</td>`;
        html += `<td>${escapeHtml(questName)}</td>`;
        if (showSectionId) {
            html += `<td>${escapeHtml(sectionId)}</td>`;
        }
        html += `<td>${episode}</td>`;
        html += `<td>${totalPd}</td>`;
        html += `<td>${enemies}</td>`;
        html += `<td>${rawPd}</td>`;
        
        // Quest Reward column
        if (hasCompletionItems) {
            let rewardStr = '';
            if (ranking.completion_items_pd > 0 && ranking.completion_items_breakdown) {
                const rewardItems = [];
                for (const [itemName, data] of Object.entries(ranking.completion_items_breakdown)) {
                    const itemPd = data.total_pd || 0;
                    rewardItems.push(`${escapeHtml(itemName)} (${itemPd.toFixed(4)})`);
                }
                rewardStr = rewardItems.join(', ');
            }
            html += `<td>${rewardStr}</td>`;
        }
        
        // Notable items columns
        const topItems = ranking.top_items || [];
        for (let i = 0; i < notableItemsCount; i++) {
            if (i < topItems.length && topItems[i]) {
                const item = topItems[i];
                const itemName = item.item || 'Unknown';
                const sources = item.enemies || [];
                const source = sources[0] || 'Unknown';
                const pdValue = item.pd_value || 0;
                const itemStr = `${escapeHtml(itemName)} (${escapeHtml(source)}: ${pdValue.toFixed(4)})`;
                html += `<td data-tooltip="${escapeHtml(itemStr)}">${itemStr}</td>`;
            } else {
                html += '<td></td>';
            }
        }
        
        html += '</tr>';
        
        // Detailed breakdown row (if show_details is true)
        if (showDetails) {
            html += `<tr class="details-row"><td colspan="${7 + (showSectionId ? 1 : 0) + (hasCompletionItems ? 1 : 0) + notableItemsCount}">`;
            html += renderDetailedBreakdown(ranking);
            html += '</td></tr>';
        }
    });
    html += '</tbody></table>';
    
    container.innerHTML = html;
}

/**
 * Render detailed breakdown for a quest
 */
function renderDetailedBreakdown(ranking) {
    let html = '<div class="detailed-breakdown">';
    html += '<h3>Enemy Breakdown</h3>';
    
    const enemyBreakdown = ranking.enemy_breakdown || {};
    if (Object.keys(enemyBreakdown).length === 0) {
        html += '<p>No enemy breakdown available.</p>';
    } else {
        html += '<table class="breakdown-table">';
        html += '<thead><tr>';
        html += '<th>Enemy</th>';
        html += '<th>Drop</th>';
        html += '<th>DAR</th>';
        html += '<th>RDR</th>';
        html += '<th>Rate</th>';
        html += '<th>Count</th>';
        html += '<th>Exp Drops</th>';
        html += '<th>PD Value</th>';
        html += '<th>Exp Value</th>';
        html += '</tr></thead>';
        html += '<tbody>';
        
        for (const [enemy, data] of Object.entries(enemyBreakdown)) {
            if (data.error) {
                html += '<tr>';
                html += `<td>${escapeHtml(enemy)}</td>`;
                html += `<td colspan="8">${escapeHtml(data.error)}</td>`;
                html += '</tr>';
            } else {
                const item = data.item || 'Unknown';
                const count = data.count || 0;
                const adjustedDar = data.adjusted_dar || data.dar || 0;
                const adjustedRdr = data.adjusted_rdr || data.rdr || 0;
                const actualRate = adjustedDar * adjustedRdr;
                const expectedDrops = data.expected_drops || 0;
                const itemPricePd = data.item_price_pd || 0;
                const expValue = data.pd_value || 0;
                
                html += '<tr>';
                html += `<td>${escapeHtml(enemy)}</td>`;
                html += `<td>${escapeHtml(item)}</td>`;
                html += `<td>${adjustedDar.toFixed(6)}</td>`;
                html += `<td>${adjustedRdr.toFixed(8)}</td>`;
                html += `<td>${actualRate.toFixed(8)}</td>`;
                html += `<td>${count}</td>`;
                html += `<td>${expectedDrops.toFixed(8)}</td>`;
                html += `<td>${itemPricePd.toFixed(8)}</td>`;
                html += `<td>${expValue.toFixed(8)}</td>`;
                html += '</tr>';
            }
        }
        
        html += '</tbody></table>';
    }
    
    // Box breakdown
    const boxBreakdown = ranking.box_breakdown || {};
    if (Object.keys(boxBreakdown).length > 0) {
        html += '<h3>Box Breakdown</h3>';
        html += '<table class="breakdown-table">';
        html += '<thead><tr>';
        html += '<th>Item</th>';
        html += '<th>Area</th>';
        html += '<th>Rate</th>';
        html += '<th>Boxes</th>';
        html += '<th>Exp Drops</th>';
        html += '<th>PD Value</th>';
        html += '<th>Exp Value</th>';
        html += '</tr></thead>';
        html += '<tbody>';
        
        for (const [itemName, data] of Object.entries(boxBreakdown)) {
            const area = data.area || 'Unknown';
            const rate = data.rate || 0;
            const boxCount = data.box_count || 0;
            const expectedDrops = data.expected_drops || 0;
            const itemPricePd = data.item_price_pd || 0;
            const expValue = data.pd_value || 0;
            
            html += '<tr>';
            html += `<td>${escapeHtml(itemName)}</td>`;
            html += `<td>${escapeHtml(area)}</td>`;
            html += `<td>${rate.toFixed(8)}</td>`;
            html += `<td>${boxCount}</td>`;
            html += `<td>${expectedDrops.toFixed(8)}</td>`;
            html += `<td>${itemPricePd.toFixed(8)}</td>`;
            html += `<td>${expValue.toFixed(8)}</td>`;
            html += '</tr>';
        }
        
        html += '</tbody></table>';
    }
    
    html += '</div>';
    return html;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

