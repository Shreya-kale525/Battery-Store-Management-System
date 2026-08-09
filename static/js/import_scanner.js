class BarcodeScanner {
    constructor() {
        this.scanner = null;
        this.isScanning = false;
        this.barcodeInput = document.getElementById('barcodeInput');
        this.startBtn = document.getElementById('startScanner');
        this.stopBtn = document.getElementById('stopScanner');
        this.scannerContainer = document.getElementById('scannerContainer');
        this.scannerElement = document.getElementById('scanner');
        this.statusElement = document.getElementById('scannerStatus');
        this.errorElement = document.getElementById('errorMessage');

        this.initEventListeners();
    }

    initEventListeners() {
        this.startBtn.addEventListener('click', () => this.startScanner());
        this.stopBtn.addEventListener('click', () => this.stopScanner());
        
        this.barcodeInput.addEventListener('focus', () => {
            this.barcodeInput.removeAttribute('readonly');
        });
    }

    async startScanner() {
        try {
            this.hideError();
            this.updateStatus('Starting camera...', 'info');

            if (this.scanner) {
                await this.scanner.stop();
            }

            this.scanner = new Html5Qrcode("scanner");

            const config = {
                fps: 10,
                qrbox: { width: 250, height: 250 },
                aspectRatio: 1.0,
                supportedScanTypes: [Html5QrcodeScanType.SCAN_TYPE_CAMERA],
                useBarCodeDetectorIfSupported: true
            };

            await this.scanner.start(
                { facingMode: "environment" },
                this.onScanSuccess.bind(this),
                this.onScanError.bind(this),
                config
            );

            this.isScanning = true;
            this.startBtn.style.display = 'none';
            this.stopBtn.style.display = 'inline-block';
            this.scannerContainer.style.display = 'block';
            this.updateStatus('Scanning... Point camera at barcode', 'success');

        } catch (error) {
            console.error('Scanner start error:', error);
            this.showError('Failed to start scanner: ' + this.getErrorMessage(error));
        }
    }

    stopScanner() {
        if (this.scanner && this.isScanning) {
            this.scanner.stop().then(() => {
                this.isScanning = false;
                this.startBtn.style.display = 'inline-block';
                this.stopBtn.style.display = 'none';
                this.scannerContainer.style.display = 'none';
                this.updateStatus('', '');
                this.scanner.clear();
                this.scanner = null;
            }).catch(err => {
                console.error('Stop scanner error:', err);
            });
        }
    }

    onScanSuccess(decodedText, decodedResult) {
        console.log('Barcode scanned:', decodedText);
        
        this.barcodeInput.value = decodedText;
        this.barcodeInput.removeAttribute('readonly');
        
        this.updateStatus(`✅ Barcode scanned: ${decodedText.substring(0, 20)}${decodedText.length > 20 ? '...' : ''}`, 'success');
        
        setTimeout(() => {
            this.stopScanner();
        }, 1500);
    }

    onScanError(error) {}

    updateStatus(message, type = 'info') {
        this.statusElement.textContent = message;
        this.statusElement.className = `mt-2 text-center alert alert-${type} small`;
    }

    showError(message) {
        this.errorElement.textContent = message;
        this.errorElement.style.display = 'block';
    }

    hideError() {
        this.errorElement.style.display = 'none';
    }

    getErrorMessage(error) {
        if (error === 'PERMISSION_DENIED') {
            return 'Camera access denied. Please allow camera permission.';
        } else if (error === 'NOT_FOUND') {
            return 'No camera found.';
        }
        return error?.message || 'Unknown error';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    window.barcodeScanner = new BarcodeScanner();
});