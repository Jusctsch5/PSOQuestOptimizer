/**
 * Pyodide loader and optimizer interface
 */

let pyodide = null;
let pyodideReady = false;
// Base path: determine from current URL path
// If we're at /web/ or /web/index.html, use '../' to go up to repo root
// If we're at / or /index.html, use './' (deployed environment)
const basePath = (() => {
    const path = window.location.pathname;
    return path.includes('/web/') ? '../' : './';
})();

// List of Python files to load (relative to web directory)
const PYTHON_MODULES = [
    // Core modules
    'drop_tables/__init__.py',
    'drop_tables/weapon_patterns.py',
    'price_guide/__init__.py',
    'price_guide/price_guide.py',
    'price_guide/weapon_value_calculator.py',
    'price_guide/armor_value_calculator.py',
    'price_guide/item_value_calculator.py',
    'quests/__init__.py',
    'quests/quest_listing.py',
    'quest_optimizer/__init__.py',
    'quest_optimizer/quest_calculator.py',
    'optimize_quests.py',
    'optimize_item_hunting.py',
    'calculate_item_value.py',
    'py-api/api.py',
];

// Data files to load
const DATA_FILES = {
    drop_table: 'drop_tables/drop_tables_ultimate.json',
    quests: 'quests/quests.json',
    price_guide: [
        'price_guide/data/weapons.json',
        'price_guide/data/frames.json',
        'price_guide/data/barriers.json',
        'price_guide/data/units.json',
        'price_guide/data/mags.json',
        'price_guide/data/techniques.json',
        'price_guide/data/tools.json',
        'price_guide/data/cells.json',
        'price_guide/data/services.json',
        'price_guide/data/meseta.json',
        'price_guide/data/common_weapons.json',
        'price_guide/data/srankweapons.json',
    ],
};

/**
 * Initialize Pyodide and load all required modules
 */
async function initializePyodide() {
    const loadingIndicator = document.getElementById('loading-indicator');
    const errorDisplay = document.getElementById('error-display');
    const resultsContainer = document.getElementById('results-container');

    try {
        // Show results container and loading indicator during initialization
        resultsContainer.classList.remove('hidden');
        loadingIndicator.classList.remove('hidden');
        loadingIndicator.querySelector('p').textContent = 'Loading Pyodide...';

        // Load Pyodide
        pyodide = await loadPyodide({
            indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.24.1/full/',
        });

        loadingIndicator.querySelector('p').textContent = 'Loading Python modules...';

        // Initialize cache and check version
        await initCache();
        await checkVersion(basePath);

        // Load Python modules
        for (const modulePath of PYTHON_MODULES) {
            try {
                const fetchUrl = `${basePath}${modulePath}`;
                const code = await fetchTextWithCache(fetchUrl);

                // Determine the path in Pyodide's filesystem
                // For modules, we need to maintain the directory structure
                const pyodidePath = `/${modulePath}`;
                const dirPath = pyodidePath.substring(0, pyodidePath.lastIndexOf('/'));

                // Create directory if needed (skip if dirPath is empty or just '/')
                if (dirPath && dirPath !== '/' && dirPath.length > 0) {
                    pyodide.runPython(`
import os
os.makedirs("${dirPath}", exist_ok=True)
`);
                }

                // Write file
                pyodide.FS.writeFile(pyodidePath, code);
            } catch (error) {
                console.error(`Error loading ${modulePath}:`, error);
                throw new Error(`Failed to load Python module ${modulePath}: ${error.message}`);
            }
        }

        // Set up Python path - root for packages, py-api for api module
        pyodide.runPython(`
import sys
sys.path.insert(0, '/')
sys.path.insert(0, '/py-api')
`);

        loadingIndicator.querySelector('p').textContent = 'Ready!';
        pyodideReady = true;
        loadingIndicator.classList.add('hidden');
        resultsContainer.classList.add('hidden');

    } catch (error) {
        console.error('Pyodide initialization error:', error);
        errorDisplay.textContent = `Initialization error: ${error.message}`;
        errorDisplay.classList.remove('hidden');
        loadingIndicator.classList.add('hidden');
        pyodideReady = false;
    }
}

/**
 * Load data files and return as objects
 */
async function loadDataFiles() {
    const data = {
        drop_table: null,
        quests: null,
        price_guide: {},
    };

    try {
        // Ensure cache is initialized
        if (!db) {
            await initCache();
        }

        // Load drop table (using cache)
        try {
            data.drop_table = await fetchJSONWithCache(`${basePath}${DATA_FILES.drop_table}`);
        } catch (error) {
            throw new Error(`Failed to load drop table: ${error.message}`);
        }

        // Load quests (using cache)
        try {
            data.quests = await fetchJSONWithCache(`${basePath}${DATA_FILES.quests}`);
        } catch (error) {
            throw new Error(`Failed to load quests: ${error.message}`);
        }

        // Load price guide files (using cache)
        for (const priceGuideFile of DATA_FILES.price_guide) {
            try {
                const filename = priceGuideFile.split('/').pop();
                data.price_guide[filename] = await fetchJSONWithCache(`${basePath}${priceGuideFile}`);
            } catch (error) {
                console.warn(`Failed to load ${priceGuideFile}, skipping...`, error);
            }
        }

        return data;
    } catch (error) {
        console.error('Error loading data files:', error);
        throw error;
    }
}

/**
 * Get active tab
 */
function getActiveTab() {
    const activeTab = document.querySelector('.tab-btn.active');
    return activeTab ? activeTab.dataset.tab : 'optimize-quests';
}

/**
 * Get form parameters for optimize quests
 */
function getOptimizeQuestsParameters() {
    const form = document.getElementById('optimizer-form');
    const formData = new FormData(form);

    // Handle RBR list
    const rbrListStr = formData.get('rbr-list');
    const rbrList = rbrListStr && rbrListStr.trim() ? rbrListStr.trim().split(/\s+/) : null;

    // Parse quest filter as space-separated list
    const questFilterStr = formData.get('quest-filter');
    const quest_filter = questFilterStr && questFilterStr.trim()
        ? questFilterStr.trim().split(/\s+/)
        : null;

    const dlRaw = formData.get('daily-luck');
    const dailyLuck = dlRaw === null || dlRaw === '' ? 0 : parseInt(dlRaw, 10);
    const daily_luck = Number.isFinite(dailyLuck) ? dailyLuck : 0;

    const params = {
        section_id: formData.get('section-id') || 'All',
        quest_filter: quest_filter,
        weekly_boost: formData.get('weekly-boost') || null,
        event_active: formData.get('event-active') || null,
        notable_items: parseInt(formData.get('notable-items')) || 5,
        show_details: document.getElementById('show-details').checked,
        exclude_event_quests: document.getElementById('exclude-event-quests').checked,
        quest_times: {}, // TODO: Load quest times if available
        rbr_active: rbrList !== null,
        rbr_list: rbrList,
        daily_luck,
    };

    return params;
}

/**
 * Get form parameters for optimize item hunt
 */
function getOptimizeItemHuntParameters() {
    const form = document.getElementById('optimizer-form');
    const formData = new FormData(form);

    const questFilterStr = formData.get('item-hunt-quest-filter');
    const quest_filter = questFilterStr && questFilterStr.trim()
        ? questFilterStr.trim().split(/\s+/)
        : null;

    const rbrListStr = formData.get('item-hunt-rbr-list');
    const rbrList = rbrListStr && rbrListStr.trim()
        ? rbrListStr.trim().split(/\s+/)
        : null;

    const ihDlRaw = formData.get('item-hunt-daily-luck');
    const ihDailyLuck = ihDlRaw === null || ihDlRaw === '' ? 0 : parseInt(ihDlRaw, 10);
    const daily_luck = Number.isFinite(ihDailyLuck) ? ihDailyLuck : 0;

    const params = {
        item_name: formData.get('item-name'),
        quest_filter: quest_filter,
        rbr_active: false,  // Not used when rbr_list is provided
        rbr_list: rbrList,
        weekly_boost: formData.get('item-hunt-weekly-boost') || null,
        event_active: formData.get('item-hunt-event-active') || null,
        exclude_event_quests: document.getElementById('item-hunt-exclude-event-quests').checked,
        top_n: parseInt(formData.get('item-hunt-top-n')) || 10,
        show_details: document.getElementById('item-hunt-show-details').checked,
        daily_luck,
    };

    return params;
}

/**
 * Get form parameters for calculate item value
 */
function getCalculateItemValueParameters() {
    const form = document.getElementById('optimizer-form');
    const formData = new FormData(form);

    const params = {
        item_name: formData.get('value-item-name'),
        drop_area: formData.get('drop-area') || null,
        price_strategy: formData.get('price-strategy') || 'MINIMUM',
    };

    return params;
}

/**
 * Call Python API to optimize quests
 */
async function optimizeQuests() {
    if (!pyodideReady) {
        throw new Error('Pyodide is not ready yet');
    }

    const loadingIndicator = document.getElementById('loading-indicator');
    const errorDisplay = document.getElementById('error-display');
    const resultsContainer = document.getElementById('results-container');

    try {
        // Hide previous results and errors, show results container
        resultsContainer.classList.remove('hidden');
        errorDisplay.classList.add('hidden');

        // Show loading in results area, hide results table
        const resultsTable = document.getElementById('results-table');
        resultsTable.innerHTML = '';
        loadingIndicator.classList.remove('hidden');
        loadingIndicator.querySelector('p').textContent = 'Processing Data';

        // Load data files
        const data = await loadDataFiles();

        loadingIndicator.querySelector('p').textContent = 'Calculating quest rankings...';

        // Get form parameters
        const params = getOptimizeQuestsParameters();

        // Call Python API
        // Convert JavaScript values to Python equivalents
        const convertToPython = (obj) => {
            return JSON.stringify(obj)
                .replace(/\bnull\b/g, 'None')
                .replace(/\btrue\b/g, 'True')
                .replace(/\bfalse\b/g, 'False');
        };

        const result = pyodide.runPython(`
import json
from api import optimize_quests

drop_table_data = ${convertToPython(data.drop_table)}
quests_data = ${convertToPython(data.quests)}
price_guide_data = ${convertToPython(data.price_guide)}
params = ${convertToPython(params)}

result = optimize_quests(drop_table_data, quests_data, price_guide_data, params)
json.dumps(result)
`);

        const resultObj = JSON.parse(result);

        // Hide loading
        loadingIndicator.classList.add('hidden');

        // Check for errors
        if (resultObj.error) {
            errorDisplay.textContent = resultObj.error;
            errorDisplay.classList.remove('hidden');
            return;
        }

        // Display results
        renderResults(resultObj.rankings, params);
        resultsContainer.classList.remove('hidden');

    } catch (error) {
        console.error('Error optimizing quests:', error);
        loadingIndicator.classList.add('hidden');
        errorDisplay.textContent = `Error: ${error.message}`;
        errorDisplay.classList.remove('hidden');
    }
}

/**
 * Switch to a specific tab
 */
function switchToTab(tabId) {
    console.log('Switching to tab:', tabId);
    const tabButtons = document.querySelectorAll('.tab-btn');

    // Remove active class from all tabs
    tabButtons.forEach(b => b.classList.remove('active'));

    // Add active class to the target tab button
    const targetButton = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
    if (targetButton) {
        targetButton.classList.add('active');
    } else {
        console.error('Tab button not found for:', tabId);
    }

    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });

    // Show active tab content
    const tabContent = document.getElementById(`tab-${tabId}`);
    if (tabContent) {
        tabContent.classList.remove('hidden');
        console.log('Tab content shown:', tabId);
    } else {
        console.error('Tab content not found for:', tabId);
    }

    // Update submit button text
    const submitBtn = document.getElementById('submit-btn');
    if (submitBtn) {
        if (tabId === 'optimize-quests') {
            submitBtn.textContent = 'Optimize Quests';
        } else if (tabId === 'optimize-item-hunt') {
            submitBtn.textContent = 'Find Best Quests';
        } else if (tabId === 'calculate-item-value') {
            submitBtn.textContent = 'Calculate Value';
        }
    }
}

/**
 * Handle tab switching
 */
function setupTabHandlers() {
    const tabButtons = document.querySelectorAll('.tab-btn');

    console.log('Setting up tab handlers, found', tabButtons.length, 'buttons');

    if (tabButtons.length === 0) {
        console.error('No tab buttons found!');
        return;
    }

    tabButtons.forEach((btn, index) => {
        const tabId = btn.dataset.tab;
        console.log(`Setting up handler for button ${index}:`, tabId);
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('Tab button clicked:', tabId);
            if (tabId) {
                switchToTab(tabId);
            } else {
                console.error('Tab button missing data-tab attribute:', btn);
            }
        });
    });

    // Initialize first tab (optimize-quests) as active
    switchToTab('optimize-quests');
}

/**
 * Handle form submission
 */
function setupFormHandlers() {
    const form = document.getElementById('optimizer-form');
    const resetBtn = document.getElementById('reset-btn');

    // Handle form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const activeTab = getActiveTab();

        // Validate required fields based on active tab
        if (activeTab === 'optimize-item-hunt') {
            const itemName = document.getElementById('item-name').value.trim();
            if (!itemName) {
                const errorDisplay = document.getElementById('error-display');
                errorDisplay.textContent = 'Item name is required for item hunt optimization.';
                errorDisplay.classList.remove('hidden');
                document.getElementById('item-name').focus();
                return;
            }
        } else if (activeTab === 'calculate-item-value') {
            const itemName = document.getElementById('value-item-name').value.trim();
            if (!itemName) {
                const errorDisplay = document.getElementById('error-display');
                errorDisplay.textContent = 'Item name is required for value calculation.';
                errorDisplay.classList.remove('hidden');
                document.getElementById('value-item-name').focus();
                return;
            }
        }

        // Clear any previous errors
        document.getElementById('error-display').classList.add('hidden');

        if (activeTab === 'optimize-quests') {
            await optimizeQuests();
        } else if (activeTab === 'optimize-item-hunt') {
            await optimizeItemHunting();
        } else if (activeTab === 'calculate-item-value') {
            await calculateItemValue();
        }
    });

    // Handle reset
    resetBtn.addEventListener('click', () => {
        form.reset();
        document.getElementById('results-container').classList.add('hidden');
        document.getElementById('error-display').classList.add('hidden');
    });
}

/**
 * Call Python API to optimize item hunting
 */
async function optimizeItemHunting() {
    if (!pyodideReady) {
        throw new Error('Pyodide is not ready yet');
    }

    const loadingIndicator = document.getElementById('loading-indicator');
    const errorDisplay = document.getElementById('error-display');
    const resultsContainer = document.getElementById('results-container');

    try {
        // Hide previous results and errors, show results container
        resultsContainer.classList.remove('hidden');
        errorDisplay.classList.add('hidden');

        // Show loading in results area, hide results table
        const resultsTable = document.getElementById('results-table');
        resultsTable.innerHTML = '';
        loadingIndicator.classList.remove('hidden');
        loadingIndicator.querySelector('p').textContent = 'Processing Data';

        // Load data files
        const data = await loadDataFiles();

        loadingIndicator.querySelector('p').textContent = 'Finding best quests for item...';

        // Get form parameters
        const params = getOptimizeItemHuntParameters();

        if (!params.item_name) {
            throw new Error('Item name is required');
        }

        // Call Python API
        const convertToPython = (obj) => {
            return JSON.stringify(obj)
                .replace(/\bnull\b/g, 'None')
                .replace(/\btrue\b/g, 'True')
                .replace(/\bfalse\b/g, 'False');
        };

        const result = pyodide.runPython(`
import json
from api import optimize_item_hunting

drop_table_data = ${convertToPython(data.drop_table)}
quests_data = ${convertToPython(data.quests)}
price_guide_data = ${convertToPython(data.price_guide)}
params = ${convertToPython(params)}

result = optimize_item_hunting(drop_table_data, quests_data, price_guide_data, params)
json.dumps(result)
`);

        const resultObj = JSON.parse(result);

        // Hide loading
        loadingIndicator.classList.add('hidden');

        // Check for errors
        if (resultObj.error) {
            errorDisplay.textContent = resultObj.error;
            errorDisplay.classList.remove('hidden');
            return;
        }

        // Display results
        renderItemHuntResults(resultObj, params);
        resultsContainer.classList.remove('hidden');

    } catch (error) {
        console.error('Error optimizing item hunt:', error);
        loadingIndicator.classList.add('hidden');
        errorDisplay.textContent = `Error: ${error.message}`;
        errorDisplay.classList.remove('hidden');
    }
}

/**
 * Call Python API to calculate item value
 */
async function calculateItemValue() {
    if (!pyodideReady) {
        throw new Error('Pyodide is not ready yet');
    }

    const loadingIndicator = document.getElementById('loading-indicator');
    const errorDisplay = document.getElementById('error-display');
    const resultsContainer = document.getElementById('results-container');

    try {
        // Hide previous results and errors, show results container
        resultsContainer.classList.remove('hidden');
        errorDisplay.classList.add('hidden');

        // Show loading in results area, hide results table
        const resultsTable = document.getElementById('results-table');
        resultsTable.innerHTML = '';
        loadingIndicator.classList.remove('hidden');
        loadingIndicator.querySelector('p').textContent = 'Processing Data';

        // Load price guide data
        const data = await loadDataFiles();

        loadingIndicator.querySelector('p').textContent = 'Calculating item value...';

        // Get form parameters
        const params = getCalculateItemValueParameters();

        if (!params.item_name) {
            throw new Error('Item name is required');
        }

        // Call Python API
        const convertToPython = (obj) => {
            return JSON.stringify(obj)
                .replace(/\bnull\b/g, 'None')
                .replace(/\btrue\b/g, 'True')
                .replace(/\bfalse\b/g, 'False');
        };

        const result = pyodide.runPython(`
import json
from api import calculate_item_value

price_guide_data = ${convertToPython(data.price_guide)}
params = ${convertToPython(params)}

result = calculate_item_value(price_guide_data, params)
json.dumps(result)
`);

        const resultObj = JSON.parse(result);

        // Hide loading
        loadingIndicator.classList.add('hidden');

        // Check for errors
        if (resultObj.error) {
            errorDisplay.textContent = resultObj.error;
            errorDisplay.classList.remove('hidden');
            return;
        }

        // Display results
        renderItemValueResults(resultObj);
        resultsContainer.classList.remove('hidden');

    } catch (error) {
        console.error('Error calculating item value:', error);
        loadingIndicator.classList.add('hidden');
        errorDisplay.textContent = `Error: ${error.message}`;
        errorDisplay.classList.remove('hidden');
    }
}

/**
 * Initialize on page load
 */
document.addEventListener('DOMContentLoaded', () => {
    // Set up tab handlers immediately - don't wait for Pyodide
    setupTabHandlers();
    setupFormHandlers();
    setupQuestShortNameAutocompletes();

    // Initialize Pyodide in the background
    initializePyodide();
});

/**
 * Quest short-name multi-token autocomplete (space-separated tokens).
 * Used for:
 * - RBR Quest List (rbr-list / item-hunt-rbr-list)
 * - Quest Filter (quest-filter / item-hunt-quest-filter)
 */
let questShortNameAutocompleteCache = null;

/**
 * @typedef {{ shortName: string, longName: string, label: string }} QuestAutocompleteEntry
 */

/**
 * Build list of quests for autocomplete: label "Long Name (SHORT)", match on short or long name.
 * @returns {Promise<QuestAutocompleteEntry[]>}
 */
async function loadQuestShortNamesForAutocomplete() {
    if (questShortNameAutocompleteCache) return questShortNameAutocompleteCache;

    const quests = await fetchJSONWithCache(`${basePath}${DATA_FILES.quests}`);
    /** @type {Map<string, QuestAutocompleteEntry>} */
    const byShortLower = new Map();

    (quests || []).forEach((q) => {
        if (!q || !q.quest_name) return;
        const shortName = String(q.quest_name).trim();
        if (!shortName) return;
        const longName = q.long_name != null ? String(q.long_name).trim() : '';
        const k = shortName.toLowerCase();
        if (byShortLower.has(k)) return;

        const label = longName ? `${longName} (${shortName})` : shortName;
        byShortLower.set(k, { shortName, longName, label });
    });

    const list = Array.from(byShortLower.values());
    list.sort((a, b) => a.label.localeCompare(b.label));
    questShortNameAutocompleteCache = list;
    return list;
}

/**
 * Whether the current token matches short name or long name (case-insensitive).
 * @param {QuestAutocompleteEntry} entry
 * @param {string} tokenLower
 */
function questEntryMatchesToken(entry, tokenLower) {
    if (!tokenLower) return false;
    const s = entry.shortName.toLowerCase();
    const l = (entry.longName || '').toLowerCase();
    return (
        s.startsWith(tokenLower) ||
        l.startsWith(tokenLower) ||
        l.includes(tokenLower) ||
        s.includes(tokenLower)
    );
}

function parseTokensForAutocomplete(value) {
    // Split by whitespace, drop empties.
    const trimmed = (value || '').trim();
    if (!trimmed) return [];
    return trimmed.split(/\s+/).filter(Boolean);
}

function getHasTrailingSpace(value) {
    return /\s$/.test(value || '');
}

function getCurrentToken(value) {
    // The token at the end (partial allowed).
    const v = value || '';
    if (!v.trim()) return '';
    const match = v.match(/(\S*)$/);
    return match ? match[1] : '';
}

function selectSuggestionIntoInput(inputEl, suggestionValue) {
    const rawValue = inputEl.value || '';
    const parts = parseTokensForAutocomplete(rawValue);
    const hasTrailingSpace = getHasTrailingSpace(rawValue);

    // If we're currently typing the last (partial) token, replace it.
    if (!hasTrailingSpace && parts.length > 0) {
        parts.pop();
    }

    parts.push(suggestionValue);
    inputEl.value = parts.join(' ') + ' ';
}

/**
 * @param {HTMLInputElement} inputEl
 * @param {QuestAutocompleteEntry[]} suggestions
 */
function attachMultiTokenAutocomplete(inputEl, suggestions) {
    if (!inputEl) return;
    if (!Array.isArray(suggestions) || suggestions.length === 0) return;

    // Use an overlay dropdown (absolute-positioned near the input).
    const dropdown = document.createElement('div');
    dropdown.className = 'multitoken-autocomplete-dropdown hidden';
    dropdown.setAttribute('role', 'listbox');
    document.body.appendChild(dropdown);

    /** @type {QuestAutocompleteEntry[]} */
    let currentMatches = [];
    let activeIndex = -1;

    function hideDropdown() {
        dropdown.classList.add('hidden');
        dropdown.innerHTML = '';
        currentMatches = [];
        activeIndex = -1;
    }

    function positionDropdown() {
        const rect = inputEl.getBoundingClientRect();
        dropdown.style.left = (rect.left + window.scrollX) + 'px';
        dropdown.style.top = (rect.bottom + window.scrollY) + 'px';
        dropdown.style.width = rect.width + 'px';
    }

    function renderDropdown(matches) {
        dropdown.innerHTML = '';
        currentMatches = matches;
        activeIndex = matches.length ? 0 : -1;

        if (!matches.length) {
            hideDropdown();
            return;
        }

        positionDropdown();
        dropdown.classList.remove('hidden');

        matches.forEach((entry, idx) => {
            const opt = document.createElement('div');
            opt.className = 'multitoken-autocomplete-option' + (idx === activeIndex ? ' active' : '');
            opt.textContent = entry.label;
            opt.setAttribute('role', 'option');
            opt.dataset.index = String(idx);
            opt.addEventListener('mousedown', (e) => {
                e.preventDefault(); // keep input focus
                selectSuggestionIntoInput(inputEl, entry.shortName);
                hideDropdown();
                inputEl.focus();
                inputEl.dispatchEvent(new Event('input', { bubbles: true }));
            });
            dropdown.appendChild(opt);
        });
    }

    function updateMatches() {
        const rawValue = inputEl.value || '';
        const hasTrailingSpace = getHasTrailingSpace(rawValue);
        const currentToken = getCurrentToken(rawValue).toLowerCase();

        // If user already typed a space, they are ready to enter the next token.
        if (!currentToken || hasTrailingSpace) {
            hideDropdown();
            return;
        }

        const allParts = parseTokensForAutocomplete(rawValue);
        // Remove the partial token from the "already chosen" list.
        const chosenParts = hasTrailingSpace ? allParts : allParts.slice(0, Math.max(0, allParts.length - 1));
        const chosenLower = new Set(chosenParts.map(t => t.toLowerCase()));

        const matches = suggestions
            .filter((entry) => !chosenLower.has(entry.shortName.toLowerCase()))
            .filter((entry) => questEntryMatchesToken(entry, currentToken))
            .slice(0, 10);

        renderDropdown(matches);
    }

    function moveActive(delta) {
        if (!currentMatches.length) return;
        activeIndex = Math.max(0, Math.min(currentMatches.length - 1, activeIndex + delta));
        dropdown.querySelectorAll('.multitoken-autocomplete-option').forEach((el) => {
            el.classList.remove('active');
        });
        const opt = dropdown.querySelector(`.multitoken-autocomplete-option[data-index="${activeIndex}"]`);
        if (opt) opt.classList.add('active');
    }

    inputEl.addEventListener('focus', () => updateMatches());
    inputEl.addEventListener('input', () => updateMatches());

    inputEl.addEventListener('keydown', (e) => {
        if (dropdown.classList.contains('hidden')) {
            return;
        }

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            moveActive(1);
            return;
        }
        if (e.key === 'ArrowUp') {
            e.preventDefault();
            moveActive(-1);
            return;
        }
        // Tab: confirm top match (index 0) for quick entry; Shift+Tab keeps native focus move
        if (e.key === 'Tab') {
            if (e.shiftKey) {
                hideDropdown();
                return;
            }
            if (currentMatches.length > 0) {
                e.preventDefault();
                selectSuggestionIntoInput(inputEl, currentMatches[0].shortName);
                hideDropdown();
                inputEl.focus();
                inputEl.dispatchEvent(new Event('input', { bubbles: true }));
            }
            return;
        }
        if (e.key === 'Enter') {
            if (activeIndex >= 0 && currentMatches[activeIndex]) {
                e.preventDefault();
                selectSuggestionIntoInput(inputEl, currentMatches[activeIndex].shortName);
                hideDropdown();
                inputEl.focus();
            }
            return;
        }
        if (e.key === 'Escape') {
            e.preventDefault();
            hideDropdown();
            return;
        }
    });

    document.addEventListener('mousedown', (e) => {
        const target = e.target;
        if (!target) return;
        if (target === inputEl || inputEl.contains(target)) return;
        if (target === dropdown || dropdown.contains(target)) return;
        hideDropdown();
    });
}

function setupQuestShortNameAutocompletes() {
    const inputIds = ['rbr-list', 'quest-filter', 'item-hunt-rbr-list', 'item-hunt-quest-filter'];
    const inputEls = inputIds.map(id => document.getElementById(id)).filter(Boolean);
    if (!inputEls.length) return;

    loadQuestShortNamesForAutocomplete()
        .then((names) => {
            inputEls.forEach(inputEl => attachMultiTokenAutocomplete(inputEl, names));
        })
        .catch((err) => {
            console.error('Failed to initialize quest autocomplete:', err);
        });
}

