/* ============================================================
   CDMS Government UI — Enhanced JavaScript
   ============================================================ */

// === Language: apply saved preference before DOMContentLoaded to prevent flash ===
(function() {
    var lang = localStorage.getItem('cdms-lang') || 'en';
    document.documentElement.setAttribute('data-lang', lang);
    document.documentElement.setAttribute('dir', lang === 'ar' ? 'rtl' : 'ltr');
    document.documentElement.setAttribute('lang', lang);
})();

document.addEventListener('DOMContentLoaded', function() {

    // === Language toggle ===
    var langBtn = document.getElementById('langToggle');
    if (langBtn) {
        var curLang = document.documentElement.getAttribute('data-lang') || 'en';
        langBtn.textContent = curLang === 'ar' ? 'EN' : 'AR';

        langBtn.addEventListener('click', function() {
            var current = document.documentElement.getAttribute('data-lang') || 'en';
            var next = current === 'ar' ? 'en' : 'ar';
            document.documentElement.setAttribute('data-lang', next);
            document.documentElement.setAttribute('dir', next === 'ar' ? 'rtl' : 'ltr');
            document.documentElement.setAttribute('lang', next);
            localStorage.setItem('cdms-lang', next);
            this.textContent = next === 'ar' ? 'EN' : 'AR';
        });
    }

    // === Auto-dismiss alerts ===
    var alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.transition = 'opacity 0.4s';
            alert.style.opacity = '0';
            setTimeout(function() { alert.remove(); }, 400);
        }, 5000);
    });

    // === Classification level dropdown color preview ===
    var classSelect = document.querySelector('select[name="classification_level"]');
    if (classSelect) {
        classSelect.addEventListener('change', function() {
            var colors = {0: '#007a33', 1: '#0033a0', 2: '#c8102e', 3: '#ff8c00'};
            var val = parseInt(this.value);
            this.style.borderColor = colors[val] || '';
        });
    }

    // === Session timer ===
    var timerEl = document.getElementById('sessionTimer');
    if (timerEl) {
        var seconds = 0;
        setInterval(function() {
            seconds++;
            var h = Math.floor(seconds / 3600);
            var m = Math.floor((seconds % 3600) / 60);
            var s = seconds % 60;
            timerEl.textContent =
                String(h).padStart(2, '0') + ':' +
                String(m).padStart(2, '0') + ':' +
                String(s).padStart(2, '0');
        }, 1000);
    }

    // === Sidebar toggle (mobile) ===
    var sidebar = document.getElementById('sidebar');
    var toggle = document.getElementById('sidebarToggle');
    var overlay = document.getElementById('sidebarOverlay');

    if (toggle && sidebar) {
        toggle.addEventListener('click', function() {
            sidebar.classList.toggle('open');
            if (overlay) overlay.classList.toggle('active');
        });
    }
    if (overlay) {
        overlay.addEventListener('click', function() {
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
        });
    }

    // === Document filter chips ===
    var filterContainer = document.getElementById('filterChips');
    var grid = document.getElementById('documentsGrid');

    if (filterContainer && grid) {
        var chips = filterContainer.querySelectorAll('.filter-chip');
        var cards = grid.querySelectorAll('.document-card');

        chips.forEach(function(chip) {
            chip.addEventListener('click', function(e) {
                e.preventDefault();
                var filter = this.getAttribute('data-filter');

                // Update active state
                chips.forEach(function(c) { c.classList.remove('active'); });
                this.classList.add('active');

                // Filter cards
                cards.forEach(function(card) {
                    if (filter === 'all' || card.getAttribute('data-classification') === filter) {
                        card.style.display = '';
                    } else {
                        card.style.display = 'none';
                    }
                });
            });
        });
    }
});
