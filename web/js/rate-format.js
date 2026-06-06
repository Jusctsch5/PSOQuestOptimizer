/**
 * Format drop rates for display (decimal/percent vs PSO-style 1/N fractions).
 * Calculations stay in decimal probabilities; this module is display-only.
 */

const RATE_FORMAT_STORAGE_KEY = 'pso-rate-format';

function normalizeRateFormat(mode) {
    if (!mode || mode === 'decimal') {
        return 'decimal';
    }
    const value = String(mode).trim().toLowerCase();
    if (value === 'fraction' || value === 'fractions' || value === 'frac' || value === '1/n') {
        return 'fraction';
    }
    return 'decimal';
}

function formatDenominator(denominator) {
    const roundedInt = Math.round(denominator);
    if (Math.abs(denominator - roundedInt) < 1e-9) {
        return String(roundedInt);
    }

    const roundedOne = Math.round(denominator * 10) / 10;
    if (Math.abs(denominator - roundedOne) < 0.05) {
        return roundedOne.toFixed(1).replace(/\.0$/, '');
    }

    return Number(denominator.toFixed(4)).toString();
}

function formatRateFraction(rate) {
    if (rate <= 0) {
        return '0';
    }
    if (rate >= 1) {
        return '1/1';
    }
    return `1/${formatDenominator(1 / rate)}`;
}

function formatRateDecimal(rate, asPercent = true, precision = null) {
    if (asPercent) {
        const places = precision != null ? precision : 6;
        return `${(rate * 100).toFixed(places)}%`;
    }
    const places = precision != null ? precision : 8;
    return rate.toFixed(places);
}

function formatRate(rate, mode = 'decimal', options = {}) {
    const { asPercent = true, precision = null } = options;
    if (normalizeRateFormat(mode) === 'fraction') {
        return formatRateFraction(rate);
    }
    return formatRateDecimal(rate, asPercent, precision);
}

function formatRateChange(baseRate, adjustedRate, mode = 'decimal', options = {}) {
    const { tolerance = 1e-12 } = options;
    const baseText = formatRate(baseRate, mode, options);
    if (Math.abs(adjustedRate - baseRate) <= tolerance) {
        return baseText;
    }
    const adjustedText = formatRate(adjustedRate, mode, options);
    return `${baseText} -> ${adjustedText}`;
}

function getStoredRateFormat() {
    try {
        return normalizeRateFormat(localStorage.getItem(RATE_FORMAT_STORAGE_KEY));
    } catch (_err) {
        return 'decimal';
    }
}

function setStoredRateFormat(mode) {
    try {
        localStorage.setItem(RATE_FORMAT_STORAGE_KEY, normalizeRateFormat(mode));
    } catch (_err) {
        // Ignore storage failures (private browsing, etc.)
    }
}

function initRateFormatControls() {
    const checkboxes = document.querySelectorAll('.rate-format-fraction');
    if (checkboxes.length === 0) {
        return;
    }

    const stored = getStoredRateFormat();
    checkboxes.forEach((checkbox) => {
        checkbox.checked = stored === 'fraction';
        checkbox.addEventListener('change', () => {
            const mode = checkbox.checked ? 'fraction' : 'decimal';
            setStoredRateFormat(mode);
            checkboxes.forEach((other) => {
                if (other !== checkbox) {
                    other.checked = checkbox.checked;
                }
            });
        });
    });
}

document.addEventListener('DOMContentLoaded', initRateFormatControls);
