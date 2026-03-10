function calculateLoan() {
    const amount = parseFloat(document.getElementById('loan-amount').value);
    const rate = parseFloat(document.getElementById('loan-rate').value) / 100 / 12;
    const years = parseFloat(document.getElementById('loan-years').value);
    const months = years * 12;

    if (isNaN(amount) || isNaN(rate) || isNaN(months) || amount <= 0 || months <= 0) {
        return;
    }

    const x = Math.pow(1 + rate, months);
    const monthly = (amount * x * rate) / (x - 1);
    const totalPayment = monthly * months;
    const totalInterest = totalPayment - amount;

    if (isFinite(monthly)) {
        document.getElementById('monthly-payment').textContent = Math.round(monthly).toLocaleString() + ' 円';
        document.getElementById('total-interest').textContent = '内利子: ' + Math.round(totalInterest).toLocaleString() + ' 円';
    }
}

// Initial calculation
window.onload = calculateLoan;
