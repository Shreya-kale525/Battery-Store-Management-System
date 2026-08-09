// static/js/scanner.js
let html5QrcodeScanner;

function startScanner() {
    html5QrcodeScanner = new Html5QrcodeScanner(
        "reader",
        { fps: 10, qrbox: {width: 250, height: 250} },
        /* verbose= */ false);
    
    html5QrcodeScanner.render(onScanSuccess, onScanFailure);
}

function onScanSuccess(decodedText, decodedResult) {
    // Play beep sound
    let audio = new Audio('https://www.soundjay.com/buttons/beep-01a.mp3');
    audio.play();

    // Add to cart via AJAX
    fetch('/sales', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: 'barcode=' + decodedText
    })
    .then(response => response.json())
    .then(data => {
        if(data.success) {
            alert(data.message);
            location.reload(); // Reload to show new item
        } else {
            alert(data.message);
        }
    })
    .catch(error => console.error('Error:', error));
}

function onScanFailure(error) {
    // handle scan failure, usually better to ignore and keep scanning.
    // console.warn(`Code scan error = ${error}`);
}

// Initialize on load
document.addEventListener('DOMContentLoaded', startScanner);
document.getElementById("barcodeInput").addEventListener("keypress", function(e) {
    if (e.key === "Enter") {
        e.preventDefault();
        
        let barcode = this.value;

        // SAME API jo scanner use karta hai
        fetch('/sales', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: 'barcode=' + barcode
        })
        .then(response => response.json())
        .then(data => {
            if(data.success) {
                alert(data.message);
                location.reload();
            } else {
                alert(data.message);
            }
        });

        this.value = ""; // input clear
    }
});