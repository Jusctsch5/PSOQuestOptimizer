/**
 * Renderer for item value calculation results
 */

/**
 * Render item value results
 */
function renderItemValueResults(result) {
    const container = document.getElementById('results-table');
    
    let html = '<div class="item-value-result">';
    
    // Display detailed breakdown if available
    if (result.breakdown) {
        if (result.item_type === 'weapon') {
            const breakdown = result.breakdown;
            
            // Header
            html += '<div class="breakdown-section">';
            html += '<h4>WEAPON VALUE CALCULATION BREAKDOWN</h4>';
            html += `<p><strong>Weapon:</strong> ${escapeHtml(breakdown.weapon_name || 'Unknown')}</p>`;
            html += `<p><strong>Average Expected Value:</strong> ${breakdown.total_value.toFixed(4)} PD</p>`;
            html += '<hr>';
            
            // Hit Probability Summary
            if (breakdown.three_roll_hit_prob !== undefined) {
                html += '<h5>Hit Probability Summary (Three Rolls):</h5>';
                html += '<ul>';
                html += `<li>Hit Rolled (at least one): ${(breakdown.three_roll_hit_prob * 100).toFixed(7)}%</li>`;
                html += `<li>No Hit: ${(breakdown.no_hit_prob * 100).toFixed(7)}%</li>`;
                html += `<li>Total: ${((breakdown.three_roll_hit_prob + breakdown.no_hit_prob) * 100).toFixed(7)}%</li>`;
                html += '</ul>';
                html += '<hr>';
            }
            
            // Hit Value Prices and Expected Values
            if (breakdown.hit_breakdown && breakdown.hit_breakdown.length > 0) {
                html += '<h5>Hit Value Prices and Expected Values:</h5>';
                html += '<table class="results-table">';
                html += '<thead><tr>';
                html += '<th>Hit</th>';
                html += '<th>Combined Prob</th>';
                html += '<th>Teched Hit</th>';
                html += '<th>Price Range</th>';
                html += '<th>Price (avg)</th>';
                html += '<th>Expected Value</th>';
                html += '</tr></thead>';
                html += '<tbody>';
                
                let totalCombinedProb = 0;
                let totalExpected = 0;
                
                for (const hit of breakdown.hit_breakdown) {
                    totalCombinedProb += hit.combined_prob;
                    totalExpected += hit.expected_value;
                    html += '<tr>';
                    html += `<td>${hit.hit_value}</td>`;
                    html += `<td>${(hit.combined_prob * 100).toFixed(7)}%</td>`;
                    html += `<td>${hit.teched_hit}</td>`;
                    html += `<td>${escapeHtml(hit.price_range || 'N/A')}</td>`;
                    html += `<td>${hit.price.toFixed(4)}</td>`;
                    html += `<td>${hit.expected_value.toFixed(7)}</td>`;
                    html += '</tr>';
                }
                
                // Total row
                html += '<tr style="font-weight: bold;">';
                html += `<td>Total</td>`;
                html += `<td>${(totalCombinedProb * 100).toFixed(7)}%</td>`;
                html += '<td></td>';
                html += '<td></td>';
                html += '<td></td>';
                html += `<td>${totalExpected.toFixed(7)}</td>`;
                html += '</tr>';
                html += '</tbody></table>';
                
                html += '<p><strong>Probability Check:</strong></p>';
                html += `<p>Combined probabilities (no hit + all hit values) sum to: ${(totalCombinedProb * 100).toFixed(7)}%</p>`;
                html += '<hr>';
            }
            
            // Calculation Equation
            html += '<h5>CALCULATION EQUATION:</h5>';
            html += '<p>Final Value = Hit Contribution + Attribute Contribution</p>';
            html += '<p><strong>Where:</strong></p>';
            html += '<ul>';
            html += '<li>Hit Contribution = sum over hit rows [price(hit) * combined_prob(hit)]</li>';
            html += '<li style="margin-left: 20px;">combined_prob already includes the three-roll hit chance and Pattern 5 distribution</li>';
            html += `<li style="margin-left: 20px;">= ${breakdown.hit_contribution.toFixed(4)} PD</li>`;
            html += '<li>Attribute Contribution (Pattern 5, >=50% prob slice already baked in)</li>';
            html += `<li style="margin-left: 20px;">= ${breakdown.attribute_contribution.toFixed(4)} PD</li>`;
            html += '</ul>';
            html += '<p><strong>Calculation:</strong></p>';
            html += `<p>${breakdown.hit_contribution.toFixed(4)} + ${breakdown.attribute_contribution.toFixed(4)} = ${breakdown.total_value.toFixed(4)} PD</p>`;
            html += '<hr>';
            
            // Final Result
            html += `<h4>FINAL RESULT: ${breakdown.total_value.toFixed(4)} PD</h4>`;
            
        } else if (result.item_type === 'frame') {
            const breakdown = result.breakdown;
            
            html += '<div class="breakdown-section">';
            html += '<h4>FRAME VALUE CALCULATION BREAKDOWN</h4>';
            html += `<p><strong>Frame:</strong> ${escapeHtml(breakdown.frame_name || 'Unknown')}</p>`;
            html += `<p><strong>Average Expected Value:</strong> ${breakdown.total_value.toFixed(4)} PD</p>`;
            html += '<hr>';
            
            // Stat Tier Probabilities
            html += '<h5>STAT TIER PROBABILITIES:</h5>';
            html += '<table class="results-table">';
            html += '<thead><tr><th>Tier</th><th>Probability</th></tr></thead>';
            html += '<tbody>';
            for (const [tier, prob] of Object.entries(breakdown.stat_probs)) {
                html += '<tr>';
                html += `<td>${tier.charAt(0).toUpperCase() + tier.slice(1)}</td>`;
                html += `<td>${(prob * 100).toFixed(7)}%</td>`;
                html += '</tr>';
            }
            html += '</tbody></table>';
            html += '<hr>';
            
            // Base Price
            html += '<h5>BASE PRICE:</h5>';
            html += `<p>Base Price: ${escapeHtml(breakdown.base_price_str)} = ${breakdown.base_price.toFixed(4)} PD</p>`;
            html += '<hr>';
            
            // Stat Tier Prices and Contributions
            html += '<h5>STAT TIER PRICES AND CONTRIBUTIONS:</h5>';
            html += '<table class="results-table">';
            html += '<thead><tr>';
            html += '<th>Tier</th>';
            html += '<th>Price Range</th>';
            html += '<th>Price (avg)</th>';
            html += '<th>Probability</th>';
            html += '<th>Contribution</th>';
            html += '</tr></thead>';
            html += '<tbody>';
            
            const tiers = ['low', 'medium', 'high', 'max'];
            for (const tier of tiers) {
                const tierDetail = breakdown.tier_details.find(t => t.tier === tier);
                if (tierDetail) {
                    html += '<tr>';
                    html += `<td>${tier.charAt(0).toUpperCase() + tier.slice(1)}</td>`;
                    html += `<td>${escapeHtml(tierDetail.price_range)}</td>`;
                    html += `<td>${tierDetail.price.toFixed(4)}</td>`;
                    html += `<td>${(tierDetail.probability * 100).toFixed(7)}%</td>`;
                    html += `<td>${tierDetail.contribution.toFixed(7)}</td>`;
                    html += '</tr>';
                }
            }
            html += '</tbody></table>';
            html += '<hr>';
            
            // Calculation Equation
            html += '<h5>CALCULATION EQUATION:</h5>';
            html += '<p>Final Value = sum over tiers [tier_price * tier_probability]</p>';
            html += '<p><strong>Where:</strong></p>';
            html += '<ul>';
            for (const tierDetail of breakdown.tier_details) {
                html += `<li>${tierDetail.tier.charAt(0).toUpperCase() + tierDetail.tier.slice(1)} tier: ${tierDetail.price.toFixed(4)} * ${(tierDetail.probability * 100).toFixed(7)}% = ${tierDetail.contribution.toFixed(4)} PD</li>`;
            }
            html += '</ul>';
            html += '<p><strong>Calculation:</strong></p>';
            const totalCheck = breakdown.tier_details.reduce((sum, t) => sum + t.contribution, 0);
            html += `<p>${totalCheck.toFixed(4)} = ${breakdown.total_value.toFixed(4)} PD</p>`;
            html += '<hr>';
            
            // Final Result
            html += `<h4>FINAL RESULT: ${breakdown.total_value.toFixed(4)} PD</h4>`;
            
        } else if (result.item_type === 'barrier') {
            const breakdown = result.breakdown;
            
            html += '<div class="breakdown-section">';
            html += '<h4>BARRIER VALUE CALCULATION BREAKDOWN</h4>';
            html += `<p><strong>Barrier:</strong> ${escapeHtml(breakdown.barrier_name || 'Unknown')}</p>`;
            html += `<p><strong>Average Expected Value:</strong> ${breakdown.total_value.toFixed(4)} PD</p>`;
            html += '<hr>';
            
            // Stat Tier Probabilities
            html += '<h5>STAT TIER PROBABILITIES:</h5>';
            html += '<table class="results-table">';
            html += '<thead><tr><th>Tier</th><th>Probability</th></tr></thead>';
            html += '<tbody>';
            for (const [tier, prob] of Object.entries(breakdown.stat_probs)) {
                html += '<tr>';
                html += `<td>${tier.charAt(0).toUpperCase() + tier.slice(1)}</td>`;
                html += `<td>${(prob * 100).toFixed(7)}%</td>`;
                html += '</tr>';
            }
            html += '</tbody></table>';
            html += '<hr>';
            
            // Base Price
            html += '<h5>BASE PRICE:</h5>';
            html += `<p>Base Price: ${escapeHtml(breakdown.base_price_str)} = ${breakdown.base_price.toFixed(4)} PD</p>`;
            html += '<hr>';
            
            // Stat Tier Prices and Contributions
            html += '<h5>STAT TIER PRICES AND CONTRIBUTIONS:</h5>';
            html += '<table class="results-table">';
            html += '<thead><tr>';
            html += '<th>Tier</th>';
            html += '<th>Price Range</th>';
            html += '<th>Price (avg)</th>';
            html += '<th>Probability</th>';
            html += '<th>Contribution</th>';
            html += '</tr></thead>';
            html += '<tbody>';
            
            const tiers = ['low', 'medium', 'high', 'max'];
            for (const tier of tiers) {
                const tierDetail = breakdown.tier_details.find(t => t.tier === tier);
                if (tierDetail) {
                    html += '<tr>';
                    html += `<td>${tier.charAt(0).toUpperCase() + tier.slice(1)}</td>`;
                    html += `<td>${escapeHtml(tierDetail.price_range)}</td>`;
                    html += `<td>${tierDetail.price.toFixed(4)}</td>`;
                    html += `<td>${(tierDetail.probability * 100).toFixed(7)}%</td>`;
                    html += `<td>${tierDetail.contribution.toFixed(7)}</td>`;
                    html += '</tr>';
                }
            }
            html += '</tbody></table>';
            html += '<hr>';
            
            // Calculation Equation
            html += '<h5>CALCULATION EQUATION:</h5>';
            html += '<p>Final Value = sum over tiers [tier_price * tier_probability]</p>';
            html += '<p><strong>Where:</strong></p>';
            html += '<ul>';
            for (const tierDetail of breakdown.tier_details) {
                html += `<li>${tierDetail.tier.charAt(0).toUpperCase() + tierDetail.tier.slice(1)} tier: ${tierDetail.price.toFixed(4)} * ${(tierDetail.probability * 100).toFixed(7)}% = ${tierDetail.contribution.toFixed(4)} PD</li>`;
            }
            html += '</ul>';
            html += '<p><strong>Calculation:</strong></p>';
            const totalCheck = breakdown.tier_details.reduce((sum, t) => sum + t.contribution, 0);
            html += `<p>${totalCheck.toFixed(4)} = ${breakdown.total_value.toFixed(4)} PD</p>`;
            html += '<hr>';
            
            // Final Result
            html += `<h4>FINAL RESULT: ${breakdown.total_value.toFixed(4)} PD</h4>`;
        }
        
        html += '</div>';
    } else {
        // Fallback: show basic value if no breakdown
        html += '<h3>Item Value Calculation</h3>';
        html += '<table class="results-table">';
        html += '<thead><tr>';
        html += '<th>Item Type</th>';
        html += '<th>Value (PD)</th>';
        html += '</tr></thead>';
        html += '<tbody>';
        html += '<tr>';
        html += `<td>${escapeHtml(result.item_type || 'Unknown')}</td>`;
        html += `<td>${result.value.toFixed(4)}</td>`;
        html += '</tr>';
        html += '</tbody></table>';
    }
    
    html += '</div>';
    
    container.innerHTML = html;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

