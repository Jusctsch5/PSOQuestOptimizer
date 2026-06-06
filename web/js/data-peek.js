/**
 * Persistent docked sidebar for quest / price-guide reference while browsing.
 */
(function () {
    let peekContext = null;

    function escapeHtml(s) {
        const div = document.createElement('div');
        div.textContent = s;
        return div.innerHTML;
    }

    function getSidebar() {
        return document.getElementById('data-peek-sidebar');
    }

    function openSidebar() {
        const sidebar = getSidebar();
        if (!sidebar) {
            return;
        }
        sidebar.hidden = false;
        document.body.classList.add('data-peek-open');
    }

    function closePeek() {
        const sidebar = getSidebar();
        if (sidebar) {
            sidebar.hidden = true;
        }
        document.body.classList.remove('data-peek-open');
        peekContext = null;
    }

    function openPeek(title, html, context) {
        const titleEl = document.getElementById('data-peek-title');
        const bodyEl = document.getElementById('data-peek-body');
        const openBtn = document.getElementById('data-peek-open-data');
        if (!titleEl || !bodyEl || !openBtn) {
            return;
        }

        peekContext = context;
        titleEl.textContent = title;
        bodyEl.innerHTML = html;
        openBtn.hidden = !context || !context.openInData;
        openSidebar();
    }

    function showPeekLoading(title) {
        openPeek(title, '<p class="data-peek-loading">Loading…</p>', null);
    }

    function showPeekError(title, message) {
        openPeek(title, '<p class="data-peek-error">' + escapeHtml(message) + '</p>', null);
    }

    function peekQuest(shortName) {
        const api = window.QuestListBrowse;
        if (!api) {
            showPeekError('Quest', 'Quest data is not available.');
            return;
        }
        showPeekLoading('Quest');
        api.loadQuests()
            .then(function () {
                const quest = api.findQuestByShortName(shortName);
                if (!quest) {
                    showPeekError('Quest', 'Quest "' + shortName + '" not found.');
                    return;
                }
                const long = quest.long_name || quest.quest_name;
                openPeek(
                    long + ' (' + quest.quest_name + ')',
                    api.buildQuestDetailHtml(quest),
                    { type: 'quest', id: quest.quest_name, openInData: true },
                );
            })
            .catch(function (err) {
                showPeekError('Quest', err.message || 'Failed to load quest data.');
            });
    }

    function peekItem(itemName) {
        const api = window.PriceGuideBrowse;
        if (!api) {
            showPeekError('Item', 'Price guide is not available.');
            return;
        }
        showPeekLoading('Item');
        api.loadPriceGuide()
            .then(function () {
                const item = api.findItemByName(itemName);
                if (!item) {
                    showPeekError('Item', 'Item "' + itemName + '" not found in price guide.');
                    return;
                }
                openPeek(
                    item.name,
                    api.buildItemDetailHtml(item),
                    { type: 'item', id: item.name, openInData: true },
                );
            })
            .catch(function (err) {
                showPeekError('Item', err.message || 'Failed to load price guide.');
            });
    }

    function setupPeekSidebar() {
        const sidebar = getSidebar();
        const closeBtn = document.getElementById('data-peek-close');
        const openBtn = document.getElementById('data-peek-open-data');

        if (closeBtn) {
            closeBtn.addEventListener('click', closePeek);
        }

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && sidebar && !sidebar.hidden) {
                closePeek();
            }
        });

        if (openBtn) {
            openBtn.addEventListener('click', function () {
                if (!peekContext) {
                    return;
                }
                const ctx = peekContext;
                if (ctx.type === 'quest' && window.QuestListBrowse) {
                    window.QuestListBrowse.openQuestInData(ctx.id);
                } else if (ctx.type === 'item' && window.PriceGuideBrowse) {
                    window.PriceGuideBrowse.openItemInData(ctx.id);
                }
            });
        }

        document.addEventListener('click', function (e) {
            const btn = e.target.closest('.data-peek-link');
            if (!btn) {
                return;
            }
            e.preventDefault();
            e.stopPropagation();
            const type = btn.getAttribute('data-peek-type');
            const id = btn.getAttribute('data-peek-id');
            if (!id) {
                return;
            }
            if (type === 'quest') {
                peekQuest(id);
            } else if (type === 'item') {
                peekItem(id);
            }
        });
    }

    window.peekQuest = peekQuest;
    window.peekItem = peekItem;

    document.addEventListener('DOMContentLoaded', setupPeekSidebar);
})();
