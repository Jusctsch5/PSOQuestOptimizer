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
            html += renderWeaponValueBreakdown(result.breakdown);
        } else if (result.item_type === 'frame' || result.item_type === 'barrier') {
            html += renderArmorValueBreakdown(result.breakdown, result.item_type);
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
 * Weapon breakdown (hit + attribute contributions)
 */
function renderWeaponValueBreakdown(breakdown) {
    let html = '<div class="breakdown-section">';
    html += '<h4>WEAPON VALUE CALCULATION BREAKDOWN</h4>';
    html += `<p><strong>Weapon:</strong> ${escapeHtml(breakdown.weapon_name || 'Unknown')}</p>`;
    html += `<p><strong>Average Expected Value:</strong> ${breakdown.total_value.toFixed(4)} PD</p>`;
    html += '<hr>';

    if (breakdown.three_roll_hit_prob !== undefined) {
        html += '<h5>Hit Probability Summary (Three Rolls):</h5>';
        html += '<ul>';
        html += `<li>Hit Rolled (at least one): ${(breakdown.three_roll_hit_prob * 100).toFixed(7)}%</li>`;
        html += `<li>No Hit: ${(breakdown.no_hit_prob * 100).toFixed(7)}%</li>`;
        html += `<li>Total: ${((breakdown.three_roll_hit_prob + breakdown.no_hit_prob) * 100).toFixed(7)}%</li>`;
        html += '</ul>';
        html += '<hr>';
    }

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

        html += '<tr style="font-weight: bold;">';
        html += '<td>Total</td>';
        html += `<td>${(totalCombinedProb * 100).toFixed(7)}%</td>`;
        html += '<td></td><td></td><td></td>';
        html += `<td>${totalExpected.toFixed(7)}</td>`;
        html += '</tr>';
        html += '</tbody></table>';

        html += '<p><strong>Probability Check:</strong></p>';
        html += `<p>Combined probabilities (no hit + all hit values) sum to: ${(totalCombinedProb * 100).toFixed(7)}%</p>`;
        html += '<hr>';
    }

    html += '<h5>CALCULATION EQUATION:</h5>';
    html += '<p>Final Value = Hit Contribution + Attribute Contribution</p>';
    html += '<p><strong>Where:</strong></p>';
    html += '<ul>';
    html += '<li>Hit Contribution = sum over hit rows [price(hit) * combined_prob(hit)]</li>';
    html += '<li style="margin-left: 20px;">combined_prob already includes the three-roll hit chance and Pattern 5 distribution</li>';
    html += `<li style="margin-left: 20px;">= ${breakdown.hit_contribution.toFixed(4)} PD</li>`;
    html += '<li>Attribute Contribution (Pattern 5, &gt;=50% prob slice already baked in)</li>';
    html += `<li style="margin-left: 20px;">= ${breakdown.attribute_contribution.toFixed(4)} PD</li>`;
    html += '</ul>';
    html += '<p><strong>Calculation:</strong></p>';
    html += `<p>${breakdown.hit_contribution.toFixed(4)} + ${breakdown.attribute_contribution.toFixed(4)} = ${breakdown.total_value.toFixed(4)} PD</p>`;
    html += '<hr>';
    html += `<h4>FINAL RESULT: ${breakdown.total_value.toFixed(4)} PD</h4>`;

    return html;
}

/**
 * Frame / barrier breakdown (uniform independent DFP×EVP rolls)
 */
function renderArmorValueBreakdown(breakdown, itemType) {
    const kindLabel = itemType === 'frame' ? 'FRAME' : 'BARRIER';
    const kindTitle = itemType === 'frame' ? 'Frame (Armor)' : 'Barrier (Shield)';
    const primary = (breakdown.primary_stat || (itemType === 'frame' ? 'dfp' : 'evp')).toUpperCase();
    const secondary = primary === 'DFP' ? 'EVP' : 'DFP';
    const [lo, hi] = breakdown.primary_range || [];
    const dfpOutcomes = breakdown.dfp_outcomes || 0;
    const evpOutcomes = breakdown.evp_outcomes || 0;
    const outcomeCount = breakdown.outcome_count || (dfpOutcomes * evpOutcomes) || 1;
    const perOutcome = breakdown.per_outcome_probability != null
        ? breakdown.per_outcome_probability
        : (1 / outcomeCount);
    const bothMaxProb = breakdown.both_max_probability || 0;
    const bothMaxContrib = breakdown.both_max_contribution || 0;
    const tiers = breakdown.tier_prices || {};
    const statRange = breakdown.stat_range || {};
    const dfpRange = formatStatRange(statRange.dfp);
    const evpRange = formatStatRange(statRange.evp);
    const dfpHi = Array.isArray(statRange.dfp) ? statRange.dfp[1] : '?';
    const evpHi = Array.isArray(statRange.evp) ? statRange.evp[1] : '?';
    const maxKey = tiers.max_key || 'Max (fallback from High/Med/Min)';
    const priceGroups = breakdown.price_groups || [];

    let html = '<div class="breakdown-section">';
    html += `<h4>${kindLabel} VALUE CALCULATION BREAKDOWN</h4>`;
    html += `<p><strong>${kindTitle}:</strong> ${escapeHtml(breakdown.item_name || 'Unknown')}</p>`;
    html += `<p><strong>Average Expected Value:</strong> ${Number(breakdown.total_value).toFixed(4)} PD</p>`;
    html += '<hr>';

    html += '<h5>STAT RANGES (INDEPENDENT UNIFORM ROLLS):</h5>';
    html += '<table class="results-table">';
    html += '<thead><tr><th>Stat</th><th>Range</th><th>Outcomes</th><th>Role</th></tr></thead><tbody>';
    html += `<tr><td>DFP</td><td>${escapeHtml(dfpRange)}</td><td>${dfpOutcomes}</td>` +
        `<td>${primary === 'DFP' ? 'Primary (Min/Med/High)' : 'Required for Max tier'}</td></tr>`;
    html += `<tr><td>EVP</td><td>${escapeHtml(evpRange)}</td><td>${evpOutcomes}</td>` +
        `<td>${primary === 'EVP' ? 'Primary (Min/Med/High)' : 'Required for Max tier'}</td></tr>`;
    html += '</tbody></table>';
    html += `<p>Joint outcomes: <strong>${dfpOutcomes} × ${evpOutcomes} = ${outcomeCount}</strong> ` +
        `(each ${(perOutcome * 100).toFixed(6)}%).</p>`;
    html += `<p><strong>Max tier</strong> only when both are max ` +
        `(DFP ${dfpHi} and EVP ${evpHi}): ` +
        `${(bothMaxProb * 100).toFixed(6)}% → ${Number(bothMaxContrib).toFixed(4)} PD contribution.</p>`;
    html += '<hr>';

    html += '<h5>PRICE GUIDE TIER ANCHORS:</h5>';
    html += '<table class="results-table">';
    html += '<thead><tr><th>Tier</th><th>Resolved PD</th><th>Notes</th></tr></thead><tbody>';
    html += `<tr><td>Base</td><td>${Number(breakdown.base_price).toFixed(4)}</td><td>${escapeHtml(String(breakdown.base_price_str ?? '0'))}</td></tr>`;
    html += `<tr><td>Min</td><td>${Number(tiers.min).toFixed(4)}</td><td>Floor (Min Stat, else base)</td></tr>`;
    html += `<tr><td>Med</td><td>${Number(tiers.med).toFixed(4)}</td><td>Mid interpolation on ${primary}</td></tr>`;
    html += `<tr><td>High</td><td>${Number(tiers.high).toFixed(4)}</td><td>Near-max ${primary}, or max ${primary} without max ${secondary}</td></tr>`;
    html += `<tr><td>Max</td><td>${Number(tiers.max).toFixed(4)}</td><td>Both stats max (${escapeHtml(maxKey)})</td></tr>`;
    html += '</tbody></table>';
    html += `<p>Non-dual-max rolls interpolate Min → Med → High by ${primary} quality. ` +
        `Exact max ${primary} alone uses High; Max requires max ${secondary} too.</p>`;
    html += '<hr>';

    html += '<h5>JOINT ROLL → PRICE GROUPS:</h5>';
    html += '<p>Outcomes that share the same PD are grouped. Probability is the share of joint rolls.</p>';
    html += '<div class="armor-price-groups">';
    html += '<table class="results-table">';
    html += '<thead><tr>';
    html += '<th>Rolls</th>';
    html += '<th>Price (PD)</th>';
    html += '<th>Probability</th>';
    html += '<th>Contribution (PD)</th>';
    html += '</tr></thead><tbody>';

    let totalProb = 0;
    let totalContribution = 0;
    for (const group of priceGroups) {
        totalProb += group.probability;
        totalContribution += group.contribution;
        const label = (() => {
            if (group.includes_both_max && Number(group.price) === Number(tiers.max)
                && Number(tiers.max) !== Number(tiers.high)) {
                return `Both max (DFP ${dfpHi} / EVP ${evpHi})`;
            }
            let text = `${primary} ${formatValueSpan(group.values || [])}`;
            if (group.includes_both_max) {
                text += ` (incl. both max ${dfpHi}/${evpHi})`;
            }
            return text;
        })();
        html += '<tr>';
        html += `<td>${escapeHtml(label)}</td>`;
        html += `<td>${Number(group.price).toFixed(4)}</td>`;
        html += `<td>${(group.probability * 100).toFixed(6)}%</td>`;
        html += `<td>${Number(group.contribution).toFixed(7)}</td>`;
        html += '</tr>';
    }
    html += '<tr style="font-weight: bold;">';
    html += '<td>Total</td><td></td>';
    html += `<td>${(totalProb * 100).toFixed(6)}%</td>`;
    html += `<td>${totalContribution.toFixed(7)}</td>`;
    html += '</tr>';
    html += '</tbody></table>';
    html += '</div>';
    html += '<hr>';

    html += '<h5>CALCULATION EQUATION:</h5>';
    html += `<p>E[PD] = (1/${outcomeCount}) × Σ price(DFP, EVP) over all joint rolls</p>`;
    html += '<p><strong>Where:</strong></p>';
    html += '<ul>';
    html += `<li>DFP and EVP roll independently and uniformly</li>`;
    html += `<li>${primary} quality drives Min / Med / High</li>`;
    html += `<li>Max tier only if DFP and EVP are both at range max</li>`;
    html += `<li>Max ${primary} without max ${secondary} → High tier</li>`;
    html += '</ul>';
    html += '<p><strong>Calculation:</strong></p>';
    html += `<p>${totalContribution.toFixed(4)} = ${Number(breakdown.total_value).toFixed(4)} PD</p>`;
    html += '<hr>';
    html += `<h4>FINAL RESULT: ${Number(breakdown.total_value).toFixed(4)} PD</h4>`;

    return html;
}

/**
 * Format [min, max] stat range for display.
 */
function formatStatRange(range) {
    if (!Array.isArray(range) || range.length < 2) {
        return 'N/A';
    }
    const [min, max] = range;
    if (min === max) {
        return String(min);
    }
    return `${min}–${max}`;
}

/**
 * Compact display for a list of primary-stat roll values.
 */
function formatValueSpan(values) {
    if (!values.length) {
        return '';
    }
    if (values.length === 1) {
        return String(values[0]);
    }
    const contiguous = values.every((v, i) => i === 0 || v === values[i - 1] + 1);
    if (contiguous) {
        if (values.length <= 3) {
            return values.join(', ');
        }
        return `${values[0]}–${values[values.length - 1]} (${values.length})`;
    }
    if (values.length <= 4) {
        return values.join(', ');
    }
    return `${values[0]}…${values[values.length - 1]} (${values.length})`;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
