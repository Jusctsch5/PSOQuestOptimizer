/**
 * Ephinea weekly boost rotation (browser-only).
 *
 * Cycle (changes 00:00 UTC each Sunday):
 *   XP -> DAR -> Rare Enemy -> RDR -> XP ...
 *
 * Calibrated so the week starting 2026-05-31 00:00 UTC is RDR.
 */

const WEEKLY_BOOST_CYCLE = ['XP', 'DAR', 'RareEnemy', 'RDR'];

/** Sunday 2026-05-31 00:00:00 UTC — known RDR week start. */
const WEEKLY_BOOST_ANCHOR_UTC_MS = Date.UTC(2026, 4, 31);
const WEEKLY_BOOST_ANCHOR_INDEX = WEEKLY_BOOST_CYCLE.indexOf('RDR');

const WEEKLY_BOOST_SELECT_IDS = ['weekly-boost', 'item-hunt-weekly-boost'];
const MS_PER_WEEK = 7 * 24 * 60 * 60 * 1000;

const WEEKLY_BOOST_LABELS = {
    XP: 'XP',
    DAR: 'DAR (Drop Anything Rate)',
    RareEnemy: 'Rare Enemy',
    RDR: 'RDR (Rare Drop Rate)',
};

function getWeeklyBoostWeekStartUtcMs(now = new Date()) {
    const weekStart = new Date(Date.UTC(
        now.getUTCFullYear(),
        now.getUTCMonth(),
        now.getUTCDate(),
    ));
    weekStart.setUTCDate(weekStart.getUTCDate() - weekStart.getUTCDay());
    return weekStart.getTime();
}

function getCurrentWeeklyBoost(now = new Date()) {
    const weekStartMs = getWeeklyBoostWeekStartUtcMs(now);
    const weeksSinceAnchor = Math.floor((weekStartMs - WEEKLY_BOOST_ANCHOR_UTC_MS) / MS_PER_WEEK);
    const index = ((WEEKLY_BOOST_ANCHOR_INDEX + weeksSinceAnchor) % WEEKLY_BOOST_CYCLE.length
        + WEEKLY_BOOST_CYCLE.length) % WEEKLY_BOOST_CYCLE.length;
    return WEEKLY_BOOST_CYCLE[index];
}

function getNextWeeklyBoostChangeUtc(now = new Date()) {
    const weekStartMs = getWeeklyBoostWeekStartUtcMs(now);
    return new Date(weekStartMs + MS_PER_WEEK);
}

function formatWeeklyBoostTooltip(boost, nextChangeUtc) {
    const label = WEEKLY_BOOST_LABELS[boost] || boost;
    const nextText = nextChangeUtc.toISOString().replace('.000Z', ' UTC');
    return `Auto-detected Ephinea weekly boost: ${label}. Next change: ${nextText}.`;
}

function setWeeklyBoostSelectValue(selectEl, boost) {
    if (!selectEl) {
        return;
    }
    selectEl.value = boost;
    selectEl.title = formatWeeklyBoostTooltip(boost, getNextWeeklyBoostChangeUtc());
}

function updateWeeklyBoostWidget(now = new Date()) {
    const boost = getCurrentWeeklyBoost(now);
    const widget = document.getElementById('weekly-boost-widget');

    document.querySelectorAll('.weekly-boost-cell').forEach((cell) => {
        cell.classList.toggle('weekly-boost-cell-active', cell.dataset.boost === boost);
    });

    if (widget) {
        widget.title = formatWeeklyBoostTooltip(boost, getNextWeeklyBoostChangeUtc(now));
    }
}

function applyWeeklyBoostToForm(now = new Date()) {
    const boost = getCurrentWeeklyBoost(now);
    WEEKLY_BOOST_SELECT_IDS.forEach((id) => {
        setWeeklyBoostSelectValue(document.getElementById(id), boost);
    });
    updateWeeklyBoostWidget(now);
    return boost;
}

function syncWeeklyBoostSelects(changedSelect) {
    WEEKLY_BOOST_SELECT_IDS.forEach((id) => {
        const selectEl = document.getElementById(id);
        if (selectEl && selectEl !== changedSelect) {
            selectEl.value = changedSelect.value;
        }
    });
}

function scheduleWeeklyBoostRefresh() {
    const nextChange = getNextWeeklyBoostChangeUtc();
    const delay = Math.max(0, nextChange.getTime() - Date.now()) + 50;
    setTimeout(() => {
        applyWeeklyBoostToForm();
        scheduleWeeklyBoostRefresh();
    }, delay);
}

function initWeeklyBoostControls() {
    applyWeeklyBoostToForm();
    scheduleWeeklyBoostRefresh();

    WEEKLY_BOOST_SELECT_IDS.forEach((id) => {
        const selectEl = document.getElementById(id);
        if (!selectEl) {
            return;
        }
        selectEl.addEventListener('change', () => {
            syncWeeklyBoostSelects(selectEl);
            WEEKLY_BOOST_SELECT_IDS.forEach((otherId) => {
                const otherEl = document.getElementById(otherId);
                if (otherEl) {
                    const boost = otherEl.value || getCurrentWeeklyBoost();
                    otherEl.title = boost
                        ? formatWeeklyBoostTooltip(boost, getNextWeeklyBoostChangeUtc())
                        : '';
                }
            });
        });
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWeeklyBoostControls);
} else {
    initWeeklyBoostControls();
}
