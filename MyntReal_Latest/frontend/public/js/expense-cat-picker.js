/* DC_CATPICKER_001 — Shared Expense + Income Category Picker Utility
 * DC May 2026: Added income category support (In & Out Cat.)
 * Usage: include after staff-fetch.js, then call:
 *   ExpCatPicker.init(mainSel, subSel)            — expense only (backward-compat)
 *   ExpCatPicker.initWithBoth(mainSel, subSel)    — expense + income with optgroups
 * Quick-add: call ExpCatPicker.openQuickAdd(callback) — requires #expCatQuickAddModal in page
 */
const ExpCatPicker = (() => {
    let _cache = null;
    let _loading = null;

    async function load() {
        if (_cache) return _cache;
        if (_loading) return _loading;
        _loading = (async () => {
            try {
                const r = await staffFetch('/api/v1/expense-categories/list');
                const d = r.ok ? await r.json() : {};
                _cache = {
                    main: d.main_categories || [],
                    sub: d.sub_categories || [],
                    incMain: d.income_main_categories || [],
                    incSub: d.income_sub_categories || []
                };
                return _cache;
            } catch (e) {
                _loading = null;
                return { main: [], sub: [], incMain: [], incSub: [] };
            }
        })();
        return _loading;
    }

    function invalidate() { _cache = null; _loading = null; }

    /* ── Expense-only fill (backward compat) ── */
    function _fillMain(sel, placeholder, selectedId) {
        const cats = (_cache || { main: [] }).main;
        sel.innerHTML = `<option value="">${placeholder || '— Main Category —'}</option>`;
        cats.forEach(c => {
            const o = document.createElement('option');
            o.value = c.id;
            o.textContent = c.name;
            if (selectedId && +c.id === +selectedId) o.selected = true;
            sel.appendChild(o);
        });
    }

    /* ── Both expense + income fill (optgroups) ── */
    function _fillMainBoth(sel, placeholder, selectedVal) {
        const expCats = (_cache || {}).main || [];
        const incCats = (_cache || {}).incMain || [];
        sel.innerHTML = `<option value="">${placeholder || '— Category —'}</option>`;
        if (expCats.length > 0) {
            const eg = document.createElement('optgroup');
            eg.label = 'Expense Heads';
            expCats.forEach(c => {
                const o = document.createElement('option');
                o.value = String(c.id);
                o.textContent = c.name;
                if (selectedVal && selectedVal === String(c.id)) o.selected = true;
                eg.appendChild(o);
            });
            sel.appendChild(eg);
        }
        if (incCats.length > 0) {
            const ig = document.createElement('optgroup');
            ig.label = 'Income Heads';
            incCats.forEach(c => {
                const o = document.createElement('option');
                o.value = `inc_${c.id}`;
                o.textContent = c.name;
                if (selectedVal && selectedVal === `inc_${c.id}`) o.selected = true;
                ig.appendChild(o);
            });
            sel.appendChild(ig);
        }
    }

    /* ── Expense-only sub populate (backward compat) ── */
    function populateSub(mainSel, subSel, placeholder, selectedId) {
        const mainId = parseInt(mainSel.value);
        const subs = ((_cache || { sub: [] }).sub).filter(s => s.parent_id === mainId);
        subSel.innerHTML = `<option value="">${placeholder || '— Sub Category (optional) —'}</option>`;
        subSel.disabled = !mainId;
        if (!mainId) return;
        subs.forEach(s => {
            const o = document.createElement('option');
            o.value = s.id;
            o.textContent = s.name;
            if (selectedId && +s.id === +selectedId) o.selected = true;
            subSel.appendChild(o);
        });
    }

    /* ── Both expense + income sub populate ── */
    function populateSubBoth(mainSel, subSel, placeholder, selectedVal) {
        const rawVal = mainSel.value;
        subSel.innerHTML = `<option value="">${placeholder || '— Sub Category (optional) —'}</option>`;
        if (!rawVal) { subSel.disabled = true; return; }
        const isIncome = rawVal.startsWith('inc_');
        const mainId = isIncome ? parseInt(rawVal.replace('inc_', '')) : parseInt(rawVal);
        const pool = isIncome
            ? ((_cache || {}).incSub || []).filter(s => s.parent_id === mainId)
            : ((_cache || {}).sub || []).filter(s => s.parent_id === mainId);
        subSel.disabled = false;
        pool.forEach(s => {
            const o = document.createElement('option');
            o.value = isIncome ? `inc_${s.id}` : String(s.id);
            o.textContent = s.name;
            if (selectedVal && selectedVal === o.value) o.selected = true;
            subSel.appendChild(o);
        });
        if (pool.length === 0) subSel.disabled = true;
    }

    /* ── Init — expense only (backward compatible) ── */
    async function init(mainSel, subSel, opts) {
        opts = opts || {};
        await load();
        _fillMain(mainSel, opts.mainPlaceholder, opts.mainId);
        populateSub(mainSel, subSel, opts.subPlaceholder, opts.subId);
        mainSel.onchange = () => populateSub(mainSel, subSel, opts.subPlaceholder);
    }

    /* ── Init — expense + income (optgroups, for journal voucher) ── */
    async function initWithBoth(mainSel, subSel, opts) {
        opts = opts || {};
        await load();
        _fillMainBoth(mainSel, opts.mainPlaceholder, opts.mainVal);
        populateSubBoth(mainSel, subSel, opts.subPlaceholder, opts.subVal);
        mainSel.onchange = () => populateSubBoth(mainSel, subSel, opts.subPlaceholder);
    }

    /* ── Quick-add expense categories modal ── */
    let _ecqaCb = null;

    function _closeModal() {
        const modal = document.getElementById('expCatQuickAddModal');
        if (!modal) return;
        modal.style.display = 'none';
        modal.classList.remove('active');
    }

    function openQuickAdd(cb) {
        _ecqaCb = cb || null;
        const modal = document.getElementById('expCatQuickAddModal');
        if (!modal) { console.warn('ExpCatPicker: #expCatQuickAddModal not in page'); return; }
        document.getElementById('ecqaMainName').value = '';
        document.getElementById('ecqaSubName').value = '';
        document.getElementById('ecqaMode').value = 'sub';
        _toggleEcqaMode();
        modal.style.display = 'flex';
        modal.classList.add('active');
    }

    function _toggleEcqaMode() {
        const mode = (document.getElementById('ecqaMode') || {}).value;
        const mg = document.getElementById('ecqaMainGroup');
        const sg = document.getElementById('ecqaSubGroup');
        if (!mg || !sg) return;
        if (mode === 'main') {
            mg.style.display = '';
            sg.style.display = 'none';
        } else {
            mg.style.display = 'none';
            sg.style.display = '';
            const ps = document.getElementById('ecqaParentSel');
            if (ps) _fillMain(ps, '— Select Main Category —');
        }
    }

    async function saveQuickAdd() {
        const mode = document.getElementById('ecqaMode').value;
        const btn = document.getElementById('ecqaSaveBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving…';
        try {
            let r, d;
            if (mode === 'main') {
                const name = document.getElementById('ecqaMainName').value.trim();
                if (!name) { alert('Category name is required'); return; }
                r = await staffFetch('/api/v1/expense-categories/main/create', {
                    method: 'POST', body: JSON.stringify({ name })
                });
                d = await r.json();
            } else {
                const pid = parseInt(document.getElementById('ecqaParentSel').value);
                const name = document.getElementById('ecqaSubName').value.trim();
                if (!pid) { alert('Please select a main category'); return; }
                if (!name) { alert('Sub category name is required'); return; }
                r = await staffFetch('/api/v1/expense-categories/sub/create', {
                    method: 'POST', body: JSON.stringify({ parent_id: pid, name })
                });
                d = await r.json();
            }
            if (d && d.success) {
                invalidate();
                await load();
                _closeModal();
                if (_ecqaCb) _ecqaCb(d.category_id, mode);
            } else {
                alert((d && d.message) || 'Failed to save category');
            }
        } catch (e) {
            alert('Error: ' + e.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-save me-1"></i>Save';
        }
    }

    return {
        load, invalidate,
        init, initWithBoth,
        populateSub, populateSubBoth,
        openQuickAdd, saveQuickAdd,
        _toggleEcqaMode, _closeModal
    };
})();
