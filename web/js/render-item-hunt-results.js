/**
 * Renderer for item hunt optimization results
 */

/**
 * Render item hunt results
 */
function renderItemHuntResults(result, params) {
    const container = document.getElementById('results-table');
    
    if (!result.quest_results || result.quest_results.length === 0) {
        container.innerHTML = '<p>No quests found that drop this item.</p>';
        return;
    }
    
    let html = `<h3>Item: ${escapeHtml(result.item_type || 'Unknown')} - ${escapeHtml(params.item_name)}</h3>`;
    
    // Quest Results Table
    html += '<h4>Best Quests for Hunting</h4>';
    html += '<table class="results-table">';
    html += '<thead><tr>';
    html += '<th>Rank</th>';
    html += '<th>Quest Name</th>';
    html += '<th>Section ID</th>';
    html += '<th>Drops From</th>';
    html += '<th>Drop Probability</th>';
    html += '<th>Expected Runs</th>';
    html += '<th>Runs for 95%</th>';
    html += '</tr></thead>';
    html += '<tbody>';
    
    result.quest_results.forEach((quest, index) => {
        const rank = index + 1;
        const questName = quest.long_name 
            ? `${quest.long_name} (${quest.quest_name})`
            : quest.quest_name;
        const probability = quest.probability || 0;
        const percentage = quest.percentage || 0;
        const expectedRuns = probability > 0 ? (1 / probability).toFixed(1) : '∞';
        const runs95 = probability > 0 ? calculateRunsForProbability(probability, 0.95).toFixed(1) : '∞';
        
        // Build drops from string from contributions
        const dropsFrom = [];
        if (quest.contributions && quest.contributions.length > 0) {
            quest.contributions.forEach(contrib => {
                if (contrib.source === 'Box') {
                    dropsFrom.push(`Box (${escapeHtml(contrib.area)})`);
                } else if (contrib.source === 'Technique') {
                    dropsFrom.push(`${escapeHtml(contrib.enemy)} (${escapeHtml(contrib.area)})`);
                } else if (contrib.enemy) {
                    dropsFrom.push(escapeHtml(contrib.enemy));
                }
            });
        }
        const dropsFromStr = dropsFrom.length > 0 ? dropsFrom.join(', ') : 'Unknown';
        
        html += '<tr>';
        html += `<td>${rank}</td>`;
        html += `<td>${escapeHtml(questName)}</td>`;
        html += `<td>${escapeHtml(quest.section_id || 'Unknown')}</td>`;
        html += `<td>${dropsFromStr}</td>`;
        html += `<td>${percentage.toFixed(6)}%</td>`;
        html += `<td>${expectedRuns}</td>`;
        html += `<td>${runs95}</td>`;
        html += '</tr>';
        
        // Show contributions if details requested
        if (params.show_details && quest.contributions && quest.contributions.length > 0) {
            html += `<tr class="details-row"><td colspan="7">`;
            html += '<div class="detailed-breakdown">';
            html += '<h5>Contributions:</h5>';
            html += '<ul>';
            quest.contributions.forEach(contrib => {
                if (contrib.source === 'Box') {
                    html += `<li>Box (${escapeHtml(contrib.area)}): ${contrib.box_count} boxes, ${(contrib.probability * 100).toFixed(6)}%</li>`;
                } else if (contrib.source === 'Technique') {
                    html += `<li>${escapeHtml(contrib.enemy)} (${escapeHtml(contrib.area)}): ${contrib.count} kills, ${(contrib.probability * 100).toFixed(6)}%</li>`;
                } else {
                    html += `<li>${escapeHtml(contrib.enemy)}: ${contrib.count} kills, ${(contrib.probability * 100).toFixed(6)}%</li>`;
                }
            });
            html += '</ul>';
            html += '</div>';
            html += '</td></tr>';
        }
    });
    
    html += '</tbody></table>';
    
    // Enemy Drops Section
    if (result.enemy_drops && result.enemy_drops.length > 0) {
        html += '<h4>Enemies that Drop this Item</h4>';
        html += '<table class="results-table">';
        html += '<thead><tr>';
        html += '<th>Enemy</th>';
        html += '<th>Section ID</th>';
        html += '<th>Area</th>';
        html += '<th>Drop Rate</th>';
        html += '<th>Expected Kills</th>';
        html += '</tr></thead>';
        html += '<tbody>';
        
        result.enemy_drops.forEach(enemy => {
            const dropRate = enemy.drop_rate || 0;
            const expectedKills = dropRate > 0 ? (1 / dropRate).toFixed(1) : '∞';
            
            html += '<tr>';
            html += `<td>${escapeHtml(enemy.enemy)}</td>`;
            html += `<td>${escapeHtml(enemy.section_id || 'N/A')}</td>`;
            html += `<td>${escapeHtml(enemy.area || 'Unknown')}</td>`;
            html += `<td>${enemy.drop_rate_percent.toFixed(6)}%</td>`;
            html += `<td>${expectedKills}</td>`;
            html += '</tr>';
        });
        
        html += '</tbody></table>';
    }
    
    // Box Drops Section
    if (result.box_drops && result.box_drops.length > 0) {
        html += '<h4>Boxes that Drop this Item</h4>';
        html += '<table class="results-table">';
        html += '<thead><tr>';
        html += '<th>Area</th>';
        html += '<th>Section ID</th>';
        html += '<th>Box Count</th>';
        html += '<th>Drop Rate</th>';
        html += '<th>Expected Boxes</th>';
        html += '</tr></thead>';
        html += '<tbody>';
        
        result.box_drops.forEach(box => {
            const dropRate = box.drop_rate || 0;
            const expectedBoxes = dropRate > 0 ? (1 / dropRate).toFixed(1) : '∞';
            
            html += '<tr>';
            html += `<td>${escapeHtml(box.area)}</td>`;
            html += `<td>${escapeHtml(box.section_id || 'N/A')}</td>`;
            html += `<td>${box.box_count || 0}</td>`;
            html += `<td>${box.drop_rate_percent.toFixed(6)}%</td>`;
            html += `<td>${expectedBoxes}</td>`;
            html += '</tr>';
        });
        
        html += '</tbody></table>';
    }
    
    container.innerHTML = html;
}

/**
 * Calculate runs needed for target probability
 */
function calculateRunsForProbability(dropRate, targetProbability = 0.95) {
    if (dropRate <= 0) return Infinity;
    if (dropRate >= 1) return 1.0;
    if (targetProbability >= 1) return Infinity;
    
    const numerator = Math.log(1 - targetProbability);
    const denominator = Math.log(1 - dropRate);
    
    if (denominator === 0) return Infinity;
    
    return numerator / denominator;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

