// static/js/charts.js
document.addEventListener('DOMContentLoaded', function() {
    const ctx = document.getElementById('salesChart');
    if(ctx) {
        const salesData = {{ sales_data|tojson }};
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: salesData.map(d => d.date),
                datasets: [{
                    label: 'Sales ($)',
                    data: salesData.map(d => d.sales),
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    }
});