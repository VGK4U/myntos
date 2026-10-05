/**
 * Suryanz Solar - Interactive Solar Calculator Client Component
 */
document.addEventListener('DOMContentLoaded', function() {
  const calcForm = document.getElementById('suryanz-calc-form');
  if (!calcForm) return;

  const billInput = document.getElementById('calc-monthly-bill');
  const roofInput = document.getElementById('calc-roof-area');
  const typeSelect = document.getElementById('calc-customer-type');
  
  const kwDisplay = document.getElementById('res-capacity-kw');
  const genDisplay = document.getElementById('res-annual-gen');
  const savDisplay = document.getElementById('res-annual-sav');
  const payDisplay = document.getElementById('res-payback-yrs');
  const co2Display = document.getElementById('res-co2-tons');

  function calculate() {
    const monthlyBill = parseFloat(billInput ? billInput.value : 0) || 5000;
    const roofArea = parseFloat(roofInput ? roofInput.value : 0) || 500;
    const custType = typeSelect ? typeSelect.value : 'residential';
    const tariff = custType === 'commercial' ? 9.5 : 8.0;

    const monthlyKwh = monthlyBill / tariff;
    const dailyKwh = monthlyKwh / 30.0;
    
    let recommendedKw = Math.round((dailyKwh / 4.0) * 10) / 10;
    if (recommendedKw < 2.0) recommendedKw = 2.0;

    const annualGenKwh = Math.round(recommendedKw * 1450);
    const annualSavInr = Math.round(annualGenKwh * tariff);
    
    const baseCostPerKw = custType === 'commercial' ? 55000 : 62000;
    const approxCost = recommendedKw * baseCostPerKw;
    let paybackYrs = Math.round((approxCost / annualSavInr) * 10) / 10;
    if (paybackYrs < 3.2) paybackYrs = 3.2;
    if (paybackYrs > 6.5) paybackYrs = 6.2;

    const co2Tons = Math.round(((annualGenKwh * 25 * 0.9 * 0.82) / 1000.0) * 10) / 10;

    if (kwDisplay) kwDisplay.innerText = recommendedKw + ' kW';
    if (genDisplay) genDisplay.innerText = annualGenKwh.toLocaleString('en-IN') + ' kWh';
    if (savDisplay) savDisplay.innerText = '₹' + annualSavInr.toLocaleString('en-IN');
    if (payDisplay) payDisplay.innerText = paybackYrs + ' Years';
    if (co2Display) co2Display.innerText = co2Tons + ' Tons';
  }

  [billInput, roofInput, typeSelect].forEach(el => {
    if (el) {
      el.addEventListener('input', calculate);
      el.addEventListener('change', calculate);
    }
  });

  calculate();
});
