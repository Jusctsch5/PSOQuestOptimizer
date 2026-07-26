/**
 * Character Bank tool — upload .psochar/.psobank/.zip, value with price guide, cache in IndexedDB.
 */

let characterBankParsed = null;
let characterBankFileData = null;
let characterBankView = { kind: 'character', index: 0 };

function setCharacterBankStatus(message, isError = false) {
    const el = document.getElementById('character-bank-status');
    if (!el) return;
    el.textContent = message || '';
    el.classList.toggle('error-text', !!isError);
}

async function readFileAsByteArray(file) {
    const buffer = await file.arrayBuffer();
    return Array.from(new Uint8Array(buffer));
}

async function collectCharacterBankFiles(fileList) {
    const entries = [];
    for (const file of fileList) {
        const name = file.name;
        const lower = name.toLowerCase();
        if (
            !(
                lower.endsWith('.zip') ||
                lower.endsWith('.psochar') ||
                lower.endsWith('.psobank') ||
                lower.endsWith('.psoclassicbank')
            )
        ) {
            continue;
        }
        entries.push({
            filename: name,
            binary: await readFileAsByteArray(file),
        });
    }
    return entries;
}

async function parseCharacterBankViaGlobals(fileEntries) {
    if (!pyodideReady) {
        throw new Error('Pyodide is not ready yet');
    }
    if (!fileEntries || fileEntries.length === 0) {
        throw new Error('No character or bank files selected');
    }

    const data = await loadDataFiles();
    const priceStrategy =
        document.getElementById('character-bank-price-strategy')?.value || 'MINIMUM';

    // Write binaries into Pyodide FS to avoid huge JS↔Python proxy conversion
    pyodide.runPython(`
import os, shutil
upload_dir = '/tmp/char_upload'
if os.path.exists(upload_dir):
    shutil.rmtree(upload_dir)
os.makedirs(upload_dir, exist_ok=True)
`);

    const manifest = [];
    for (let i = 0; i < fileEntries.length; i++) {
        const entry = fileEntries[i];
        const safeName = `file_${i}_${entry.filename.replace(/[^\w.\- ]+/g, '_')}`;
        const path = `/tmp/char_upload/${safeName}`;
        pyodide.FS.writeFile(path, new Uint8Array(entry.binary));
        manifest.push({ filename: entry.filename, path });
    }

    const convertToPython = (obj) => {
        return JSON.stringify(obj)
            .replace(/\bnull\b/g, 'None')
            .replace(/\btrue\b/g, 'True')
            .replace(/\bfalse\b/g, 'False');
    };

    const result = pyodide.runPython(`
import json
from api import parse_character_data

manifest = ${convertToPython(manifest)}
price_guide_data = ${convertToPython(data.price_guide)}
params = ${convertToPython({ price_strategy: priceStrategy })}

file_entries = []
for item in manifest:
    with open(item['path'], 'rb') as f:
        file_entries.append({'filename': item['filename'], 'binary': list(f.read())})

result = parse_character_data(file_entries, price_guide_data, params)
json.dumps(result)
`);

    return JSON.parse(result);
}

function formatPd(value) {
    const n = Number(value) || 0;
    return n.toFixed(2);
}

function renderCharacterBankPager(result) {
    const parts = [];
    (result.characters || []).forEach((c, i) => {
        const label = `Slot ${c.slot}: ${c.name} (${formatPd(c.total_pd)} PD)`;
        parts.push(
            `<button type="button" class="character-bank-page-btn" data-kind="character" data-index="${i}">${escapeHtml(label)}</button>`
        );
    });
    (result.share_banks || []).forEach((b, i) => {
        const label = `${b.slot} (${formatPd(b.total_pd)} PD)`;
        parts.push(
            `<button type="button" class="character-bank-page-btn" data-kind="shareBank" data-index="${i}">${escapeHtml(label)}</button>`
        );
    });
    (result.all_items || []).forEach((a, i) => {
        if (!(a.inventory && a.inventory.length)) return;
        const label = `${a.slot} (${formatPd(a.total_pd)} PD)`;
        parts.push(
            `<button type="button" class="character-bank-page-btn" data-kind="allItems" data-index="${i}">${escapeHtml(label)}</button>`
        );
    });
    return `<div class="character-bank-pager">${parts.join('')}</div>`;
}

function escapeHtml(text) {
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function escapeAttr(text) {
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function dataPeekLink(type, id, label) {
    if (!id) {
        return escapeHtml(label != null ? label : '');
    }
    const display = label != null ? label : id;
    return `<button type="button" class="data-peek-link" data-peek-type="${escapeAttr(type)}" data-peek-id="${escapeAttr(id)}">${escapeHtml(display)}</button>`;
}

function itemDisplayHtml(item) {
    const display = item.display || item.name || '';
    // Prefer guide_name; fall back to name for older cached parses (except mag/disk formatted names)
    let guideName = item.guide_name;
    if (!guideName && item.name && item.type !== 5 && item.type !== 6 && item.type !== 10) {
        guideName = item.name;
    }
    // Skip meseta / undefined / unknown codes — no price-guide entry
    if (
        !guideName ||
        item.type === 10 ||
        String(guideName).startsWith('undefined.') ||
        String(guideName).startsWith('unknown.')
    ) {
        return escapeHtml(display);
    }
    return dataPeekLink('item', guideName, display);
}

function itemRowsHtml(entries) {
    if (!entries || !entries.length) {
        return '<tr><td colspan="4">No items</td></tr>';
    }
    const sorted = [...entries].sort((a, b) => {
        const pa = Number(a[1]?.price) || 0;
        const pb = Number(b[1]?.price) || 0;
        return pb - pa;
    });
    return sorted
        .map((entry) => {
            const hex = entry[0];
            const item = entry[1] || {};
            const slot = entry[2];
            const priced = item.priced !== false && item.type !== 10;
            const priceCell =
                item.type === 10
                    ? '—'
                    : priced
                      ? `${formatPd(item.price)} PD`
                      : `<span class="unpriced" title="Not in price guide">0.00 PD</span>`;
            return `<tr class="${priced || item.type === 10 ? '' : 'unpriced-row'}">
                <td class="mono">${escapeHtml(hex)}</td>
                <td>${itemDisplayHtml(item)}</td>
                <td>${escapeHtml(slot)}</td>
                <td class="num">${priceCell}</td>
            </tr>`;
        })
        .join('');
}

function renderCharacterBankSummary(result) {
    const totals = result.totals || {};
    const charCount = (result.characters || []).length;
    const bankCount = (result.share_banks || []).length;
    return `
        <div class="character-bank-summary">
            <div class="character-bank-summary-counts">
                ${charCount} character(s) · ${bankCount} bank(s)
            </div>
            <div class="character-bank-summary-totals">
                Characters <strong>${formatPd(totals.characters_pd)} PD</strong>
                · Banks <strong>${formatPd(totals.share_banks_pd)} PD</strong>
                · Combined <strong>${formatPd((totals.characters_pd || 0) + (totals.share_banks_pd || 0))} PD</strong>
            </div>
        </div>`;
}

function renderCharacterBankView() {
    const resultsTable = document.getElementById('results-table');
    if (!resultsTable || !characterBankParsed) return;

    const result = characterBankParsed;
    const { kind, index } = characterBankView;
    let headerHtml = '';
    let items = [];
    let totalPd = 0;

    if (kind === 'character' && result.characters[index]) {
        const c = result.characters[index];
        headerHtml = `
            <div class="character-bank-profile">
                <h3>${escapeHtml(c.name)} <span class="muted">Slot ${c.slot}</span></h3>
                <div class="character-bank-meta">
                    <span>${escapeHtml(c.character_class)}</span>
                    <span>${escapeHtml(c.section_id)}</span>
                    <span>Lv ${c.level}</span>
                    <span>${escapeHtml(c.mode_name)}</span>
                    <span>GC ${escapeHtml(c.guild_card_number)}</span>
                </div>
                <div class="character-bank-totals">
                    Inventory: <strong>${formatPd(c.inventory_pd)} PD</strong>
                    · Bank: <strong>${formatPd(c.bank_pd)} PD</strong>
                    · Total: <strong>${formatPd(c.total_pd)} PD</strong>
                </div>
                <div class="muted">${escapeHtml(c.ep1_progress)} · ${escapeHtml(c.ep2_progress)}</div>
            </div>`;
        items = [...(c.inventory || []), ...(c.bank || [])];
        totalPd = c.total_pd;
    } else if (kind === 'shareBank' && result.share_banks[index]) {
        const b = result.share_banks[index];
        headerHtml = `
            <div class="character-bank-profile">
                <h3>${escapeHtml(b.slot)}</h3>
                <div class="character-bank-totals">Total: <strong>${formatPd(b.total_pd)} PD</strong></div>
            </div>`;
        items = b.bank || [];
        totalPd = b.total_pd;
    } else if (kind === 'allItems' && result.all_items[index]) {
        const a = result.all_items[index];
        headerHtml = `
            <div class="character-bank-profile">
                <h3>${escapeHtml(a.slot)}</h3>
                <div class="character-bank-totals">Total: <strong>${formatPd(a.total_pd)} PD</strong></div>
            </div>`;
        items = a.inventory || [];
        totalPd = a.total_pd;
    }

    resultsTable.innerHTML = `
        <div class="character-bank-results">
            ${renderCharacterBankSummary(result)}
            ${renderCharacterBankPager(result)}
            ${headerHtml}
            <div class="character-bank-table-wrap">
                <table class="results-table character-bank-table">
                    <thead>
                        <tr>
                            <th>Code</th>
                            <th>Item</th>
                            <th>Slot</th>
                            <th class="num">PD <span class="character-bank-pd-total">(${formatPd(totalPd)})</span></th>
                        </tr>
                    </thead>
                    <tbody>${itemRowsHtml(items)}</tbody>
                </table>
            </div>
        </div>`;

    resultsTable.querySelectorAll('.character-bank-page-btn').forEach((btn) => {
        const k = btn.getAttribute('data-kind');
        const i = Number(btn.getAttribute('data-index'));
        if (k === characterBankView.kind && i === characterBankView.index) {
            btn.classList.add('active');
        }
        btn.addEventListener('click', () => {
            characterBankView = { kind: k, index: i };
            renderCharacterBankView();
        });
    });
}

async function runCharacterBankParse(fileEntries) {
    const loadingIndicator = document.getElementById('loading-indicator');
    const errorDisplay = document.getElementById('error-display');
    const resultsContainer = document.getElementById('results-container');
    const resultsTable = document.getElementById('results-table');

    resultsContainer.classList.remove('hidden');
    errorDisplay.classList.add('hidden');
    loadingIndicator.classList.remove('hidden');
    loadingIndicator.querySelector('p').textContent = 'Parsing character data...';
    resultsTable.innerHTML = '';
    setCharacterBankStatus('Parsing...');

    try {
        const result = await parseCharacterBankViaGlobals(fileEntries);
        if (result.error) {
            throw new Error(result.error);
        }
        characterBankParsed = result;
        characterBankFileData = fileEntries;
        await setCharacterBankCache(fileEntries);

        if (result.characters && result.characters.length) {
            characterBankView = { kind: 'character', index: 0 };
        } else if (result.share_banks && result.share_banks.length) {
            characterBankView = { kind: 'shareBank', index: 0 };
        } else {
            characterBankView = { kind: 'allItems', index: 0 };
        }

        loadingIndicator.classList.add('hidden');
        renderCharacterBankView();
        setCharacterBankStatus('');
    } catch (err) {
        loadingIndicator.classList.add('hidden');
        errorDisplay.textContent = err.message || String(err);
        errorDisplay.classList.remove('hidden');
        setCharacterBankStatus(err.message || String(err), true);
        throw err;
    }
}

async function restoreCharacterBankFromCache() {
    try {
        const cached = await getCharacterBankCache();
        if (!cached || !cached.length) {
            setCharacterBankStatus('No saved character data in this browser.');
            return;
        }
        setCharacterBankStatus(`Restoring ${cached.length} saved file(s)...`);
        await runCharacterBankParse(cached);
    } catch (err) {
        console.warn('Character bank restore failed:', err);
        setCharacterBankStatus('Could not restore saved data. Upload files again.', true);
    }
}

function setupCharacterBankHandlers() {
    const fileInput = document.getElementById('character-bank-files');
    const parseBtn = document.getElementById('character-bank-parse-btn');
    const clearBtn = document.getElementById('character-bank-clear-btn');

    if (!fileInput || !parseBtn || !clearBtn) return;

    parseBtn.addEventListener('click', async () => {
        try {
            let entries = characterBankFileData;
            if (fileInput.files && fileInput.files.length > 0) {
                entries = await collectCharacterBankFiles(fileInput.files);
            }
            if (!entries || !entries.length) {
                setCharacterBankStatus('Select character/bank files or a zip first.', true);
                return;
            }
            await runCharacterBankParse(entries);
        } catch (err) {
            console.error(err);
        }
    });

    fileInput.addEventListener('change', async () => {
        if (!fileInput.files || !fileInput.files.length) return;
        try {
            const entries = await collectCharacterBankFiles(fileInput.files);
            if (!entries.length) {
                setCharacterBankStatus('No valid .psochar / .psobank / .zip files found.', true);
                return;
            }
            await runCharacterBankParse(entries);
        } catch (err) {
            console.error(err);
        }
    });

    clearBtn.addEventListener('click', async () => {
        await clearCharacterBankCache();
        characterBankParsed = null;
        characterBankFileData = null;
        fileInput.value = '';
        document.getElementById('results-table').innerHTML = '';
        setCharacterBankStatus('Cleared saved character data.');
    });
}

window.setupCharacterBankHandlers = setupCharacterBankHandlers;
window.restoreCharacterBankFromCache = restoreCharacterBankFromCache;

window.onPyodideReady = function onPyodideReadyCharacterBank() {
    const activeTab = document.querySelector('.tab-btn.active')?.dataset?.tab;
    if (activeTab === 'character-bank') {
        restoreCharacterBankFromCache();
    }
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupCharacterBankHandlers);
} else {
    setupCharacterBankHandlers();
}
