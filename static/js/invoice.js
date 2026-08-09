// static/js/invoice.js

// Print Invoice Function
function printInvoice() {
    window.print();
}

// Download PDF Function
function downloadPDF() {
    // In production, use jsPDF or window.print() to save as PDF
    const invoiceNumber = document.getElementById('invoiceNumber').innerText;
    window.open(`/export_invoice/${invoiceNumber}`, '_blank');
}

// Format Currency
function formatCurrency(amount) {
    return '$' + parseFloat(amount).toFixed(2);
}

// Format Date
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-US', options);
}

// Initialize on load
document.addEventListener('DOMContentLoaded', function() {
    // Format all currency elements
    const currencyElements = document.querySelectorAll('.currency');
    currencyElements.forEach(el => {
        el.innerText = formatCurrency(el.innerText);
    });
    
    // Format all date elements
    const dateElements = document.querySelectorAll('.date');
    dateElements.forEach(el => {
        el.innerText = formatDate(el.innerText);
    });
});