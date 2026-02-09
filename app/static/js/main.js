// Auto-dismiss alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    var alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.transition = 'opacity 0.4s';
            alert.style.opacity = '0';
            setTimeout(function() { alert.remove(); }, 400);
        }, 5000);
    });

    // Classification level change preview
    var classSelect = document.querySelector('select[name="classification_level"]');
    if (classSelect) {
        classSelect.addEventListener('change', function() {
            var colors = {0: '#007a33', 1: '#0033a0', 2: '#c8102e', 3: '#ff8c00'};
            var val = parseInt(this.value);
            this.style.borderColor = colors[val] || '';
        });
    }
});
