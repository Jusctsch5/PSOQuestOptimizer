/**
 * Browsable quest list: left sidebar (search + list), right panel (quest detail).
 */
(function () {
    const path = window.location.pathname;
    const basePath = path.indexOf('/web/') !== -1 ? '../' : './';
    const questsUrl = basePath + 'quests/quests.json';

    let questListData = null;
    let filteredList = [];

    function escapeHtml(s) {
        const div = document.createElement('div');
        div.textContent = s;
        return div.innerHTML;
    }

    function loadQuests() {
        if (questListData && Array.isArray(questListData)) return Promise.resolve(questListData);
        if (typeof fetchJSONWithCache !== 'undefined') {
            return fetchJSONWithCache(questsUrl).then(function (raw) {
                questListData = Array.isArray(raw) ? raw : (raw && raw.quests) ? raw.quests : [];
                return questListData;
            });
        }
        return fetch(questsUrl)
            .then(function (res) {
                if (!res.ok) throw new Error(res.statusText);
                return res.json();
            })
            .then(function (raw) {
                questListData = Array.isArray(raw) ? raw : (raw && raw.quests) ? raw.quests : [];
                return questListData;
            });
    }

    function filterQuests(quests, searchStr) {
        const search = (searchStr || '').trim().toLowerCase();
        if (!search) return quests;
        return quests.filter(function (q) {
            const short = (q.quest_name || '').toLowerCase();
            const long = (q.long_name || '').toLowerCase();
            return short.indexOf(search) !== -1 || long.indexOf(search) !== -1;
        });
    }

    function renderDetail(quest) {
        const panel = document.getElementById('quest-detail-content');
        if (!panel) return;
        const name = quest.quest_name || '?';
        const long = quest.long_name || name;
        const ep = quest.episode != null ? quest.episode : 1;
        const flags = [];
        if (quest.is_in_rbr_rotation) flags.push('RBR');
        if (quest.is_event_quest) flags.push('Event');
        const flagsStr = flags.length ? ' <span class="quest-flags">' + flags.map(function (f) { return '<span class="quest-flag">' + escapeHtml(f) + '</span>'; }).join('') + '</span>' : '';

        let html = '<div class="quest-detail-header">';
        html += '<h2>' + escapeHtml(long) + ' (' + escapeHtml(name) + ')</h2>';
        html += '<p>Episode ' + ep + flagsStr + '</p>';
        html += '</div>';

        const areas = quest.areas || [];
        areas.forEach(function (a) {
            html += '<div class="quest-detail-area">';
            html += '<h3>' + escapeHtml(a.name) + '</h3>';
            if (a.enemies && Object.keys(a.enemies).length) {
                html += '<p><strong>Enemies:</strong> ' + escapeHtml(Object.keys(a.enemies).map(function (e) { return e + ': ' + a.enemies[e]; }).join(', ')) + '</p>';
            }
            if (a.boxes && Object.keys(a.boxes).length) {
                html += '<p><strong>Boxes:</strong> ' + escapeHtml(Object.keys(a.boxes).map(function (b) { return b + ': ' + a.boxes[b]; }).join(', ')) + '</p>';
            }
            html += '</div>';
        });

        const completion = quest.quest_completion_items;
        if (completion && Object.keys(completion).length) {
            html += '<div class="quest-detail-completion"><h3>Completion items</h3><p>' + escapeHtml(Object.keys(completion).map(function (k) { return k + ': ' + completion[k]; }).join(', ')) + '</p></div>';
        }

        panel.innerHTML = html;
        panel.classList.remove('quest-detail-placeholder');
    }

    function renderLeftList(container, list) {
        if (!list.length) {
            container.innerHTML = '<p class="quest-list-empty">No quests match the current filters.</p>';
            return;
        }
        filteredList = list;
        container.innerHTML = list.map(function (q, i) {
            const name = q.quest_name || '?';
            const long = q.long_name || name;
            const ep = q.episode != null ? q.episode : 1;
            return '<button type="button" class="quest-list-item" data-i="' + i + '"><strong class="quest-item-long">' + escapeHtml(long) + '</strong> <span class="quest-item-short">(' + escapeHtml(name) + ')</span> <span class="quest-item-ep">Ep' + ep + '</span></button>';
        }).join('');

        container.querySelectorAll('.quest-list-item').forEach(function (btn) {
            btn.addEventListener('click', function () {
                container.querySelectorAll('.quest-list-item').forEach(function (b) { b.classList.remove('selected'); });
                btn.classList.add('selected');
                const i = parseInt(btn.getAttribute('data-i'), 10);
                const quest = filteredList[i];
                if (quest) renderDetail(quest);
            });
        });
    }

    function applyFilters() {
        const container = document.getElementById('quest-list-container');
        const summary = document.getElementById('quest-list-summary');
        const loading = document.getElementById('quest-list-loading');
        if (!container || !questListData) return;
        const searchVal = (document.getElementById('quest-list-search') || {}).value || '';
        const filtered = filterQuests(questListData, searchVal);
        renderLeftList(container, filtered);
        if (summary) {
            summary.classList.remove('hidden');
            summary.textContent = filtered.length === questListData.length ? 'Showing ' + filtered.length + ' quest(s).' : 'Showing ' + filtered.length + ' of ' + questListData.length + ' quest(s).';
        }
        if (loading) loading.classList.add('hidden');
        document.getElementById('quest-detail-content').innerHTML = 'Select a quest from the list.';
        document.getElementById('quest-detail-content').classList.add('quest-detail-placeholder');
    }

    function showQuestList() {
        const loading = document.getElementById('quest-list-loading');
        const container = document.getElementById('quest-list-container');
        const summary = document.getElementById('quest-list-summary');
        const detailContent = document.getElementById('quest-detail-content');
        if (!container) return;
        if (loading) loading.classList.remove('hidden');
        container.innerHTML = '';
        if (summary) summary.classList.add('hidden');
        if (detailContent) {
            detailContent.innerHTML = 'Select a quest from the list.';
            detailContent.classList.add('quest-detail-placeholder');
        }
        loadQuests()
            .then(function () {
                if (!questListData || !questListData.length) {
                    container.innerHTML = '<p class="quest-list-error">No quest data loaded.</p>';
                } else {
                    applyFilters();
                }
            })
            .catch(function (err) {
                container.innerHTML = '<p class="quest-list-error">Failed to load quest list: ' + escapeHtml(err.message) + '</p>';
            })
            .then(function () {
                if (loading) loading.classList.add('hidden');
            });
    }

    function setupSectionNav() {
        const btns = document.querySelectorAll('.section-btn');
        btns.forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                const section = btn.getAttribute('data-section');
                if (!section) return;
                btns.forEach(function (b) { b.classList.remove('active'); });
                btn.classList.add('active');
                document.querySelectorAll('.section-content').forEach(function (el) { el.classList.add('hidden'); });
                const target = document.getElementById('section-' + section);
                if (target) target.classList.remove('hidden');
                if (section === 'data') showQuestList();
            });
        });
    }

    function setupDataTabs() {
        document.querySelectorAll('.data-tab-btn:not([disabled])').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                const tab = btn.getAttribute('data-data-tab') || btn.dataset.dataDataTab;
                if (!tab) return;
                document.querySelectorAll('.data-tab-btn').forEach(function (b) { b.classList.remove('active'); });
                btn.classList.add('active');
                document.querySelectorAll('.data-tab-panel').forEach(function (el) { el.classList.add('hidden'); });
                const panel = document.getElementById('data-' + tab);
                if (panel) panel.classList.remove('hidden');
                if (tab === 'quest-list') showQuestList();
            });
        });
    }

    function setupFilters() {
        const search = document.getElementById('quest-list-search');
        function apply() { if (questListData) applyFilters(); }
        if (search) search.addEventListener('input', apply);
    }

    document.addEventListener('DOMContentLoaded', function () {
        setupSectionNav();
        setupDataTabs();
        setupFilters();
    });
})();
