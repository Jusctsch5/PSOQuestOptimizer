/**
 * Renderer for quest optimization results
 */

/** Column header tooltips (Optimize Quests results) */
const QUEST_RESULTS_HEADER_TOOLTIPS = {
    rank: 'Position in the ranking (1 = best). Sorted by PD per minute when quest times are available; otherwise by total PD.',
    questName: 'Full quest title and short quest code (e.g. MU1).',
    sectionId: 'Section ID used for area-specific rare drop rates (RDR) and which items enemies can drop.',
    episode: 'Episode: 1, 2, or 4.',
    pdPerQuest:
        'PD per quest: sums expected PD from enemy and box drops, raw photon-drop PD, and completion rewards. Completion rewards are the same entries as the Quest Reward column (when shown)—not a separate quest-item source.',
    enemies: 'Total number of enemies across the quest (used for drop expectations).',
    rawPdPerQuest:
        'Expected average number of photon drops per quest run (raw PD contribution from PD drops only, before item price value).',
    questReward: 'Quest completion reward items and their PD value contribution.',
    notableItem:
        'Next most worthwhile item by expected PD value for this quest (sources may be listed; number is total expected PD from that item). Hover the cell for per-source equations.',
};

/**
 * Escape text for use inside an HTML attribute (e.g. title="...").
 */
function escapeAttr(text) {
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

/**
 * Table header cell with native tooltip (title).
 */
function thWithTitle(label, tooltip) {
    const titleAttr = tooltip ? ` title="${escapeAttr(tooltip)}"` : '';
    return `<th scope="col" class="col-has-tooltip"${titleAttr}>${escapeHtml(label)}</th>`;
}

/**
 * Row tooltip for a notable item: total PD plus per-source equations from server `breakdown`.
 */
function formatNotableItemTooltip(item) {
    const name = item.item || 'Item';
    const total = Number(item.pd_value || 0);
    const totalStr = total.toFixed(6);
    const breakdown = item.breakdown;
    if (!Array.isArray(breakdown) || breakdown.length === 0) {
        return `${name}: total ${totalStr} PD (per-source breakdown unavailable — use latest optimizer output).`;
    }
    const lines = breakdown.map((b) => {
        const src = b.source != null ? String(b.source) : 'source';
        const eq = b.equation != null
            ? String(b.equation)
            : `expected_drops × item_price_pd = ${Number(b.expected_drops || 0).toFixed(8)} × ${Number(b.item_price_pd || 0).toFixed(8)} = ${Number(b.pd_value || 0).toFixed(6)}`;
        return `${src}: ${eq}`;
    });
    return `${name} — total ${totalStr} PD\n${lines.join('\n')}`;
}

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
    
    // Header row (tooltips on columns for quick reference)
    html += '<thead><tr>';
    html += thWithTitle('Rank', QUEST_RESULTS_HEADER_TOOLTIPS.rank);
    html += thWithTitle('Quest Name', QUEST_RESULTS_HEADER_TOOLTIPS.questName);
    if (showSectionId) {
        html += thWithTitle('Section ID', QUEST_RESULTS_HEADER_TOOLTIPS.sectionId);
    }
    html += thWithTitle('Episode', QUEST_RESULTS_HEADER_TOOLTIPS.episode);
    html += thWithTitle('PD/Quest', QUEST_RESULTS_HEADER_TOOLTIPS.pdPerQuest);
    html += thWithTitle('Enemies', QUEST_RESULTS_HEADER_TOOLTIPS.enemies);
    html += thWithTitle('Raw PD/Quest', QUEST_RESULTS_HEADER_TOOLTIPS.rawPdPerQuest);
    if (hasCompletionItems) {
        html += thWithTitle('Quest Reward', QUEST_RESULTS_HEADER_TOOLTIPS.questReward);
    }
    for (let i = 1; i <= notableItemsCount; i++) {
        html += thWithTitle(`Notable Item ${i}`, QUEST_RESULTS_HEADER_TOOLTIPS.notableItem);
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
        
        // Notable items columns (sources ordered by contribution, top first)
        const topItems = ranking.top_items || [];
        for (let i = 0; i < notableItemsCount; i++) {
            if (i < topItems.length && topItems[i]) {
                const item = topItems[i];
                const itemName = item.item || 'Unknown';
                const sources = item.enemies || [];
                const pdValue = item.pd_value || 0;
                const sourceLabel = sources.length > 1
                    ? sources.map(s => escapeHtml(s)).join(', ') + ': '
                    : (escapeHtml(sources[0] || 'Unknown') + ': ');
                const itemStr = `${escapeHtml(itemName)} (${sourceLabel}${pdValue.toFixed(4)})`;
                const breakdownTitle = escapeAttr(formatNotableItemTooltip(item));
                html += `<td class="notable-item-cell" title="${breakdownTitle}">${itemStr}</td>`;
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

