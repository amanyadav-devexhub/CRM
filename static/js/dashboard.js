// ───────────────────────────────────────────────
// Healthcare CRM — Dashboard JS
// ───────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {

    // ── Sidebar toggle (mobile) ──
    const sidebar = document.querySelector('.sidebar');
    const menuBtn = document.querySelector('.menu-toggle');
    if (menuBtn) {
        menuBtn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    // ── Animated counters for stat cards ──
    document.querySelectorAll('.stat-value[data-target]').forEach(el => {
        const target = parseInt(el.dataset.target, 10);
        if (isNaN(target) || target === 0) {
            el.textContent = '0';
            return;
        }
        const duration = 1200;
        const step = Math.max(1, Math.ceil(target / (duration / 16)));
        let current = 0;

        const timer = setInterval(() => {
            current += step;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            el.textContent = current.toLocaleString();
        }, 16);
    });

    // ── Search filter on recent patients table ──
    const searchInput = document.querySelector('.search-box input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            document.querySelectorAll('.data-table tbody tr').forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            });
        });
    }

    // ── Close sidebar on outside click (mobile) ──
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 768 && sidebar && sidebar.classList.contains('open')) {
            if (!sidebar.contains(e.target) && !menuBtn.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        }
    });
});

// ── Drawer Management Functions ──
function openDrawer(id) {
    const drawer = document.getElementById(id);
    if (drawer) {
        drawer.style.display = 'block';
        setTimeout(() => drawer.classList.add('active'), 10);
        document.body.style.overflow = 'hidden';
    }
}

function closeDrawer(id) {
    const drawer = document.getElementById(id);
    if (drawer) {
        drawer.classList.remove('active');
        setTimeout(() => {
            drawer.style.display = 'none';
            document.body.style.overflow = '';
        }, 400);
    }
}

// Close on backdrop click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('drawer-overlay')) {
        closeDrawer(e.target.id);
    }
});
