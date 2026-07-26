/**
 * Browsable price guide: left sidebar (search + list), right panel (item detail).
 */
(function () {
    const path = window.location.pathname;
    const basePath = path.indexOf('/web/') !== -1 ? '../' : './';
    const PRICE_GUIDE_FILES = [
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
        'price_guide/data/srankweapons.json'
    ];

    let allItems = [];
    let filteredItems = [];

    function escapeHtml(s) {
        const div = document.createElement('div');
        div.textContent = s;
        return div.innerHTML;
    }

    function categoryLabel(filename) {
        const name = filename.replace('.json', '');
        return name.replace(/_/g, ' ');
    }

    function loadPriceGuide() {
        if (allItems.length) return Promise.resolve(allItems);
        const fetchOne = function (filePath) {
            const url = basePath + filePath;
            if (typeof fetchJSONWithCache !== 'undefined') {
                return fetchJSONWithCache(url);
            }
            return fetch(url).then(function (r) {
                if (!r.ok) throw new Error(r.statusText);
                return r.json();
            });
        };
        const category = function (filePath) {
            return categoryLabel(filePath.split('/').pop());
        };
        return Promise.all(PRICE_GUIDE_FILES.map(function (filePath) {
            return fetchOne(filePath)
                .then(function (data) {
                    if (!data || typeof data !== 'object') return [];
                    const cat = category(filePath);
                    const fileName = filePath.split('/').pop();
                    // srankweapons.json is { weapons: {...}, modifiers: {...} }
                    if (fileName === 'srankweapons.json' && data.weapons) {
                        const items = Object.keys(data.weapons).map(function (name) {
                            return {
                                name: name,
                                category: 'srank weapons',
                                data: data.weapons[name],
                                modifiers: data.modifiers || {},
                            };
                        });
                        if (data.modifiers) {
                            Object.keys(data.modifiers).forEach(function (name) {
                                items.push({
                                    name: name,
                                    category: 'srank modifiers',
                                    data: data.modifiers[name],
                                });
                            });
                        }
                        return items;
                    }
                    return Object.keys(data).map(function (name) {
                        return { name: name, category: cat, data: data[name] };
                    });
                })
                .catch(function () { return []; });
        })).then(function (arrays) {
            allItems = arrays.reduce(function (acc, arr) { return acc.concat(arr); }, []);
            allItems.sort(function (a, b) {
                const na = (a.name || '').toLowerCase();
                const nb = (b.name || '').toLowerCase();
                return na.localeCompare(nb);
            });
            return allItems;
        });
    }

    function filterByType(items, typeValue) {
        if (!typeValue || typeValue === '') return items;
        return items.filter(function (item) { return (item.category || '') === typeValue; });
    }

    function filterItems(items, searchStr) {
        const search = (searchStr || '').trim().toLowerCase();
        if (!search) return items;
        return items.filter(function (item) {
            return (item.name || '').toLowerCase().indexOf(search) !== -1 ||
                (item.category || '').toLowerCase().indexOf(search) !== -1;
        });
    }

    function populateTypeFilter() {
        const select = document.getElementById('price-guide-type');
        if (!select) return;
        const categories = [];
        const seen = {};
        allItems.forEach(function (item) {
            const c = item.category || '';
            if (c && !seen[c]) { seen[c] = true; categories.push(c); }
        });
        categories.sort();
        select.innerHTML = '<option value="">All types</option>' +
            categories.map(function (c) { return '<option value="' + escapeHtml(c) + '">' + escapeHtml(c) + '</option>'; }).join('');
    }

    function formatValue(v) {
        if (v === null || v === undefined) return '—';
        if (typeof v === 'object') return JSON.stringify(v);
        return String(v);
    }

    function buildItemDetailHtml(item) {
        let html = '<div class="quest-detail-header">';
        html += '<h2>' + escapeHtml(item.name) + '</h2>';
        html += '<p><strong>Category:</strong> ' + escapeHtml(item.category) + '</p>';
        html += '</div><div class="quest-detail-area">';
        const d = item.data;
        if (d && typeof d === 'object') {
            Object.keys(d).forEach(function (key) {
                const val = d[key];
                if (val !== null && typeof val === 'object' && !Array.isArray(val)) {
                    html += '<p><strong>' + escapeHtml(key) + ':</strong></p><div class="price-guide-nested"><ul>';
                    Object.keys(val).forEach(function (k) {
                        html += '<li>' + escapeHtml(k) + ': ' + escapeHtml(formatValue(val[k])) + '</li>';
                    });
                    html += '</ul></div>';
                } else {
                    html += '<p><strong>' + escapeHtml(key) + ':</strong> ' + escapeHtml(formatValue(val)) + '</p>';
                }
            });
        }
        if (item.modifiers && typeof item.modifiers === 'object') {
            html += '<p><strong>Special modifiers (add to base):</strong></p><div class="price-guide-nested"><ul>';
            Object.keys(item.modifiers).forEach(function (k) {
                const mod = item.modifiers[k];
                const base = mod && typeof mod === 'object' ? mod.base : mod;
                html += '<li>' + escapeHtml(k) + ': +' + escapeHtml(formatValue(base)) + ' PD</li>';
            });
            html += '</ul></div>';
        }
        html += '</div>';
        return html;
    }

    function renderDetail(item) {
        const panel = document.getElementById('price-guide-detail');
        if (!panel) return;
        panel.innerHTML = buildItemDetailHtml(item);
        panel.classList.remove('quest-detail-placeholder');
    }

    function findItemByName(itemName) {
        if (!itemName || !allItems.length) return null;
        const key = String(itemName).trim().toLowerCase();
        return allItems.find(function (item) {
            return (item.name || '').toLowerCase() === key;
        }) || null;
    }

    function activateDataSection() {
        document.querySelectorAll('.section-btn').forEach(function (b) { b.classList.remove('active'); });
        const dataBtn = document.querySelector('.section-btn[data-section="data"]');
        if (dataBtn) dataBtn.classList.add('active');
        document.querySelectorAll('.section-content').forEach(function (el) { el.classList.add('hidden'); });
        const section = document.getElementById('section-data');
        if (section) section.classList.remove('hidden');
    }

    function activatePriceGuideTab() {
        document.querySelectorAll('.data-tab-btn').forEach(function (b) { b.classList.remove('active'); });
        const tabBtn = document.querySelector('.data-tab-btn[data-data-tab="price-guide"]');
        if (tabBtn) tabBtn.classList.add('active');
        document.querySelectorAll('.data-tab-panel').forEach(function (el) { el.classList.add('hidden'); });
        const panel = document.getElementById('data-price-guide');
        if (panel) panel.classList.remove('hidden');
    }

    function selectItemInList(item) {
        const search = document.getElementById('price-guide-search');
        const typeSelect = document.getElementById('price-guide-type');
        if (typeSelect) typeSelect.value = '';
        if (search) search.value = item.name || '';
        applyFilters();
        const idx = filteredItems.findIndex(function (i) {
            return (i.name || '').toLowerCase() === (item.name || '').toLowerCase();
        });
        const container = document.getElementById('price-guide-container');
        if (container && idx >= 0) {
            const btn = container.querySelector('.quest-list-item[data-i="' + idx + '"]');
            if (btn) {
                btn.click();
                return;
            }
        }
        renderDetail(item);
    }

    function openItemInData(itemName) {
        return loadPriceGuide().then(function () {
            populateTypeFilter();
            const item = findItemByName(itemName);
            if (!item) return;
            activateDataSection();
            activatePriceGuideTab();
            selectItemInList(item);
        });
    }

    function renderList(container, list) {
        if (!list.length) {
            container.innerHTML = '<p class="quest-list-empty">No items match the search.</p>';
            return;
        }
        filteredItems = list;
        container.innerHTML = list.map(function (item, i) {
            return '<button type="button" class="quest-list-item" data-i="' + i + '"><strong class="quest-item-long">' + escapeHtml(item.name) + '</strong> <span class="quest-item-category">' + escapeHtml(item.category) + '</span></button>';
        }).join('');
        container.querySelectorAll('.quest-list-item').forEach(function (btn) {
            btn.addEventListener('click', function () {
                container.querySelectorAll('.quest-list-item').forEach(function (b) { b.classList.remove('selected'); });
                btn.classList.add('selected');
                const i = parseInt(btn.getAttribute('data-i'), 10);
                const item = filteredItems[i];
                if (item) renderDetail(item);
            });
        });
    }

    function applyFilters() {
        const container = document.getElementById('price-guide-container');
        const summary = document.getElementById('price-guide-summary');
        const loading = document.getElementById('price-guide-loading');
        if (!container || !allItems.length) return;
        const typeVal = (document.getElementById('price-guide-type') || {}).value || '';
        const searchVal = (document.getElementById('price-guide-search') || {}).value || '';
        let filtered = filterByType(allItems, typeVal);
        filtered = filterItems(filtered, searchVal);
        renderList(container, filtered);
        if (summary) {
            summary.classList.remove('hidden');
            const total = allItems.length;
            summary.textContent = filtered.length === total ? 'Showing ' + total + ' items.' : 'Showing ' + filtered.length + ' of ' + total + ' items.';
        }
        if (loading) loading.classList.add('hidden');
        const detail = document.getElementById('price-guide-detail');
        if (detail) {
            detail.innerHTML = 'Select an item from the list.';
            detail.classList.add('quest-detail-placeholder');
        }
    }

    function showPriceGuide() {
        const loading = document.getElementById('price-guide-loading');
        const container = document.getElementById('price-guide-container');
        const summary = document.getElementById('price-guide-summary');
        const detail = document.getElementById('price-guide-detail');
        if (!container) return;
        if (loading) loading.classList.remove('hidden');
        container.innerHTML = '';
        if (summary) summary.classList.add('hidden');
        if (detail) {
            detail.innerHTML = 'Select an item from the list.';
            detail.classList.add('quest-detail-placeholder');
        }
        loadPriceGuide()
            .then(function () {
                if (!allItems.length) {
                    container.innerHTML = '<p class="quest-list-error">No price guide data loaded.</p>';
                } else {
                    populateTypeFilter();
                    applyFilters();
                }
            })
            .catch(function (err) {
                container.innerHTML = '<p class="quest-list-error">Failed to load price guide: ' + escapeHtml(err.message) + '</p>';
            })
            .then(function () {
                if (loading) loading.classList.add('hidden');
            });
    }

    function setupSearch() {
        const search = document.getElementById('price-guide-search');
        if (search) search.addEventListener('input', function () { if (allItems.length) applyFilters(); });
        const typeSelect = document.getElementById('price-guide-type');
        if (typeSelect) typeSelect.addEventListener('change', function () { if (allItems.length) applyFilters(); });
    }

    window.showPriceGuide = showPriceGuide;
    window.PriceGuideBrowse = {
        loadPriceGuide: loadPriceGuide,
        buildItemDetailHtml: buildItemDetailHtml,
        findItemByName: findItemByName,
        openItemInData: openItemInData,
    };
    document.addEventListener('DOMContentLoaded', setupSearch);
})();
