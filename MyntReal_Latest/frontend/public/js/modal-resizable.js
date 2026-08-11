/**
 * Universal Modal Mouse Pointer Resizer & Dragger
 * Allows users to select and drag from any border edge or corner to expand/contract modal dialogs.
 */
(function() {
    'use strict';

    // Inject CSS handles styling once
    if (!document.getElementById('modalResizerStyles')) {
        const style = document.createElement('style');
        style.id = 'modalResizerStyles';
        style.textContent = `
            .modal-resize-handle {
                position: absolute;
                z-index: 99999;
                touch-action: none;
                user-select: none;
            }
            .modal-resize-n  { top: -5px; left: 10px; right: 10px; height: 10px; cursor: ns-resize; }
            .modal-resize-s  { bottom: -5px; left: 10px; right: 10px; height: 10px; cursor: ns-resize; }
            .modal-resize-w  { left: -5px; top: 10px; bottom: 10px; width: 10px; cursor: ew-resize; }
            .modal-resize-e  { right: -5px; top: 10px; bottom: 10px; width: 10px; cursor: ew-resize; }
            .modal-resize-nw { top: -7px; left: -7px; width: 16px; height: 16px; cursor: nwse-resize; }
            .modal-resize-ne { top: -7px; right: -7px; width: 16px; height: 16px; cursor: nesw-resize; }
            .modal-resize-sw { bottom: -7px; left: -7px; width: 16px; height: 16px; cursor: nesw-resize; }
            .modal-resize-se { bottom: -7px; right: -7px; width: 16px; height: 16px; cursor: nwse-resize; }

            /* Corner affordance indicators on hover */
            .modal-resize-se::after, .modal-resize-sw::after, .modal-resize-ne::after, .modal-resize-nw::after {
                content: '';
                position: absolute;
                width: 7px;
                height: 7px;
                border-radius: 50%;
                background: rgba(148, 163, 184, 0.4);
                transition: background 0.2s, transform 0.2s;
            }
            .modal-resize-se::after { right: 3px; bottom: 3px; }
            .modal-resize-sw::after { left: 3px; bottom: 3px; }
            .modal-resize-ne::after { right: 3px; top: 3px; }
            .modal-resize-nw::after { left: 3px; top: 3px; }
            .modal-resize-handle:hover::after {
                background: #3b82f6;
                transform: scale(1.4);
            }
        `;
        document.head.appendChild(style);
    }

    window.makeModalResizableAndDraggable = function(modalEl, headerEl) {
        if (!modalEl || modalEl.dataset.resizableInit === "true") return;
        modalEl.dataset.resizableInit = "true";

        // Ensure modal positioning
        if (getComputedStyle(modalEl).position === 'static') {
            modalEl.style.position = 'relative';
        }

        const handles = ['n', 's', 'w', 'e', 'nw', 'ne', 'sw', 'se'];
        handles.forEach(dir => {
            const h = document.createElement('div');
            h.className = `modal-resize-handle modal-resize-${dir}`;
            modalEl.appendChild(h);

            h.addEventListener('mousedown', function(e) {
                e.preventDefault();
                e.stopPropagation();

                const startX = e.clientX;
                const startY = e.clientY;
                const rect = modalEl.getBoundingClientRect();
                const startWidth = rect.width;
                const startHeight = rect.height;
                const startLeft = rect.left;
                const startTop = rect.top;

                modalEl.style.margin = '0';
                modalEl.style.position = 'fixed';
                modalEl.style.left = startLeft + 'px';
                modalEl.style.top = startTop + 'px';
                modalEl.style.maxWidth = '100vw';
                modalEl.style.maxHeight = '100vh';

                function onMouseMove(me) {
                    me.preventDefault();
                    const dx = me.clientX - startX;
                    const dy = me.clientY - startY;

                    let newW = startWidth;
                    let newH = startHeight;
                    let newL = startLeft;
                    let newT = startTop;

                    if (dir.includes('e')) newW = Math.max(340, startWidth + dx);
                    if (dir.includes('s')) newH = Math.max(260, startHeight + dy);
                    if (dir.includes('w')) {
                        const candidateW = startWidth - dx;
                        if (candidateW >= 340) {
                            newW = candidateW;
                            newL = startLeft + dx;
                        }
                    }
                    if (dir.includes('n')) {
                        const candidateH = startHeight - dy;
                        if (candidateH >= 260) {
                            newH = candidateH;
                            newT = startTop + dy;
                        }
                    }

                    modalEl.style.width = newW + 'px';
                    modalEl.style.height = newH + 'px';
                    modalEl.style.left = newL + 'px';
                    modalEl.style.top = newT + 'px';

                    // Update scroll container height inside modal
                    const tableWrap = modalEl.querySelector('#edLeadTableWrap, .modal-body, .table-responsive, [id*="TableWrap"]');
                    if (tableWrap) {
                        const hH = headerEl ? headerEl.offsetHeight : 50;
                        const panel = modalEl.querySelector('#edDetailPanel, .modal-footer');
                        const pH = (panel && panel.style.display !== 'none') ? panel.offsetHeight : 0;
                        const remH = newH - hH - pH - 24;
                        if (remH > 80) {
                            tableWrap.style.maxHeight = remH + 'px';
                        }
                    }
                }

                function onMouseUp() {
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                }

                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            });
        });

        // Make header draggable to move the modal
        if (headerEl) {
            headerEl.style.cursor = 'move';
            headerEl.addEventListener('mousedown', function(e) {
                if (e.target.tagName === 'BUTTON' || e.target.tagName === 'I' || e.target.closest('button')) return;
                e.preventDefault();

                const rect = modalEl.getBoundingClientRect();
                const startLeft = rect.left;
                const startTop = rect.top;
                const startX = e.clientX;
                const startY = e.clientY;

                modalEl.style.margin = '0';
                modalEl.style.position = 'fixed';
                modalEl.style.left = startLeft + 'px';
                modalEl.style.top = startTop + 'px';

                function onHeaderMove(me) {
                    me.preventDefault();
                    const dx = me.clientX - startX;
                    const dy = me.clientY - startY;
                    modalEl.style.left = (startLeft + dx) + 'px';
                    modalEl.style.top = (startTop + dy) + 'px';
                }

                function onHeaderUp() {
                    document.removeEventListener('mousemove', onHeaderMove);
                    document.removeEventListener('mouseup', onHeaderUp);
                }

                document.addEventListener('mousemove', onHeaderMove);
                document.addEventListener('mouseup', onHeaderUp);
            });
        }
    };

    // Auto-initialize on DOM ready & dynamic modals
    function autoInitModals() {
        const modals = document.querySelectorAll('#edModal, .modal-content, [id*="Modal"]');
        modals.forEach(m => {
            if ((m.offsetWidth > 0 || m.offsetHeight > 0 || getComputedStyle(m).display !== 'none') && m.id !== 'staffSidebar') {
                const header = m.querySelector('#edModalHeader, .modal-header, [id*="Header"]');
                window.makeModalResizableAndDraggable(m, header);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', autoInitModals);
    } else {
        autoInitModals();
    }

    // Observe body for dynamically inserted or shown modals
    const observer = new MutationObserver(autoInitModals);
    observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['style', 'class'] });
})();
