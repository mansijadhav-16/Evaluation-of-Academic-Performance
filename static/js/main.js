// Custom JS for flash messages, form validation, etc.
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        let flashes = document.querySelectorAll('.flash');
        flashes.forEach(f => f.style.display = 'none');
    }, 4000);
});